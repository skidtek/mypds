from datetime import UTC, datetime

from mypds.widgets.calendar.service import expand, normalize_url, parse_ics

ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//FR
BEGIN:VTIMEZONE
TZID:Europe/Paris
BEGIN:STANDARD
DTSTART:19701025T030000
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:19700329T020000
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
UID:weekly-1
DTSTART;TZID=Europe/Paris:20261102T110000
DTEND;TZID=Europe/Paris:20261102T120000
RRULE:FREQ=WEEKLY;COUNT=10
EXDATE;TZID=Europe/Paris:20261130T110000
SUMMARY:Réunion projet
LOCATION:Visio
END:VEVENT
BEGIN:VEVENT
UID:allday-1
DTSTART;VALUE=DATE:20261126
DTEND;VALUE=DATE:20261127
SUMMARY:Journée entière
END:VEVENT
BEGIN:VEVENT
UID:cancel-1
DTSTART:20261125T150000Z
SUMMARY:Annulé
STATUS:CANCELLED
END:VEVENT
END:VCALENDAR
"""


def test_recurrence_timezone_exdate() -> None:
    cal = parse_ics(ICS)
    occ = expand(cal, "s1", datetime(2026, 11, 20, tzinfo=UTC), datetime(2026, 12, 10, tzinfo=UTC))
    meetings = [o for o in occ if o.title == "Réunion projet"]
    # 23/11 et 07/12 ; le 30/11 est exclu par EXDATE
    assert [m.start for m in meetings] == ["2026-11-23T11:00:00+01:00", "2026-12-07T11:00:00+01:00"]
    assert meetings[0].location == "Visio"
    allday = [o for o in occ if o.all_day]
    assert allday[0].start == "2026-11-26"
    assert not [o for o in occ if o.title == "Annulé"]


def test_webcal() -> None:
    assert normalize_url(" webcal://p.example/cal.ics") == "https://p.example/cal.ics"


def test_split_credentials() -> None:
    from mypds.widgets.calendar.service import split_credentials

    assert split_credentials("https://jdupont@dav.example.org/SOGo/dav/jdupont/Calendar/personal.ics") == (
        "https://dav.example.org/SOGo/dav/jdupont/Calendar/personal.ics",
        "jdupont",
        None,
    )
    assert split_credentials("https://a%40b:p%3Ass@h.example/c.ics") == ("https://h.example/c.ics", "a@b", "p:ss")
    assert split_credentials("https://h.example/c.ics") == ("https://h.example/c.ics", None, None)


async def test_basic_auth_refused_over_http() -> None:
    import pytest

    from mypds.core import net

    with pytest.raises(net.OutboundError, match="non chiffrée"):
        await net.fetch("http://cal.example.org/c.ics", max_bytes=10, basic_auth=("u", "p"))
