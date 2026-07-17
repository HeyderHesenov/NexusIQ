"""SWR: paralel `force` yeniləmələri BİRLƏŞMƏLİDİR (coalesce).

Kök səbəb: `_locked_refresh` qoruması `if not force and _is_fresh(...)` idi —
`force=True` olduqda yoxlama kilidi ALDIQDAN SONRA da tam atlanırdı. Nəticədə
N paralel `?refresh=true` birləşmirdi: hər biri növbə ilə kilidi alıb TAM
yenidən hesablama edirdi. `/radar?refresh=true` hər çağırışda bulk `yf.download`
+ daxili 16-thread hovuz işə salır, `/anomalies?refresh=true` isə bütün
universumu yenidən skan edir — və hər ikisi limitsiz idi. Yəni "keşi keç"
düyməsi limitsiz DoS gücləndiricisi idi.

Coalesce meyarı `ttl` DEYİL, sorğunun BAŞLAMA anıdır (`t0`): biz kilidi
gözləyərkən yazılmış dəyər bizim sorğumuzdan SONRA hesablanıb, deməli "təzə
dəyər ver" tələbini ödəyir. Köhnə dəyər ödəmir → force semantikası qorunur.
"""
from __future__ import annotations

import asyncio

from app.analytics import swr


def _run(coro):
    return asyncio.run(coro)


def test_concurrent_force_coalesces():
    """10 paralel force → hesablama BİR dəfə. Regresiya budur."""
    calls = 0

    async def refresh():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)  # bahalı iş (yf.download təqlidi)
        return {"v": calls}

    store: dict = {}

    async def go():
        return await asyncio.gather(
            *(swr.get(store, 300.0, refresh, force=True) for _ in range(10))
        )

    results = _run(go())
    assert calls == 1, f"force birləşmədi — {calls} dəfə hesablandı"
    assert all(r == {"v": 1} for r in results)


def test_sequential_force_still_recomputes():
    """Ardıcıl (örtüşməyən) force HƏR DƏFƏ yeniləməlidir — semantika qorunur.

    Bu, yuxarıdakı düzəlişin `force`-u sadəcə söndürmədiyini pinləyir.
    """
    calls = 0

    async def refresh():
        nonlocal calls
        calls += 1
        return {"v": calls}

    store: dict = {}
    _run(swr.get(store, 300.0, refresh, force=True))
    _run(swr.get(store, 300.0, refresh, force=True))
    assert calls == 2, "force artıq təzə dəyər gətirmir — semantika qırılıb"


def test_force_bypasses_fresh_cache():
    """Keş TƏZƏ olsa belə force yenidən hesablayır (düymənin mənası budur)."""
    calls = 0

    async def refresh():
        nonlocal calls
        calls += 1
        return {"v": calls}

    store: dict = {}
    _run(swr.get(store, 300.0, refresh))  # soyuq → 1
    _run(swr.get(store, 300.0, refresh))  # təzə → keşdən, hesablama yox
    assert calls == 1
    _run(swr.get(store, 300.0, refresh, force=True))  # force → yenidən
    assert calls == 2


def test_non_force_fresh_read_is_cached():
    """Adi oxu davranışı dəyişməyib."""
    calls = 0

    async def refresh():
        nonlocal calls
        calls += 1
        return {"v": calls}

    store: dict = {}

    async def go():
        return await asyncio.gather(
            *(swr.get(store, 300.0, refresh) for _ in range(10))
        )

    _run(go())
    assert calls == 1
