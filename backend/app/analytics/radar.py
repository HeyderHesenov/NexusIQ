"""Radar — kəşf rejimi orkestratoru + fürsət balı.

Bilinməyən, kiçik kapitallı fürsətləri sıralayır (majors yox):
  crypto    → discovery_crypto (real gəlir + MC $1-50M)
  stock     → discovery_stocks (curated tematik, MC ≤ $1B)
  commodity → discovery_stocks (niş mədən/enerji small-cap)

Mənbə modulları xam item qaytarır; bu modul yalnız bal verir, sıralayır və
SWR ilə keşləyir. AI izahı ayrıca, on-demand (`agents.radar_ai`).
"""
from __future__ import annotations

import asyncio
import math

from app.analytics import discovery_crypto, discovery_stocks, swr

TAB_CONFIG: dict[str, dict] = {
    "crypto": {"ttl": 3600.0},
    "stock": {"ttl": 1800.0},
    "commodity": {"ttl": 1800.0},
}

_caches: dict[str, dict] = {t: {"ts": 0.0, "data": []} for t in TAB_CONFIG}


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _trend_pct(spark: list[float]) -> float:
    if spark and len(spark) >= 2 and spark[0]:
        return (spark[-1] - spark[0]) / spark[0] * 100.0
    return 0.0


def _score_crypto(item: dict) -> tuple[float, dict]:
    mom = _clamp(50.0 + (item.get("chgPct") or 0.0) * 2.5)
    trend = _clamp(50.0 + (item.get("chg7d") or 0.0) * 2.0)
    # Gəlir — log10 miqyası: ~$30K → 0, ~$30M+ → 100 ("həqiqətən qazanan").
    rev = item.get("revenue30d") or 0.0
    rev_s = _clamp((math.log10(rev) - 4.48) / (7.48 - 4.48) * 100.0) if rev > 0 else 0.0
    score = round(0.35 * mom + 0.40 * rev_s + 0.25 * trend, 1)
    return score, {
        "momentum": round(mom, 1),
        "revenue": round(rev_s, 1),
        "trend": round(trend, 1),
    }


def _score_stocks(items: list[dict]) -> None:
    """İki keçidli: əvvəl tema istiliyi (orta trend), sonra item balı. In-place."""
    theme_trends: dict[str, list[float]] = {}
    for it in items:
        tp = _trend_pct(it.get("spark") or [])
        it["_trendPct"] = tp
        theme_trends.setdefault(it.get("theme", ""), []).append(tp)
    theme_avg = {
        th: sum(v) / len(v) for th, v in theme_trends.items() if v
    }
    for it in items:
        mom = _clamp(50.0 + (it.get("chgPct") or 0.0) * 3.0)
        trend = _clamp(50.0 + it["_trendPct"] * 1.2)
        theme = _clamp(50.0 + theme_avg.get(it.get("theme", ""), 0.0) * 1.2)
        it["score"] = round(0.40 * mom + 0.35 * trend + 0.25 * theme, 1)
        it["breakdown"] = {
            "momentum": round(mom, 1),
            "trend": round(trend, 1),
            "theme": round(theme, 1),
        }
        it.pop("_trendPct", None)


async def _compute(category: str) -> list[dict]:
    if category == "crypto":
        items = await discovery_crypto.compute()
        for it in items:
            it["score"], it["breakdown"] = _score_crypto(it)
    else:
        items = await asyncio.to_thread(discovery_stocks.compute_sync, category)
        _score_stocks(items)
    items.sort(key=lambda x: x.get("score", 0), reverse=True)
    return items


async def get_radar(category: str, force: bool = False) -> list[dict]:
    """Kateqoriya üzrə kəşf sıralaması (SWR — köhnə dərhal, arxa planda yenilə)."""
    if category not in TAB_CONFIG:
        return []
    store = _caches[category]
    ttl = TAB_CONFIG[category]["ttl"]
    return await swr.get(store, ttl, lambda: _compute(category), force=force) or []


async def find_item(key: str) -> tuple[dict | None, str | None]:
    """Açar üzrə item-i sıralamalarda tap (keşdən). → (item, category)."""
    for cat in TAB_CONFIG:
        items = await get_radar(cat)
        item = next((i for i in items if i["key"] == key), None)
        if item:
            return item, cat
    return None, None


async def get_detail(key: str) -> dict | None:
    """Item + zənginləşdirmə (açıqlama, sayt, opensource GitHub linki)."""
    item, cat = await find_item(key)
    if not item:
        return None
    if cat == "crypto":
        extra = await discovery_crypto.detail(key)
    else:
        extra = await asyncio.to_thread(discovery_stocks.detail_sync, key)
    # "tab" = kateqoriya (crypto/stock/commodity); item-in öz "category"-si
    # (məs. kripto "Dexs") qorunur.
    return {**item, "tab": cat, **extra}
