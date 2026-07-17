"""Per-user data — watchlist / holdings / bookmarks / alerts / saved events / prefs.

Hamısı user_id FK ON DELETE CASCADE + kompozit UNIQUE (idempotent upsert) + cap
(service invariant). NUMERIC (Float YOX) + CHECK(qty>0 AND <=1e12) bir konstraintlə
NaN/±Inf/sıfır/mənfini öldürür (Postgres sıralamasında NaN>0 TRUE, amma NaN<=1e12 FALSE).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

_MAX = "1000000000000"  # 1e12


def _uid_fk():
    return mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


def _pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _created():
    return mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UserWatchlist(Base):
    __tablename__ = "user_watchlist"
    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _uid_fk()
    asset_key: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = _created()
    __table_args__ = (
        UniqueConstraint("user_id", "asset_key", name="uq_user_watchlist"),
        Index("ix_user_watchlist_user", "user_id", "created_at"),
    )


class UserHolding(Base, TimestampMixin):
    __tablename__ = "user_holdings"
    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _uid_fk()
    asset_key: Mapped[str] = mapped_column(String(32), nullable=False)
    qty: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False)
    avg_cost: Mapped[float | None] = mapped_column(Numeric(24, 8))
    __table_args__ = (
        UniqueConstraint("user_id", "asset_key", name="uq_user_holdings"),
        Index("ix_user_holdings_user", "user_id"),
        CheckConstraint(f"qty > 0 AND qty <= {_MAX}", name="ck_holding_qty"),
        CheckConstraint(
            f"avg_cost IS NULL OR (avg_cost >= 0 AND avg_cost <= {_MAX})",
            name="ck_holding_cost",
        ),
    )


class UserBookmark(Base):
    __tablename__ = "user_bookmarks"
    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _uid_fk()
    news_id: Mapped[int] = mapped_column(
        ForeignKey("news.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = _created()
    __table_args__ = (
        UniqueConstraint("user_id", "news_id", name="uq_user_bookmarks"),
        Index("ix_user_bookmarks_user", "user_id", created_at.desc()),
    )


class UserAlert(Base):
    __tablename__ = "user_alerts"
    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _uid_fk()
    asset_key: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str | None] = mapped_column(String(64))
    direction: Mapped[str] = mapped_column(String(5), nullable=False)  # above|below
    price: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()
    __table_args__ = (
        UniqueConstraint("user_id", "asset_key", "direction", "price", name="uq_user_alerts"),
        Index("ix_user_alerts_user", "user_id"),
        CheckConstraint("direction IN ('above','below')", name="ck_alert_direction"),
        CheckConstraint(f"price > 0 AND price <= {_MAX}", name="ck_alert_price"),
    )


class UserSavedEvent(Base):
    __tablename__ = "user_saved_events"
    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = _uid_fk()
    event_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    __table_args__ = (
        UniqueConstraint("user_id", "event_key", name="uq_user_saved_events"),
        Index("ix_user_saved_events_user", "user_id", saved_at.desc()),
    )


class UserPrefs(Base, TimestampMixin):
    __tablename__ = "user_prefs"
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lang: Mapped[str] = mapped_column(
        String(5), nullable=False, default="az", server_default="az"
    )
    theme: Mapped[str | None] = mapped_column(String(5))
