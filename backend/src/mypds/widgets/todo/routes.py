"""Tâches des widgets Todo : propres à chaque utilisateur, rangées par widget de la Home."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.auth.deps import Principal, current_principal
from mypds.core.db import get_db, utcnow
from mypds.core.http import problem
from mypds.landing.schema import WidgetId
from mypds.widgets.todo.models import TodoItem

router = APIRouter(prefix="/api/v1/todo", tags=["todo"])
MAX_ITEMS = 500


class TodoOut(BaseModel):
    id: uuid.UUID
    text: str
    position: int
    created_at: datetime
    done_at: datetime | None


class TodoIn(BaseModel):
    widget: WidgetId
    text: str = Field(min_length=1, max_length=500)


class TodoPatch(BaseModel):
    text: str | None = Field(default=None, min_length=1, max_length=500)
    done: bool | None = None
    position: int | None = Field(default=None, ge=-100_000, le=100_000)


def _out(t: TodoItem) -> TodoOut:
    return TodoOut(id=t.id, text=t.text, position=t.position, created_at=t.created_at, done_at=t.done_at)


async def _own(db: AsyncSession, p: Principal, tid: uuid.UUID) -> TodoItem:
    t = await db.get(TodoItem, tid)
    if not t or t.user_id != p.user.id:
        raise problem(404, "Tâche introuvable")
    return t


@router.get("", response_model=list[TodoOut])
async def list_items(
    widget: WidgetId = Query(), p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    rows = await db.scalars(
        select(TodoItem)
        .where(TodoItem.user_id == p.user.id, TodoItem.widget_id == widget)
        .order_by(TodoItem.done_at.desc().nulls_first(), TodoItem.position, TodoItem.created_at)
    )
    return [_out(t) for t in rows]


@router.post("", response_model=TodoOut, status_code=201)
async def add(body: TodoIn, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    where = (TodoItem.user_id == p.user.id, TodoItem.widget_id == body.widget)
    if (await db.scalar(select(func.count()).select_from(TodoItem).where(*where))) >= MAX_ITEMS:
        raise problem(422, f"Liste pleine ({MAX_ITEMS} tâches maximum) : supprimez des tâches terminées")
    # Nouvelle tâche en haut de la liste
    top = await db.scalar(select(func.min(TodoItem.position)).where(*where, TodoItem.done_at.is_(None)))
    t = TodoItem(user_id=p.user.id, widget_id=body.widget, text=body.text.strip(), position=(top or 0) - 1)
    db.add(t)
    await db.commit()
    return _out(t)


@router.patch("/{tid}", response_model=TodoOut)
async def update(
    tid: uuid.UUID, body: TodoPatch, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    t = await _own(db, p, tid)
    if body.text is not None:
        t.text = body.text.strip()
    if body.position is not None:
        t.position = body.position
    if body.done is not None:
        t.done_at = (t.done_at or utcnow()) if body.done else None
    await db.commit()
    return _out(t)


@router.delete("/{tid}", status_code=204)
async def remove(tid: uuid.UUID, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    await db.delete(await _own(db, p, tid))
    await db.commit()


@router.delete("", status_code=204)
async def remove_widget(
    widget: WidgetId = Query(),
    done_only: bool = False,
    p: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    """Toutes les tâches d'un widget (suppression du widget) ou seulement les terminées."""
    q = delete(TodoItem).where(TodoItem.user_id == p.user.id, TodoItem.widget_id == widget)
    if done_only:
        q = q.where(TodoItem.done_at.is_not(None))
    await db.execute(q)
    await db.commit()
