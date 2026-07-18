"""Sərhəd validasiyası — xidmət qatı qorusu + 422 handler-in girişi əks etdirməməsi.

QEYD: köhnə /watchlist-intel route-unun IntelRequest/Holding sxem testləri Faza 4-də
route silindiyi üçün buradan çıxarıldı — həmin validasiya indi /me/holdings + /me/prefs
səviyyəsində `test_me_validation.py`-də (Infinity/NaN/range/açar/cap) örtülür.

Kök səbəb (qalan qorular):
- `_num`-un NaN qorusu (`v == v`) inf-i BURAXIRDI (inf==inf → True) → portfel riyaziyyatı
  səssizcə null/NaN olurdu. İndi ±Inf də kəsilir.
- FastAPI defolt 422 XAM `input`-u əks etdirirdi → `input: inf` cavab serializasiyasını
  partladıb 422-ni 500-ə çevirirdi. Handler `input`-u atır.
"""
from __future__ import annotations

import pytest

from app.services import watchlist_intel as svc


# ---- Xidmət qatının öz ədəd qorusu ----

@pytest.mark.parametrize("bad", [float("inf"), float("-inf"), float("nan")])
def test_service_num_guard_rejects_non_finite(bad):
    """`_num` NaN VƏ ±Inf-in hər ikisini kəsməlidir (əvvəl yalnız NaN)."""
    assert svc._num(bad) is None


def test_service_num_keeps_finite():
    assert svc._num(2.5) == 2.5
    assert svc._num("3") == 3.0
    assert svc._num(None) is None


# ---- Validasiya xətası girişi geri əks etdirməməlidir ----

def test_validation_handler_drops_input():
    """422 gövdəsi `input` daşımamalıdır (regresiya: `input: inf` → 500)."""
    import inspect

    from app import main

    src = inspect.getsource(main.create_app)
    assert "RequestValidationError" in src
    assert '"loc"' in src and '"msg"' in src and '"type"' in src
    assert '"input"' not in src
