"""Météo : qualité de l'air selon le lieu, nouveaux indicateurs (vent, pluie, UV)."""

import pytest

from mypds.widgets.weather import provider as wp


def test_air_scale_selon_le_lieu():
    assert wp.air_scale("Europe/Paris") == "eu"
    assert wp.air_scale("Atlantic/Canary") == "eu"
    assert wp.air_scale("America/New_York") == "us"
    assert wp.air_scale("Asia/Tokyo") == "us"


@pytest.mark.parametrize(
    ("index", "scale", "level"),
    [
        (10, "eu", 0),
        (20, "eu", 0),
        (21, "eu", 1),
        (75, "eu", 3),
        (140, "eu", 5),
        (42, "us", 0),
        (120, "us", 2),
        (350, "us", 5),
    ],
)
def test_air_level(index, scale, level):
    assert wp.air_level(index, scale) == level


FORECAST = {
    "timezone": "Europe/Paris",
    "utc_offset_seconds": 3600,
    "current": {
        "temperature_2m": 4.2,
        "apparent_temperature": 1.0,
        "weather_code": 61,
        "is_day": 1,
        "relative_humidity_2m": 88,
        "wind_speed_10m": 18.5,
        "wind_gusts_10m": 41.0,
        "wind_direction_10m": 250,
        "precipitation": 0.4,
    },
    "daily": {
        "time": ["2026-11-25"],
        "weather_code": [61],
        "temperature_2m_max": [6.0],
        "temperature_2m_min": [2.0],
        "sunrise": ["2026-11-25T08:21"],
        "sunset": ["2026-11-25T17:03"],
        "precipitation_sum": [3.2],
        "precipitation_probability_max": [80],
        "uv_index_max": [1.4],
        "wind_speed_10m_max": [32.0],
    },
}


async def test_report_complet(monkeypatch):
    calls: list[str] = []

    async def fake_get(self, url: str):
        calls.append(url)
        if url.startswith(wp.OpenMeteo.AIR):
            assert "european_aqi" in url
            return {"current": {"european_aqi": 34}}
        return FORECAST

    monkeypatch.setattr(wp.OpenMeteo, "_get", fake_get)
    r = await wp.OpenMeteo().report(49.44, 1.09, "celsius")
    assert r.current.wind_gusts == 41.0 and r.current.precipitation == 0.4
    assert r.days[0].precipitation_sum == 3.2 and r.days[0].uv_index_max == 1.4
    assert r.utc_offset_seconds == 3600
    assert r.air is not None and r.air.scale == "eu" and r.air.level == 1


async def test_air_facultatif(monkeypatch):
    async def fake_get(self, url: str):
        if url.startswith(wp.OpenMeteo.AIR):
            raise wp.net.OutboundError("indisponible")
        return FORECAST

    monkeypatch.setattr(wp.OpenMeteo, "_get", fake_get)
    r = await wp.OpenMeteo().report(49.44, 1.09, "celsius")
    assert r.air is None and r.current.temperature == 4.2
