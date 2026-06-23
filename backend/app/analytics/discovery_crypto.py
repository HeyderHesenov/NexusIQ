"""Kripto kəşfi — real gəlir qazanan mikrokoinlər (MC $1M–$50M).

Pipeline (pulsuz, açarsız):
  1. DefiLlama `/protocols`     → gecko_id + simvol + kateqoriya (slug ilə açar).
  2. DefiLlama `/overview/fees` → slug → 30g gəlir (real qazanc).
  3. Birləşdir: gecko_id-li + gəliri həddən yuxarı protokollar.
  4. CoinGecko `/coins/markets?ids=…` → dəqiq MC + qiymət + 7g sparkline.
  5. Filtr: MC ∈ [$1M, $50M].

Nəticə xam item-dir — bal `radar.py`-də hesablanır.
"""
from __future__ import annotations

import time

import httpx

_MIN_MCAP = 1_000_000.0
_MAX_MCAP = 50_000_000.0
_MIN_REV30D = 30_000.0  # 30 günlük gəlir həddi (real qazanc filtri)
_SPARK_EVERY = 6  # 168 saatlıq nöqtəni ~28-ə seyrəlt


def _fmt_mcap(mc: float) -> str:
    if mc >= 1e9:
        return f"${mc / 1e9:.2f}B"
    return f"${mc / 1e6:.1f}M"


def _fmt_rev(r: float) -> str:
    if r >= 1e6:
        return f"${r / 1e6:.1f}M"
    return f"${r / 1e3:.0f}K"


def _fmt_price(p: float) -> str:
    if p >= 1:
        return f"{p:,.2f}"
    if p >= 0.01:
        return f"{p:,.4f}"
    return f"{p:,.6f}"


async def _earning_protocols(client: httpx.AsyncClient) -> dict[str, dict]:
    """gecko_id → {symbol, name, category, revenue30d} (gəliri olanlar)."""
    prot = (await client.get("https://api.llama.fi/protocols")).json()
    by_slug = {p["slug"]: p for p in prot if p.get("gecko_id")}

    fees = (await client.get(
        "https://api.llama.fi/overview/fees",
        params={
            "excludeTotalDataChart": "true",
            "excludeTotalDataChartBreakdown": "true",
        },
    )).json().get("protocols", [])
    rev_by_slug = {f.get("slug"): (f.get("total30d") or 0) for f in fees}

    out: dict[str, dict] = {}
    for slug, p in by_slug.items():
        rev = rev_by_slug.get(slug, 0)
        if rev < _MIN_REV30D:
            continue
        gid = p["gecko_id"]
        # Eyni gecko_id-li bir neçə protokolun gəlirini topla.
        if gid in out:
            out[gid]["revenue30d"] += rev
            continue
        out[gid] = {
            "symbol": (p.get("symbol") or "").upper(),
            "name": p.get("name") or gid,
            "category": p.get("category") or "DeFi",
            "revenue30d": float(rev),
        }
    return out


async def _markets(client: httpx.AsyncClient, ids: list[str]) -> dict[str, dict]:
    """gecko_id → CoinGecko bazar datası (MC, qiymət, 7g sparkline)."""
    out: dict[str, dict] = {}
    for i in range(0, len(ids), 250):
        chunk = ids[i:i + 250]
        r = await client.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "usd",
                "ids": ",".join(chunk),
                "sparkline": "true",
                "price_change_percentage": "24h,7d",
                "per_page": 250,
            },
        )
        if r.status_code != 200:
            continue
        for m in r.json():
            out[m["id"]] = m
    return out


# Detal keşi: gecko_id → (ts, dict). 6 saat.
_detail_cache: dict[str, tuple[float, dict]] = {}
_DETAIL_TTL = 21_600.0


def _trim(text: str, n: int = 360) -> str:
    text = " ".join((text or "").split())
    if len(text) <= n:
        return text
    cut = text[:n]
    dot = cut.rfind(". ")
    return (cut[: dot + 1] if dot > n * 0.5 else cut).rstrip() + " …"


async def detail(gecko_id: str) -> dict:
    """Kripto detalı — açıqlama + homepage + GitHub (opensource). 6s keş."""
    hit = _detail_cache.get(gecko_id)
    if hit and time.time() - hit[0] < _DETAIL_TTL:
        return hit[1]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"https://api.coingecko.com/api/v3/coins/{gecko_id}",
                params={
                    "localization": "false", "tickers": "false",
                    "market_data": "false", "community_data": "false",
                    "developer_data": "false", "sparkline": "false",
                },
            )
        if r.status_code != 200:
            return {}
        d = r.json()
    except (httpx.HTTPError, ValueError):
        return {}
    links = d.get("links") or {}
    gh = [g for g in ((links.get("repos_url") or {}).get("github") or []) if g]
    hp = [h for h in (links.get("homepage") or []) if h]
    out = {
        "description": _trim((d.get("description") or {}).get("en") or ""),
        "homepage": hp[0] if hp else None,
        "github": gh[0] if gh else None,
        "image": (d.get("image") or {}).get("small"),
    }
    _detail_cache[gecko_id] = (time.time(), out)
    return out


async def compute() -> list[dict]:
    async with httpx.AsyncClient(timeout=25.0) as client:
        try:
            earners = await _earning_protocols(client)
        except (httpx.HTTPError, ValueError, KeyError):
            return []
        if not earners:
            return []
        try:
            mkts = await _markets(client, list(earners))
        except (httpx.HTTPError, ValueError):
            return []

    items: list[dict] = []
    for gid, info in earners.items():
        m = mkts.get(gid)
        if not m:
            continue
        mc = m.get("market_cap") or 0
        if mc < _MIN_MCAP or mc > _MAX_MCAP:
            continue
        price = m.get("current_price") or 0
        chg = m.get("price_change_percentage_24h_in_currency") or 0.0
        chg7d = m.get("price_change_percentage_7d_in_currency") or 0.0
        spark = (m.get("sparkline_in_7d") or {}).get("price") or []
        items.append({
            "key": gid,
            "label": info["symbol"] or m.get("symbol", "").upper(),
            "name": info["name"],
            "type": "crypto",
            "price": price,
            "val": _fmt_price(price),
            "chg": f"{chg:+.2f}%",
            "chgPct": round(chg, 2),
            "chg7d": round(chg7d, 2),
            "up": chg >= 0,
            "spark": [round(float(x), 8) for x in spark[::_SPARK_EVERY]],
            "mcap": mc,
            "mcapFmt": _fmt_mcap(mc),
            "revenue30d": info["revenue30d"],
            "revenueFmt": _fmt_rev(info["revenue30d"]),
            "category": info["category"],
            "link": f"https://www.coingecko.com/en/coins/{gid}",
        })
    return items
