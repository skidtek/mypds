"""Modèle de disposition de la Landing Page (mypds.landing-layout, version 1).

Disposition libre : grille à colonnes, placement automatique quand `placement.<bp>` est nul,
ordre mobile indépendant si `mobile.mode == "custom"`. Aucune donnée secrète n'y figure :
les widgets référencent des identifiants (catégories RSS, calendriers).
"""

import uuid
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA = "mypds.landing-layout"
CURRENT_VERSION = 1
COLUMNS = {"desktop": 12, "tablet": 8}
MAX_WIDGETS = 60
WidgetId = Annotated[str, Field(pattern=r"^w_[A-Za-z0-9_-]{1,40}$")]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Placement(Strict):
    x: int = Field(ge=0, le=11)
    y: int = Field(ge=0, le=500)
    w: int = Field(ge=1, le=12)
    h: int = Field(ge=1, le=12)


class Placements(Strict):
    desktop: Placement | None = None
    tablet: Placement | None = None
    mobile_h: int | None = Field(default=None, ge=1, le=12)

    @model_validator(mode="after")
    def _bounds(self) -> "Placements":
        for bp, cols in COLUMNS.items():
            pl: Placement | None = getattr(self, bp)
            if pl and pl.x + pl.w > cols:
                raise ValueError(f"Le widget dépasse la grille {bp} ({cols} colonnes)")
        return self


class SearchConfig(Strict):
    pass


class WeatherConfig(Strict):
    label: str = Field(default="", max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    forecast_days: int = Field(default=5, ge=0, le=7)


class CalendarConfig(Strict):
    source_ids: list[uuid.UUID] | None = None  # None = tous les calendriers actifs
    days_ahead: int = Field(default=7, ge=1, le=60)
    max_events: int = Field(default=6, ge=1, le=30)


class NewsConfig(Strict):
    category_ids: list[uuid.UUID] | None = None  # None = toutes les catégories
    count: int = Field(default=9, ge=1, le=30)


class TodoConfig(Strict):
    shape: Literal["square", "round"] = "square"  # forme des cases à cocher


class NoteConfig(Strict):
    pass  # couleur et texture sont propres à chaque post-it (table note)


CONFIG_MODELS: dict[str, type[Strict]] = {
    "search": SearchConfig,
    "weather": WeatherConfig,
    "calendar": CalendarConfig,
    "news": NewsConfig,
    "todo": TodoConfig,
    "note": NoteConfig,
}


class Widget(Strict):
    id: WidgetId
    type: Literal["search", "weather", "calendar", "news", "todo", "note"]
    title: str | None = Field(default=None, max_length=60)
    hidden: bool = False
    config: dict[str, Any] = Field(default_factory=dict)
    placement: Placements = Field(default_factory=Placements)

    @model_validator(mode="after")
    def _config(self) -> "Widget":
        self.config = CONFIG_MODELS[self.type].model_validate(self.config).model_dump(mode="json")
        return self


class MobileLayout(Strict):
    mode: Literal["auto", "custom"] = "auto"
    order: list[WidgetId] = Field(default_factory=list)


class LandingLayout(Strict):
    schema_: Literal["mypds.landing-layout"] = Field(default=SCHEMA, alias="schema")
    version: Literal[1] = 1
    widgets: list[Widget] = Field(default_factory=list, max_length=MAX_WIDGETS)
    mobile: MobileLayout = Field(default_factory=MobileLayout)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="after")
    def _ids(self) -> "LandingLayout":
        ids = [w.id for w in self.widgets]
        if len(ids) != len(set(ids)):
            raise ValueError("Identifiants de widgets en double")
        known = set(ids)
        self.mobile.order = [i for i in dict.fromkeys(self.mobile.order) if i in known]
        return self

    def dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)


def migrate(document: dict[str, Any]) -> dict[str, Any]:
    """Migre un document ancien vers la version courante (chaîne de fonctions pures)."""
    version = document.get("version")
    if version == CURRENT_VERSION:
        return document
    raise ValueError(f"Version de disposition non prise en charge : {version}")


def default_layout() -> LandingLayout:
    def w(wid: str, type_: str, d: tuple[int, int, int, int], t: tuple[int, int, int, int], cfg=None):  # noqa: ANN001
        return {
            "id": wid,
            "type": type_,
            "config": cfg or {},
            "placement": {
                "desktop": dict(zip("xywh", d, strict=True)),
                "tablet": dict(zip("xywh", t, strict=True)),
            },
        }

    return LandingLayout.model_validate(
        {
            "schema": SCHEMA,
            "version": 1,
            "widgets": [
                w("w_search", "search", (0, 0, 12, 1), (0, 0, 8, 1)),
                w(
                    "w_weather",
                    "weather",
                    (0, 1, 6, 3),
                    (0, 1, 4, 3),
                    {"label": "Paris", "latitude": 48.8566, "longitude": 2.3522},
                ),
                w("w_calendar", "calendar", (6, 1, 6, 3), (4, 1, 4, 3)),
                w("w_news", "news", (0, 4, 12, 4), (0, 4, 8, 5)),
            ],
        }
    )
