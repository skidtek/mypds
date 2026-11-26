import asyncio
import uuid
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.auth.deps import Principal, current_principal
from mypds.auth.service import audit
from mypds.core import crypto, net
from mypds.core.db import get_db
from mypds.core.http import client_ip, problem
from mypds.widgets.calendar.models import CalendarSource
from mypds.widgets.calendar.service import (
    PROVIDERS,
    CalendarError,
    expand,
    normalize_url,
    parsed_calendar,
    password_context,
    source_auth,
    split_credentials,
    url_context,
)

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])
HEX = r"^#[0-9A-Fa-f]{6}$"


class SourceIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    url: str = Field(min_length=10, max_length=2000)
    color: str = Field(default="#0A84FF", pattern=HEX)
    # Connexion HTTP Basic facultative (le mot de passe est chiffré, jamais renvoyé)
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=512)


class SourcePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    url: str | None = Field(default=None, min_length=10, max_length=2000)
    color: str | None = Field(default=None, pattern=HEX)
    enabled: bool | None = None
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=512)  # vide ou absent = inchangé
    clear_auth: bool = False


class SourceOut(BaseModel):
    id: uuid.UUID
    name: str
    color: str
    enabled: bool
    url_host: str  # l'URL complète n'est jamais renvoyée
    auth_username: str | None  # le mot de passe n'est jamais renvoyé
    event_count: int
    last_success_at: datetime | None
    last_error: str | None


class EventOut(BaseModel):
    id: str
    source_id: str
    title: str
    start: str
    end: str | None
    all_day: bool
    location: str | None
    color: str


class EventsOut(BaseModel):
    events: list[EventOut]
    synced_at: datetime | None


def _out(s: CalendarSource) -> SourceOut:
    return SourceOut.model_validate(s, from_attributes=True)


def _host(url: str) -> str:
    try:
        return httpx.URL(normalize_url(url)).host[:255]
    except Exception as exc:  # noqa: BLE001
        raise problem(422, "URL invalide") from exc


async def _own(db: AsyncSession, p: Principal, sid: uuid.UUID) -> CalendarSource:
    s = await db.get(CalendarSource, sid)
    if s is None or s.user_id != p.user.id:
        raise problem(404, "Calendrier introuvable")
    return s


async def _validate(url: str, auth: tuple[str, str] | None = None) -> None:
    try:
        await PROVIDERS["ics"].validate(url, auth)  # type: ignore[attr-defined]
    except (net.OutboundError, CalendarError) as exc:
        raise problem(422, f"Calendrier inaccessible : {exc}") from exc


def _clean_url(raw: str) -> tuple[str, str | None, str | None]:
    """URL sans identifiants + identifiants éventuellement présents dans l'URL (« user@hôte »)."""
    return split_credentials(normalize_url(raw))


@router.get("/sources", response_model=list[SourceOut])
async def list_sources(p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.scalars(
            select(CalendarSource).where(CalendarSource.user_id == p.user.id).order_by(CalendarSource.name)
        )
    ).all()
    return [_out(s) for s in rows]


@router.post("/sources", response_model=SourceOut, status_code=201)
async def add_source(
    body: SourceIn, request: Request, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    url, url_user, url_password = _clean_url(body.url)
    username = (body.username or url_user or "").strip() or None
    password = body.password or url_password
    if username and not password:
        raise problem(422, "Mot de passe requis pour l'identifiant indiqué")
    auth = (username, password) if username and password else None
    await _validate(url, auth)
    sid = uuid.uuid4()
    src = CalendarSource(
        id=sid,
        user_id=p.user.id,
        name=body.name.strip(),
        color=body.color,
        url_enc=crypto.encrypt(url, url_context(sid)),
        url_host=_host(url),
        auth_username=username if auth else None,
        auth_password_enc=crypto.encrypt(password, password_context(sid)) if auth else None,
    )
    db.add(src)
    await audit(
        db,
        "calendar.source.add",
        actor=p.user.id,
        ip=client_ip(request),
        target_type="calendar_source",
        target_id=str(sid),
    )
    await db.commit()
    await PROVIDERS["ics"].sync(db, src)
    return _out(src)


@router.patch("/sources/{sid}", response_model=SourceOut)
async def update_source(
    sid: uuid.UUID,
    body: SourcePatch,
    request: Request,
    p: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    src = await _own(db, p, sid)
    if body.name:
        src.name = body.name.strip()
    if body.color:
        src.color = body.color
    if body.enabled is not None:
        src.enabled = body.enabled
    url_changed = bool(body.url)
    auth_changed = body.clear_auth or bool(body.username) or bool(body.password)
    if url_changed or auth_changed:
        if body.url:
            url, url_user, url_password = _clean_url(body.url)
        else:
            url, url_user, url_password = crypto.decrypt(src.url_enc, url_context(src.id)), None, None
        current = source_auth(src)
        if body.clear_auth:
            auth = None
        else:
            username = (body.username or url_user or (current[0] if current else "") or "").strip() or None
            password = body.password or url_password or (current[1] if current else None)
            if username and not password:
                raise problem(422, "Mot de passe requis pour l'identifiant indiqué")
            auth = (username, password) if username and password else None
        await _validate(url, auth)
        src.url_enc, src.url_host = crypto.encrypt(url, url_context(src.id)), _host(url)
        src.auth_username = auth[0] if auth else None
        src.auth_password_enc = crypto.encrypt(auth[1], password_context(src.id)) if auth else None
        src.etag = src.last_modified = None
        await audit(
            db,
            "calendar.source.access",
            actor=p.user.id,
            ip=client_ip(request),
            target_id=str(sid),
            details={"url_changed": url_changed, "auth_changed": auth_changed},
        )
    await db.commit()
    if url_changed or auth_changed:
        await PROVIDERS["ics"].sync(db, src)
    return _out(src)


@router.delete("/sources/{sid}", status_code=204)
async def delete_source(sid: uuid.UUID, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    await db.delete(await _own(db, p, sid))
    await db.commit()


@router.post("/sources/{sid}/sync", response_model=SourceOut)
async def sync_source(sid: uuid.UUID, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    src = await _own(db, p, sid)
    await PROVIDERS[src.kind].sync(db, src)
    return _out(src)


@router.get("/events", response_model=EventsOut)
async def events(
    days: int = Query(default=7, ge=1, le=60),
    source_id: list[uuid.UUID] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    p: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    q = select(CalendarSource).where(CalendarSource.user_id == p.user.id, CalendarSource.enabled.is_(True))
    if source_id:
        q = q.where(CalendarSource.id.in_(source_id))
    sources = (await db.scalars(q)).all()
    now = datetime.now(UTC)
    start, end = now - timedelta(hours=12), now + timedelta(days=days)
    result: list[EventOut] = []
    synced: list[datetime] = []
    for s in sources:
        cal = await asyncio.to_thread(parsed_calendar, s)
        if cal is None:
            continue
        if s.last_success_at:
            synced.append(s.last_success_at)
        for occ in await asyncio.to_thread(expand, cal, str(s.id), start, end):
            result.append(EventOut(**asdict(occ), color=s.color))

    def key(e: EventOut) -> datetime:
        if e.all_day:
            return datetime.fromisoformat(e.start).replace(tzinfo=UTC)
        return datetime.fromisoformat(e.start)

    def still_relevant(e: EventOut) -> bool:
        if e.end is None:
            return key(e) >= now - timedelta(hours=1)
        end_dt = datetime.fromisoformat(e.end)
        if e.all_day:
            end_dt = end_dt.replace(tzinfo=UTC)
        return end_dt > now

    result = sorted((e for e in result if still_relevant(e)), key=key)[:limit]
    return EventsOut(events=result, synced_at=min(synced) if synced else None)
