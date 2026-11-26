"""Cycle de vie des instances : chargement (secrets déchiffrés), collecte isolée, cache du dernier état.

Chaque collecte a un délai maximal ; une instance en échec passe « degraded » puis « error » avec
un intervalle qui s'allonge (backoff), sans jamais bloquer les autres ni l'application.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.connectors.models import ConnectorInstance
from mypds.connectors.sdk import Connector, ConnectorError, Snapshot, readable, registry
from mypds.core import crypto
from mypds.core.db import sessionmaker, utcnow

log = logging.getLogger("mypds.connectors")
COLLECT_TIMEOUT_S = 20
MAX_BACKOFF_S = 600


def secrets_context(instance_id: object) -> str:
    return f"connector_instance:{instance_id}:secrets"


def load_secrets(row: ConnectorInstance) -> dict:
    if not row.secrets_enc:
        return {}
    return json.loads(crypto.decrypt(row.secrets_enc, secrets_context(row.id)))


def store_secrets(row: ConnectorInstance, secrets: dict) -> None:
    clean = {k: v for k, v in secrets.items() if v}
    row.secrets_enc = crypto.encrypt(json.dumps(clean), secrets_context(row.id)) if clean else None


def instantiate(row: ConnectorInstance) -> Connector:
    cls = registry().get(row.type)
    if cls is None:
        raise ConnectorError(f"Type de connecteur inconnu : {row.type}")
    try:
        config = cls.config_model.model_validate(row.config)
        secrets = cls.secrets_model.model_validate(load_secrets(row))
    except (ValidationError, ValueError) as exc:
        raise ConnectorError(f"Configuration invalide : {readable(exc)}") from exc
    return cls(str(row.id), config, secrets)


@dataclass(slots=True)
class CacheEntry:
    snapshot: Snapshot | None = None
    failures: int = 0
    next_at: datetime | None = None
    error: str | None = None


_cache: dict[str, CacheEntry] = {}


def cached(instance_id: str) -> CacheEntry:
    return _cache.setdefault(instance_id, CacheEntry())


def forget(instance_id: str) -> None:
    _cache.pop(instance_id, None)


async def collect_one(db: AsyncSession, row: ConnectorInstance) -> CacheEntry:
    from mypds.alerts.engine import evaluate  # import local : les alertes dépendent des connecteurs

    entry = cached(str(row.id))
    try:
        snap = await asyncio.wait_for(instantiate(row).collect(), timeout=COLLECT_TIMEOUT_S)
    except (ConnectorError, TimeoutError, crypto.SecretKeyError) as exc:
        entry.failures += 1
        entry.error = "Délai dépassé" if isinstance(exc, TimeoutError) else str(exc)
        delay = min(MAX_BACKOFF_S, row.poll_interval_s * 2 ** min(entry.failures, 6))
        entry.next_at = utcnow() + timedelta(seconds=delay)
        row.status = "degraded" if entry.failures < 3 else "error"
        row.last_error = entry.error[:500]
        log.info("Connector %s failing (%s): %s", row.id, entry.failures, entry.error)
        await evaluate(db, row, None, entry.error, entry.failures)
    else:
        entry.snapshot, entry.failures, entry.error = snap, 0, None
        entry.next_at = utcnow() + timedelta(seconds=row.poll_interval_s)
        row.status, row.last_ok_at, row.last_error = "ok", utcnow(), None
        await evaluate(db, row, snap.data, None, 0)
    await db.commit()
    return entry


async def tick() -> None:
    """Appelé par le planificateur : collecte les instances arrivées à échéance."""
    async with sessionmaker()() as db:
        rows = (await db.scalars(select(ConnectorInstance).where(ConnectorInstance.enabled.is_(True)))).all()
        now = utcnow()
        due = [r for r in rows if (cached(str(r.id)).next_at or now) <= now]
        for row in due:
            await collect_one(db, row)


class ConnectorLoop:
    """Boucle dédiée (cadence plus rapide que RSS/ICS)."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None

    async def _run(self) -> None:
        await asyncio.sleep(2)
        while True:
            try:
                await tick()
            except Exception:  # noqa: BLE001 - la boucle ne doit jamais s'arrêter
                log.exception("Connector loop error")
            await asyncio.sleep(5)

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="mypds-connectors")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()


loop = ConnectorLoop()
