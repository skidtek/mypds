import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.alerts.models import Alert
from mypds.alerts.settings import AlertSettings, load, save
from mypds.auth.deps import Principal, current_principal, require_role
from mypds.auth.service import audit
from mypds.connectors.models import ConnectorInstance
from mypds.core.db import get_db, utcnow
from mypds.core.http import client_ip, problem

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])
SEVERITY_ORDER = {"critical": 0, "warning": 1}


class AlertOut(BaseModel):
    id: uuid.UUID
    connector_id: uuid.UUID
    connector: str
    demo: bool
    kind: str
    resource: str | None
    severity: str
    title: str
    detail: str | None
    params: dict
    state: str
    started_at: datetime
    resolved_at: datetime | None


class AlertsOut(BaseModel):
    active: list[AlertOut]
    resolved: list[AlertOut]


@router.get("", response_model=AlertsOut)
async def alerts(_: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Alert, ConnectorInstance)
            .join(ConnectorInstance, ConnectorInstance.id == Alert.connector_id)
            .where(ConnectorInstance.enabled.is_(True))
            .where((Alert.state == "firing") | (Alert.resolved_at >= utcnow() - timedelta(hours=24)))
        )
    ).all()

    def out(a: Alert, c: ConnectorInstance) -> AlertOut:
        return AlertOut(
            id=a.id,
            connector_id=c.id,
            connector=c.name,
            demo=c.config.get("mode") == "demo",
            kind=a.kind,
            resource=a.resource,
            severity=a.severity,
            title=a.title,
            detail=a.detail,
            params=a.params or {},
            state=a.state,
            started_at=a.started_at,
            resolved_at=a.resolved_at,
        )

    active = sorted(
        (out(a, c) for a, c in rows if a.state == "firing"),
        key=lambda a: (SEVERITY_ORDER.get(a.severity, 9), -a.started_at.timestamp()),
    )
    resolved = sorted((out(a, c) for a, c in rows if a.state == "resolved"), key=lambda a: a.resolved_at, reverse=True)
    return AlertsOut(active=active, resolved=resolved[:20])


@router.get("/settings", response_model=AlertSettings)
async def get_settings_(_: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    return await load(db)


@router.put("/settings", response_model=AlertSettings)
async def put_settings(
    body: dict, request: Request, p: Principal = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)
):
    try:
        value = AlertSettings.model_validate(body)
    except ValidationError as exc:
        raise problem(422, f"Seuils invalides : {exc.errors()[0]['msg']}") from exc
    await save(db, value)
    await audit(db, "alerts.settings", actor=p.user.id, ip=client_ip(request), details=value.model_dump())
    await db.commit()
    return value
