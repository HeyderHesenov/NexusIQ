"""Xəbər ↔ aktiv bağlantısı — şəxsi digest, portfel və doğruluq kartının bünövrəsi.

Hər sətir bir xəbərin bir aktivə toxunduğunu göstərir:
  - source="detected": xəbər mətnində aktiv aşkarlandı (deterministik, AI YOX).
  - source="forecast":  AI proqnozu bu aktivi göstərdi (istiqamət dondurulur →
    sonradan real qiymət hərəkəti ilə point-in-time qiymətləndirilir).

Denormalizasiya (published_at + sentiment + impact_score) məqsədlə saxlanır ki,
per-asset digest/scorecard sorğuları `news`-ə join olmadan indekslə işləsin.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.news import News


class NewsAsset(Base, TimestampMixin):
    """Bir xəbərin bir aktivə toxunması (aşkarlanmış və ya proqnozlaşdırılmış)."""

    __tablename__ = "news_asset"

    id: Mapped[int] = mapped_column(primary_key=True)

    news_id: Mapped[int] = mapped_column(
        ForeignKey("news.id", ondelete="CASCADE"), nullable=False
    )
    # Reyestr açarı (btc, nvda, eurusd...) və ya dinamik coin (c_<base>).
    asset_key: Mapped[str] = mapped_column(String(32), nullable=False)
    # `news.published_at`-dan denormalizasiya — join-suz per-asset zaman sorğusu.
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # "detected" | "forecast"
    source: Mapped[str] = mapped_column(String(10), nullable=False)
    # up | down | mixed | neutral
    impact_dir: Mapped[str | None] = mapped_column(String(8))
    sentiment: Mapped[float | None] = mapped_column(Float)  # link vaxtı kopya
    impact_score: Mapped[float | None] = mapped_column(Float)  # link vaxtı kopya

    # ---- Proqnoz qiymətləndirməsi (yalnız source="forecast") ----
    # Generasiya vaxtı DONDURULMUŞ istiqamət (point-in-time; lookahead yox).
    scored_dir: Mapped[str | None] = mapped_column(String(8))
    ret_1: Mapped[float | None] = mapped_column(Float)  # +1 ticarət günü % gəlir
    ret_5: Mapped[float | None] = mapped_column(Float)  # +5 ticarət günü
    ret_30: Mapped[float | None] = mapped_column(Float)  # +30 ticarət günü
    hit_1: Mapped[bool | None] = mapped_column(Boolean)  # istiqamət düz çıxdımı
    hit_5: Mapped[bool | None] = mapped_column(Boolean)
    hit_30: Mapped[bool | None] = mapped_column(Boolean)
    # null = hələ qiymətləndirilməyib (üfüq bağlanmayıb).
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    news: Mapped[News] = relationship()

    __table_args__ = (
        # Link populyasiyası idempotent — təkrar backfill/self-heal təhlükəsiz.
        UniqueConstraint("news_id", "asset_key", "source", name="uq_news_asset_link"),
        # Keystone indeks: per-asset digest + scorecard-by-asset (ən çox işlənən).
        Index(
            "ix_news_asset_key_published",
            "asset_key",
            published_at.desc().nullslast(),
        ),
        # Scorer üçün ucuz "gözləyən forecast" sorğusu.
        Index("ix_news_asset_pending", "source", "scored_at"),
        Index("ix_news_asset_news", "news_id"),
    )

    def __repr__(self) -> str:
        return f"<NewsAsset {self.news_id}->{self.asset_key} ({self.source})>"
