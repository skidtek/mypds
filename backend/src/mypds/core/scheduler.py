"""Planificateur interne (asyncio) : flux RSS, calendriers, purge des sessions.

Chaque tâche est isolée : une erreur est journalisée sans interrompre les autres.
"""

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import delete, or_, select

from mypds.auth.service import purge_expired
from mypds.core.db import sessionmaker, utcnow
from mypds.core.settings import get_settings
from mypds.widgets.calendar.models import CalendarSource
from mypds.widgets.calendar.service import PROVIDERS as CAL_PROVIDERS
from mypds.widgets.rss.models import RssFeed
from mypds.widgets.rss.service import refresh_feed

log = logging.getLogger("mypds.scheduler")
TICK_SECONDS = 60
CONCURRENCY = 4


async def _due_feeds() -> list:
    s = get_settings()
    cutoff = utcnow() - timedelta(minutes=s.rss_refresh_minutes)
    async with sessionmaker()() as db:
        return list(
            (
                await db.scalars(
                    select(RssFeed.id)
                    .where(
                        RssFeed.enabled.is_(True),
                        or_(RssFeed.last_fetch_at.is_(None), RssFeed.last_fetch_at < cutoff),
                    )
                    .limit(200)
                )
            ).all()
        )


async def _due_calendars() -> list:
    cutoff = utcnow() - timedelta(minutes=get_settings().calendar_refresh_minutes)
    async with sessionmaker()() as db:
        return list(
            (
                await db.scalars(
                    select(CalendarSource.id).where(
                        CalendarSource.enabled.is_(True),
                        or_(CalendarSource.last_sync_at.is_(None), CalendarSource.last_sync_at < cutoff),
                    )
                )
            ).all()
        )


async def _run_feed(fid, sem: asyncio.Semaphore) -> None:  # noqa: ANN001
    async with sem, sessionmaker()() as db:
        feed = await db.get(RssFeed, fid)
        if feed is not None:
            await refresh_feed(db, feed)


async def _run_calendar(cid, sem: asyncio.Semaphore) -> None:  # noqa: ANN001
    async with sem, sessionmaker()() as db:
        src = await db.get(CalendarSource, cid)
        if src is not None:
            await CAL_PROVIDERS[src.kind].sync(db, src)


async def tick() -> None:
    sem = asyncio.Semaphore(CONCURRENCY)
    jobs = [_run_feed(f, sem) for f in await _due_feeds()]
    jobs += [_run_calendar(c, sem) for c in await _due_calendars()]
    results = await asyncio.gather(*jobs, return_exceptions=True)
    for r in results:
        if isinstance(r, Exception):
            log.warning("Scheduled job failed: %r", r)
    async with sessionmaker()() as db:
        await purge_expired(db)
        from mypds.alerts.models import Alert

        await db.execute(
            delete(Alert).where(Alert.state == "resolved", Alert.resolved_at < utcnow() - timedelta(days=90))
        )
        await db.commit()


class Scheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self.last_tick_at = None

    async def _loop(self) -> None:
        await asyncio.sleep(5)
        while True:
            try:
                await tick()
                self.last_tick_at = utcnow()
            except Exception:  # noqa: BLE001 - le planificateur ne doit jamais mourir
                log.exception("Scheduler error")
            await asyncio.sleep(TICK_SECONDS)

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop(), name="mypds-scheduler")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()


scheduler = Scheduler()
