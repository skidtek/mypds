import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mypds.core.db import Base, utcnow


class Alert(Base):
    """Alerte calculée à partir de l'état réel d'un connecteur. Une alerte « firing » est résolue
    automatiquement dès que la condition disparaît ; l'historique reste consultable."""

    __tablename__ = "alert"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    connector_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("connector_instance.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(160), index=True)  # identité stable de la condition
    kind: Mapped[str] = mapped_column(String(40))
    resource: Mapped[str | None] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(16))  # warning | critical
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str | None] = mapped_column(String(500))
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # pour la traduction côté interface
    state: Mapped[str] = mapped_column(String(16), default="firing", index=True)  # firing | resolved
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
