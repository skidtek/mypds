import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mypds.core.db import Base, utcnow


class CalendarSource(Base):
    """Source ICS. L'URL est chiffrée (souvent porteuse d'un jeton) et jamais renvoyée au navigateur."""

    __tablename__ = "calendar_source"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="ics")
    name: Mapped[str] = mapped_column(String(80))
    color: Mapped[str] = mapped_column(String(7), default="#0A84FF")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    url_enc: Mapped[bytes] = mapped_column(LargeBinary)
    url_host: Mapped[str] = mapped_column(String(255))  # affichage seul (« calendar.google.com »)
    # Authentification HTTP Basic (SOGo, Nextcloud, serveurs d'entreprise) : mot de passe chiffré
    auth_username: Mapped[str | None] = mapped_column(String(255))
    auth_password_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    etag: Mapped[str | None] = mapped_column(String(300))
    last_modified: Mapped[str | None] = mapped_column(String(100))
    ics_cache: Mapped[str | None] = mapped_column(Text)
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
