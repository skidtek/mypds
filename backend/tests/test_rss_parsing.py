import pytest

from mypds.widgets.rss.parsing import FeedParseError, build_opml, parse_feed, parse_opml

RSS = b"""<?xml version="1.0"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
<channel><title>Exemple &amp; Co</title><link>https://exemple.org/</link>
<item><title>Premier &lt;b&gt;article&lt;/b&gt;</title><link>https://exemple.org/a</link>
<guid>a1</guid><pubDate>Tue, 24 Nov 2026 08:00:00 GMT</pubDate>
<description><![CDATA[<p>Bonjour <script>alert(1)</script><b>monde</b> <img src="https://img.exemple.org/x.jpg"></p>]]></description>
</item>
<item><title>Deuxi&#232;me</title><link>javascript:alert(1)</link><guid>a2</guid>
<media:thumbnail url="https://img.exemple.org/thumb.png"/></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Atom</title>
<entry><title>Entr\xc3\xa9e</title><id>urn:1</id><updated>2026-11-20T10:00:00Z</updated>
<link href="https://atom.example/1"/><summary>R\xc3\xa9sum\xc3\xa9</summary></entry></feed>"""


def test_rss() -> None:
    feed = parse_feed(RSS)
    assert feed.title == "Exemple & Co"
    first, second = feed.items
    assert first.title == "Premier article"
    assert "script" not in (first.summary_text or "") and "alert" not in (first.summary_text or "")
    assert first.summary_text == "Bonjour monde"
    assert first.image_url == "https://img.exemple.org/x.jpg"
    assert first.published_at.isoformat().startswith("2026-11-24T08:00")
    assert second.link is None  # schéma javascript: refusé
    assert second.image_url == "https://img.exemple.org/thumb.png"


def test_atom() -> None:
    feed = parse_feed(ATOM)
    assert feed.items[0].title == "Entrée"
    assert feed.items[0].link == "https://atom.example/1"


def test_entity_expansion_refused() -> None:
    bomb = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;">]><rss><channel/></rss>'
    with pytest.raises(FeedParseError):
        parse_feed(bomb)


def test_not_a_feed() -> None:
    with pytest.raises(FeedParseError):
        parse_feed(b"<html><body>Bonjour</body></html")


NETNEWSWIRE = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.1"><head><title>Subscriptions-iCloud.opml</title></head><body>
<outline text="Tech" title="Tech">
  <outline text="MacG" title="MacG" description="" type="rss" version="RSS" htmlUrl="https://www.macg.co/" xmlUrl="https://www.macg.co/rss.xml"/>
  <outline text="Sous-dossier"><outline text="Deep" type="rss" xmlUrl="https://deep.example/feed"/></outline>
</outline>
<outline text="Sans dossier" type="rss" xmlUrl="https://solo.example/atom"/>
<outline text="Mauvais" type="rss" xmlUrl="file:///etc/passwd"/>
</body></opml>"""


def test_opml_netnewswire() -> None:
    feeds = parse_opml(NETNEWSWIRE)
    assert [(f.title, f.category) for f in feeds] == [("MacG", "Tech"), ("Deep", "Tech"), ("Sans dossier", None)]
    assert feeds[0].html_url == "https://www.macg.co/"


def test_opml_roundtrip() -> None:
    data = build_opml({"Tech": [("MacG", "https://www.macg.co/rss.xml", None)], None: [("Solo", "https://s/x", None)]})
    feeds = parse_opml(data)
    assert {(f.title, f.category) for f in feeds} == {("MacG", "Tech"), ("Solo", None)}


def test_opml_rejects_entities() -> None:
    with pytest.raises(FeedParseError):
        parse_opml(b'<!DOCTYPE o [<!ENTITY x "y">]><opml><body/></opml>')


def test_discover_feed_links() -> None:
    from mypds.widgets.rss.parsing import discover_feed_links

    page = b"""<html><head>
    <link rel="stylesheet" href="/style.css">
    <link rel="alternate" type="application/rss+xml" title="" href="/feed.xml" />
    <link rel="alternate" type="application/atom+xml" href="https://site.example/atom">
    <link rel="alternate" type="application/rss+xml" href="javascript:alert(1)">
    </head><body>Bonjour</body></html>"""
    assert discover_feed_links(page, "https://site.example/blog/") == [
        "https://site.example/feed.xml",
        "https://site.example/atom",
    ]
    assert discover_feed_links(b"<html><body>rien</body></html>", "https://x.example/") == []
