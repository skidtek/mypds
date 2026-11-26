"""Contrat commun des connecteurs (ADR-0007).

Un connecteur déclare ses capacités, ses schémas de configuration (non secrète) et de secrets,
puis implémente `test()` et `collect()`. Le cœur ne connaît aucun équipement : il découvre les
connecteurs par le point d'entrée Python `mypds.connectors` (plus les connecteurs intégrés).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from importlib.metadata import entry_points
from typing import Any, ClassVar
from urllib.parse import urlsplit

from pydantic import BaseModel

log = logging.getLogger("mypds.connectors")
SDK_VERSION = 1


class Capability(StrEnum):
    STATUS = "status"
    METRICS = "metrics"
    HISTORY = "history"
    DISCOVERY = "discovery"
    CONTROL = "control"  # pilotage : non activé à l'étape B (lecture seule)


class ConnectorError(Exception):
    """Erreur lisible par l'utilisateur (connexion, droits, réponse inattendue)."""


@dataclass(slots=True)
class TestReport:
    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Snapshot:
    """Dernier état collecté. `demo=True` : données fictives, toujours signalées à l'écran."""

    fetched_at: datetime
    data: dict[str, Any]
    demo: bool = False


class Connector:
    type_id: ClassVar[str]
    display_name: ClassVar[str]
    sdk_version: ClassVar[int] = SDK_VERSION
    capabilities: ClassVar[set[Capability]]
    config_model: ClassVar[type[BaseModel]]
    secrets_model: ClassVar[type[BaseModel]]
    default_interval_s: ClassVar[int] = 30

    def __init__(self, instance_id: str, config: BaseModel, secrets: BaseModel) -> None:
        self.instance_id = instance_id
        self.config = config
        self.secrets = secrets

    @property
    def demo(self) -> bool:
        return bool(getattr(self.config, "mode", "live") == "demo")

    async def test(self) -> TestReport:
        raise NotImplementedError

    async def collect(self) -> Snapshot:
        raise NotImplementedError

    async def history(self, resource: str, timeframe: str) -> list[dict[str, Any]]:
        raise ConnectorError("Historique non disponible pour ce connecteur")


def split_host(data: Any, port_key: str = "port") -> Any:
    """Accepte une adresse collée sous forme d'URL (« https://192.168.0.1:8443/ ») : garde l'hôte,
    et reprend le port s'il y figure. Validateur « before » partagé par les configurations."""
    if not isinstance(data, dict) or not isinstance(data.get("host"), str):
        return data
    raw = data["host"].strip()
    if "://" not in raw and "/" not in raw and raw.count(":") != 1:
        return {**data, "host": raw}
    parsed = urlsplit(raw if "://" in raw else f"//{raw}")
    out = {**data, "host": parsed.hostname or raw}
    try:
        port = parsed.port
    except ValueError:
        port = None
    if port:
        out[port_key] = port
    return out


FIELD_LABELS = {
    "host": "Adresse",
    "port": "Port",
    "snmp_port": "Port SNMP",
    "dsm_port": "Port DSM",
    "token_id": "Identifiant du jeton",
    "site": "Site",
    "snmp_user": "Utilisateur SNMP",
    "tls_fingerprint": "Empreinte",
    "url": "Lien",
}


def readable(exc: Exception) -> str:
    """Erreurs de validation en français lisible (au lieu du détail technique de pydantic)."""
    from pydantic import ValidationError

    if not isinstance(exc, ValidationError):
        return str(exc)
    parts = []
    for e in exc.errors():
        field = str(e["loc"][-1]) if e.get("loc") else ""
        label = FIELD_LABELS.get(field, field)
        if field == "host" and e["type"] == "string_pattern_mismatch":
            parts.append("Adresse invalide : indiquez seulement l'IP ou le nom (ex. 192.168.0.1)")
        elif e["type"] == "value_error":
            parts.append(str(e.get("ctx", {}).get("error") or e["msg"]))
        elif e["type"] == "string_too_short":
            parts.append(f"{label} : trop court ({e.get('ctx', {}).get('min_length')} caractères minimum)")
        else:
            parts.append(f"{label} : valeur invalide" if label else e["msg"])
    return " ; ".join(parts)


_REGISTRY: dict[str, type[Connector]] = {}


def register(cls: type[Connector]) -> type[Connector]:
    if cls.sdk_version != SDK_VERSION:
        log.warning("Connector %s skipped: SDK %s expected", cls.type_id, SDK_VERSION)
        return cls
    _REGISTRY[cls.type_id] = cls
    return cls


def registry() -> dict[str, type[Connector]]:
    if not _REGISTRY:
        # Connecteurs intégrés
        from mypds.connectors.docker.connector import DockerConnector
        from mypds.connectors.proxmox.connector import ProxmoxConnector
        from mypds.connectors.synology.connector import SynologyConnector
        from mypds.connectors.unifi.connector import UnifiConnector

        for cls in (ProxmoxConnector, UnifiConnector, SynologyConnector, DockerConnector):
            register(cls)
        for ep in entry_points(group="mypds.connectors"):
            try:
                register(ep.load())
            except Exception:  # noqa: BLE001 - un connecteur tiers défaillant ne bloque pas le cœur
                log.exception("Connector %s could not be loaded", ep.name)
    return _REGISTRY
