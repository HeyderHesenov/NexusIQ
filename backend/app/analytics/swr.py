"""Stale-while-revalidate keş köməkçisi — sorğu heç vaxt yfinance-i gözləməsin.

Prinsip:
- Keş təzədir → dərhal qaytar.
- Keş köhnədir → köhnəni dərhal qaytar, arxa planda yenilə.
- Keş tam boşdursa (soyuq start) → bir dəfə blokla və hesabla.

Eyni anda gələn soyuq sorğular **lock** ilə birləşir (coalesce) — eyni iş
iki dəfə görülmür. Lock-dan sonra təkrar yoxlama: başqası artıq yeniləyibsə,
hesablama atılır.

`store` = {"ts": float, "data": Any} forması olan dict (mövcud keşlərlə uyğun).
`refresh` = data qaytaran async callable.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable

Refresh = Callable[[], Awaitable[Any]]


def _lock(store: dict) -> asyncio.Lock:
    lk = store.get("_lock")
    if lk is None:
        lk = asyncio.Lock()
        store["_lock"] = lk
    return lk


def _is_fresh(store: dict, ttl: float) -> bool:
    return bool(store.get("data")) and time.time() - store.get("ts", 0.0) < ttl


async def _locked_refresh(
    store: dict, ttl: float, refresh: Refresh, force: bool
) -> Any:
    # Kilidi GÖZLƏMƏZDƏN ƏVVƏLKİ an. `force` yolunda coalesce meyarı budur.
    t0 = time.time()
    async with _lock(store):
        # Gözləyərkən başqası yeniləyibsə, təkrar hesablama.
        if force:
            # Əvvəl `force` kilidi aldıqdan SONRA da yoxlamanı tam atlayırdı →
            # N paralel `?refresh=true` BİRLƏŞMİRDİ: hər biri növbə ilə kilidi
            # alıb TAM yenidən hesablama edirdi (radar üçün bulk yf.download +
            # daxili 16-thread hovuz). Yəni "keşi keç" düyməsi limitsiz DoS
            # gücləndiricisinə çevrilirdi.
            #
            # Meyar `ttl` DEYİL, `t0`-dır: biz gözləyərkən yazılmış dəyər bizim
            # sorğumuzdan SONRA hesablanıb, deməli "təzə dəyər ver" tələbini
            # onsuz da ödəyir. Köhnə (t0-dan əvvəlki) dəyər isə ödəmir → force
            # semantikası qorunur, yalnız ZAMAN ÜZRƏ ÖRTÜŞƏN sorğular birləşir.
            if store.get("data") and store.get("ts", 0.0) >= t0:
                return store["data"]
        elif _is_fresh(store, ttl):
            return store["data"]
        data = await refresh()
        if data:
            store["data"] = data
            store["ts"] = time.time()
    return store.get("data")


def _spawn(store: dict, ttl: float, refresh: Refresh) -> None:
    """Arxa planda yeniləmə — dublikatın qarşısını alır."""
    if store.get("_bg"):
        return
    store["_bg"] = True

    async def runner() -> None:
        try:
            async with _lock(store):
                if _is_fresh(store, ttl):
                    return
                data = await refresh()
                if data:
                    store["data"] = data
                    store["ts"] = time.time()
        finally:
            store["_bg"] = False

    asyncio.create_task(runner())


async def get(
    store: dict, ttl: float, refresh: Refresh, force: bool = False
) -> Any:
    """SWR oxuma. `force=True` → təzə dəyər üçün blokla (manual yenilə)."""
    if not force and _is_fresh(store, ttl):
        return store["data"]
    if not force and store.get("data"):
        _spawn(store, ttl, refresh)  # köhnə — arxa planda yenilə, köhnəni qaytar
        return store["data"]
    # soyuq və ya force → blokla (paralel sorğular birləşir)
    return await _locked_refresh(store, ttl, refresh, force)
