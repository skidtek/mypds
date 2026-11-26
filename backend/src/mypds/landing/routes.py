import json
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.auth.deps import Principal, current_principal
from mypds.auth.service import audit
from mypds.core.db import get_db
from mypds.core.http import client_ip, problem
from mypds.landing.models import LandingLayoutRow
from mypds.landing.schema import CURRENT_VERSION, LandingLayout, default_layout, migrate

router = APIRouter(prefix="/api/v1/landing", tags=["landing"])
MAX_DOC_BYTES = 256 * 1024


class LayoutOut(BaseModel):
    revision: int
    document: dict[str, Any]


class LayoutIn(BaseModel):
    revision: int = Field(ge=0)
    document: dict[str, Any]


def _validate(doc: dict[str, Any]) -> LandingLayout:
    if len(json.dumps(doc)) > MAX_DOC_BYTES:
        raise problem(413, "Disposition trop volumineuse")
    try:
        return LandingLayout.model_validate(migrate(doc))
    except (ValidationError, ValueError) as exc:
        raise problem(422, f"Disposition invalide : {exc}") from exc


async def _get_or_create(db: AsyncSession, p: Principal) -> LandingLayoutRow:
    row = await db.get(LandingLayoutRow, p.user.id)
    if row is None:
        row = LandingLayoutRow(
            user_id=p.user.id, schema_version=CURRENT_VERSION, document=default_layout().dump(), revision=1
        )
        db.add(row)
        await db.commit()
    elif row.schema_version != CURRENT_VERSION:
        row.document = _validate(row.document).dump()
        row.schema_version = CURRENT_VERSION
        await db.commit()
    return row


@router.get("/layout", response_model=LayoutOut)
async def get_layout(p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    row = await _get_or_create(db, p)
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
    row = await _get_or_create(db, p)
    row.document = default_layout().dump()
    row.revision += 1
    await audit(db, "landing.reset", actor=p.user.id, ip=client_ip(request))
    await db.commit()
    return LayoutOut(revision=row.revision, document=row.document)


@router.get("/layout/export")
async def export_layout(p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    row = await _get_or_create(db, p)
    return Response(
        json.dumps(row.document, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="mypds-landing.json"'},
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
    await audit(db, "landing.import", actor=p.user.id, ip=client_ip(request))
    await db.commit()
    return LayoutOut(revision=row.revision, document=row.document)
