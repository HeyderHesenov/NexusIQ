"""Xəbər saxlama xidməti — dedup + normalize + bazaya yazma."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.scoring import score_text
from app.ingestion.rss_collector import NormalizedNews
from app.ingestion.sources import FEEDS
from app.models import News, Source
from app.services import link_service

# Mənbə adı → metadata (homepage, rss, default kateqoriya).
_SOURCE_META = {f.name: f for f in FEEDS}


async def _get_or_create_sources(
    session: AsyncSession, names: set[str]
) -> dict[str, int]:
    """Mənbələri tapır və ya yaradır; ad → id xəritəsi qaytarır."""
    existing = (
        await session.scalars(select(Source).where(Source.name.in_(names)))
    ).all()
    mapping = {s.name: s.id for s in existing}

    for name in names - mapping.keys():
        meta = _SOURCE_META.get(name)
        source = Source(
            name=name,
            homepage_url=meta.homepage if meta else None,
            rss_url=meta.rss_url if meta else None,
            default_category=meta.category.value if meta else None,
        )
        session.add(source)
        await session.flush()  # id almaq üçün
        mapping[name] = source.id
    return mapping


async def store_news(
    session: AsyncSession, items: list[NormalizedNews]
) -> dict[str, int]:
    """Dublikatları atıb yeni xəbərləri yazır. Sayğacları qaytarır."""
    if not items:
        return {"fetched": 0, "added": 0, "skipped": 0}

    # 1) Mənbələri hazırla.
    names = {it.source_name for it in items}
    source_ids = await _get_or_create_sources(session, names)

    # 2) DB-də artıq olan hash-ləri tap (toplu sorğu).
    hashes = {it.dedup_hash for it in items}
    known = set(
        (
            await session.scalars(
                select(News.dedup_hash).where(News.dedup_hash.in_(hashes))
            )
        ).all()
    )

    # 3) Yalnız yeni olanları əlavə et.
    added = 0
    batch_seen: set[str] = set()
    new_objs: list[News] = []
    for it in items:
        if it.dedup_hash in known or it.dedup_hash in batch_seen:
            continue
        batch_seen.add(it.dedup_hash)
        sentiment, impact = score_text(it.title, it.summary, it.category.value)
        obj = News(
            title=it.title,
            url=it.url,
            summary=it.summary,
            image_url=it.image_url,
            published_at=it.published_at,
            category=it.category.value,
            dedup_hash=it.dedup_hash,
            source_id=source_ids.get(it.source_name),
            sentiment=sentiment,
            impact_score=impact,
            is_processed=False,
        )
        session.add(obj)
        new_objs.append(obj)
        added += 1

    # 4) Yeni xəbərlərə xəbər↔aktiv detected linklərini yaz (deterministik, AI YOX).
    if new_objs:
        await session.flush()  # id-lər üçün
        for obj in new_objs:
            await link_service.populate_detected(session, obj)

    await session.commit()
    return {"fetched": len(items), "added": added, "skipped": len(items) - added}
