"""Synchronise les alertes en base avec les conditions observées à chaque collecte."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.alerts.models import Alert
from mypds.alerts.rules import Candidate, CpuHistory, docker_rules, proxmox_rules, synology_rules, unifi_rules
from mypds.connectors.models import ConnectorInstance
from mypds.core.db import utcnow

cpu_history = CpuHistory()
CONNECTOR_DOWN_AFTER = 2  # échecs consécutifs avant d'alerter (évite les faux positifs ponctuels)


def candidates_for(
    row: ConnectorInstance,
    data: dict | None,
    error: str | None,
    failures: int,
    settings=None,  # noqa: ANN001
) -> list[Candidate]:
    if data is None:
        if error and failures >= CONNECTOR_DOWN_AFTER:
            return [
                Candidate(
                    "connector",
                    "connector",
                    "critical",
                    f"{row.name} injoignable",
                    error[:300],
                    params={"name": row.name},
                )
            ]
        return []
    if row.type == "proxmox":
        return proxmox_rules(data, cpu_history, str(row.id), settings=settings)
    if row.type == "unifi":
        return unifi_rules(data)
    if row.type == "synology":
        return synology_rules(data, settings)
    if row.type == "docker":
        return docker_rules(data)
    return []


async def evaluate(
    db: AsyncSession, row: ConnectorInstance, data: dict | None, error: str | None, failures: int
) -> None:
    """Ouvre, met à jour ou résout les alertes du connecteur. Ne valide pas la transaction."""
    from mypds.alerts.settings import load

    current = {c.key: c for c in candidates_for(row, data, error, failures, await load(db))}
    if data is None and failures < CONNECTOR_DOWN_AFTER:
        return  # erreur ponctuelle : on garde l'état précédent
    firing = {
        a.key: a
        for a in (await db.scalars(select(Alert).where(Alert.connector_id == row.id, Alert.state == "firing"))).all()
    }
    now = utcnow()
    for key, c in current.items():
        a = firing.get(key)
        if a is None:
            db.add(
                Alert(
                    connector_id=row.id,
                    key=key,
                    kind=c.kind,
                    resource=c.resource,
                    severity=c.severity,
                    title=c.title,
                    detail=c.detail,
                    params=c.params,
                    started_at=now,
                    last_seen_at=now,
                )
            )
        else:
            a.severity, a.title, a.detail, a.last_seen_at = c.severity, c.title, c.detail, now
            a.params = c.params
    # Connecteur injoignable : les autres alertes restent ouvertes (état inconnu, pas résolu)
    if data is None:
        return
    for key, a in firing.items():
        if key not in current:
            a.state, a.resolved_at = "resolved", now
