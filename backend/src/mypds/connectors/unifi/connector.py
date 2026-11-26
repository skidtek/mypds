"""Connecteur UniFi Network — API officielle « Network Integration » (ADR-0014), lecture seule.

Authentification : en-tête `X-API-Key` (clé créée dans UniFi Network → Paramètres → Control Plane →
Intégrations). Base : `https://<console>/proxy/network/integration/v1`. Seules des requêtes GET sont
émises. Les données que l'API officielle n'expose pas (speedtest, latence, fournisseur d'accès,
historique de débit, alertes UniFi) sont signalées comme non disponibles.

Le format des réponses varie selon la version de l'application Network : la lecture est tolérante
(champs absents = information non affichée).
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mypds.connectors.sdk import Capability, Connector, ConnectorError, Snapshot, TestReport, split_host
from mypds.connectors.unifi import demo as demo_data
from mypds.core import net

HOST_RE = r"^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$"
BASE = "/proxy/network/integration/v1"
MAX_DEVICES = 60
# Passerelles : leur liaison montante est l'accès Internet. Selon la version de Network, le modèle est
# un code (« UDM-SE ») ou un nom complet (« UniFi Dream Machine PRO SE ») ; l'API n'a pas de capacité
# « passerelle » dédiée (une UDM ne déclare que « switching »).
GATEWAY_RE = re.compile(
    r"^(UDM|UDR|UDW|UCG|UXG|USG|EFG|UX\b)|Dream (Machine|Router|Wall)|Cloud Gateway|Security Gateway|"
    r"Next-Gen Gateway|Fortress Gateway|UniFi Express",
    re.I,
)
UNAVAILABLE = ["speedtest", "latency", "isp", "wan_history", "unifi_alerts"]


class UnifiConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    _host = model_validator(mode="before")(classmethod(lambda cls, d: split_host(d, "port")))

    mode: Literal["live", "demo"] = "live"
    host: str | None = Field(default=None, pattern=HOST_RE)
    port: int = Field(default=443, ge=1, le=65535)
    site: str | None = Field(default=None, max_length=80)  # nom du site ; vide = premier site
    tls_fingerprint: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def _check(self) -> UnifiConfig:
        if self.mode == "live" and not self.host:
            raise ValueError("Adresse de la console UniFi requise (ou choisissez le mode démo)")
        if self.tls_fingerprint:
            try:
                self.tls_fingerprint = net.normalize_fingerprint(self.tls_fingerprint)
            except net.OutboundError as exc:
                raise ValueError(str(exc)) from exc
        return self


class UnifiSecrets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_key: str | None = Field(default=None, max_length=200)


def _items(payload: Any) -> list[dict[str, Any]]:
    """Listes paginées `{data: [...]}` ou listes brutes selon la version."""
    if isinstance(payload, dict):
        payload = payload.get("data", [])
    return [x for x in payload if isinstance(x, dict)] if isinstance(payload, list) else []


def _num(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def device_kind(d: dict[str, Any]) -> str:
    feats = {str(f).lower() for f in d.get("features") or []}
    if GATEWAY_RE.search(str(d.get("model") or "")):
        return "gateway"
    if "accesspoint" in feats:
        return "ap"
    if "switching" in feats:
        return "switch"
    return "other"


def build(
    site: dict[str, Any],
    devices: list[dict[str, Any]],
    stats: dict[str, dict[str, Any]],
    clients: list[dict[str, Any]],
    app_version: str | None,
) -> dict[str, Any]:
    out_devices = []
    for d in devices[:MAX_DEVICES]:
        st = stats.get(d["id"], {})
        up = st.get("uplink") or {}
        state = str(d.get("state") or "UNKNOWN").upper()
        out_devices.append(
            {
                "id": str(d["id"]),
                "name": d.get("name") or d.get("model") or "?",
                "model": d.get("model"),
                "kind": device_kind(d),
                "state": state,
                "online": state == "ONLINE",
                "ip": d.get("ipAddress"),
                "mac": d.get("macAddress"),
                "firmware": d.get("firmwareVersion"),
                "firmware_updatable": bool(d.get("firmwareUpdatable")),
                "uptime_s": _num(st.get("uptimeSec")),
                "cpu_pct": _num(st.get("cpuUtilizationPct")),
                "mem_pct": _num(st.get("memoryUtilizationPct")),
                "tx_bps": _num(up.get("txRateBps")),
                "rx_bps": _num(up.get("rxRateBps")),
            }
        )
    order = {"gateway": 0, "switch": 1, "ap": 2, "other": 3}
    out_devices.sort(key=lambda x: (order[x["kind"]], x["name"].lower()))
    gw = next((x for x in out_devices if x["kind"] == "gateway"), None)
    kinds = [str(c.get("type") or "").upper() for c in clients]
    return {
        "site": {"id": site.get("id"), "name": site.get("name") or site.get("internalReference") or "default"},
        "app_version": app_version,
        "gateway": gw,
        # Débit Internet en direct = liaison montante de la passerelle (tx = envoi, rx = réception)
        "wan": {"down_bps": gw["rx_bps"], "up_bps": gw["tx_bps"]} if gw else None,
        "devices": out_devices,
        "counts": {
            "devices": len(out_devices),
            "online": sum(1 for x in out_devices if x["online"]),
            "offline": sum(1 for x in out_devices if not x["online"]),
            "updates": sum(1 for x in out_devices if x["firmware_updatable"]),
        },
        "clients": {
            "total": len(clients),
            "wired": kinds.count("WIRED"),
            "wireless": kinds.count("WIRELESS"),
            "vpn": kinds.count("VPN"),
        },
        "unavailable": UNAVAILABLE,
    }


class UnifiConnector(Connector):
    type_id = "unifi"
    display_name = "UniFi Network"
    capabilities: ClassVar = {Capability.STATUS, Capability.METRICS, Capability.DISCOVERY}
    config_model = UnifiConfig
    secrets_model = UnifiSecrets
    default_interval_s = 30

    config: UnifiConfig
    secrets: UnifiSecrets

    async def _get(self, path: str) -> Any:
        c = self.config
        if self.demo:
            return demo_data.api(path)
        if not self.secrets.api_key:
            raise ConnectorError("Clé API UniFi manquante")
        try:
            res = await net.fetch(
                f"https://{c.host}:{c.port}{BASE}{path}",
                max_bytes=4 * 1024 * 1024,
                timeout=10,
                max_redirects=0,
                allow_private=True,  # hôte fixé par un administrateur
                tls_fingerprint=c.tls_fingerprint,
                headers={"X-API-Key": self.secrets.api_key, "Accept": "application/json"},
            )
        except net.OutboundError as exc:
            msg = str(exc)
            if not c.tls_fingerprint and ("SSL" in msg or "CERTIFICATE" in msg):
                msg += " — certificat auto-signé ? Renseignez son empreinte SHA-256."
            raise ConnectorError(msg) from exc
        if res.status == 401:
            raise ConnectorError("Clé API refusée (HTTP 401) : vérifiez la clé d'intégration")
        if res.status == 403:
            raise ConnectorError("Accès refusé (HTTP 403) : la clé doit venir d'un compte administrateur")
        if res.status == 404:
            raise ConnectorError(
                "API d'intégration introuvable (HTTP 404) : mettez à jour l'application UniFi Network (9.0 ou plus)"
            )
        if res.status != 200:
            raise ConnectorError(f"Réponse inattendue de la console UniFi (HTTP {res.status})")
        try:
            return json.loads(res.content)
        except ValueError as exc:
            raise ConnectorError("Réponse UniFi illisible") from exc

    async def _site(self) -> dict[str, Any]:
        sites = _items(await self._get("/sites?limit=50"))
        if not sites:
            raise ConnectorError("Aucun site UniFi trouvé")
        wanted = (self.config.site or "").strip().lower()
        if wanted:
            for s in sites:
                if wanted in {str(s.get("name", "")).lower(), str(s.get("internalReference", "")).lower()}:
                    return s
            raise ConnectorError(f"Site « {self.config.site} » introuvable")
        return sites[0]

    async def test(self) -> TestReport:
        try:
            snap = await self.collect()
        except ConnectorError as exc:
            return TestReport(False, str(exc))
        d = snap.data
        version = f" {d['app_version']}" if d.get("app_version") else ""
        return TestReport(
            True,
            f"Connecté à UniFi Network{version} — site « {d['site']['name']} », "
            f"{d['counts']['online']}/{d['counts']['devices']} équipement(s) en ligne",
            {"demo": self.demo},
        )

    async def collect(self) -> Snapshot:
        try:
            info = await self._get("/info")
            app_version = info.get("applicationVersion") if isinstance(info, dict) else None
        except ConnectorError:
            app_version = None
        site = await self._site()
        sid = site["id"]
        devices = _items(await self._get(f"/sites/{sid}/devices?limit=200"))

        async def detail(d: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
            # Détail (firmware) et statistiques (uptime, CPU, RAM, débit) : facultatifs
            try:
                full = await self._get(f"/sites/{sid}/devices/{d['id']}")
            except ConnectorError:
                full = {}
            try:
                st = await self._get(f"/sites/{sid}/devices/{d['id']}/statistics/latest")
            except ConnectorError:
                st = {}
            return {**d, **(full if isinstance(full, dict) else {})}, (st if isinstance(st, dict) else {})

        pairs = await asyncio.gather(*(detail(d) for d in devices[:MAX_DEVICES] if d.get("id")))
        full_devices = [p[0] for p in pairs]
        stats = {str(p[0]["id"]): p[1] for p in pairs}
        try:
            clients = _items(await self._get(f"/sites/{sid}/clients?limit=1000"))
        except ConnectorError:
            clients = []
        return Snapshot(
            fetched_at=datetime.now(UTC), data=build(site, full_devices, stats, clients, app_version), demo=self.demo
        )
