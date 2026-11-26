"""Analyse sûre des flux RSS/Atom et des fichiers OPML (fonctions pures, testables)."""

import calendar
import hashlib
import html
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import feedparser
import nh3
from defusedxml import ElementTree as SafeET

MAX_SUMMARY = 400
_WS = re.compile(r"\s+")
_IMG = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.IGNORECASE)
_ENTITY_DECL = re.compile(rb"<!ENTITY", re.IGNORECASE)


class FeedParseError(ValueError):
    pass


def safe_http_url(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    return url if url.lower().startswith(("http://", "https://")) and len(url) <= 2000 else None


def html_to_text(value: str | None, limit: int = MAX_SUMMARY) -> str | None:
    if not value:
        return None
    text = html.unescape(nh3.clean(value, tags=set()))
    text = _WS.sub(" ", text).strip()
    if len(text) > limit:
        text = text[: limit - 1].rsplit(" ", 1)[0] + "…"
    return text or None


@dataclass(slots=True)
class ParsedItem:
    guid_hash: str
    title: str
    link: str | None
    author: str | None
    published_at: datetime
    summary_text: str | None
    image_url: str | None


@dataclass(slots=True)
class ParsedFeed:
    title: str | None
    site_url: str | None
    items: list[ParsedItem] = field(default_factory=list)


def _image(entry: Any) -> str | None:
    for key in ("media_thumbnail", "media_content"):
        for media in entry.get(key) or []:
            url = safe_http_url(media.get("url"))
            mtype = media.get("type", "") or ""
            medium = media.get("medium", "") or ""
            if url and (key == "media_thumbnail" or medium == "image" or mtype.startswith("image/")):
                return url
    for enc in entry.get("enclosures") or []:
        if (enc.get("type") or "").startswith("image/"):
            url = safe_http_url(enc.get("href") or enc.get("url"))
            if url:
                return url
    for content in [*(entry.get("content") or []), {"value": entry.get("summary", "")}]:
        m = _IMG.search(content.get("value") or "")
        if m:
            url = safe_http_url(html.unescape(m.group(1)))
            if url:
                return url
    return None


def _date(entry: Any, fallback: datetime) -> datetime:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        st = entry.get(key)
        if st:
            try:
                return datetime.fromtimestamp(calendar.timegm(st), tz=UTC)
            except (OverflowError, ValueError):
                continue
    return fallback


def parse_feed(content: bytes, now: datetime | None = None) -> ParsedFeed:
    if _ENTITY_DECL.search(content[:4096]):
        raise FeedParseError("Flux refusé : déclaration d'entités XML")
    now = now or datetime.now(UTC)
    parsed = feedparser.parse(content, sanitize_html=False, resolve_relative_uris=False)
    if parsed.get("bozo") and not parsed.entries:
        raise FeedParseError("Ce document n'est pas un flux RSS ou Atom valide")
    feed = parsed.feed
    out = ParsedFeed(
        title=html_to_text(feed.get("title"), 200),
        site_url=safe_http_url(feed.get("link")),
    )
    for entry in parsed.entries[:200]:
        link = safe_http_url(entry.get("link"))
        title = html_to_text(entry.get("title"), 500) or "(sans titre)"
        guid = entry.get("id") or link or title
        summary_src = entry.get("summary") or next(
            (c.get("value") for c in entry.get("content") or [] if c.get("value")), None
        )
        out.items.append(
            ParsedItem(
                guid_hash=hashlib.sha256(guid.encode()).hexdigest(),
                title=title,
                link=link,
                author=html_to_text(entry.get("author"), 200),
                published_at=min(_date(entry, now), now),
                summary_text=html_to_text(summary_src),
                image_url=_image(entry),
            )
        )
    return out


@dataclass(slots=True)
class OpmlFeed:
    title: str
    xml_url: str
    html_url: str | None
    category: str | None


def parse_opml(content: bytes, max_feeds: int = 2000) -> list[OpmlFeed]:
    """OPML 1.0/2.0, dont les exports NetNewsWire (dossiers = outlines imbriqués)."""
    try:
        root = SafeET.fromstring(content)
    except Exception as exc:  # defusedxml lève des exceptions variées
        raise FeedParseError("Fichier OPML invalide") from exc
    body = root.find("body")
    if body is None:
        raise FeedParseError("Fichier OPML sans élément <body>")
    feeds: list[OpmlFeed] = []

    def walk(node: Any, category: str | None) -> None:
        for outline in node.findall("outline"):
            xml_url = safe_http_url(outline.get("xmlUrl"))
            name = (outline.get("title") or outline.get("text") or "").strip()
            if xml_url:
                if len(feeds) >= max_feeds:
                    return
                feeds.append(
                    OpmlFeed(
                        title=name[:200] or xml_url,
                        xml_url=xml_url,
                        html_url=safe_http_url(outline.get("htmlUrl")),
                        category=category,
                    )
                )
            else:
                # Dossier : les sous-dossiers sont rattachés au dossier de premier niveau
                walk(outline, category or (name[:80] or None))

    walk(body, None)
    return feeds


def build_opml(categories: dict[str | None, list[tuple[str, str, str | None]]]) -> bytes:
    from xml.etree.ElementTree import Element, SubElement, tostring  # noqa: S405 - génération seule

    root = Element("opml", version="2.0")
    head = SubElement(root, "head")
    SubElement(head, "title").text = "My Personal Digital Space — abonnements"
    body = SubElement(root, "body")
    for cat, feeds in categories.items():
        parent = body if cat is None else SubElement(body, "outline", text=cat, title=cat)
        for title, xml_url, html_url in feeds:
            attrs = {"type": "rss", "text": title, "title": title, "xmlUrl": xml_url}
            if html_url:
                attrs["htmlUrl"] = html_url
            SubElement(parent, "outline", attrs)
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="utf-8")


# JSON Feed (application/feed+json) n'est pas encore pris en charge par le lecteur
FEED_TYPES = {"application/rss+xml", "application/atom+xml", "application/rdf+xml"}


def discover_feed_links(content: bytes, base_url: str, limit: int = 5) -> list[str]:
    """Découverte automatique (comme NetNewsWire) : <link rel="alternate" type="application/rss+xml" href="…">."""
    from html.parser import HTMLParser
    from urllib.parse import urljoin

    found: list[str] = []

    class _Links(HTMLParser):
        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag != "link" or len(found) >= limit:
                return
            a = {k.lower(): (v or "") for k, v in attrs}
            rels = a.get("rel", "").lower().split()
            if "alternate" in rels and a.get("type", "").lower().split(";")[0].strip() in FEED_TYPES and a.get("href"):
                url = safe_http_url(urljoin(base_url, a["href"].strip()))
                if url and url not in found:
                    found.append(url)

    import contextlib

    # HTML mal formé : on garde les liens trouvés avant l'erreur
    with contextlib.suppress(Exception):
        _Links().feed(content[: 512 * 1024].decode("utf-8", "replace"))
    return found
