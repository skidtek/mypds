"""Connecteur Synology DSM (ADR-0013), lecture seule.

1. **SNMP v3** (authPriv, utilisateur dédié) — MIB officielle Synology (guide « SNMP MIB Guide ») :
   système `.6574.1` (état, température, alimentation, ventilateurs, modèle, version DSM, mise à jour
   disponible, CPU et RAM), disques `.6574.2` (état, température, santé, durée de vie restante),
   stockage `.6574.3` (volumes et groupes : état, espace libre et total).
2. **Web API DSM** (facultative, compte dédié) : état des tâches Hyper Backup, si la version de DSM
   les expose (`SYNO.API.Info`) ; sinon l'information est signalée « non disponible ».
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, ClassVar, Literal
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mypds.connectors.sdk import Capability, Connector, ConnectorError, Snapshot, TestReport, split_host
from mypds.connectors.synology import demo as demo_data
from mypds.connectors.synology import snmp
from mypds.core import net

HOST_RE = r"^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$"

SYS = "1.3.6.1.4.1.6574.1"
DISK = "1.3.6.1.4.1.6574.2.1.1"
RAID = "1.3.6.1.4.1.6574.3.1.1"
SYSTEM_OIDS = {
    "status": f"{SYS}.1.0",
    "temperature": f"{SYS}.2.0",
    "power": f"{SYS}.3.0",
    "system_fan": f"{SYS}.4.1.0",
    "cpu_fan": f"{SYS}.4.2.0",
    "model": f"{SYS}.5.1.0",
    "version": f"{SYS}.5.3.0",
    "upgrade": f"{SYS}.5.4.0",
    "cpu_pct": f"{SYS}.7.1.0",
    "mem_pct": f"{SYS}.7.2.0",
    "thermal": f"{SYS}.8.0",
}
DISK_STATUS = {
    1: "normal",
    2: "initialized",
    3: "not_initialized",
    4: "partition_failed",
    5: "crashed",
    6: "disconnected",
}
DISK_HEALTH = {1: "normal", 2: "warning", 3: "critical", 4: "failing"}
RAID_BUSY = set(range(2, 11)) | {13, 14, 15, 16, 17, 18, 19, 20}  # opérations en cours (réparation, vérification…)


def raid_state(code: int | None) -> str:
    if code == 1:
        return "normal"
    if code == 11:
        return "degraded"
    if code == 12:
        return "crashed"
    if code in RAID_BUSY:
        return "busy"
    return "unknown"


class SynologyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    _host = model_validator(mode="before")(classmethod(lambda cls, d: split_host(d, "snmp_port")))

    mode: Literal["live", "demo"] = "live"
    host: str | None = Field(default=None, pattern=HOST_RE)
    snmp_port: int = Field(default=161, ge=1, le=65535)
    snmp_user: str | None = Field(default=None, max_length=64)
    snmp_auth: Literal["SHA", "SHA256", "MD5"] = "SHA"
    snmp_priv: Literal["AES", "DES"] = "AES"
    # Web API DSM (facultative) : état des sauvegardes Hyper Backup
    dsm_enabled: bool = False
    dsm_port: int = Field(default=5001, ge=1, le=65535)
    dsm_user: str | None = Field(default=None, max_length=64)
    tls_fingerprint: str | None = Field(default=None, max_length=120)
    url: str | None = Field(default=None, max_length=300)  # lien d'ouverture de DSM (clic sur la tuile)

    @model_validator(mode="after")
    def _check(self) -> SynologyConfig:
        if self.mode == "live":
            if not self.host or not self.snmp_user:
                raise ValueError("Adresse du NAS et utilisateur SNMP v3 requis (ou choisissez le mode démo)")
            if self.dsm_enabled and not self.dsm_user:
                raise ValueError("Compte DSM requis pour l'API DSM")
        if self.tls_fingerprint:
            try:
                self.tls_fingerprint = net.normalize_fingerprint(self.tls_fingerprint)
            except net.OutboundError as exc:
                raise ValueError(str(exc)) from exc
        if self.url and not self.url.startswith(("https://", "http://")):
            raise ValueError("Le lien doit commencer par https:// ou http://")
        return self


class SynologySecrets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snmp_auth_key: str | None = Field(default=None, min_length=8, max_length=128)
    snmp_priv_key: str | None = Field(default=None, min_length=8, max_length=128)
    dsm_password: str | None = Field(default=None, max_length=256)


def _int(v: Any) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def build(system: dict[str, Any], disks: dict[str, dict[int, Any]], raids: dict[str, dict[int, Any]]) -> dict[str, Any]:
    def ok(code: Any) -> bool | None:
        c = _int(code)
        return None if c is None else c == 1

    disk_list = []
    for idx, cols in sorted(disks.items(), key=lambda kv: kv[0]):
        status = DISK_STATUS.get(_int(cols.get(5)) or 0, "unknown")
        health = DISK_HEALTH.get(_int(cols.get(13)) or 0)
        disk_list.append(
            {
                "id": idx,
                "name": str(cols.get(12) or cols.get(2) or f"Disque {idx}"),
                "model": str(cols.get(3) or "").strip() or None,
                "type": str(cols.get(4) or "").strip() or None,
                "status": status,
                "health": health,
                "temperature": _int(cols.get(6)),
                "role": str(cols.get(7)) if cols.get(7) is not None else None,
                "bad_sectors": _int(cols.get(9)),
                "remain_life": _int(cols.get(11)),
            }
        )
    volumes = []
    for idx, cols in sorted(raids.items(), key=lambda kv: kv[0]):
        total = _int(cols.get(5)) or 0
        free = _int(cols.get(4)) or 0
        volumes.append(
            {
                "id": idx,
                "name": str(cols.get(2) or f"Stockage {idx}"),
                "state": raid_state(_int(cols.get(3))),
                "status_code": _int(cols.get(3)),
                "total": total,
                "used": max(0, total - free),
                "pct": round((total - free) / total, 4) if total else None,
            }
        )
    upgrade = _int(system.get("upgrade"))
    return {
        "model": str(system.get("model") or "").strip() or None,
        "version": str(system.get("version") or "").strip() or None,
        "system_ok": ok(system.get("status")),
        "power_ok": ok(system.get("power")),
        "fans_ok": None
        if ok(system.get("system_fan")) is None and ok(system.get("cpu_fan")) is None
        else (ok(system.get("system_fan")) is not False and ok(system.get("cpu_fan")) is not False),
        "thermal_ok": ok(system.get("thermal")),
        "temperature": _int(system.get("temperature")),
        "cpu_pct": _int(system.get("cpu_pct")),
        "mem_pct": _int(system.get("mem_pct")),
        "update_available": upgrade == 1 if upgrade in (1, 2) else None,
        "disks": disk_list,
        "volumes": volumes,
        "backups": None,  # renseigné par l'API DSM si activée
    }


class SynologyConnector(Connector):
    type_id = "synology"
    display_name = "Synology DSM"
    capabilities: ClassVar = {Capability.STATUS, Capability.METRICS}
    config_model = SynologyConfig
    secrets_model = SynologySecrets
    default_interval_s = 60

    config: SynologyConfig
    secrets: SynologySecrets

    async def _snmp(self) -> dict[str, Any]:
        c, s = self.config, self.secrets
        if not s.snmp_auth_key or not s.snmp_priv_key:
            raise ConnectorError("Mots de passe SNMP v3 (authentification et chiffrement) manquants")
        cred = snmp.Credentials(c.snmp_user or "", s.snmp_auth_key, s.snmp_priv_key, c.snmp_auth, c.snmp_priv)
        try:
            system = await snmp.get(c.host or "", c.snmp_port, cred, SYSTEM_OIDS)
            if all(v is None for v in system.values()):
                raise ConnectorError(
                    "Le NAS répond mais ne fournit pas la MIB Synology : SNMP est-il activé dans DSM ?"
                )
            disks = await snmp.table(c.host or "", c.snmp_port, cred, DISK)
            raids = await snmp.table(c.host or "", c.snmp_port, cred, RAID)
        except snmp.SnmpError as exc:
            raise ConnectorError(str(exc)) from exc
        return build(system, disks, raids)

    async def _dsm(self, path: str, params: dict[str, str]) -> Any:
        c = self.config
        res = await net.fetch(
            f"https://{c.host}:{c.dsm_port}/webapi/{path}?{urlencode(params)}",
            max_bytes=2 * 1024 * 1024,
            timeout=10,
            max_redirects=0,
            allow_private=True,
            tls_fingerprint=c.tls_fingerprint,
        )
        if res.status != 200:
            raise ConnectorError(f"API DSM : HTTP {res.status}")
        body = json.loads(res.content)
        if not body.get("success"):
            code = (body.get("error") or {}).get("code")
            raise ConnectorError(
                f"API DSM : erreur {code}"
                + (" (identifiants refusés ou double authentification)" if code in (400, 401, 402, 403, 404) else "")
            )
        return body.get("data")

    async def _backups(self) -> dict[str, Any]:
        """Tâches Hyper Backup, si DSM les expose. Toute absence = « non disponible », sans erreur bloquante."""
        c, s = self.config, self.secrets
        if not s.dsm_password:
            return {"available": False, "reason": "Mot de passe DSM manquant"}
        try:
            auth = await self._dsm(
                "entry.cgi",
                {
                    "api": "SYNO.API.Auth",
                    "version": "6",
                    "method": "login",
                    "account": c.dsm_user or "",
                    "passwd": s.dsm_password,
                    "session": "MyPDS",
                    "format": "sid",
                },
            )
            sid = auth["sid"]
        except (ConnectorError, net.OutboundError, KeyError, TypeError, ValueError) as exc:
            return {"available": False, "reason": str(exc)}
        try:
            info = await self._dsm(
                "entry.cgi",
                {"api": "SYNO.API.Info", "version": "1", "method": "query", "query": "SYNO.Backup.Task", "_sid": sid},
            )
            if "SYNO.Backup.Task" not in (info or {}):
                return {"available": False, "reason": "Hyper Backup non exposé par cette version de DSM"}
            data = await self._dsm(
                "entry.cgi",
                {
                    "api": "SYNO.Backup.Task",
                    "version": "1",
                    "method": "list",
                    "additional": '["last_bkp_time","last_bkp_result","next_bkp_time","is_modified","schedule"]',
                    "_sid": sid,
                },
            )
            tasks = []
            for t in (data or {}).get("task_list", [])[:30]:
                result = str(t.get("last_bkp_result") or "").lower() or None
                tasks.append(
                    {
                        "name": t.get("name") or f"Tâche {t.get('task_id')}",
                        "state": str(t.get("state") or "").lower() or None,
                        "last_result": result,
                        "ok": None if result is None else result in {"done", "success", "backingup", "none"},
                        "last_time": t.get("last_bkp_time"),
                        "next_time": t.get("next_bkp_time"),
                    }
                )
            return {"available": True, "tasks": tasks}
        except (ConnectorError, net.OutboundError, ValueError, TypeError) as exc:
            return {"available": False, "reason": str(exc)}
        finally:
            try:
                await self._dsm(
                    "entry.cgi",
                    {"api": "SYNO.API.Auth", "version": "6", "method": "logout", "session": "MyPDS", "_sid": sid},
                )
            except (ConnectorError, net.OutboundError, ValueError):
                pass

    async def test(self) -> TestReport:
        try:
            snap = await self.collect()
        except ConnectorError as exc:
            return TestReport(False, str(exc))
        d = snap.data
        msg = (
            f"Connecté à {d.get('model') or 'Synology'} ({d.get('version') or 'DSM'}) — "
            f"{len(d['disks'])} disque(s), {len(d['volumes'])} stockage(s)"
        )
        b = d.get("backups")
        if b is not None:
            msg += (
                f" ; Hyper Backup : {len(b.get('tasks', []))} tâche(s)"
                if b.get("available")
                else f" ; Hyper Backup non disponible ({b.get('reason')})"
            )
        return TestReport(True, msg, {"demo": self.demo})

    async def collect(self) -> Snapshot:
        if self.demo:
            return Snapshot(fetched_at=datetime.now(UTC), data=demo_data.snapshot(), demo=True)
        data = await self._snmp()
        if self.config.dsm_enabled:
            data["backups"] = await self._backups()
        data["url"] = self.config.url
        return Snapshot(fetched_at=datetime.now(UTC), data=data)
