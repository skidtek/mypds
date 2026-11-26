"""API des connecteurs. Administration réservée au rôle admin ; lecture pour tout utilisateur connecté.
Les secrets ne sont jamais renvoyés : seule leur présence est indiquée."""

import re
import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.auth.deps import Principal, current_principal, require_role
from mypds.auth.service import audit
from mypds.connectors.models import ConnectorInstance
from mypds.connectors.sdk import ConnectorError, readable, registry
from mypds.connectors.service import cached, collect_one, forget, instantiate, load_secrets, store_secrets
from mypds.core.db import get_db
from mypds.core.http import client_ip, problem

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])


class TypeOut(BaseModel):
    type: str
    name: str
    capabilities: list[str]
    config_schema: dict[str, Any]
    secret_fields: list[str]


class InstanceIn(BaseModel):
    type: str = Field(max_length=40)
    name: str = Field(min_length=1, max_length=80)
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, str | None] = Field(default_factory=dict)  # valeur vide = inchangée
    poll_interval_s: int | None = Field(default=None, ge=10, le=3600)


class InstancePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    enabled: bool | None = None
    config: dict[str, Any] | None = None
    secrets: dict[str, str | None] | None = None
    poll_interval_s: int | None = Field(default=None, ge=10, le=3600)


class InstanceOut(BaseModel):
    id: uuid.UUID
    type: str
    name: str
    enabled: bool
    config: dict[str, Any]
    secrets_set: list[str]
    poll_interval_s: int
    status: str
    last_ok_at: datetime | None
    last_error: str | None
    demo: bool


class TestOut(BaseModel):
    ok: bool
    message: str


class SnapshotOut(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    demo: bool
    status: str
    fetched_at: datetime | None
    error: str | None
    data: dict[str, Any] | None


def _out(row: ConnectorInstance) -> InstanceOut:
    try:
        secrets_set = sorted(load_secrets(row))
    except Exception:  # noqa: BLE001 - clé absente ou changée : on l'indique sans planter
        secrets_set = []
    return InstanceOut(
        id=row.id,
        type=row.type,
        name=row.name,
        enabled=row.enabled,
        config=row.config,
        secrets_set=secrets_set,
        poll_interval_s=row.poll_interval_s,
        status=row.status,
        last_ok_at=row.last_ok_at,
        last_error=row.last_error,
        demo=row.config.get("mode") == "demo",
    )


def _validate(type_id: str, config: dict[str, Any], secrets: dict[str, Any]) -> tuple[dict, dict]:
    cls = registry().get(type_id)
    if cls is None:
        raise problem(422, f"Type de connecteur inconnu : {type_id}")
    try:
        cfg = cls.config_model.model_validate(config).model_dump(mode="json", exclude_none=True)
        sec = cls.secrets_model.model_validate(secrets).model_dump(exclude_none=True)
    except (ValidationError, ValueError) as exc:
        raise problem(422, f"Configuration invalide : {readable(exc)}") from exc
    return cfg, sec


async def _row(db: AsyncSession, cid: uuid.UUID) -> ConnectorInstance:
    row = await db.get(ConnectorInstance, cid)
    if row is None:
        raise problem(404, "Connecteur introuvable")
    return row


# ---------- Administration ----------
@router.get("/types", response_model=list[TypeOut])
async def types(_: Principal = Depends(require_role("admin"))):
    return [
        TypeOut(
            type=t,
            name=cls.display_name,
            capabilities=sorted(cls.capabilities),
            config_schema=cls.config_model.model_json_schema(),
            secret_fields=list(cls.secrets_model.model_fields),
        )
        for t, cls in registry().items()
    ]


@router.get("", response_model=list[InstanceOut])
async def list_instances(_: Principal = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(ConnectorInstance).order_by(ConnectorInstance.name))).all()
    return [_out(r) for r in rows]


@router.post("", response_model=InstanceOut, status_code=201)
async def create(
    body: InstanceIn,
    request: Request,
    p: Principal = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    cfg, sec = _validate(body.type, body.config, body.secrets)
    cls = registry()[body.type]
    row = ConnectorInstance(
        id=uuid.uuid4(),
        type=body.type,
        name=body.name.strip(),
        enabled=body.enabled,
        config=cfg,
        poll_interval_s=body.poll_interval_s or cls.default_interval_s,
    )
    store_secrets(row, sec)
    db.add(row)
    await audit(
        db, "connector.create", actor=p.user.id, ip=client_ip(request), target_type=body.type, target_id=str(row.id)
    )
    await db.commit()
    if row.enabled:
        await collect_one(db, row)
    return _out(row)


@router.patch("/{cid}", response_model=InstanceOut)
async def update(
    cid: uuid.UUID,
    body: InstancePatch,
    request: Request,
    p: Principal = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    row = await _row(db, cid)
    current_secrets = load_secrets(row)
    new_secrets = {**current_secrets, **{k: v for k, v in (body.secrets or {}).items() if v}}
    cfg, sec = _validate(row.type, body.config if body.config is not None else row.config, new_secrets)
    row.config = cfg
    store_secrets(row, sec)
    if body.name:
        row.name = body.name.strip()
    if body.enabled is not None:
        row.enabled = body.enabled
    if body.poll_interval_s:
        row.poll_interval_s = body.poll_interval_s
    await audit(
        db,
        "connector.update",
        actor=p.user.id,
        ip=client_ip(request),
        target_type=row.type,
        target_id=str(row.id),
        details={"secrets_changed": bool(body.secrets and any(body.secrets.values()))},
    )
    await db.commit()
    forget(str(row.id))
    if row.enabled:
        await collect_one(db, row)
    return _out(row)


@router.delete("/{cid}", status_code=204)
async def delete(
    cid: uuid.UUID, request: Request, p: Principal = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)
):
    row = await _row(db, cid)
    await audit(
        db, "connector.delete", actor=p.user.id, ip=client_ip(request), target_type=row.type, target_id=str(row.id)
    )
    await db.delete(row)
    await db.commit()
    forget(str(cid))


@router.post("/{cid}/test", response_model=TestOut)
async def test(cid: uuid.UUID, p: Principal = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)):
    row = await _row(db, cid)
    try:
        report = await instantiate(row).test()
    except ConnectorError as exc:
        return TestOut(ok=False, message=str(exc))
    if report.ok and row.enabled:
        forget(str(row.id))  # remet à zéro l'attente après échec : l'état se rétablit tout de suite
        await collect_one(db, row)
    return TestOut(ok=report.ok, message=report.message)


# ---------- Lecture (tuiles) ----------
@router.get("/snapshots", response_model=list[SnapshotOut])
async def snapshots(_: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    """Dernier état de chaque connecteur actif (alimente toutes les tuiles du Cockpit)."""
    rows = (await db.scalars(select(ConnectorInstance).where(ConnectorInstance.enabled.is_(True)))).all()
    out = []
    for r in rows:
        entry = cached(str(r.id))
        snap = entry.snapshot
        out.append(
            SnapshotOut(
                id=r.id,
                name=r.name,
                type=r.type,
                demo=r.config.get("mode") == "demo",
                status=r.status,
                fetched_at=snap.fetched_at if snap else None,
                error=entry.error or r.last_error,
                data=snap.data if snap else None,
            )
        )
    return out


@router.get("/{cid}/history")
async def history(
    cid: uuid.UUID,
    resource: str = Query(max_length=100),
    timeframe: Literal["hour", "day", "week", "month", "year"] = "hour",
    _: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    row = await _row(db, cid)
    try:
        points = await instantiate(row).history(resource, timeframe)
    except ConnectorError as exc:
        raise problem(502, str(exc)) from exc
    return {"demo": row.config.get("mode") == "demo", "points": points}


class OnDemandIn(BaseModel):
    # Proxmox : « qemu/101 » ou « lxc/104 » ; Docker : nom du conteneur
    guest: str = Field(pattern=r"^((qemu|lxc)/\d{1,9}|[A-Za-z0-9][A-Za-z0-9_.-]{0,127})$")
    on_demand: bool


@router.post("/{cid}/on-demand", response_model=InstanceOut)
async def set_on_demand(
    cid: uuid.UUID,
    body: OnDemandIn,
    request: Request,
    p: Principal = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Option « Ignorer » : un invité démarré à la demande n'est pas une anomalie quand il est arrêté."""
    row = await _row(db, cid)
    if row.type not in {"proxmox", "docker"}:
        raise problem(422, "Option réservée aux connexions Proxmox et Docker")
    if (row.type == "proxmox") != bool(re.fullmatch(r"(qemu|lxc)/\d{1,9}", body.guest)):
        raise problem(422, "Élément invalide pour ce type de connexion")
    current = set(row.config.get("on_demand", []))
    current.add(body.guest) if body.on_demand else current.discard(body.guest)
    row.config = {**row.config, "on_demand": sorted(current)}
    await audit(
        db,
        "connector.on_demand",
        actor=p.user.id,
        ip=client_ip(request),
        target_type="guest",
        target_id=body.guest,
        details={"on_demand": body.on_demand},
    )
    await db.commit()
    if row.enabled:
        await collect_one(db, row)  # recalcule tout de suite l'état et les alertes
    return _out(row)
