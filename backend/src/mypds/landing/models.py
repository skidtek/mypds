import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mypds.core.db import Base, utcnow


class LandingLayoutRow(Base):
    """Disposition de la Landing — table distincte de celle du Cockpit (ADR-0008)."""

    __tablename__ = "landing_layout"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer)
    document: Mapped[dict[str, Any]] = mapped_column(JSONB)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
