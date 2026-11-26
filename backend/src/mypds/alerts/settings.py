"""Seuils d'alerte réglables (communs à tous les utilisateurs, modifiables par un administrateur)."""

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from mypds.config.models import AppSetting

KEY = "alerts"


class AlertSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cpu_warn: int = Field(default=85, ge=70, le=100)
    cpu_crit: int = Field(default=95, ge=70, le=100)
    cpu_minutes: int = Field(default=5, ge=1, le=30)  # durée pendant laquelle le CPU doit rester au-dessus
    mem_warn: int = Field(default=85, ge=70, le=100)
    mem_crit: int = Field(default=95, ge=70, le=100)
    disk_warn: int = Field(default=85, ge=70, le=100)
    disk_crit: int = Field(default=95, ge=70, le=100)

    @model_validator(mode="after")
    def _order(self) -> "AlertSettings":
        for kind in ("cpu", "mem", "disk"):
            if getattr(self, f"{kind}_warn") > getattr(self, f"{kind}_crit"):
                raise ValueError("Le seuil d'avertissement doit être inférieur ou égal au seuil critique")
        return self


async def load(db: AsyncSession) -> AlertSettings:
    row = await db.get(AppSetting, KEY)
    return AlertSettings.model_validate(row.value) if row else AlertSettings()


async def save(db: AsyncSession, value: AlertSettings) -> None:
    row = await db.get(AppSetting, KEY)
    if row is None:
        db.add(AppSetting(key=KEY, value=value.model_dump()))
    else:
        row.value = value.model_dump()
