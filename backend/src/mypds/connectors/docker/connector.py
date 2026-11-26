"""Connecteur Docker Engine — TLS mutuel natif (`dockerd --tlsverify`, port 2376), ADR-0012.

Le certificat client donne un accès complet à l'hôte Docker : MyPDS n'émet **que des lectures**
(`/version`, `/info`, `/containers/json`, `/containers/{id}/json`, `/containers/{id}/stats`).
Certificats chiffrés en base, jamais renvoyés au navigateur ; l'autorité du serveur est vérifiée.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any, ClassVar, Literal
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mypds.connectors.docker import demo as demo_data
from mypds.connectors.sdk import Capability, Connector, ConnectorError, Snapshot, TestReport, split_host
from mypds.core import net

HOST_RE = r"^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$"
API = "v1.41"  # Docker 20.10+ (compatible avec les versions plus récentes)
MAX_CONTAINERS = 100
MAX_STATS = 40  # statistiques CPU/RAM : conteneurs en marche, plafonné (une requête chacun)


class DockerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    _host = model_validator(mode="before")(classmethod(lambda cls, d: split_host(d, "port")))

    mode: Literal["live", "demo"] = "live"
    host: str | None = Field(default=None, pattern=HOST_RE)
    port: int = Field(default=2376, ge=1, le=65535)
    # Conteneurs arrêtés volontairement : pas d'alerte (comme « démarré à la demande » côté Proxmox)
    on_demand: list[str] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def _check(self) -> DockerConfig:
        if self.mode == "live" and not self.host:
            raise ValueError("Adresse de l'hôte Docker requise (ou choisissez le mode démo)")
        self.on_demand = sorted({n.strip("/") for n in self.on_demand if n.strip("/")})
        return self


class DockerSecrets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ca_pem: str | None = Field(default=None, max_length=20_000)
    cert_pem: str | None = Field(default=None, max_length=20_000)
    key_pem: str | None = Field(default=None, max_length=20_000)


def cpu_pct(stats: dict[str, Any]) -> float | None:
    """Formule de `docker stats` : part du temps CPU du conteneur sur la période, × nombre de CPU."""
    try:
        cpu, pre = stats["cpu_stats"], stats["precpu_stats"]
        d_cpu = cpu["cpu_usage"]["total_usage"] - pre["cpu_usage"]["total_usage"]
        d_sys = cpu["system_cpu_usage"] - pre.get("system_cpu_usage", 0)
        ncpu = cpu.get("online_cpus") or len(cpu["cpu_usage"].get("percpu_usage") or []) or 1
        return round(d_cpu / d_sys * ncpu * 100, 1) if d_sys > 0 and d_cpu >= 0 else 0.0
    except (KeyError, TypeError, ZeroDivisionError):
        return None


def mem(stats: dict[str, Any]) -> tuple[int | None, int | None]:
    m = stats.get("memory_stats") or {}
    usage, limit = m.get("usage"), m.get("limit")
    if not isinstance(usage, int):
        return None, limit if isinstance(limit, int) else None
    st = m.get("stats") or {}
    cache = st.get("inactive_file", st.get("total_inactive_file", st.get("cache", 0))) or 0
    return max(0, usage - cache), limit if isinstance(limit, int) else None


def build(
    version: dict[str, Any],
    info: dict[str, Any],
    containers: list[dict[str, Any]],
    details: dict[str, dict[str, Any]],
    stats: dict[str, dict[str, Any]],
    on_demand: set[str],
) -> dict[str, Any]:
    out = []
    for c in containers[:MAX_CONTAINERS]:
        cid = c.get("Id", "")
        name = (c.get("Names") or ["/?"])[0].lstrip("/")
        d = details.get(cid, {})
        st = d.get("State") or {}
        health = (st.get("Health") or {}).get("Status")  # healthy / unhealthy / starting
        s = stats.get(cid)
        used, limit = mem(s) if s else (None, None)
        labels = c.get("Labels") or {}
        out.append(
            {
                "id": cid[:12],
                "name": name,
                "image": c.get("Image"),
                "state": c.get("State"),  # running, exited, paused, restarting, created, dead
                "status": c.get("Status"),
                "health": health,
                "restart_count": d.get("RestartCount"),
                "exit_code": st.get("ExitCode") if c.get("State") != "running" else None,
                "started_at": st.get("StartedAt"),
                "project": labels.get("com.docker.compose.project"),
                "ports": sorted(
                    {
                        f"{p['PublicPort']}→{p['PrivatePort']}/{p.get('Type', 'tcp')}"
                        for p in c.get("Ports") or []
                        if p.get("PublicPort")
                    }
                ),
                "cpu_pct": cpu_pct(s) if s else None,
                "mem_used": used,
                "mem_limit": limit,
                "on_demand": name in on_demand,
            }
        )
    out.sort(key=lambda x: (x["state"] != "running", x["name"].lower()))
    return {
        "host": {
            "name": info.get("Name"),
            "docker_version": version.get("Version"),
            "api_version": version.get("ApiVersion"),
            "os": info.get("OperatingSystem"),
            "cpus": info.get("NCPU"),
            "mem_total": info.get("MemTotal"),
            "images": info.get("Images"),
        },
        "counts": {
            "total": len(out),
            "running": sum(1 for c in out if c["state"] == "running"),
            "stopped": sum(1 for c in out if c["state"] in {"exited", "dead", "created"}),
            "unhealthy": sum(1 for c in out if c["health"] == "unhealthy"),
            "restarting": sum(1 for c in out if c["state"] == "restarting"),
        },
        "containers": out,
    }


class DockerConnector(Connector):
    type_id = "docker"
    display_name = "Docker"
    capabilities: ClassVar = {Capability.STATUS, Capability.METRICS, Capability.DISCOVERY}
    config_model = DockerConfig
    secrets_model = DockerSecrets
    default_interval_s = 30

    config: DockerConfig
    secrets: DockerSecrets

    async def _get(self, path: str) -> Any:
        c, s = self.config, self.secrets
        if self.demo:
            return demo_data.api(path)
        if not (s.ca_pem and s.cert_pem and s.key_pem):
            raise ConnectorError("Certificats TLS manquants (ca.pem, cert.pem, key.pem)")
        try:
            res = await net.fetch(
                f"https://{c.host}:{c.port}/{API}{path}",
                max_bytes=8 * 1024 * 1024,
                timeout=15,
                max_redirects=0,
                allow_private=True,  # hôte fixé par un administrateur
                client_tls=net.ClientTls(s.ca_pem, s.cert_pem, s.key_pem),
            )
        except net.OutboundError as exc:
            msg = str(exc)
            if "CERTIFICATE_VERIFY_FAILED" in msg or "hostname" in msg.lower():
                msg += " — le certificat du serveur doit être signé par ce CA et contenir cette adresse (SAN)"
            raise ConnectorError(msg) from exc
        if res.status in (401, 403):
            raise ConnectorError(f"Accès refusé par Docker (HTTP {res.status}) : certificat client non reconnu")
        if res.status != 200:
            raise ConnectorError(f"Réponse inattendue de Docker (HTTP {res.status})")
        try:
            return json.loads(res.content)
        except ValueError as exc:
            raise ConnectorError("Réponse Docker illisible") from exc

    async def test(self) -> TestReport:
        try:
            snap = await self.collect()
        except ConnectorError as exc:
            return TestReport(False, str(exc))
        h, n = snap.data["host"], snap.data["counts"]
        return TestReport(
            True,
            f"Connecté à Docker {h.get('docker_version') or '?'} sur {h.get('name') or self.config.host} — "
            f"{n['running']}/{n['total']} conteneur(s) en marche",
            {"demo": self.demo},
        )

    async def collect(self) -> Snapshot:
        version = await self._get("/version")
        info = await self._get("/info")
        containers = await self._get("/containers/json?all=1")
        if not isinstance(containers, list):
            raise ConnectorError("Liste des conteneurs illisible")
        containers = containers[:MAX_CONTAINERS]

        async def detail(cid: str) -> tuple[str, dict[str, Any]]:
            try:
                return cid, await self._get(f"/containers/{quote(cid)}/json")
            except ConnectorError:
                return cid, {}

        async def stat(cid: str) -> tuple[str, dict[str, Any] | None]:
            try:
                return cid, await self._get(f"/containers/{quote(cid)}/stats?stream=false&one-shot=false")
            except ConnectorError:
                return cid, None

        ids = [c["Id"] for c in containers if c.get("Id")]
        running = [c["Id"] for c in containers if c.get("State") == "running"][:MAX_STATS]
        details = dict(await asyncio.gather(*(detail(i) for i in ids)))
        stats = {k: v for k, v in await asyncio.gather(*(stat(i) for i in running)) if v}
        data = build(version, info, containers, details, stats, set(self.config.on_demand))
        return Snapshot(fetched_at=datetime.now(UTC), data=data, demo=self.demo)
