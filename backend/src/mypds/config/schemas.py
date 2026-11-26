from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

HEX = r"^#[0-9A-Fa-f]{6}$"


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Thème unique : glassmorphism. Le fond d'écran existe en version claire et sombre,
    # la version affichée suit color_mode. « custom » = fonds importés par l'utilisateur.
    background: Literal["nature", "abstract", "minimal", "it", "custom"] = "nature"
    color_mode: Literal["auto", "light", "dark"] = "auto"
    accent: str = Field(default="#0A84FF", pattern=HEX)
    blur: int = Field(default=24, ge=0, le=40)  # px
    transparency: int = Field(default=55, ge=20, le=90)  # opacité des surfaces, en %
    search_engine: Literal["google", "bing", "duckduckgo", "qwant", "custom"] = "google"
    search_custom_url: str | None = Field(default=None, max_length=300)
    search_autofocus: bool = True
    temperature_unit: Literal["celsius", "fahrenheit"] = "celsius"
    locale: Literal["auto", "fr", "en"] = "auto"  # « auto » : langue du navigateur
    # Empreintes des fonds d'écran importés (fixées par le serveur, ignorées en écriture)
    wallpaper_light: str | None = Field(default=None, max_length=16)
    wallpaper_dark: str | None = Field(default=None, max_length=16)

    @field_validator("search_custom_url")
    @classmethod
    def _custom(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not v.startswith(("https://", "http://")) or "%s" not in v:
            raise ValueError("L'URL doit commencer par http(s):// et contenir %s à la place des mots-clés")
        return v


class Branding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="My Personal Digital Space", max_length=60)
    short_title: str = Field(default="My Digital Space", max_length=30)
    subtitle: str = Field(default="Votre espace personnel", max_length=80)
    display: Literal["full", "short", "hidden"] = "full"
    show_logo: bool = True
    logo_position: Literal["top", "left", "right"] = "top"  # au-dessus, à gauche ou à droite du titre
    # Empreinte courte du logo importé (fixée par le serveur, ignorée en écriture). None = logo par défaut.
    logo_version: str | None = Field(default=None, max_length=16)
