"""Sərhəd validasiyası — sərhədsiz epoch, Infinity/NaN, açar forması.

Kök səbəblər:
1. `last_seen: int | None` sərhədsiz idi → `datetime.fromtimestamp(1e17)` →
   `ValueError: year is out of range` → TUTULMAMIŞ 500 (canlı təsdiqləndi).
2. `qty: float` sərhədsiz idi. JSON `1e999` Python-da `float('inf')`-ə parse
   olunur; `_num`-un NaN qorusu (`v == v`) inf-i BURAXIR (inf == inf → True) və
   inf `qty > 0`-dan da keçir → portfel riyaziyyatı (`value`, `total_value`,
   `weight`) səssizcə null/NaN-a çevrilirdi.
3. FastAPI-ın defolt 422 cavabı XAM `input`-u geri əks etdirir. `input` inf
   olanda cavabın SERİALİZASİYASI partlayır ("Out of range float values are not
   JSON compliant") → düzgün 422 → 500-ə çevrilir. Yəni float qəbul edən
   İSTƏNİLƏN endpoint belə partladıla bilirdi.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.v1.routes import watchlist_intel as wi
from app.services import watchlist_intel as svc


# ---- 1. Epoch sərhədləri ----


def test_epoch_overflow_rejected():
    """`lastSeen` tavanı — əvvəl 500 verirdi."""
    with pytest.raises(ValidationError):
        wi.IntelRequest(keys=["btc"], lastSeen=99999999999999999999)


def test_epoch_negative_rejected():
    with pytest.raises(ValidationError):
        wi.IntelRequest(keys=["btc"], lastSeen=-1)


def test_epoch_normal_accepted():
    r = wi.IntelRequest(keys=["btc"], lastSeen=1780000000000)
    assert r.last_seen == 1780000000000
    assert wi._to_dt(r.last_seen) is not None


# ---- 2. Holding ədədi sərhədləri ----


@pytest.mark.parametrize("bad", [float("inf"), float("-inf"), float("nan")])
def test_holding_qty_non_finite_rejected(bad):
    """Infinity/NaN sərhəddə kəsilir — riyaziyyata çatmır."""
    with pytest.raises(ValidationError):
        wi.Holding(key="btc", qty=bad)


@pytest.mark.parametrize("bad", [0, -1, 1e13])
def test_holding_qty_range_rejected(bad):
    with pytest.raises(ValidationError):
        wi.Holding(key="btc", qty=bad)


def test_holding_avg_cost_non_finite_rejected():
    with pytest.raises(ValidationError):
        wi.Holding(key="btc", qty=1, avgCost=float("inf"))


def test_holding_valid_accepted():
    h = wi.Holding(key="btc", qty=2.5, avgCost=40000)
    assert h.qty == 2.5 and h.avg_cost == 40000


@pytest.mark.parametrize("bad", ["../../etc/passwd", "a" * 33, "", "a b", "x;drop"])
def test_holding_key_shape_rejected(bad):
    with pytest.raises(ValidationError):
        wi.Holding(key=bad, qty=1)


@pytest.mark.parametrize("ok", ["btc", "c_pepe", "eurusd", "^ndx", "BRK-B", "cl=f"])
def test_holding_key_real_forms_accepted(ok):
    """Real reyestr açarları qapıdan keçməlidir."""
    assert wi.Holding(key=ok, qty=1).key == ok


# ---- 3. Xidmət qatının öz qorusu ----


@pytest.mark.parametrize("bad", [float("inf"), float("-inf"), float("nan")])
def test_service_num_guard_rejects_non_finite(bad):
    """`_num` NaN VƏ ±Inf-in hər ikisini kəsməlidir (əvvəl yalnız NaN)."""
    assert svc._num(bad) is None


def test_service_num_keeps_finite():
    assert svc._num(2.5) == 2.5
    assert svc._num("3") == 3.0
    assert svc._num(None) is None


# ---- 4. Validasiya xətası girişi geri əks etdirməməlidir ----


def test_validation_handler_drops_input():
    """422 gövdəsi `input` daşımamalıdır.

    Regresiya: `input: inf` cavabın serializasiyasını partladıb 422-ni 500-ə
    çevirirdi. Həm də xam girişi geri qaytarmaq lazımsızdır.
    """
    import inspect

    from app import main

    src = inspect.getsource(main.create_app)
    assert "RequestValidationError" in src
    # yalnız loc/msg/type qaytarılır
    assert '"loc"' in src and '"msg"' in src and '"type"' in src
    assert '"input"' not in src
