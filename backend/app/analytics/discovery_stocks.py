"""Səhm/əmtəə kəşfi — curated tematik universe + yfinance (MC filtri).

Tək toplu `yf.download` (qiymət + sparkline) + paralel `fast_info` (market cap).
MC həddini keçən, delist olan və ya datası olmayan ticker-lər atılır.
Nəticə xam item-dir — bal `radar.py`-də hesablanır.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf

from app.analytics.discovery_universe import universe

# Kateqoriya üzrə market cap aralığı (min — ölü mikro-səhmləri at).
_MIN_MCAP = 10_000_000.0
_MAX_MCAP = {"stock": 1_000_000_000.0, "commodity": 2_000_000_000.0}
_SPARK_POINTS = 24


def _fmt_mcap(mc: float) -> str:
    if mc >= 1e9:
        return f"${mc / 1e9:.2f}B"
    return f"${mc / 1e6:.0f}M"


def _fmt_price(p: float) -> str:
    if p >= 1000:
        return f"{p:,.0f}"
    if p >= 1:
        return f"{p:,.2f}"
    return f"{p:,.4f}"


def _overview(tickers: list[str]) -> dict[str, dict]:
    """Toplu qiymət + 1aylıq sparkline (tək yf çağırışı)."""
    out: dict[str, dict] = {}
    try:
        df = yf.download(
            " ".join(tickers), period="1mo", interval="1d",
            auto_adjust=True, progress=False, threads=True,
        )["Close"]
    except Exception:  # noqa: BLE001
        return out
    for t in tickers:
        try:
            series = df[t].dropna() if t in df else None
            if series is None or len(series) < 2:
                continue
            closes = [float(v) for v in series]
            last, prev = closes[-1], closes[-2]
            chg = (last - prev) / prev * 100 if prev else 0.0
            out[t] = {
                "price": last,
                "chgPct": round(chg, 2),
                "spark": [round(c, 4) for c in closes[-_SPARK_POINTS:]],
            }
        except (KeyError, IndexError, ValueError, TypeError):
            continue
    return out


def _mcap(ticker: str) -> float | None:
    try:
        mc = yf.Ticker(ticker).fast_info["market_cap"]
        return float(mc) if mc else None
    except Exception:  # noqa: BLE001
        return None


def _mcaps(tickers: list[str]) -> dict[str, float]:
    """Paralel market cap (fast_info) — GIL şəbəkə I/O-da buraxılır."""
    with ThreadPoolExecutor(max_workers=16) as ex:
        pairs = ex.map(lambda t: (t, _mcap(t)), tickers)
    return {t: mc for t, mc in pairs if mc}


# Detal keşi: ticker → (ts, dict). 6 saat.
_detail_cache: dict[str, tuple[float, dict]] = {}
_DETAIL_TTL = 21_600.0


def _trim(text: str, n: int = 360) -> str:
    text = " ".join((text or "").split())
    if len(text) <= n:
        return text
    cut = text[:n]
    dot = cut.rfind(". ")
    return (cut[: dot + 1] if dot > n * 0.5 else cut).rstrip() + " …"


def detail_sync(ticker: str) -> dict:
    """Səhm detalı — şirkət adı + açıqlama + sayt. 6s keş (yf .info yavaşdır)."""
    hit = _detail_cache.get(ticker)
    if hit and time.time() - hit[0] < _DETAIL_TTL:
        return hit[1]
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:  # noqa: BLE001
        return {}
    out = {
        "name": info.get("shortName") or info.get("longName") or ticker,
        "description": _trim(info.get("longBusinessSummary") or ""),
        "homepage": info.get("website"),
        "github": None,
    }
    _detail_cache[ticker] = (time.time(), out)
    return out


def compute_sync(category: str) -> list[dict]:
    cap = _MAX_MCAP.get(category, 1e9)
    uni = universe(category)
    tickers = list(uni)
    if not tickers:
        return []
    ov = _overview(tickers)
    mcaps = _mcaps(tickers)

    items: list[dict] = []
    for t in tickers:
        d = ov.get(t)
        mc = mcaps.get(t)
        if not d or not mc or mc < _MIN_MCAP or mc > cap:
            continue
        items.append({
            "key": t,
            "label": t,
            "name": t,
            "type": category,
            "price": d["price"],
            "val": _fmt_price(d["price"]),
            "chg": f"{d['chgPct']:+.2f}%",
            "chgPct": d["chgPct"],
            "up": d["chgPct"] >= 0,
            "spark": d["spark"],
            "mcap": mc,
            "mcapFmt": _fmt_mcap(mc),
            "theme": uni[t],
            "link": f"https://finance.yahoo.com/quote/{t}",
        })
    return items
