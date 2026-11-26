import asyncio
import uuid
from collections import OrderedDict
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.auth.deps import Principal, current_principal
from mypds.auth.service import audit
from mypds.core import net
from mypds.core.db import get_db, sessionmaker
from mypds.core.http import client_ip, problem
from mypds.widgets.rss.models import RssCategory, RssFeed, RssItem
from mypds.widgets.rss.parsing import FeedParseError, build_opml, parse_opml
from mypds.widgets.rss.service import probe, refresh_feed

router = APIRouter(prefix="/api/v1/rss", tags=["rss"])
MAX_OPML_BYTES = 2 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"}


# ---------- Schémas ----------
class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    position: int = Field(default=0, ge=0, le=10_000)


class CategoryOut(CategoryIn):
    id: uuid.UUID
    feed_count: int = 0


class FeedIn(BaseModel):
    url: str = Field(min_length=8, max_length=1000)
    category_id: uuid.UUID | None = None


class FeedPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: uuid.UUID | None = None
    enabled: bool | None = None


class FeedOut(BaseModel):
    id: uuid.UUID
    title: str
    feed_url: str
    site_url: str | None
    category_id: uuid.UUID | None
    enabled: bool
    last_success_at: datetime | None
    last_error: str | None


class ItemOut(BaseModel):
    id: uuid.UUID
    title: str
    link: str | None
    source: str
    feed_id: uuid.UUID
    category_id: uuid.UUID | None
    published_at: datetime
    summary: str | None
    image: str | None  # URL du proxy interne, jamais l'URL distante


class ImportReport(BaseModel):
    feeds_added: int
    feeds_skipped: int
    categories_added: int


def _feed_out(f: RssFeed) -> FeedOut:
    return FeedOut.model_validate(f, from_attributes=True)


async def _own_category(db: AsyncSession, p: Principal, cid: uuid.UUID | None) -> None:
    if cid is None:
        return
    cat = await db.get(RssCategory, cid)
    if cat is None or cat.user_id != p.user.id:
        raise problem(404, "Catégorie introuvable")


async def _own_feed(db: AsyncSession, p: Principal, fid: uuid.UUID) -> RssFeed:
    feed = await db.get(RssFeed, fid)
    if feed is None or feed.user_id != p.user.id:
        raise problem(404, "Flux introuvable")
    return feed


async def _refresh_ids(ids: list[uuid.UUID]) -> None:
    sem = asyncio.Semaphore(4)

    async def one(fid: uuid.UUID) -> None:
        async with sem, sessionmaker()() as db:
            feed = await db.get(RssFeed, fid)
            if feed:
                await refresh_feed(db, feed)

    await asyncio.gather(*(one(i) for i in ids))


# ---------- Catégories ----------
@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    counts = dict(
        (
            await db.execute(
                select(RssFeed.category_id, func.count())
                .where(RssFeed.user_id == p.user.id)
                .group_by(RssFeed.category_id)
            )
        ).all()
    )
    cats = (
        await db.scalars(
            select(RssCategory).where(RssCategory.user_id == p.user.id).order_by(RssCategory.position, RssCategory.name)
        )
    ).all()
    return [CategoryOut(id=c.id, name=c.name, position=c.position, feed_count=counts.get(c.id, 0)) for c in cats]


@router.post("/categories", response_model=CategoryOut, status_code=201)
async def create_category(
    body: CategoryIn, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    cat = RssCategory(user_id=p.user.id, name=body.name.strip(), position=body.position)
    db.add(cat)
    await db.commit()
    return CategoryOut(id=cat.id, name=cat.name, position=cat.position)


@router.put("/categories/{cid}", response_model=CategoryOut)
async def update_category(
    cid: uuid.UUID, body: CategoryIn, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    await _own_category(db, p, cid)
    cat = await db.get(RssCategory, cid)
    assert cat is not None
    cat.name, cat.position = body.name.strip(), body.position
    await db.commit()
    return CategoryOut(id=cat.id, name=cat.name, position=cat.position)


@router.delete("/categories/{cid}", status_code=204)
async def delete_category(
    cid: uuid.UUID, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    await _own_category(db, p, cid)
    await db.delete(await db.get(RssCategory, cid))
    await db.commit()


# ---------- Flux ----------
@router.get("/feeds", response_model=list[FeedOut])
async def list_feeds(p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    feeds = (await db.scalars(select(RssFeed).where(RssFeed.user_id == p.user.id).order_by(RssFeed.title))).all()
    return [_feed_out(f) for f in feeds]


@router.post("/feeds", response_model=FeedOut, status_code=201)
async def add_feed(
    body: FeedIn, request: Request, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    await _own_category(db, p, body.category_id)
    try:
        url, parsed = await probe(body.url.strip())
    except (net.OutboundError, FeedParseError) as exc:
        raise problem(422, f"Impossible d'ajouter ce flux : {exc}") from exc
    if await db.scalar(select(RssFeed.id).where(RssFeed.user_id == p.user.id, RssFeed.feed_url == url)):
        raise problem(409, "Ce flux est déjà dans vos abonnements")
    feed = RssFeed(
        user_id=p.user.id,
        category_id=body.category_id,
        title=parsed.title or url,
        feed_url=url,
        site_url=parsed.site_url,
    )
    db.add(feed)
    await audit(db, "rss.feed.add", actor=p.user.id, ip=client_ip(request), target_type="rss_feed")
    await db.commit()
    await refresh_feed(db, feed)
    return _feed_out(feed)


@router.patch("/feeds/{fid}", response_model=FeedOut)
async def update_feed(
    fid: uuid.UUID, body: FeedPatch, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    feed = await _own_feed(db, p, fid)
    fields = body.model_dump(exclude_unset=True)
    if "category_id" in fields:
        await _own_category(db, p, fields["category_id"])
        feed.category_id = fields["category_id"]
    if fields.get("title"):
        feed.title = fields["title"].strip()
    if fields.get("enabled") is not None:
        feed.enabled = fields["enabled"]
    await db.commit()
    return _feed_out(feed)


@router.delete("/feeds/{fid}", status_code=204)
async def delete_feed(fid: uuid.UUID, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    await db.delete(await _own_feed(db, p, fid))
    await db.commit()


@router.post("/feeds/{fid}/refresh", response_model=FeedOut)
async def refresh(fid: uuid.UUID, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    feed = await _own_feed(db, p, fid)
    await refresh_feed(db, feed)
    return _feed_out(feed)


# ---------- Articles ----------
@router.get("/items", response_model=list[ItemOut])
async def items(
    category_id: list[uuid.UUID] | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=60),
    p: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(RssItem, RssFeed.title, RssFeed.category_id)
        .join(RssFeed, RssFeed.id == RssItem.feed_id)
        .where(RssFeed.user_id == p.user.id, RssFeed.enabled.is_(True))
        .order_by(RssItem.published_at.desc())
        .limit(limit)
    )
    if category_id:
        q = q.where(RssFeed.category_id.in_(category_id))
    rows = (await db.execute(q)).all()
    return [
        ItemOut(
            id=it.id,
            title=it.title,
            link=it.link,
            source=src,
            feed_id=it.feed_id,
            category_id=cat,
            published_at=it.published_at,
            summary=it.summary_text,
            image=f"/api/v1/rss/items/{it.id}/image" if it.image_url else None,
        )
        for it, src, cat in rows
    ]


class _ImageCache:
    """Petit cache mémoire LRU des miniatures (borné en octets)."""

    def __init__(self, max_bytes: int = 32 * 1024 * 1024) -> None:
        self.max_bytes, self.size = max_bytes, 0
        self.data: OrderedDict[uuid.UUID, tuple[str, bytes]] = OrderedDict()

    def get(self, key: uuid.UUID) -> tuple[str, bytes] | None:
        if key in self.data:
            self.data.move_to_end(key)
            return self.data[key]
        return None

    def put(self, key: uuid.UUID, value: tuple[str, bytes]) -> None:
        self.data[key] = value
        self.size += len(value[1])
        while self.size > self.max_bytes and self.data:
            _, (_, old) = self.data.popitem(last=False)
            self.size -= len(old)


_images = _ImageCache()


@router.get("/items/{iid}/image")
async def item_image(iid: uuid.UUID, p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    """Proxy des miniatures : seule l'URL issue du flux de l'utilisateur est récupérable."""
    cached = _images.get(iid)
    if cached is None:
        row = (
            await db.execute(
                select(RssItem.image_url)
                .join(RssFeed, RssFeed.id == RssItem.feed_id)
                .where(RssItem.id == iid, RssFeed.user_id == p.user.id)
            )
        ).first()
        if row is None or not row[0]:
            raise problem(404, "Image introuvable")
        try:
            res = await net.fetch(row[0], max_bytes=3 * 1024 * 1024, timeout=10, headers={"Accept": "image/*"})
        except net.OutboundError as exc:
            raise problem(502, str(exc)) from exc
        ctype = (res.headers.get("content-type") or "").split(";")[0].strip().lower()
        if res.status != 200 or ctype not in IMAGE_TYPES:
            raise problem(502, "Image indisponible")
        cached = (ctype, res.content)
        _images.put(iid, cached)
    return Response(cached[1], media_type=cached[0], headers={"Cache-Control": "private, max-age=86400"})


# ---------- OPML ----------
@router.post("/opml", response_model=ImportReport)
async def import_opml(
    file: UploadFile,
    request: Request,
    background: BackgroundTasks,
    p: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read(MAX_OPML_BYTES + 1)
    if len(content) > MAX_OPML_BYTES:
        raise problem(413, "Fichier OPML trop volumineux (2 Mo max)")
    try:
        entries = parse_opml(content)
    except FeedParseError as exc:
        raise problem(422, str(exc)) from exc
    cats = {
        c.name.lower(): c for c in (await db.scalars(select(RssCategory).where(RssCategory.user_id == p.user.id))).all()
    }
    existing = set((await db.scalars(select(RssFeed.feed_url).where(RssFeed.user_id == p.user.id))).all())
    added_ids: list[uuid.UUID] = []
    cats_added = skipped = 0
    for e in entries:
        if e.xml_url in existing:
            skipped += 1
            continue
        cat_id = None
        if e.category:
            cat = cats.get(e.category.lower())
            if cat is None:
                cat = RssCategory(user_id=p.user.id, name=e.category, position=len(cats))
                db.add(cat)
                await db.flush()
                cats[e.category.lower()] = cat
                cats_added += 1
            cat_id = cat.id
        feed = RssFeed(user_id=p.user.id, category_id=cat_id, title=e.title, feed_url=e.xml_url, site_url=e.html_url)
        db.add(feed)
        await db.flush()
        existing.add(e.xml_url)
        added_ids.append(feed.id)
    await audit(db, "rss.opml.import", actor=p.user.id, ip=client_ip(request), details={"added": len(added_ids)})
    await db.commit()
    background.add_task(_refresh_ids, added_ids)
    return ImportReport(feeds_added=len(added_ids), feeds_skipped=skipped, categories_added=cats_added)


@router.get("/opml")
async def export_opml(p: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)):
    cats = {c.id: c.name for c in (await db.scalars(select(RssCategory).where(RssCategory.user_id == p.user.id))).all()}
    grouped: dict[str | None, list[tuple[str, str, str | None]]] = {}
    for f in (await db.scalars(select(RssFeed).where(RssFeed.user_id == p.user.id).order_by(RssFeed.title))).all():
        grouped.setdefault(cats.get(f.category_id) if f.category_id else None, []).append(
            (f.title, f.feed_url, f.site_url)
        )
    return Response(
        build_opml(grouped),
        media_type="text/x-opml",
        headers={"Content-Disposition": 'attachment; filename="mypds-abonnements.opml"'},
    )
