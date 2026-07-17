"""Şəxsi digest xidməti — "Mənə Aid": izlənən aktivlərə toxunan xəbərlər.

Server HEÇ NƏ saxlamır — klient localStorage watchlist açarlarını + son-baxış
vaxtını göndərir. Hər aktiv üçün: window-dəki xəbərlər, əhval trendi, "sən yox
ikən" sayı. Link seyrəkdirsə `anomaly_news.news_for_asset` ilə doldurulur.
"""
from __future__ import annotations

import asyncio
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, selectinload

from app.analytics import accuracy, anomaly_news, assets, correlation
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
# Aktiv başına link tavanı — sorğu sərhədsiz idi. Ölçüldü: bu gün ən çox 467
# sətir (120 günlük pəncərə), amma korpusla xətti artır. Tavan real sayları
# təsirləməyəcək qədər yüksəkdir.
_MAX_LINK_ROWS = 2000


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


async def _links_for_keys(
    session: AsyncSession, keys: list[str], since: datetime
) -> dict[str, list]:
    """BÜTÜN açarların linklərini BİR sorğu ilə gətirir (açar → sətirlər).

    Əvvəl `digest` açar başına ayrıca sorğu atırdı (`_MAX_KEYS`=40 → 40 ardıcıl
    gediş-gəliş). Paralelləşdirmək OLMAZ: hamısı bir `AsyncSession`-u bölüşür,
    SQLAlchemy async sessiyası isə paralel əməliyyata dözmür. Doğru həll —
    `IN (...)` ilə tək sorğu + Python-da qruplaşdırma.

    `_MAX_LINK_ROWS`: sorğu tamamilə sərhədsiz idi. Bu gün ən çox 467 sətir
    (ölçüldü), amma korpus böyüdükcə xətti artır. Tavan yüksək qoyulub ki, real
    saylar (`count`/`sinceCount`) təsirlənməsin — yalnız patoloji hal kəsilir.
    """
    rows = (
        await session.execute(
            select(
                NewsAsset.asset_key,
                NewsAsset.news_id,
                NewsAsset.published_at,
                NewsAsset.sentiment,
            )
            .where(NewsAsset.asset_key.in_(keys))
            .where(NewsAsset.published_at >= since)
            .order_by(NewsAsset.published_at.desc().nullslast())
        )
    ).all()
    out: dict[str, list] = {k: [] for k in keys}
    for r in rows:
        bucket = out.get(r.asset_key)
        if bucket is not None and len(bucket) < _MAX_LINK_ROWS:
            bucket.append(r)
    return out


async def asset_digest(
    session: AsyncSession,
    key: str,
    since: datetime,
    last_seen: datetime | None,
    per_asset: int,
    days: int,
    rows: list | None = None,
) -> dict | None:
    """Bir aktiv üçün digest — heç xəbər yoxdursa None.

    `rows` verilsə təkrar sorğu atılmır (`digest` toplu gətirir).
    """
    if rows is None:
        rows = (await _links_for_keys(session, [key], since))[key]

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
        # Proqnoz doğruluq nişanı — n<20 olsa None (gizli). SWR keşli, ucuz.
        "trust": await accuracy.asset_trust(key),
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
    # Bütün açarların linkləri TƏK sorğu ilə (əvvəl açar başına bir sorğu idi).
    links = await _links_for_keys(session, uniq, since)
    out: list[dict] = []
    for k in uniq:
        d = await asset_digest(session, k, since, last_seen, per_asset, days, links[k])
        if d:
            out.append(d)
    # Ən çox "sən yox ikən" olan aktiv öndə; sonra ümumi say.
    out.sort(key=lambda a: (a["sinceCount"], a["count"]), reverse=True)
    total_since = sum(a["sinceCount"] for a in out)
    return {"ready": True, "sinceCount": total_since, "assets": out}


# ---- Faza B: Portfel + P&L (pul-çəkili xəbər relevance) ----

_DIR_SIGN = {"up": 1, "down": -1, "mixed": 0, "neutral": 0}


def _num(x) -> float | None:
    """Sonlu float, əks halda None. NaN VƏ ±Inf-in hər ikisini kəsir.

    Əvvəl yalnız NaN qorunurdu (`v == v`) — `inf == inf` True olduğu üçün
    Infinity keçirdi, `qty > 0` yoxlamasından da keçirdi və portfel riyaziyyatını
    (`value`, `total_value`, `weight`) səssizcə null/NaN-a çevirirdi.
    Sərhəd validasiyası (route-da `allow_inf_nan=False`) əsas qapıdır; bu isə
    xidmət qatının öz qorusudur — çağıran dəyişsə də riyaziyyat qorunsun.
    """
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


async def portfolio(
    session: AsyncSession,
    holdings: list[dict],
    last_seen: datetime | None,
    days: int = 14,
    per_asset_news: int = 24,
) -> dict:
    """Portfel P&L + bugünkü xəbərlərin PUL-ÇƏKİLİ sıralanması.

    holdings: [{key, qty, avgCost}]. Server heç nə saxlamır. Canlı qiymət
    `assets.get_quote`. Xəbər relevance = Σ weight_i · (impact/100) (toxunan∩portfel).
    """
    parsed: list[dict] = []
    seen: set[str] = set()
    for h in holdings or []:
        key = str((h or {}).get("key", "")).strip()
        qty = _num((h or {}).get("qty"))
        cost = _num((h or {}).get("avgCost"))
        if not key or key in seen or qty is None or qty <= 0:
            continue
        seen.add(key)
        parsed.append({"key": key, "qty": qty, "avgCost": cost})
    if not parsed:
        return {"ready": True, "totals": _empty_totals(), "positions": [], "news": []}

    quotes = await asyncio.gather(*[assets.get_quote(p["key"]) for p in parsed])

    positions: list[dict] = []
    total_value = 0.0
    total_cost = 0.0
    for p, q in zip(parsed, quotes):
        price = _num(q["price"]) if q else None
        value = price * p["qty"] if price is not None else None
        cost = p["avgCost"] * p["qty"] if p["avgCost"] is not None else None
        pnl = (value - cost) if (value is not None and cost is not None) else None
        pnl_pct = (
            (price / p["avgCost"] - 1) * 100
            if (price is not None and p["avgCost"])
            else None
        )
        if value is not None:
            total_value += value
        if cost is not None:
            total_cost += cost
        positions.append(
            {
                "key": p["key"],
                "label": (q["label"] if q else _label(p["key"])),
                "qty": p["qty"],
                "avgCost": p["avgCost"],
                "price": price,
                "chgPct": (q["chgPct"] if q else None),
                "value": round(value, 2) if value is not None else None,
                "pnl": round(pnl, 2) if pnl is not None else None,
                "pnlPct": round(pnl_pct, 2) if pnl_pct is not None else None,
                "weight": 0.0,  # aşağıda doldurulur
            }
        )

    # Çəkilər dəyəri bilinən mövqelərdən (weight-lər cəmi 1).
    for pos in positions:
        pos["weight"] = (
            round(pos["value"] / total_value, 4)
            if (pos["value"] and total_value > 0)
            else 0.0
        )
    weights = {pos["key"]: pos["weight"] for pos in positions}

    total_pnl = round(total_value - total_cost, 2) if total_cost else None
    totals = {
        "value": round(total_value, 2),
        "cost": round(total_cost, 2),
        "pnl": total_pnl,
        "pnlPct": (
            round((total_value / total_cost - 1) * 100, 2) if total_cost > 0 else None
        ),
    }

    news = await _money_ranked_news(
        session, list(weights), weights, last_seen, days, per_asset_news
    )
    return {"ready": True, "totals": totals, "positions": positions, "news": news}


def _empty_totals() -> dict:
    return {"value": 0.0, "cost": 0.0, "pnl": None, "pnlPct": None}


async def _money_ranked_news(
    session: AsyncSession,
    keys: list[str],
    weights: dict[str, float],
    last_seen: datetime | None,
    days: int,
    limit: int,
) -> list[dict]:
    """Portfelə toxunan xəbərlər — pul-çəkili relevance ilə sıralı."""
    if not keys:
        return []
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        await session.execute(
            select(
                NewsAsset.news_id,
                NewsAsset.asset_key,
                NewsAsset.published_at,
                NewsAsset.impact_score,
                NewsAsset.impact_dir,
            )
            .where(NewsAsset.asset_key.in_(keys))
            .where(NewsAsset.published_at >= since)
        )
    ).all()

    # news_id → {impact, touched:[(key,dir)], published_at}
    agg: dict[int, dict] = {}
    for r in rows:
        e = agg.setdefault(
            r.news_id,
            {"impact": _num(r.impact_score) or 0.0, "touched": [], "pub": r.published_at},
        )
        e["touched"].append((r.asset_key, r.impact_dir))

    scored: list[tuple[float, float, int, list[str]]] = []
    for nid, e in agg.items():
        w_sum = sum(weights.get(k, 0.0) for k, _d in e["touched"])
        if w_sum <= 0:
            continue
        rel = round(e["impact"] / 100.0 * w_sum, 4)
        tilt = round(
            e["impact"]
            / 100.0
            * sum(weights.get(k, 0.0) * _DIR_SIGN.get(d, 0) for k, d in e["touched"]),
            4,
        )
        touched = [k for k, _d in e["touched"] if k in weights]
        scored.append((rel, tilt, nid, touched))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]
    news_map = await _load_news(session, [nid for _r, _t, nid, _k in top])

    out: list[dict] = []
    for rel, tilt, nid, touched in top:
        n = news_map.get(nid)
        if not n:
            continue
        d = _news_dict(n)
        d["relevanceScore"] = rel
        d["moneyTilt"] = tilt
        d["touched"] = touched
        out.append(d)
    return out
