"""Xəbər Pydantic sxemləri — frontend (camelCase) ilə uyğun."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.core.imagejunk import clean_image
from app.models import News

_EXCERPT_MAX = 1400


def _excerpt(content: str | None) -> str | None:
    """Tam mətndən təmiz bir hissə — cümlə sərhədində kəsilir."""
    if not content:
        return None
    text = content.strip()
    if len(text) <= _EXCERPT_MAX:
        return text
    cut = text[:_EXCERPT_MAX]
    dot = cut.rfind(". ")
    if dot > _EXCERPT_MAX * 0.5:
        cut = cut[: dot + 1]
    return cut.rstrip() + " …"


class NewsOut(BaseModel):
    """Frontend NewsItem ilə eyni forma. AI emalı varsa az variantı seçilir."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    title: str
    summary: str | None = None
    content: str | None = None
    image_url: str | None = None
    category: str
    source: str | None = None
    original_url: str | None = None
    published_at: datetime | None = None
    sentiment: float | None = None
    impact_score: float | None = None
    is_processed: bool = False
    # {"az": {"title","body"}, "en": {...}, "ru": {...}, "tr": {...}}
    translations: dict | None = None

    @classmethod
    def from_model(cls, n: News, with_content: bool = False) -> "NewsOut":
        """ORM modeli → çıxış sxemi. title/summary orijinal; dil seçimi frontend-də.

        with_content=True yalnız tək-xəbər səhifəsində — siyahını şişirtmir.
        """
        return cls(
            id=str(n.id),
            title=n.title,
            summary=n.summary,
            content=_excerpt(n.content) if with_content else None,
            image_url=clean_image(n.image_url),
            category=n.category,
            source=n.source.name if n.source else None,
            original_url=n.url,
            published_at=n.published_at,
            sentiment=n.sentiment,
            impact_score=n.impact_score,
            is_processed=n.is_processed,
            translations=n.translations,
        )


class AssetNewsOut(BaseModel):
    """Aktiv səhifəsi üçün VAHİD xəbər forması — DB və Yahoo eyni formada çıxır.

    Şəkil sahəsi qəsdən `image_url` (→ `imageUrl`) adlanır: köhnə Yahoo yolu onu
    `image` adlandırırdı və məhz bu ad divergensiyası örtük bug-ını gizlətmişdi.
    `id` yalnız DB xəbərlərində var (→ daxili `/news/{id}` linki); Yahoo
    xəbərlərində `None`-dur (→ xarici link).
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str | None = None
    title: str
    url: str | None = None
    source: str | None = None
    published_at: datetime | None = None
    image_url: str | None = None
    category: str
    summary: str | None = None

    @classmethod
    def from_model(cls, n: News) -> "AssetNewsOut":
        return cls(
            id=str(n.id),
            title=n.title,
            url=n.url,
            source=n.source.name if n.source else None,
            published_at=n.published_at,
            image_url=clean_image(n.image_url),
            category=n.category,
            summary=n.summary,
        )

    @classmethod
    def from_yahoo(cls, d: dict, category: str) -> "AssetNewsOut":
        return cls(
            id=None,
            title=d["title"],
            url=d.get("url"),
            source=d.get("source"),
            published_at=d.get("publishedAt"),
            image_url=clean_image(d.get("imageUrl")),
            category=category,
            summary=d.get("summary"),
        )
