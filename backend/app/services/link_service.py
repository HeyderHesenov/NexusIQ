"""Xəbər ↔ aktiv link populyasiyası — ingest hook + backfill + self-heal.

Bütün yazılar `on_conflict_do_nothing` (uq_news_asset_link) ilə idempotentdir,
ona görə təkrar ingest / backfill / scheduler self-heal təhlükəsizdir.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import exists, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import asset_map
from app.models import News, NewsAsset


def _dir_from_sentiment(sentiment: float | None) -> str:
    """Aşkarlanmış link üçün istiqamət — sentiment işarəsindən."""
    if sentiment is None:
        return "neutral"
    if sentiment > 0.1:
        return "up"
    if sentiment < -0.1:
        return "down"
    return "neutral"


def _detected_row(news: News, key: str) -> dict:
    return {
        "news_id": news.id,
        "asset_key": key,
        "published_at": news.published_at,
        "source": "detected",
        "impact_dir": _dir_from_sentiment(news.sentiment),
        "sentiment": news.sentiment,
        "impact_score": news.impact_score,
    }


async def _insert_rows(session: AsyncSession, rows: list[dict]) -> int:
    """Toplu insert (dublikatları atır). Yazılan sətir sayı."""
    if not rows:
        return 0
    stmt = (
        pg_insert(NewsAsset)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_news_asset_link")
    )
    result = await session.execute(stmt)
    return result.rowcount or 0


async def populate_detected(session: AsyncSession, news: News) -> int:
    """Xəbər mətnindəki aktivləri link et (deterministik, AI YOX). Commit ETMİR."""
    text = f"{news.title} {news.summary or ''}"
    keys = asset_map.assets_in_text(text)
    if not keys:
        return 0
    rows = [_detected_row(news, k) for k in keys]
    return await _insert_rows(session, rows)


async def populate_forecast(
    session: AsyncSession, news: News, pairs: list[dict]
) -> int:
    """AI proqnozunun göstərdiyi aktivləri link et (istiqamət dondurulur). Commit ETMİR."""
    rows: list[dict] = []
    seen: set[str] = set()
    for p in pairs or []:
        sym = (p or {}).get("sym")
        key = asset_map.normalize_sym(sym) if sym else None
        if not key or key in seen:
            continue
        seen.add(key)
        impact = (p or {}).get("impact") or "neutral"
        rows.append(
            {
                "news_id": news.id,
                "asset_key": key,
                "published_at": news.published_at,
                "source": "forecast",
                "impact_dir": impact,
                "scored_dir": impact,  # point-in-time: generasiya vaxtı dondurulur
                "sentiment": news.sentiment,
                "impact_score": news.impact_score,
            }
        )
    return await _insert_rows(session, rows)


def _rows_for(r) -> list[dict]:
    """Bir xəbər sətrindən (id,title,summary,published_at,sentiment,impact) linklər."""
    keys = asset_map.assets_in_text(f"{r.title} {r.summary or ''}")
    return [
        {
            "news_id": r.id,
            "asset_key": k,
            "published_at": r.published_at,
            "source": "detected",
            "impact_dir": _dir_from_sentiment(r.sentiment),
            "sentiment": r.sentiment,
            "impact_score": r.impact_score,
        }
        for k in keys
    ]


_BACKFILL_COLS = (
    News.id,
    News.title,
    News.summary,
    News.published_at,
    News.sentiment,
    News.impact_score,
)


async def backfill_detected(batch: int = 1000) -> dict:
    """Korpus üzrə birdəfəlik detected linkləri — sıfır AI. Öz-özünə commit edir.

    Offset ilə BÜTÜN korpusdan bir dəfə keçir (on_conflict idempotent → mövcud
    linklər atılır, yeni ləqəb uyğunluqları əlavə olunur). Aktiv tapılmayan xəbər
    linksiz qalır — bu düzgündür (sonsuz təkrar yoxdur, offset irəliləyir).
    """
    from app.db.session import AsyncSessionLocal

    processed = 0
    linked = 0
    while True:
        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(
                    select(*_BACKFILL_COLS)
                    .order_by(News.id)
                    .offset(processed)
                    .limit(batch)
                )
            ).all()
            if not rows:
                break
            all_rows = [row for r in rows for row in _rows_for(r)]
            linked += await _insert_rows(session, all_rows)
            await session.commit()
            processed += len(rows)
    return {"processed": processed, "linked": linked}


def _pairs_from_forecast(fc: dict | None) -> list[dict]:
    """Forecast JSONB-dən (dil üzrə) pairs siyahısı — en, sonra hər dil."""
    fc = fc or {}
    for lg in ("en", "az", "ru", "tr"):
        v = fc.get(lg)
        if isinstance(v, dict) and v.get("pairs"):
            return v["pairs"]
    for v in fc.values():
        if isinstance(v, dict) and v.get("pairs"):
            return v["pairs"]
    return []


async def backfill_forecast(batch: int = 500) -> dict:
    """Mövcud news.forecast JSONB-lərindən forecast linkləri (doğruluq kartı datası).

    İdempotent (on_conflict). Linklər üfüq bağlananda scorer tərəfindən ballanır.
    """
    from app.db.session import AsyncSessionLocal

    processed = 0
    linked = 0
    while True:
        async with AsyncSessionLocal() as session:
            rows = (
                await session.scalars(
                    select(News)
                    .where(News.forecast.is_not(None))
                    .order_by(News.id)
                    .offset(processed)
                    .limit(batch)
                )
            ).all()
            if not rows:
                break
            for n in rows:
                pairs = _pairs_from_forecast(n.forecast)
                if pairs:
                    linked += await populate_forecast(session, n, pairs)
            await session.commit()
            processed += len(rows)
    return {"processed": processed, "linked": linked}


async def self_heal_recent(session: AsyncSession, hours: int = 48) -> int:
    """Son `hours` saatda detected linki olmayan xəbərləri link et (scheduler).

    Məhdud pəncərə — ingest hook əsas işi görür, bu yalnız qaçanları tutur.
    Aktivsiz xəbərlər hər dövr yenidən yoxlanır (pəncərə kiçik → ucuz).
    """
    from datetime import timedelta, timezone

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    has_link = exists().where(
        (NewsAsset.news_id == News.id) & (NewsAsset.source == "detected")
    )
    rows = (
        await session.execute(
            select(*_BACKFILL_COLS)
            .where(News.published_at >= since)
            .where(~has_link)
            .limit(500)
        )
    ).all()
    all_rows = [row for r in rows for row in _rows_for(r)]
    linked = await _insert_rows(session, all_rows)
    await session.commit()
    return linked
