import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mypds.core.db import Base, utcnow


class RssCategory(Base):
    __tablename__ = "rss_category"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    position: Mapped[int] = mapped_column(Integer, default=0)


class RssFeed(Base):
    __tablename__ = "rss_feed"
    __table_args__ = (UniqueConstraint("user_id", "feed_url"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rss_category.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200))
    feed_url: Mapped[str] = mapped_column(String(1000))
    site_url: Mapped[str | None] = mapped_column(String(1000))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    etag: Mapped[str | None] = mapped_column(String(300))
    last_modified: Mapped[str | None] = mapped_column(String(100))
    last_fetch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(500))
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RssItem(Base):
    __tablename__ = "rss_item"
    __table_args__ = (UniqueConstraint("feed_id", "guid_hash"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    feed_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rss_feed.id", ondelete="CASCADE"), index=True)
    guid_hash: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(500))
    link: Mapped[str | None] = mapped_column(String(2000))
    author: Mapped[str | None] = mapped_column(String(200))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    summary_text: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(2000))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
