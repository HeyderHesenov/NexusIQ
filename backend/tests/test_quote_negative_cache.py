"""`get_quote` uğursuzluğu da keşləməlidir — yoxsa bahalı yol qorunmamış qalır.

Kök səbəb: `if data: _quote_cache[key] = ...` — YALNIZ uğur keşlənirdi. Upstream-i
sınıq/ləng olan reyestr açarı (məs. bayat `CNH=X`) HƏR sorğuda yenidən
`asyncio.to_thread(_quote_sync, key)` ilə DEFOLT hovuza düşür və təzə şəbəkə
çağırışı edirdi — sonsuza qədər. Defolt hovuz 8 CPU-da cəmi 12 işçidir və
yfinance çağırışları ilə paylaşılır (img_cache.py:58 bu starvasiyanı ölçüb).

Üstəlik `/{key}/quote` və `/{key}` TAMAMİLƏ rate-limit-siz idi (qardaş
`/{key}/news`-də 60/60 var idi) — yəni tək açarla limitsiz outbound gücləndirici.

Kod bazası dərsi artıq yazmışdı (img_cache.py:25-26: "keş yalnız uğuru saxlayırdı
= bahalı yol qorunmamış qalırdı") — sadəcə bura köçürülməmişdi.
"""
from __future__ import annotations

import time

import pytest

from app.analytics import assets


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    assets._quote_cache.clear()
    assets._quote_neg.clear()
    yield
    assets._quote_cache.clear()
    assets._quote_neg.clear()


@pytest.mark.asyncio
async def test_failure_is_cached(monkeypatch):
    """Uğursuz açar üçün upstream BİR dəfə çağırılır, hər sorğuda yox."""
    calls = 0

    def failing(_key):
        nonlocal calls
        calls += 1
        return None

    monkeypatch.setattr(assets, "_quote_sync", failing)
    for _ in range(20):
        assert await assets.get_quote("gold") is None
    assert calls == 1, f"neqativ keş işləmir — {calls} upstream çağırışı"


@pytest.mark.asyncio
async def test_negative_ttl_expires(monkeypatch):
    """TTL bitəndə yenidən cəhd — keçici blip həmişəlik "ölü" olmasın.

    netguard/img_cache dərsi: keçici nasazlıq davamlı verdikt kimi yazılmamalıdır.
    """
    calls = 0

    def failing(_key):
        nonlocal calls
        calls += 1
        return None

    monkeypatch.setattr(assets, "_quote_sync", failing)
    await assets.get_quote("gold")
    assert calls == 1
    assets._quote_neg["gold"] = time.time() - assets._QUOTE_NEG_TTL - 1
    await assets.get_quote("gold")
    assert calls == 2


@pytest.mark.asyncio
async def test_success_clears_negative(monkeypatch):
    """Uğur neqativ damğanı silməlidir."""
    monkeypatch.setattr(assets, "_quote_sync", lambda _k: None)
    await assets.get_quote("gold")
    assert "gold" in assets._quote_neg

    monkeypatch.setattr(assets, "_quote_sync", lambda k: {"key": k, "price": 1.0})
    assets._quote_neg["gold"] = time.time() - assets._QUOTE_NEG_TTL - 1
    assert await assets.get_quote("gold") is not None
    assert "gold" not in assets._quote_neg


@pytest.mark.asyncio
async def test_negative_cache_is_bounded(monkeypatch):
    """Yaddaş sonsuz böyüməsin (dinamik `c_*` açarları saysızdır)."""
    monkeypatch.setattr(assets, "_quote_sync", lambda _k: None)
    for i in range(assets._NEG_MAX + 50):
        await assets.get_quote(f"c_x{i}")
    assert len(assets._quote_neg) <= assets._NEG_MAX


def test_asset_routes_have_rate_limits():
    """`/{key}/quote` və `/{key}` limitsiz qalmamalıdır."""
    import inspect

    from app.api.v1.routes import assets as routes

    src = inspect.getsource(routes)
    assert 'rate_limit("asset_read"' in src
    assert 'rate_limit("asset_registry"' in src
