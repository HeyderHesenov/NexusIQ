"""Tarixi Analoq motoru — bənzər keçmiş xəbərlərdən sonrakı bazar hərəkəti.

Axın:
  1) Hədəf xəbərin embedding-i ilə kNN — keçmişdə ən bənzər (nəticəsi məlum)
     xəbərləri tap (yaddaşda VectorStore, app/rag/store.py reuse).
  2) Hədəf üçün TƏK aktiv aşkarla (correlation.detect_assets, yoxsa kateqoriya
     benchmark) — bütün analoqlar həmin aktivlə ölçülür (ardıcıllıq üçün).
  3) Hər analoq hadisədən sonra aktivin +1/+5/+30 ticarət günü gəlirini hesabla.
  4) Pəncərə üzrə ortalama + müsbət nisbət (hit rate) ümumiləşdir.

Data-əsaslıdır (GPT təxmini yox). Aktiv qiymət tarixçəsi yfinance "5y", keşli.
"""
from __future__ import annotations

import asyncio
import time
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf
from sqlalchemy import select

from app.analytics import correlation
from app.db.session import AsyncSessionLocal
from app.models import News
from app.rag import store

WINDOWS = (1, 5, 30)
_MIN_AGE_DAYS = 35  # 30g nəticəsi olsun deyə bu qədər köhnə analoqlar
_DUP_SIM = 0.985  # bundan yüksək oxşarlıq ~ eyni xəbər → at

# Kateqoriya → benchmark aktiv (aşkar aktiv tapılmasa).
_BENCHMARK = {"forex": "dxy", "us": "spx", "crypto": "btc", "commodities": "gold"}
_KEY_TO_SYM = correlation._KEY_TO_SYM  # 9 aktivin Yahoo simvolu

# ---- yaddaşda kNN indeksi ----
_index_cache: dict = {"ts": 0.0, "store": None}
_INDEX_TTL = 1800.0  # 30 dəqiqə

# ---- aktiv qiymət tarixçəsi keşi ----
_closes_cache: dict[str, tuple[float, pd.Series]] = {}
_CLOSES_TTL = 3600.0  # 1 saat


def reset_index() -> None:
    """Embedding dövrü yeni xəbər əlavə edəndə indeksi köhnəlt."""
    _index_cache["ts"] = 0.0


async def _build_index() -> store.VectorStore | None:
    """Nəticəsi məlum (kifayət köhnə) embedding-li xəbərlərdən kNN indeksi."""
    cutoff = datetime.now(timezone.utc).timestamp() - _MIN_AGE_DAYS * 86400
    cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)
    async with AsyncSessionLocal() as s:
        rows = (
            await s.execute(
                select(News.id, News.title, News.published_at, News.category, News.embedding)
                .where(News.embedding.is_not(None))
                .where(News.published_at.is_not(None))
                .where(News.published_at <= cutoff_dt)
            )
        ).all()
    if not rows:
        return None
    meta = [
        {
            "id": r[0],
            "title": r[1],
            "published_at": r[2].date().isoformat(),
            "category": r[3],
        }
        for r in rows
    ]
    vectors = np.array([r[4] for r in rows], dtype=np.float32)
    return store.VectorStore(meta, vectors)


async def _index() -> store.VectorStore | None:
    now = time.time()
    if _index_cache["store"] is not None and now - _index_cache["ts"] < _INDEX_TTL:
        return _index_cache["store"]
    st = await _build_index()
    if st is not None:
        _index_cache["store"] = st
        _index_cache["ts"] = now
    return _index_cache["store"]


# ---- aktiv qiymət tarixçəsi ----
def _fetch_closes(sym: str) -> pd.Series:
    raw = yf.download(
        sym, period="5y", interval="1d", auto_adjust=True, progress=False, threads=True
    )
    if raw is None or raw.empty:
        return pd.Series(dtype=float)
    close = raw["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close.dropna()


async def _asset_closes(key: str) -> pd.Series:
    """Aktivin 5-illik gündəlik bağlanışları (keşli, thread-də yfinance)."""
    sym = _KEY_TO_SYM.get(key)
    if not sym:
        return pd.Series(dtype=float)
    cached = _closes_cache.get(key)
    now = time.time()
    if cached and now - cached[0] < _CLOSES_TTL:
        return cached[1]
    series = await asyncio.to_thread(_fetch_closes, sym)
    if not series.empty:
        _closes_cache[key] = (now, series)
    elif cached:
        return cached[1]
    return series


def _move_after(closes: pd.Series, event_day: date, n: int) -> float | None:
    """Hadisə günündən (və ya sonrakı ilk ticarət günü) +n ticarət günü gəlir %.

    Nəticə hələ yoxdursa (gələcək data çatmır) None.
    """
    if closes.empty:
        return None
    idx = closes.index
    # Hadisə günündə/sonra ilk ticarət günü mövqeyi.
    pos = idx.searchsorted(pd.Timestamp(event_day), side="left")
    if pos >= len(closes) or pos + n >= len(closes):
        return None
    entry = float(closes.iloc[pos])
    exit_ = float(closes.iloc[pos + n])
    if entry == 0:
        return None
    return round((exit_ - entry) / entry * 100.0, 2)


def _asset_for(title: str, summary: str | None, category: str) -> str:
    """Mətndə aşkar aktiv; yoxsa kateqoriya benchmark; yoxsa btc."""
    found = correlation.detect_assets(f"{title} {summary or ''}")
    if found:
        return found[0]
    return _BENCHMARK.get(category, "btc")


def _aggregate(events: list[dict]) -> dict:
    out: dict[str, dict] = {}
    for n in WINDOWS:
        vals = [e["moves"][str(n)] for e in events if e["moves"][str(n)] is not None]
        if vals:
            out[str(n)] = {
                "avg": round(sum(vals) / len(vals), 2),
                "hitRate": round(sum(1 for v in vals if v > 0) / len(vals), 2),
                "count": len(vals),
            }
        else:
            out[str(n)] = {"avg": None, "hitRate": None, "count": 0}
    return out


async def analogs_for(
    vec: np.ndarray,
    title: str,
    summary: str | None,
    category: str,
    exclude_id: int | None = None,
    k: int = 5,
) -> dict:
    """Bənzər keçmiş hadisələr + hədəf aktivin onlardan sonrakı hərəkəti."""
    st = await _index()
    if st is None:
        return {"ready": False}

    asset_key = _asset_for(title, summary, category)
    closes = await _asset_closes(asset_key)

    # Buferlə axtar (self/dublikatları atdıqdan sonra k qalsın).
    hits = st.search(np.asarray(vec, dtype=np.float32), k=k + 6)

    events: list[dict] = []
    for meta, score in hits:
        if exclude_id is not None and meta["id"] == exclude_id:
            continue
        if score >= _DUP_SIM:  # demək olar eyni xəbər
            continue
        event_day = date.fromisoformat(meta["published_at"])
        moves = {str(n): _move_after(closes, event_day, n) for n in WINDOWS}
        events.append(
            {
                "id": meta["id"],
                "title": meta["title"],
                "publishedAt": meta["published_at"],
                "similarity": round(float(score), 3),
                "moves": moves,
            }
        )
        if len(events) >= k:
            break

    return {
        "ready": True,
        "asset": {"key": asset_key, "label": correlation.label_for(asset_key)},
        "count": len(events),
        "windows": _aggregate(events),
        "events": events,
    }


async def analogs_for_news(news: News, k: int = 5) -> dict:
    """Saxlanmış embedding ilə bir xəbər üçün analoqlar."""
    if not news.embedding:
        return {"ready": False}
    return await analogs_for(
        np.array(news.embedding, dtype=np.float32),
        news.title,
        news.summary,
        str(news.category),
        exclude_id=news.id,
        k=k,
    )
