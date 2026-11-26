"""Agenda ICS : synchronisation côté serveur et expansion des récurrences.

Architecture extensible : `CalendarProvider` permettra d'ajouter CalDAV sans toucher aux routes.
"""

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol

import icalendar
import recurring_ical_events
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.core import crypto, net
from mypds.core.db import utcnow
from mypds.widgets.calendar.models import CalendarSource
from mypds.widgets.rss.parsing import html_to_text

MAX_ICS_BYTES = 5 * 1024 * 1024
MAX_OCCURRENCES = 500


class CalendarError(ValueError):
    pass


def normalize_url(url: str) -> str:
    url = url.strip()
    if url.lower().startswith("webcal://"):
        url = "https://" + url[len("webcal://") :]
    return url


def url_context(source_id: object) -> str:
    return f"calendar_source:{source_id}:url"


def password_context(source_id: object) -> str:
    return f"calendar_source:{source_id}:password"


def split_credentials(url: str) -> tuple[str, str | None, str | None]:
    """Retire « identifiant[:mot de passe]@ » d'une URL : ils ne doivent pas rester dans l'adresse."""
    from urllib.parse import unquote, urlsplit, urlunsplit

    parts = urlsplit(url)
    if "@" not in parts.netloc:
        return url, None, None
    userinfo, host = parts.netloc.rsplit("@", 1)
    user, _, password = userinfo.partition(":")
    clean = urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))
    return clean, unquote(user) or None, unquote(password) or None


def source_auth(source: CalendarSource) -> tuple[str, str] | None:
    if not source.auth_username or not source.auth_password_enc:
        return None
    return source.auth_username, crypto.decrypt(source.auth_password_enc, password_context(source.id))


@dataclass(slots=True)
class Occurrence:
    id: str
    source_id: str
    title: str
    start: str  # ISO 8601 avec fuseau, ou AAAA-MM-JJ si journée entière
    end: str | None
    all_day: bool
    location: str | None


def parse_ics(text: str) -> icalendar.Calendar:
    try:
        cal = icalendar.Calendar.from_ical(text)
    except ValueError as exc:
        raise CalendarError("Fichier ICS invalide") from exc
    if not isinstance(cal, icalendar.Calendar):
        raise CalendarError("Fichier ICS invalide")
    return cal


def _iso(value: date | datetime, tz_default) -> tuple[str, bool]:  # noqa: ANN001
    if isinstance(value, datetime):
        if value.tzinfo is None:  # heure « flottante » : interprétée dans le fuseau de référence
            value = value.replace(tzinfo=tz_default)
        return value.isoformat(), False
    return value.isoformat(), True


def calendar_timezone(cal: icalendar.Calendar):  # noqa: ANN201
    """Fuseau de référence pour les heures « flottantes » (X-WR-TIMEZONE), UTC sinon."""
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    name = str(cal.get("X-WR-TIMEZONE", "") or "")
    try:
        return ZoneInfo(name) if name else UTC
    except (ZoneInfoNotFoundError, ValueError):
        return UTC


def expand(
    cal: icalendar.Calendar, source_id: str, start: datetime, end: datetime, tz_default=None
) -> list[Occurrence]:  # noqa: ANN001
    tz_default = tz_default or calendar_timezone(cal)
    out: list[Occurrence] = []
    query = recurring_ical_events.of(cal, skip_bad_series=True)
    for ev in query.between(start, end):
        if len(out) >= MAX_OCCURRENCES:
            break
        if str(ev.get("STATUS", "")).upper() == "CANCELLED":
            continue
        dtstart = ev.decoded("DTSTART")
        dtend = ev.decoded("DTEND") if "DTEND" in ev else None
        s, all_day = _iso(dtstart, tz_default)
        e = _iso(dtend, tz_default)[0] if dtend is not None else None
        uid = str(ev.get("UID", ""))
        out.append(
            Occurrence(
                id=hashlib.sha1(f"{source_id}|{uid}|{s}".encode(), usedforsecurity=False).hexdigest()[:20],
                source_id=source_id,
                title=html_to_text(str(ev.get("SUMMARY", "")), 200) or "(sans titre)",
                start=s,
                end=e,
                all_day=all_day,
                location=html_to_text(str(ev.get("LOCATION", "")), 200),
            )
        )
    return out


class CalendarProvider(Protocol):
    kind: str

    async def sync(self, db: AsyncSession, source: CalendarSource) -> None: ...


class IcsProvider:
    kind = "ics"

    async def fetch(
        self,
        url: str,
        etag: str | None = None,
        last_modified: str | None = None,
        auth: tuple[str, str] | None = None,
    ) -> net.FetchResult:
        headers = {"Accept": "text/calendar, */*;q=0.5"}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        res = await net.fetch(normalize_url(url), max_bytes=MAX_ICS_BYTES, headers=headers, timeout=20, basic_auth=auth)
        if res.status in (401, 403):
            raise CalendarError(
                "Accès refusé : vérifiez l'identifiant et le mot de passe"
                if auth
                else "Ce calendrier demande une connexion : renseignez l'identifiant et le mot de passe"
            )
        return res

    async def validate(self, url: str, auth: tuple[str, str] | None = None) -> int:
        res = await self.fetch(url, auth=auth)
        if res.status != 200:
            raise CalendarError(f"Le serveur a répondu HTTP {res.status}")
        cal = await asyncio.to_thread(parse_ics, res.content.decode("utf-8", "replace"))
        return len(cal.walk("VEVENT"))

    async def sync(self, db: AsyncSession, source: CalendarSource) -> None:
        source.last_sync_at = utcnow()
        try:
            url = crypto.decrypt(source.url_enc, url_context(source.id))
            res = await self.fetch(url, source.etag, source.last_modified, auth=source_auth(source))
            if res.status == 304:
                source.last_success_at, source.last_error = utcnow(), None
                await db.commit()
                return
            if res.status != 200:
                raise CalendarError(f"HTTP {res.status}")
            text = res.content.decode("utf-8", "replace")
            cal = await asyncio.to_thread(parse_ics, text)
        except (net.OutboundError, CalendarError, crypto.SecretKeyError) as exc:
            source.last_error = str(exc)[:500]
            await db.commit()
            return
        source.ics_cache = text
        source.event_count = len(cal.walk("VEVENT"))
        source.etag = (res.headers.get("etag") or "")[:300] or None
        source.last_modified = (res.headers.get("last-modified") or "")[:100] or None
        source.last_success_at, source.last_error = utcnow(), None
        _parsed_cache.pop(source.id, None)
        await db.commit()


PROVIDERS: dict[str, CalendarProvider] = {"ics": IcsProvider()}

# Cache des calendriers analysés, invalidé à chaque synchronisation
_parsed_cache: dict[object, tuple[datetime | None, icalendar.Calendar]] = {}


def parsed_calendar(source: CalendarSource) -> icalendar.Calendar | None:
    if not source.ics_cache:
        return None
    hit = _parsed_cache.get(source.id)
    if hit and hit[0] == source.last_success_at:
        return hit[1]
    cal = parse_ics(source.ics_cache)
    _parsed_cache[source.id] = (source.last_success_at, cal)
    return cal
