import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mypds.core.db import Base, utcnow


class CockpitLayoutRow(Base):
    """Disposition du Cockpit — table distincte de celle de la Landing (ADR-0008)."""

    __tablename__ = "cockpit_layout"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer)
    document: Mapped[dict[str, Any]] = mapped_column(JSONB)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class IconAsset(Base):
    """Logo importé pour une tuile (PNG, JPEG ou WebP vérifiés)."""

    __tablename__ = "icon_asset"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    content_type: Mapped[str] = mapped_column(String(32))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
