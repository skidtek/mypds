import hashlib
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.auth.deps import Principal, current_principal
from mypds.auth.service import audit
from mypds.cockpit.models import CockpitLayoutRow, IconAsset
from mypds.cockpit.schema import CURRENT_VERSION, CockpitLayout, default_layout, migrate, reconcile
from mypds.config.routes import sniff_image
from mypds.connectors.models import ConnectorInstance
from mypds.connectors.service import cached
from mypds.core.db import get_db
from mypds.core.http import client_ip, problem

router = APIRouter(prefix="/api/v1/cockpit", tags=["cockpit"])
MAX_DOC_BYTES = 512 * 1024
MAX_ICON_BYTES = 256 * 1024


class LayoutOut(BaseModel):
    revision: int
    document: dict[str, Any]


class LayoutIn(BaseModel):
    revision: int = Field(ge=0)
    document: dict[str, Any]


class IconOut(BaseModel):
    id: uuid.UUID
    name: str


def _validate(doc: dict[str, Any]) -> CockpitLayout:
    if len(json.dumps(doc)) > MAX_DOC_BYTES:
        raise problem(413, "Disposition trop volumineuse")
    try:
        return CockpitLayout.model_validate(migrate(doc))
    except (ValidationError, ValueError) as exc:
        raise problem(422, f"Disposition invalide : {exc}") from exc


def ui_lang(request: Request) -> str:
    """Langue de l'interface, transmise par le client dans Accept-Language (« fr » par défaut)."""
    return "en" if request.headers.get("accept-language", "").lower().startswith("en") else "fr"


async def _default(db: AsyncSession, lang: str = "fr") -> CockpitLayout:
    rows = (
        await db.scalars(
            select(ConnectorInstance).where(ConnectorInstance.enabled.is_(True)).order_by(ConnectorInstance.created_at)
        )
    ).all()
    pairs = []
    for r in rows:
        snap = cached(str(r.id)).snapshot
        pairs.append((str(r.id), snap.data if snap else None, r.type))
    return default_layout(pairs, lang)


async def _get_or_create(db: AsyncSession, p: Principal, lang: str = "fr") -> CockpitLayoutRow:
    row = await db.get(CockpitLayoutRow, p.user.id)
    if row is None:
        row = CockpitLayoutRow(
            user_id=p.user.id, schema_version=CURRENT_VERSION, document=(await _default(db, lang)).dump(), revision=1
        )
        db.add(row)
        await db.commit()
        return row
    # Alignement sur les connexions existantes (ajout des nouvelles, retrait des supprimées)
    conns = (await db.scalars(select(ConnectorInstance))).all()
    existing = {str(c.id) for c in conns}
    snaps = {
        str(c.id): (c.type, cached(str(c.id)).snapshot.data if cached(str(c.id)).snapshot else None)
        for c in conns
        if c.enabled
    }
    doc, changed = reconcile(json.loads(json.dumps(row.document)), existing, snaps, lang)
    if changed:
        row.document = CockpitLayout.model_validate(doc).dump()
        row.revision += 1
        await db.commit()
    return row


@router.get("/layout", response_model=LayoutOut)
async def get_layout(request: Request, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    row = await _get_or_create(db, p, ui_lang(request))
    return LayoutOut(revision=row.revision, document=row.document)


@router.put("/layout", response_model=LayoutOut)
async def put_layout(body: LayoutIn, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    layout = _validate(body.document)
    row = await _get_or_create(db, p)
    if body.revision != row.revision:
        raise problem(409, "La disposition a été modifiée ailleurs. Rechargez la page.")
    row.document = layout.dump()
    row.revision += 1
    await db.commit()
    return LayoutOut(revision=row.revision, document=row.document)


@router.post("/layout/reset", response_model=LayoutOut)
async def reset_layout(request: Request, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    row = await _get_or_create(db, p, ui_lang(request))
    row.document = (await _default(db, ui_lang(request))).dump()
    row.revision += 1
    await audit(db, "cockpit.reset", actor=p.user.id, ip=client_ip(request))
    await db.commit()
    return LayoutOut(revision=row.revision, document=row.document)


@router.get("/layout/export")
async def export_layout(p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    row = await _get_or_create(db, p)
    return Response(
        json.dumps(row.document, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="mypds-cockpit.json"'},
    )


@router.post("/layout/import", response_model=LayoutOut)
async def import_layout(
    document: dict[str, Any],
    request: Request,
    p: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    layout = _validate(document)
    row = await _get_or_create(db, p)
    row.document = layout.dump()
    row.revision += 1
    await audit(db, "cockpit.import", actor=p.user.id, ip=client_ip(request))
    await db.commit()
    return LayoutOut(revision=row.revision, document=row.document)


# ---------- Logos importés ----------
@router.get("/icons", response_model=list[IconOut])
async def list_icons(p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.scalars(select(IconAsset).where(IconAsset.user_id == p.user.id).order_by(IconAsset.created_at))
    ).all()
    return [IconOut(id=r.id, name=r.name) for r in rows]


@router.post("/icons", response_model=IconOut, status_code=201)
async def upload_icon(file: UploadFile, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    data = await file.read(MAX_ICON_BYTES + 1)
    if len(data) > MAX_ICON_BYTES:
        raise problem(413, "Logo trop volumineux (256 Ko maximum)")
    ctype = sniff_image(data)
    if ctype is None:
        raise problem(422, "Format non pris en charge : utilisez une image PNG, JPEG ou WebP")
    name = (file.filename or "logo").rsplit(".", 1)[0][:80] or "logo"
    icon = IconAsset(
        user_id=p.user.id, name=name, content_type=ctype, data=data, sha256=hashlib.sha256(data).hexdigest()
    )
    db.add(icon)
    await db.commit()
    return IconOut(id=icon.id, name=icon.name)


@router.get("/icons/{iid}")
async def get_icon(iid: uuid.UUID, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    icon = await db.get(IconAsset, iid)
    if icon is None or icon.user_id != p.user.id:
        raise problem(404, "Logo introuvable")
    return Response(
        icon.data, media_type=icon.content_type, headers={"Cache-Control": "private, max-age=31536000, immutable"}
    )


@router.delete("/icons/{iid}", status_code=204)
async def delete_icon(iid: uuid.UUID, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    icon = await db.get(IconAsset, iid)
    if icon is None or icon.user_id != p.user.id:
        raise problem(404, "Logo introuvable")
    await db.delete(icon)
    await db.commit()
