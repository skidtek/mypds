from typing import Literal

from fastapi import APIRouter, Depends, Query

from mypds.auth.deps import Principal, current_principal
from mypds.core import net
from mypds.core.http import problem
from mypds.widgets.weather.provider import DEFAULT_PROVIDER, PROVIDERS, Place, TTLCache, WeatherReport

router = APIRouter(prefix="/api/v1/weather", tags=["weather"])
_reports = TTLCache(ttl=15 * 60)
_places = TTLCache(ttl=24 * 3600)


@router.get("", response_model=WeatherReport)
async def weather(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    unit: Literal["celsius", "fahrenheit"] = "celsius",
    _: Principal = Depends(current_principal),
):
    key = (round(lat, 3), round(lon, 3), unit)
    cached = _reports.get(key)
    if cached:
        return cached
    try:
        report = await PROVIDERS[DEFAULT_PROVIDER].report(key[0], key[1], unit)
    except (net.OutboundError, KeyError, ValueError) as exc:
        raise problem(502, f"Météo indisponible : {exc}") from exc
    _reports.set(key, report)
    return report


@router.get("/geocode", response_model=list[Place])
async def geocode(q: str = Query(min_length=2, max_length=80), _: Principal = Depends(current_principal)):
    key = q.strip().lower()
    cached = _places.get(key)
    if cached is not None:
        return cached
    try:
        places = await PROVIDERS[DEFAULT_PROVIDER].geocode(q.strip())
    except (net.OutboundError, KeyError, ValueError) as exc:
        raise problem(502, f"Recherche de lieu indisponible : {exc}") from exc
    _places.set(key, places)
    return places
