"""Proqnoz doğruluq kartı — aqreqasiya (kateqoriya/aktiv/istiqamət/üfüq üzrə).

Hər slice: hitRate (proqnoz düz çıxma nisbəti) vs baseRate ("həmişə ▲" naiv
nisbəti) → delta. n<20 → insufficient (dürüst "toplanır", gizlətmə YOX).
SWR keşli (30 dəq) — scorer yavaş dəyişir.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select

from app.analytics import assets, correlation, swr
from app.db.session import AsyncSessionLocal
from app.models import News, NewsAsset

_MIN_N = 20  # bundan az → dürüst "toplanır", göstərmə
_HORIZONS = (1, 5, 30)
_BY = {"category", "asset", "direction", "horizon"}

_cache: dict[str, dict] = {}


def _label(key: str) -> str:
    meta = assets._BY_KEY.get(key)
    if meta:
        return meta[1]
    lbl = correlation.label_for(key)
    return lbl if lbl != key else key.upper()


def _slice(label: str, key: str, horizon: int, pairs: list[tuple]) -> dict:
    """(ret, hit) cütlərindən bir slice statistikası."""
    n = len(pairs)
    hit_rate = sum(1 for _r, h in pairs if h) / n
    base_rate = sum(1 for r, _h in pairs if r is not None and r > 0) / n
    return {
        "key": key,
        "label": label,
        "horizon": horizon,
        "n": n,
        "hitRate": round(hit_rate, 3),
        "baseRate": round(base_rate, 3),
        "delta": round(hit_rate - base_rate, 3),
        "insufficient": n < _MIN_N,
    }


async def _build(by: str, horizon: int) -> dict:
    async with AsyncSessionLocal() as session:
        if by == "horizon":
            slices = []
            for h in _HORIZONS:
                ret_c = getattr(NewsAsset, f"ret_{h}")
                hit_c = getattr(NewsAsset, f"hit_{h}")
                rows = (
                    await session.execute(
                        select(ret_c, hit_c)
                        .where(NewsAsset.source == "forecast")
                        .where(NewsAsset.scored_at.is_not(None))
                        .where(hit_c.is_not(None))
                    )
                ).all()
                if rows:
                    slices.append(
                        _slice(f"+{h}g", str(h), h, [(r[0], r[1]) for r in rows])
                    )
            return {"ready": True, "by": by, "horizon": horizon, "slices": slices}

        ret_c = getattr(NewsAsset, f"ret_{horizon}")
        hit_c = getattr(NewsAsset, f"hit_{horizon}")
        rows = (
            await session.execute(
                select(
                    NewsAsset.asset_key, NewsAsset.scored_dir, ret_c, hit_c, News.category
                )
                .join(News, News.id == NewsAsset.news_id)
                .where(NewsAsset.source == "forecast")
                .where(NewsAsset.scored_at.is_not(None))
                .where(hit_c.is_not(None))
            )
        ).all()

    groups: dict[tuple[str, str], list[tuple]] = defaultdict(list)
    for asset_key, scored_dir, ret, hit, category in rows:
        if by == "asset":
            gk = (asset_key, _label(asset_key))
        elif by == "direction":
            gk = (scored_dir or "?", (scored_dir or "?"))
        else:  # category
            gk = (category, category)
        groups[gk].append((ret, hit))

    slices = [_slice(lbl, key, horizon, pairs) for (key, lbl), pairs in groups.items()]
    # Kifayət edən (n>=20) öndə, sonra n azalan.
    slices.sort(key=lambda s: (not s["insufficient"], s["n"]), reverse=True)
    return {"ready": True, "by": by, "horizon": horizon, "slices": slices}


async def scorecard(by: str = "category", horizon: int = 5) -> dict:
    by = by if by in _BY else "category"
    horizon = horizon if horizon in _HORIZONS else 5
    ck = f"{by}:{horizon}"
    store = _cache.setdefault(ck, {"ts": 0.0, "data": None})
    data = await swr.get(store, 1800.0, lambda: _build(by, horizon))
    return data or {"ready": True, "by": by, "horizon": horizon, "slices": []}


async def asset_trust(key: str, horizon: int = 5) -> dict | None:
    """Bir aktiv üçün güvən nişanı (per-asset digest). n<20 → None (gizli)."""
    card = await scorecard("asset", horizon)
    for s in card["slices"]:
        if s["key"] == key and not s["insufficient"]:
            return {
                "hitRate": s["hitRate"],
                "baseRate": s["baseRate"],
                "delta": s["delta"],
                "n": s["n"],
                "horizon": s["horizon"],
            }
    return None
