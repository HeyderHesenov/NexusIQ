"""Xəbər modeli — platformanın əsas verisi."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import Category
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.source import Source


class News(Base, TimestampMixin):
    """Bir xəbər vahidi. Orijinal + AI emalı sahələri birlikdə."""

    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True)

    # ---- Orijinal məzmun ----
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1000))
    # Şəkil çəkmə cəhdləri — `enrich_images` backoff üçün. Bunsuz NULL sətirlər
    # (markersiz) hər dövrdə yenidən çəkilirdi; zibil sətirləri isə heç.
    image_attempts: Mapped[int] = mapped_column(
        SmallInteger, server_default="0", nullable=False, default=0
    )
    image_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ---- Təsnifat ----
    category: Mapped[Category] = mapped_column(String(20), nullable=False)
    language: Mapped[str | None] = mapped_column(String(8))

    # ---- AI emalı (Addım 4-də doldurulur) ----
    title_az: Mapped[str | None] = mapped_column(String(500))
    summary_az: Mapped[str | None] = mapped_column(Text)
    # 4 dil: {"az": {"title": ..., "body": ...}, "en": {...}, "ru": {...}, "tr": {...}}
    translations: Mapped[dict | None] = mapped_column(JSONB)
    # AI bazar proqnozu, dil üzrə keşlənir (on-demand doldurulur):
    # {"az": {"summary": ..., "pairs": [{"sym","impact","reason"}]}, ...}
    forecast: Mapped[dict | None] = mapped_column(JSONB)
    # Orijinal mətnin dil üzrə tərcüməsi, on-demand keşlənir: {"az": "...", ...}
    content_tr: Mapped[dict | None] = mapped_column(JSONB)
    sentiment: Mapped[float | None] = mapped_column(Float)  # -1..1
    impact_score: Mapped[float | None] = mapped_column(Float)  # 0..100
    is_processed: Mapped[bool] = mapped_column(default=False, nullable=False)
    # Tarixi Analoq motoru üçün 1536-ölçülü embedding (embedding modeli).
    # Backfill + scheduler hook ilə doldurulur; kNN axtarışında işlədilir.
    embedding: Mapped[list[float] | None] = mapped_column(JSONB)

    # ---- Deduplikasiya ----
    # url + başlıqdan çıxarılan unikal hash (Addım 3-də doldurulur)
    dedup_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )

    # ---- Əlaqələr ----
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL")
    )
    source: Mapped[Source | None] = relationship(back_populates="news")

    __table_args__ = (
        Index("ix_news_category_published", "category", "published_at"),
        # Trending/fallback sıralaması: impact_score DESC, published_at DESC.
        # Sıra sorğu ilə EYNİ olmalıdır — ASC qurulanda planner indeksi sıra üçün
        # işlədə bilmirdi (ölçüldü: Seq Scan + top-N heapsort, 851 bufer).
        Index(
            "ix_news_impact_published",
            impact_score.desc().nullslast(),
            published_at.desc().nullslast(),
        ),
        # Ön səhifə (kateqoriyasız) sıralaması — sorğu ilə eyni sıra (DESC NULLS
        # LAST) ki, planner scale-də seq scan+sort əvəzinə index scan seçsin.
        Index("ix_news_published", published_at.desc().nullslast()),
        # Şəkil retry backoff sorğusu (migrasiya e5f6a7b8c9d0-də yaradıldı).
        Index("ix_news_image_retry", "image_attempts", "image_attempted_at"),
    )

    def __repr__(self) -> str:
        return f"<News {self.id} {self.title[:40]!r}>"
