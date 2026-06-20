"""Crypto token-unlock təqvimi — DefiLlama pulsuz dataset (açarsız).

Seçilmiş coinlər üçün ən yaxın GƏLƏCƏK token açılışı (unlock) — real qiymət
katalizatoru. `api.llama.fi/emissions` Pro-ya keçib; bu açıq dataset host
(`defillama-datasets.llama.fi`) hələ pulsuzdur. Nəticə 3 saat keşlənir.

Qeyd: XRP/Render/Fetch DefiLlama emissions siyahısında yoxdur — daxil edilmir.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import httpx

_BASE = "https://defillama-datasets.llama.fi/emissions"
_UA = {"User-Agent": "Mozilla/5.0 (NexusIQ)"}
_TTL = 10800.0  # 3 saat
_cache: list | None = None
_cache_at = 0.0

# (simvol, DefiLlama slug, sektor). Sektorlar frontend dropdown-u ilə uyğun.
#   major = lider coinlər (çoxu artıq dövriyyədə → unlock seyrək)
#   rwa   = Real-World Assets (top 10)
#   ai    = AI coinlər
_COINS = [
    # --- Lider coinlər ---
    ("BTC", "bitcoin", "major"),
    ("ETH", "ethereum", "major"),
    ("SOL", "solana", "major"),
    # --- Perp DEX (törəmə birjalar) ---
    ("HYPE", "hyperliquid", "perp"),
    ("ASTER", "aster", "perp"),
    ("DYDX", "dydx", "perp"),
    ("GMX", "gmx", "perp"),
    ("JUP", "jupiter", "perp"),
    ("DRIFT", "drift", "perp"),
    ("INJ", "injective-orderbook", "perp"),
    ("SNX", "synthetix", "perp"),
    ("PERP", "perpetual-protocol", "perp"),
    ("BLUE", "bluefin", "perp"),
    # --- RWA (top 10) ---
    ("ONDO", "ondo-finance", "rwa"),
    ("OM", "mantra-dao", "rwa"),
    ("CFG", "centrifuge", "rwa"),
    ("PENDLE", "pendle", "rwa"),
    ("ENA", "ethena", "rwa"),
    ("USUAL", "usual", "rwa"),
    ("PLUME", "plume-mainnet", "rwa"),
    ("MPL", "maple-finance", "rwa"),
    ("GFI", "goldfinch", "rwa"),
    ("CPOOL", "clearpool", "rwa"),
    # --- AI ---
    ("TAO", "bittensor", "ai"),
    ("WLD", "worldcoin", "ai"),
    ("NEAR", "near", "ai"),
    ("VIRTUAL", "virtuals-protocol", "ai"),
    ("GRASS", "grass", "ai"),
    ("ARKM", "arkham", "ai"),
    ("ATH", "aethir", "ai"),
    ("KAITO", "kaito", "ai"),
    ("VANA", "vana", "ai"),
    ("SHELL", "myshell", "ai"),
    ("GRT", "the-graph", "ai"),
]


def _fmt_tokens(n: float) -> str:
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(n) >= div:
            return f"{n / div:.1f}{unit}"
    return str(int(n))


async def _next_unlock(
    client: httpx.AsyncClient, sym: str, slug: str, sector: str
) -> dict | None:
    """Bu coin üçün ən yaxın gələcək unlock hadisəsi (yoxdursa None)."""
    try:
        r = await client.get(f"{_BASE}/{slug}", timeout=25.0)
        r.raise_for_status()
        events = (r.json().get("metadata") or {}).get("events") or []
    except Exception:  # noqa: BLE001
        return None

    now = time.time()
    future = sorted(
        (e for e in events if (e.get("timestamp") or 0) >= now),
        key=lambda e: e["timestamp"],
    )
    if not future:
        return None

    ts = future[0]["timestamp"]
    same = [e for e in future if e["timestamp"] == ts]  # eyni gündə birləşdir
    tokens = sum(sum(e.get("noOfTokens") or [0]) for e in same)
    if tokens <= 0:
        return None
    return {
        "sym": sym,
        "sector": sector,
        "date": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(),
        "tokens": _fmt_tokens(tokens),
        "category": same[0].get("category") or "",
    }


async def get_crypto_calendar() -> list[dict]:
    """Yaxın token unlock-ları (sektor etiketli), tarixə görə sıralı."""
    global _cache, _cache_at
    now = time.monotonic()
    if _cache is not None and now - _cache_at < _TTL:
        return _cache
    try:
        async with httpx.AsyncClient(headers=_UA, follow_redirects=True) as client:
            results = await asyncio.gather(
                *(_next_unlock(client, s, slug, sec) for s, slug, sec in _COINS)
            )
    except Exception:  # noqa: BLE001
        return _cache or []
    items = sorted((r for r in results if r), key=lambda x: x["date"])
    if items:
        _cache, _cache_at = items, now
    return items
