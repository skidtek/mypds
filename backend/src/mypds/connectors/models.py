import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mypds.core.db import Base, TimestampMixin


class ConnectorInstance(TimestampMixin, Base):
    """Instance configurée par un administrateur. Secrets chiffrés (AES-GCM), jamais exportés."""

    __tablename__ = "connector_instance"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(80))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    secrets_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    poll_interval_s: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(16), default="unknown")  # ok | degraded | error | unknown
    last_ok_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(500))
