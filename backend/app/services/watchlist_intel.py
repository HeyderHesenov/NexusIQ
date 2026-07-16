"""Şəxsi digest xidməti — "Mənə Aid": izlənən aktivlərə toxunan xəbərlər.

Server HEÇ NƏ saxlamır — klient localStorage watchlist açarlarını + son-baxış
vaxtını göndərir. Hər aktiv üçün: window-dəki xəbərlər, əhval trendi, "sən yox
ikən" sayı. Link seyrəkdirsə `anomaly_news.news_for_asset` ilə doldurulur.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, selectinload

from app.analytics import anomaly_news, assets, correlation
from app.models import News, NewsAsset
from app.schemas.news import NewsOut

_HEAVY = (
    defer(News.embedding),
    defer(News.forecast),
    defer(News.content_tr),
    defer(News.content),
)
_MAX_KEYS = 40
_MIN_LINKED = 3  # bundan az link olsa fallback ilə doldur


def _label(key: str) -> str:
    meta = assets._BY_KEY.get(key)
    if meta:
        return meta[1]
    lbl = correlation.label_for(key)
    if lbl != key:
        return lbl
    if key.startswith("c_"):
        return key[2:].upper()
    return key.upper()


def _news_dict(n: News) -> dict:
    return NewsOut.from_model(n).model_dump(by_alias=True)


def _trend(combined: dict[int, tuple[datetime | None, float | None]]) -> list[float]:
    """Gün üzrə orta əhval (köhnədən təzəyə) — sparkline üçün, son ~14 nöqtə."""
    by_day: dict[str, list[float]] = {}
    for _pub, sent in combined.values():
        if _pub is None or sent is None:
            continue
        day = _pub.date().isoformat()
        by_day.setdefault(day, []).append(sent)
    days = sorted(by_day)[-14:]
    return [round(sum(by_day[d]) / len(by_day[d]), 3) for d in days]


async def _load_news(session: AsyncSession, ids: list[int]) -> dict[int, News]:
    if not ids:
        return {}
    rows = (
        await session.scalars(
            select(News)
            .options(selectinload(News.source), *_HEAVY)
            .where(News.id.in_(ids))
        )
    ).all()
    return {n.id: n for n in rows}


async def asset_digest(
    session: AsyncSession,
    key: str,
    since: datetime,
    last_seen: datetime | None,
    per_asset: int,
    days: int,
) -> dict | None:
    """Bir aktiv üçün digest — heç xəbər yoxdursa None."""
    rows = (
        await session.execute(
            select(NewsAsset.news_id, NewsAsset.published_at, NewsAsset.sentiment)
            .where(NewsAsset.asset_key == key)
            .where(NewsAsset.published_at >= since)
            .order_by(NewsAsset.published_at.desc().nullslast())
        )
    ).all()

    combined: dict[int, tuple[datetime | None, float | None]] = {}
    for r in rows:
        combined.setdefault(r.news_id, (r.published_at, r.sentiment))

    # Link seyrəkdirsə söz-sərhədi fallback ilə doldur (digest boş qalmasın).
    if len(combined) < _MIN_LINKED:
        for n in await anomaly_news.news_for_asset(session, key, days=days, k=per_asset):
            combined.setdefault(n.id, (n.published_at, n.sentiment))

    if not combined:
        return None

    ordered = sorted(
        combined.items(),
        key=lambda kv: (kv[1][0] or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )
    ordered_ids = [nid for nid, _ in ordered]
    display_ids = ordered_ids[:per_asset]
    news_map = await _load_news(session, display_ids)
    news = [_news_dict(news_map[i]) for i in display_ids if i in news_map]

    since_count = 0
    if last_seen is not None:
        since_count = sum(
            1 for _nid, (pub, _s) in combined.items() if pub and pub > last_seen
        )

    return {
        "key": key,
        "label": _label(key),
        "count": len(combined),
        "sinceCount": since_count,
        "sentimentTrend": _trend(combined),
        "news": news,
        "trust": None,  # Faza C dolduracaq (proqnoz doğruluq nişanı)
    }


async def digest(
    session: AsyncSession,
    keys: list[str],
    last_seen: datetime | None,
    days: int = 14,
    per_asset: int = 8,
) -> dict:
    """Watchlist üçün tam digest — aktiv üzrə qruplanmış."""
    uniq: list[str] = []
    for k in keys:
        k = (k or "").strip()
        if k and k not in uniq:
            uniq.append(k)
    uniq = uniq[:_MAX_KEYS]
    if not uniq:
        return {"ready": True, "sinceCount": 0, "assets": []}

    since = datetime.now(timezone.utc) - timedelta(days=days)
    out: list[dict] = []
    for k in uniq:
        d = await asset_digest(session, k, since, last_seen, per_asset, days)
        if d:
            out.append(d)
    # Ən çox "sən yox ikən" olan aktiv öndə; sonra ümumi say.
    out.sort(key=lambda a: (a["sinceCount"], a["count"]), reverse=True)
    total_since = sum(a["sinceCount"] for a in out)
    return {"ready": True, "sinceCount": total_since, "assets": out}
