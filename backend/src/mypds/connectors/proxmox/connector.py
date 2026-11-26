"""Connecteur Proxmox VE (API REST officielle /api2/json), lecture seule.

Authentification par jeton API dédié (rôle PVEAuditor) :
  Authorization: PVEAPIToken=<utilisateur@realm!jeton>=<secret>
Endpoints utilisés : /cluster/status, /cluster/resources, /nodes/{node}/rrddata,
/nodes/{node}/{qemu|lxc}/{vmid}/rrddata.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mypds.connectors.proxmox import demo as demo_data
from mypds.connectors.sdk import Capability, Connector, ConnectorError, Snapshot, TestReport, split_host
from mypds.core import net

HOST_RE = r"^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$"
TOKEN_RE = r"^[A-Za-z0-9._-]+@[A-Za-z0-9._-]+![A-Za-z0-9._-]+$"  # noqa: S105 - motif, pas un secret
NODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,62}$")
TIMEFRAMES = {"hour", "day", "week", "month", "year"}


class ProxmoxConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    _host = model_validator(mode="before")(classmethod(lambda cls, d: split_host(d, "port")))

    mode: Literal["live", "demo"] = "live"
    host: str | None = Field(default=None, pattern=HOST_RE)
    port: int = Field(default=8006, ge=1, le=65535)
    token_id: str | None = Field(default=None, pattern=TOKEN_RE)
    tls_fingerprint: str | None = Field(default=None, max_length=120)
    verify_tls: bool = True
    # Invités démarrés à la demande : leur arrêt n'est pas une anomalie (option « Ignorer »)
    on_demand: list[str] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def _live_needs_target(self) -> ProxmoxConfig:
        for g in self.on_demand:
            if not re.fullmatch(r"(qemu|lxc)/\d{1,9}", g):
                raise ValueError(f"Invité invalide : {g}")
        self.on_demand = sorted(set(self.on_demand))
        if self.mode == "live" and (not self.host or not self.token_id):
            raise ValueError("Hôte et identifiant de jeton requis (ou choisissez le mode démo)")
        if self.tls_fingerprint:
            try:
                self.tls_fingerprint = net.normalize_fingerprint(self.tls_fingerprint)
            except net.OutboundError as exc:
                raise ValueError(str(exc)) from exc
        return self


class ProxmoxSecrets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token_secret: str | None = Field(default=None, max_length=200)


def _pct(used: float, total: float) -> float | None:
    return round(used / total, 4) if total else None


TASK_LABELS = {
    "vzdump": "Sauvegarde",
    "qmstart": "Démarrage VM",
    "qmstop": "Arrêt VM",
    "qmshutdown": "Extinction VM",
    "qmreboot": "Redémarrage VM",
    "vzstart": "Démarrage LXC",
    "vzstop": "Arrêt LXC",
    "vzshutdown": "Extinction LXC",
    "vzreboot": "Redémarrage LXC",
    "qmigrate": "Migration VM",
    "vzmigrate": "Migration LXC",
    "qmclone": "Clonage VM",
    "vzcreate": "Création LXC",
    "qmcreate": "Création VM",
    "aptupdate": "Mise à jour des paquets",
    "startall": "Démarrage des invités",
    "stopall": "Arrêt des invités",
    "imgcopy": "Copie d'image",
    "download": "Téléchargement",
}


def summarize_tasks(tasks: list[dict[str, Any]], names: dict[str, str], limit: int = 40) -> list[dict[str, Any]]:
    """Dernières tâches terminées ou en cours, les plus récentes d'abord."""
    out = []
    for t in sorted(tasks, key=lambda t: t.get("starttime") or 0, reverse=True)[:limit]:
        status = t.get("status")
        ttype = t.get("type") or "task"
        target = str(t.get("id") or "")
        name = names.get(target, "")
        out.append(
            {
                "upid": t.get("upid"),
                "type": ttype,
                "label": TASK_LABELS.get(ttype, ttype),
                "target": target,
                "target_name": name,
                "node": t.get("node"),
                "user": t.get("user"),
                "start": t.get("starttime"),
                "end": t.get("endtime"),
                "state": "running"
                if not t.get("endtime")
                else ("ok" if status == "OK" else "warning" if str(status).startswith("WARNINGS") else "error"),
                "status": status,
            }
        )
    return out


def build_summary(status: list[dict[str, Any]], resources: list[dict[str, Any]]) -> dict[str, Any]:
    """Assemble la vue « Résumé » (équivalent du Summary Proxmox, sans la souscription)."""
    cluster = next((s for s in status if s.get("type") == "cluster"), None)
    node_status = {s["name"]: s for s in status if s.get("type") == "node"}
    nodes_res = [r for r in resources if r.get("type") == "node"]
    guests = [r for r in resources if r.get("type") in ("qemu", "lxc") and not r.get("template")]
    storages = [r for r in resources if r.get("type") == "storage" and r.get("status", "available") == "available"]

    nodes = []
    for r in sorted(nodes_res, key=lambda n: n.get("node", "")):
        name = r.get("node", "")
        online = r.get("status") == "online" or bool(node_status.get(name, {}).get("online"))
        mine = [g for g in guests if g.get("node") == name]
        nodes.append(
            {
                "name": name,
                "online": online,
                "ip": node_status.get(name, {}).get("ip"),
                "cpu": r.get("cpu"),
                "maxcpu": r.get("maxcpu"),
                "mem": r.get("mem"),
                "maxmem": r.get("maxmem"),
                "disk": r.get("disk"),
                "maxdisk": r.get("maxdisk"),
                "uptime": r.get("uptime"),
                "vms": sum(1 for g in mine if g["type"] == "qemu"),
                "lxcs": sum(1 for g in mine if g["type"] == "lxc"),
            }
        )
    online = [n for n in nodes if n["online"]]

    # Stockage : un stockage partagé n'est compté qu'une fois (évite le double comptage)
    seen_shared: set[str] = set()
    disk_used = disk_total = 0
    for s in storages:
        if s.get("shared"):
            if s.get("storage") in seen_shared:
                continue
            seen_shared.add(s.get("storage"))
        disk_used += s.get("disk") or 0
        disk_total += s.get("maxdisk") or 0

    cpus = sum(n["maxcpu"] or 0 for n in online)
    cpu_used = sum((n["cpu"] or 0) * (n["maxcpu"] or 0) for n in online)
    mem_used = sum(n["mem"] or 0 for n in online)
    mem_total = sum(n["maxmem"] or 0 for n in online)

    def count(t: str, running: bool) -> int:
        return sum(1 for g in guests if g["type"] == t and (g.get("status") == "running") == running)

    quorate = bool(cluster.get("quorate")) if cluster else None
    if not nodes:
        health = "unknown"
    elif len(online) < len(nodes) or quorate is False:
        health = "warning" if online else "down"
    else:
        health = "ok"
    return {
        "cluster": {
            "name": cluster.get("name") if cluster else (nodes[0]["name"] if nodes else None),
            "standalone": cluster is None,
            "quorate": quorate,
            "nodes_online": len(online),
            "nodes_total": len(nodes),
            "health": health,
        },
        "guests": {
            "vm_running": count("qemu", True),
            "vm_stopped": count("qemu", False),
            "lxc_running": count("lxc", True),
            "lxc_stopped": count("lxc", False),
        },
        "resources": {
            "cpu": _pct(cpu_used, cpus),
            "cpus": cpus,
            "mem_used": mem_used,
            "mem_total": mem_total,
            "mem": _pct(mem_used, mem_total),
            "disk_used": disk_used,
            "disk_total": disk_total,
            "disk": _pct(disk_used, disk_total),
        },
        "nodes": nodes,
        "storages": [
            {
                "storage": st.get("storage"),
                "node": None if st.get("shared") else st.get("node"),
                "shared": bool(st.get("shared")),
                "used": st.get("disk") or 0,
                "total": st.get("maxdisk") or 0,
            }
            for st in {
                (st.get("storage") if st.get("shared") else f"{st.get('node')}/{st.get('storage')}"): st
                for st in storages
            }.values()
        ],
        "guest_list": [
            {
                "id": g["id"],
                "vmid": g.get("vmid"),
                "type": g["type"],
                "name": g.get("name") or f"{g['type']}/{g.get('vmid')}",
                "node": g.get("node"),
                "status": g.get("status", "unknown"),
                "cpu": g.get("cpu"),
                "maxcpu": g.get("maxcpu"),
                "mem": g.get("mem"),
                "maxmem": g.get("maxmem"),
                "uptime": g.get("uptime"),
                "tags": [t for t in re.split(r"[;, ]", g.get("tags") or "") if t],
            }
            for g in sorted(guests, key=lambda g: g.get("vmid") or 0)
        ],
    }


class ProxmoxConnector(Connector):
    type_id = "proxmox"
    display_name = "Proxmox VE"
    capabilities: ClassVar = {Capability.STATUS, Capability.METRICS, Capability.HISTORY, Capability.DISCOVERY}
    config_model = ProxmoxConfig
    secrets_model = ProxmoxSecrets
    default_interval_s = 15

    config: ProxmoxConfig
    secrets: ProxmoxSecrets

    async def _get(self, path: str) -> Any:
        c = self.config
        if self.demo:
            return demo_data.api(path)
        if not self.secrets.token_secret:
            raise ConnectorError("Secret du jeton API manquant")
        url = f"https://{c.host}:{c.port}/api2/json{path}"
        try:
            res = await net.fetch(
                url,
                max_bytes=8 * 1024 * 1024,
                timeout=10,
                max_redirects=0,
                allow_private=True,  # hôte fixé par un administrateur (politique « infrastructure »)
                tls_fingerprint=c.tls_fingerprint,
                headers={"Authorization": f"PVEAPIToken={c.token_id}={self.secrets.token_secret}"},
            )
        except net.OutboundError as exc:
            msg = str(exc)
            if not c.tls_fingerprint and ("SSL" in msg or "CERTIFICATE" in msg or "ConnectError" in msg):
                msg += " — certificat auto-signé ? Renseignez son empreinte SHA-256."
            raise ConnectorError(msg) from exc
        if res.status == 401:
            raise ConnectorError("Jeton refusé (HTTP 401) : vérifiez l'identifiant et le secret")
        if res.status == 403:
            raise ConnectorError("Droits insuffisants (HTTP 403) : le jeton doit avoir le rôle PVEAuditor sur /")
        if res.status != 200:
            raise ConnectorError(f"Réponse inattendue de Proxmox (HTTP {res.status})")
        try:
            return json.loads(res.content)["data"]
        except (ValueError, KeyError) as exc:
            raise ConnectorError("Réponse Proxmox illisible") from exc

    async def test(self) -> TestReport:
        try:
            version = await self._get("/version")
            snap = await self.collect()
        except ConnectorError as exc:
            return TestReport(False, str(exc))
        c = snap.data["cluster"]
        return TestReport(
            True,
            f"Connecté à Proxmox VE {version.get('version', '?')} — "
            f"{c['nodes_online']}/{c['nodes_total']} nœud(s) en ligne",
            {"cluster": c["name"], "demo": self.demo},
        )

    async def collect(self) -> Snapshot:
        status = await self._get("/cluster/status")
        resources = await self._get("/cluster/resources")
        data = build_summary(status, resources)
        on_demand = set(self.config.on_demand)
        for g in data["guest_list"]:
            g["on_demand"] = g["id"] in on_demand
        names = {str(g["vmid"]): g["name"] for g in data["guest_list"]}
        try:
            data["tasks"] = summarize_tasks(await self._get("/cluster/tasks"), names)
        except ConnectorError:  # les tâches sont un complément : leur absence ne bloque pas l'état
            data["tasks"] = []
        return Snapshot(fetched_at=datetime.now(UTC), data=data, demo=self.demo)

    async def history(self, resource: str, timeframe: str) -> list[dict[str, Any]]:
        """`resource` : « node/<nom> » ou « <qemu|lxc>/<vmid>@<nœud> »."""
        if timeframe not in TIMEFRAMES:
            raise ConnectorError("Période inconnue")
        m_node = re.fullmatch(r"node/([A-Za-z0-9-]{1,63})", resource)
        m_guest = re.fullmatch(r"(qemu|lxc)/(\d{1,9})@([A-Za-z0-9-]{1,63})", resource)
        if m_node:
            path = f"/nodes/{m_node.group(1)}/rrddata"
        elif m_guest:
            kind, vmid, node = m_guest.groups()
            path = f"/nodes/{node}/{kind}/{vmid}/rrddata"
        else:
            raise ConnectorError("Ressource invalide")
        rows = await self._get(f"{path}?timeframe={timeframe}&cf=AVERAGE")
        out = []
        for r in rows or []:
            mem_total = r.get("memtotal") or r.get("maxmem")
            mem_used = r.get("memused") if r.get("memused") is not None else r.get("mem")
            out.append(
                {
                    "t": r.get("time"),
                    "cpu": r.get("cpu"),
                    "mem": (mem_used / mem_total) if mem_used is not None and mem_total else None,
                    "netin": r.get("netin"),
                    "netout": r.get("netout"),
                }
            )
        return out
