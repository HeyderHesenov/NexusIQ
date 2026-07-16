"""Aktiv səhifəsinin xəbərləri — DB-first, boşluqda Yahoo ehtiyatı.

Əvvəllər `/assets/{key}/news` sırf canlı Yahoo passthrough idi: DB-yə heç
toxunmurdu, sahəni `image` adlandırırdı və tətbiqdə `NewsImage` örtük
zəmanətindən kənarda qalan yeganə xəbər səthi idi. Nəticədə Yahoo thumbnail
verməyəndə (məs. wire-copy) istifadəçi boş boz qutu görürdü.

Zəncir (ucuzdan bahaya):
1. `news_asset` linkləri — bizim öz şəkil pipeline-ımızdan keçmiş xəbərlər.
2. `anomaly_news.news_for_asset` — söz-sərhədi uyğunluğu (pulsuz, DB), link seyrək olsa.
3. Yahoo (`assets.get_asset_news`, SWR) — DB hələ də azdırsa ƏLAVƏ olunur.

Yahoo əvəz etmir, əlavə edir: DB elementləri `id` daşıyır (daxili `/news/{id}`
linki + real og:image), onları itirmək geriləmə olardı.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, selectinload

from app.analytics import anomaly_news, assets
from app.models import News, NewsAsset
from app.schemas.news import AssetNewsOut

_HEAVY = (
    defer(News.embedding),
    defer(News.forecast),
    defer(News.content_tr),
    defer(News.content),
)
_MIN_DB = 3  # bundan az DB xəbəri olsa növbəti mənbəyə keç


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


async def for_asset(
    session: AsyncSession, key: str, limit: int = 8, days: int = 30
) -> list[dict]:
    """Aktivə aid xəbərlər — vahid `AssetNewsOut` formasında."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        await session.execute(
            select(NewsAsset.news_id)
            .where(NewsAsset.asset_key == key)
            .where(NewsAsset.published_at >= since)
            .order_by(NewsAsset.published_at.desc().nullslast())
        )
    ).all()

    ids: list[int] = []
    seen: set[int] = set()
    for r in rows:
        if r.news_id not in seen:
            seen.add(r.news_id)
            ids.append(r.news_id)

    # Link seyrəkdirsə söz-sərhədi fallback (watchlist_intel ilə eyni naxış).
    if len(ids) < _MIN_DB:
        for n in await anomaly_news.news_for_asset(session, key, days=days, k=limit):
            if n.id not in seen:
                seen.add(n.id)
                ids.append(n.id)

    ids = ids[:limit]
    news_map = await _load_news(session, ids)
    out = [
        AssetNewsOut.from_model(news_map[i]).model_dump(by_alias=True)
        for i in ids
        if i in news_map
    ]
    if len(out) >= _MIN_DB:
        return out

    # DB boşdur/azdır (coinlər, kiçik səhmlər) → Yahoo ilə tamamla.
    cat = assets.category_for(key)
    urls = {o["url"] for o in out if o["url"]}
    for d in await assets.get_asset_news(key):
        if len(out) >= limit:
            break
        if d.get("url") and d["url"] in urls:
            continue
        out.append(AssetNewsOut.from_yahoo(d, cat).model_dump(by_alias=True))
    return out
