"""Fournisseurs météo interchangeables. Par défaut : Open-Meteo (gratuit, sans clé)."""

import json
import time
from datetime import date, datetime
from typing import Literal, Protocol

from pydantic import BaseModel

from mypds.core import net

Condition = Literal[
    "clear", "partly-cloudy", "cloudy", "fog", "drizzle", "rain", "snow", "showers", "thunderstorm", "unknown"
]

# Codes météo WMO (utilisés par Open-Meteo) → condition neutre + libellé
_WMO: dict[int, tuple[Condition, str]] = {
    0: ("clear", "Ciel dégagé"),
    1: ("partly-cloudy", "Plutôt dégagé"),
    2: ("partly-cloudy", "Éclaircies"),
    3: ("cloudy", "Couvert"),
    45: ("fog", "Brouillard"),
    48: ("fog", "Brouillard givrant"),
    51: ("drizzle", "Bruine légère"),
    53: ("drizzle", "Bruine"),
    55: ("drizzle", "Bruine dense"),
    56: ("drizzle", "Bruine verglaçante"),
    57: ("drizzle", "Bruine verglaçante"),
    61: ("rain", "Pluie faible"),
    63: ("rain", "Pluie"),
    65: ("rain", "Pluie forte"),
    66: ("rain", "Pluie verglaçante"),
    67: ("rain", "Pluie verglaçante"),
    71: ("snow", "Neige faible"),
    73: ("snow", "Neige"),
    75: ("snow", "Neige forte"),
    77: ("snow", "Grains de neige"),
    80: ("showers", "Averses"),
    81: ("showers", "Averses"),
    82: ("showers", "Averses violentes"),
    85: ("snow", "Averses de neige"),
    86: ("snow", "Averses de neige"),
    95: ("thunderstorm", "Orage"),
    96: ("thunderstorm", "Orage avec grêle"),
    99: ("thunderstorm", "Orage avec grêle"),
}


def describe(code: int | None) -> tuple[Condition, str]:
    return _WMO.get(code if code is not None else -1, ("unknown", "Inconnu"))


class Current(BaseModel):
    temperature: float
    apparent_temperature: float | None
    condition: Condition
    label: str
    is_day: bool
    humidity: float | None
    wind_speed: float | None
    wind_gusts: float | None = None
    wind_direction: float | None = None  # degrés, d'où vient le vent
    precipitation: float | None = None  # mm, dernière heure


class Day(BaseModel):
    date: date
    condition: Condition
    label: str
    temp_min: float
    temp_max: float
    sunrise: str | None  # heure locale du lieu, « HH:MM »
    sunset: str | None
    precipitation_sum: float | None = None  # mm
    precipitation_probability: float | None = None  # %
    uv_index_max: float | None = None
    wind_max: float | None = None


class AirQuality(BaseModel):
    """Indice de qualité de l'air, échelle choisie selon le lieu (européenne en Europe, américaine ailleurs)."""

    scale: Literal["eu", "us"]
    index: float
    level: int  # 0 (bon) à 5 (extrêmement mauvais / dangereux), commun aux deux échelles


class WeatherReport(BaseModel):
    provider: str
    attribution: str
    timezone: str
    utc_offset_seconds: int = 0
    unit: Literal["celsius", "fahrenheit"]
    fetched_at: datetime
    current: Current
    days: list[Day]
    air: AirQuality | None = None


class Place(BaseModel):
    name: str
    admin: str | None
    country: str | None
    latitude: float
    longitude: float
    timezone: str | None


class WeatherProvider(Protocol):
    name: str

    async def report(self, lat: float, lon: float, unit: str) -> WeatherReport: ...
    async def geocode(self, query: str) -> list[Place]: ...


def _hhmm(iso: str | None) -> str | None:
    return iso[11:16] if iso and len(iso) >= 16 else None


# Europe géographique hors fuseaux « Europe/* » (Canaries, Madère, Açores, Féroé, Islande)
_EU_EXTRA = {"Atlantic/Canary", "Atlantic/Madeira", "Atlantic/Azores", "Atlantic/Faroe", "Atlantic/Reykjavik"}
_EU_STEPS = (20, 40, 60, 80, 100)  # Bon, Correct, Modéré, Mauvais, Très mauvais, Extrêmement mauvais
_US_STEPS = (50, 100, 150, 200, 300)  # Good … Hazardous


def air_scale(timezone: str) -> Literal["eu", "us"]:
    return "eu" if timezone.startswith("Europe/") or timezone in _EU_EXTRA else "us"


def air_level(index: float, scale: str) -> int:
    steps = _EU_STEPS if scale == "eu" else _US_STEPS
    return next((i for i, s in enumerate(steps) if index <= s), len(steps))


def _at(values: list | None, i: int):
    return values[i] if values and i < len(values) else None


class OpenMeteo:
    name = "open-meteo"
    FORECAST = "https://api.open-meteo.com/v1/forecast"
    GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
    AIR = "https://air-quality-api.open-meteo.com/v1/air-quality"

    async def _get(self, url: str) -> dict:
        res = await net.fetch(url, max_bytes=512 * 1024, timeout=10)
        if res.status != 200:
            raise net.OutboundError(f"Service météo indisponible (HTTP {res.status})")
        return json.loads(res.content)

    async def report(self, lat: float, lon: float, unit: str) -> WeatherReport:
        url = (
            f"{self.FORECAST}?latitude={lat:.4f}&longitude={lon:.4f}"
            "&current=temperature_2m,apparent_temperature,weather_code,is_day,relative_humidity_2m,wind_speed_10m,"
            "wind_gusts_10m,wind_direction_10m,precipitation"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_sum,"
            "precipitation_probability_max,uv_index_max,wind_speed_10m_max"
            f"&timezone=auto&forecast_days=8&temperature_unit={unit}"
        )
        data = await self._get(url)
        cur = data["current"]
        cond, label = describe(cur.get("weather_code"))
        d = data["daily"]
        days = []
        for i, day in enumerate(d["time"]):
            c, lab = describe(d["weather_code"][i])
            days.append(
                Day(
                    date=day,
                    condition=c,
                    label=lab,
                    temp_min=d["temperature_2m_min"][i],
                    temp_max=d["temperature_2m_max"][i],
                    sunrise=_hhmm(d["sunrise"][i]),
                    sunset=_hhmm(d["sunset"][i]),
                    precipitation_sum=_at(d.get("precipitation_sum"), i),
                    precipitation_probability=_at(d.get("precipitation_probability_max"), i),
                    uv_index_max=_at(d.get("uv_index_max"), i),
                    wind_max=_at(d.get("wind_speed_10m_max"), i),
                )
            )
        tz = data.get("timezone", "UTC")
        return WeatherReport(
            provider=self.name,
            attribution="Données météo : Open-Meteo.com (CC BY 4.0)",
            timezone=tz,
            utc_offset_seconds=int(data.get("utc_offset_seconds") or 0),
            unit=unit,  # type: ignore[arg-type]
            fetched_at=datetime.now().astimezone(),
            current=Current(
                temperature=cur["temperature_2m"],
                apparent_temperature=cur.get("apparent_temperature"),
                condition=cond,
                label=label,
                is_day=bool(cur.get("is_day", 1)),
                humidity=cur.get("relative_humidity_2m"),
                wind_speed=cur.get("wind_speed_10m"),
                wind_gusts=cur.get("wind_gusts_10m"),
                wind_direction=cur.get("wind_direction_10m"),
                precipitation=cur.get("precipitation"),
            ),
            days=days,
            air=await self.air(lat, lon, tz),
        )

    async def air(self, lat: float, lon: float, timezone: str) -> AirQuality | None:
        """Facultatif : une panne du service qualité de l'air ne prive pas de la météo."""
        scale = air_scale(timezone)
        field = "european_aqi" if scale == "eu" else "us_aqi"
        try:
            data = await self._get(f"{self.AIR}?latitude={lat:.4f}&longitude={lon:.4f}&current={field}&timezone=auto")
            value = data["current"][field]
        except (net.OutboundError, KeyError, ValueError, TypeError):
            return None
        if value is None:
            return None
        return AirQuality(scale=scale, index=float(value), level=air_level(float(value), scale))

    async def geocode(self, query: str) -> list[Place]:
        from urllib.parse import quote

        data = await self._get(f"{self.GEOCODE}?name={quote(query)}&count=6&language=fr&format=json")
        return [
            Place(
                name=r["name"],
                admin=r.get("admin1"),
                country=r.get("country"),
                latitude=r["latitude"],
                longitude=r["longitude"],
                timezone=r.get("timezone"),
            )
            for r in data.get("results", [])
        ]


class TTLCache:
    def __init__(self, ttl: float, maxsize: int = 256) -> None:
        self.ttl, self.maxsize = ttl, maxsize
        self._data: dict[object, tuple[float, object]] = {}

    def get(self, key: object) -> object | None:
        hit = self._data.get(key)
        if hit and hit[0] > time.monotonic():
            return hit[1]
        return None

    def set(self, key: object, value: object) -> None:
        if len(self._data) >= self.maxsize:
            self._data.pop(next(iter(self._data)))
        self._data[key] = (time.monotonic() + self.ttl, value)


PROVIDERS: dict[str, WeatherProvider] = {"open-meteo": OpenMeteo()}
DEFAULT_PROVIDER = "open-meteo"
