import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mypds.core.db import Base, utcnow


class Note(Base):
    """Post-it d'un widget Post-it de la Home : un onglet (intercalaire) par note."""

    __tablename__ = "note"
    __table_args__ = (Index("ix_note_user_widget", "user_id", "widget_id"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"))
    widget_id: Mapped[str] = mapped_column(String(48))
    title: Mapped[str] = mapped_column(String(40), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    color: Mapped[str] = mapped_column(String(16), default="yellow")
    texture: Mapped[str] = mapped_column(String(16), default="plain")
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
