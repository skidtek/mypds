"""Récupération des flux (côté serveur uniquement) et maintenance des articles."""

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.core import net
from mypds.core.db import utcnow
from mypds.widgets.rss.models import RssFeed, RssItem
from mypds.widgets.rss.parsing import FeedParseError, ParsedFeed, discover_feed_links, parse_feed

log = logging.getLogger("mypds.rss")
MAX_FEED_BYTES = 5 * 1024 * 1024
KEEP_PER_FEED = 200
KEEP_DAYS = 30
ACCEPT = "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5"


async def download(url: str, etag: str | None = None, last_modified: str | None = None) -> net.FetchResult:
    headers = {"Accept": ACCEPT}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    return await net.fetch(url, max_bytes=MAX_FEED_BYTES, headers=headers)


async def probe(url: str) -> tuple[str, ParsedFeed]:
    """Vérifie une URL (ajout manuel). Si c'est une page web, cherche le flux qu'elle annonce.

    Renvoie l'URL du flux réellement retenu et son contenu analysé.
    """
    res = await download(url)
    if res.status != 200:
        raise net.OutboundError(f"Le serveur a répondu HTTP {res.status}")
    try:
        return res.url, await asyncio.to_thread(parse_feed, res.content)
    except FeedParseError:
        candidates = discover_feed_links(res.content, res.url)
        if not candidates:
            raise FeedParseError("Ni flux RSS/Atom, ni page annonçant un flux à cette adresse") from None
    last: Exception | None = None
    for candidate in candidates[:3]:
        try:
            sub = await download(candidate)
            if sub.status != 200:
                raise net.OutboundError(f"HTTP {sub.status}")
            return sub.url, await asyncio.to_thread(parse_feed, sub.content)
        except (net.OutboundError, FeedParseError) as exc:
            last = exc
    raise FeedParseError(f"La page annonce un flux, mais il est illisible : {last}")


async def refresh_feed(db: AsyncSession, feed: RssFeed) -> int:
    """Met à jour un flux. Renvoie le nombre de nouveaux articles. Ne lève pas d'exception."""
    feed.last_fetch_at = utcnow()
    try:
        res = await download(feed.feed_url, feed.etag, feed.last_modified)
        if res.status == 304:
            feed.last_success_at, feed.last_error, feed.error_count = utcnow(), None, 0
            await db.commit()
            return 0
        if res.status != 200:
            raise net.OutboundError(f"HTTP {res.status}")
        parsed = await asyncio.to_thread(parse_feed, res.content)
    except (net.OutboundError, FeedParseError) as exc:
        feed.last_error = str(exc)[:500]
        feed.error_count += 1
        await db.commit()
        log.info("Feed %s failing: %s", feed.id, exc)
        return 0
    feed.etag = (res.headers.get("etag") or "")[:300] or None
    feed.last_modified = (res.headers.get("last-modified") or "")[:100] or None
    feed.last_success_at, feed.last_error, feed.error_count = utcnow(), None, 0
    if parsed.site_url and not feed.site_url:
        feed.site_url = parsed.site_url
    added = 0
    for item in parsed.items:
        stmt = (
            insert(RssItem)
            .values(
                feed_id=feed.id,
                guid_hash=item.guid_hash,
                title=item.title,
                link=item.link,
                author=item.author,
                published_at=item.published_at,
                summary_text=item.summary_text,
                image_url=item.image_url,
            )
            .on_conflict_do_nothing(index_elements=["feed_id", "guid_hash"])
        )
        result = await db.execute(stmt)
        added += result.rowcount or 0
    await _prune(db, feed)
    await db.commit()
    return added


async def _prune(db: AsyncSession, feed: RssFeed) -> None:
    await db.execute(
        delete(RssItem).where(RssItem.feed_id == feed.id, RssItem.published_at < utcnow() - timedelta(days=KEEP_DAYS))
    )
    keep = (
        select(RssItem.id).where(RssItem.feed_id == feed.id).order_by(RssItem.published_at.desc()).limit(KEEP_PER_FEED)
    )
    await db.execute(delete(RssItem).where(RssItem.feed_id == feed.id, RssItem.id.not_in(keep)))
