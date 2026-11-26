"""Post-it : notes à onglets, propres à chaque utilisateur, rangées par widget de la Home."""

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.auth.deps import Principal, current_principal
from mypds.core.db import get_db
from mypds.core.http import problem
from mypds.landing.schema import WidgetId
from mypds.widgets.notes.models import Note

router = APIRouter(prefix="/api/v1/notes", tags=["notes"])
MAX_NOTES = 20
Color = Literal["yellow", "pink", "green", "blue", "orange", "purple"]
Texture = Literal["plain", "paper", "lined", "grid"]


class NoteOut(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    color: Color
    texture: Texture
    position: int
    created_at: datetime
    updated_at: datetime


class NoteIn(BaseModel):
    widget: WidgetId
    title: str = Field(default="", max_length=40)
    color: Color = "yellow"
    texture: Texture = "plain"


class NotePatch(BaseModel):
    title: str | None = Field(default=None, max_length=40)
    body: str | None = Field(default=None, max_length=20_000)
    color: Color | None = None
    texture: Texture | None = None
    position: int | None = Field(default=None, ge=0, le=1000)


def _out(n: Note) -> NoteOut:
    return NoteOut.model_validate(n, from_attributes=True)


async def _own(db: AsyncSession, p: Principal, nid: uuid.UUID) -> Note:
    n = await db.get(Note, nid)
    if not n or n.user_id != p.user.id:
        raise problem(404, "Note introuvable")
    return n


@router.get("", response_model=list[NoteOut])
async def list_notes(
    widget: WidgetId = Query(), p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    rows = await db.scalars(
        select(Note).where(Note.user_id == p.user.id, Note.widget_id == widget).order_by(Note.position, Note.created_at)
    )
    return [_out(n) for n in rows]


@router.post("", response_model=NoteOut, status_code=201)
async def add(body: NoteIn, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    where = (Note.user_id == p.user.id, Note.widget_id == body.widget)
    if (await db.scalar(select(func.count()).select_from(Note).where(*where))) >= MAX_NOTES:
        raise problem(422, f"{MAX_NOTES} post-it maximum par widget")
    last = await db.scalar(select(func.max(Note.position)).where(*where))
    n = Note(
        user_id=p.user.id,
        widget_id=body.widget,
        title=body.title.strip(),
        color=body.color,
        texture=body.texture,
        position=(last + 1) if last is not None else 0,
    )
    db.add(n)
    await db.commit()
    return _out(n)


@router.patch("/{nid}", response_model=NoteOut)
async def update(
    nid: uuid.UUID, body: NotePatch, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    n = await _own(db, p, nid)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(n, field, value.strip() if field == "title" else value)
    await db.commit()
    await db.refresh(n)
    return _out(n)


@router.delete("/{nid}", status_code=204)
async def remove(nid: uuid.UUID, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    await db.delete(await _own(db, p, nid))
    await db.commit()


@router.delete("", status_code=204)
async def remove_widget(
    widget: WidgetId = Query(), p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    await db.execute(delete(Note).where(Note.user_id == p.user.id, Note.widget_id == widget))
    await db.commit()
