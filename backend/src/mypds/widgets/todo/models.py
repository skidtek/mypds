import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from mypds.core.db import Base, utcnow


class TodoItem(Base):
    """Tâche d'un widget Todo de la Home. Cochée = clôturée (`done_at`), jamais supprimée d'office."""

    __tablename__ = "todo_item"
    __table_args__ = (Index("ix_todo_item_user_widget", "user_id", "widget_id"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"))
    widget_id: Mapped[str] = mapped_column(String(48))
    text: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
