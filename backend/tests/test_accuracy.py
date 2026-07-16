"""Proqnoz doğruluq riyaziyyatı testləri — xarici sorğusuz (sırf hesablama).

İşlət: backend/.venv/bin/python -m tests.test_accuracy
"""
from __future__ import annotations

from app.analytics import accuracy, forecast_scorer


# ---- forecast_scorer._hit: istiqamət düzgünlüyü ----
def test_hit_up_positive() -> None:
    assert forecast_scorer._hit("up", 2.5) is True
    assert forecast_scorer._hit("up", -1.0) is False


def test_hit_down_negative() -> None:
    assert forecast_scorer._hit("down", -3.0) is True
    assert forecast_scorer._hit("down", 1.0) is False


def test_hit_neutral_and_none() -> None:
    # mixed/neutral → istiqamət iddiası yox
    assert forecast_scorer._hit("mixed", 5.0) is None
    assert forecast_scorer._hit("neutral", -5.0) is None
    assert forecast_scorer._hit("up", None) is None


# ---- forecast_scorer._sym_for: simvol çözümü ----
def test_sym_for_registry_and_coin() -> None:
    assert forecast_scorer._sym_for("btc") == "BTC-USD"
    assert forecast_scorer._sym_for("nvda") == "NVDA"
    assert forecast_scorer._sym_for("c_fet") == "FET-USD"
    assert forecast_scorer._sym_for("zzz_unknown") is None


# ---- accuracy._slice: hitRate / baseRate / delta / n-gate ----
def test_slice_basic_rates() -> None:
    # 10 proqnoz: 7 düz (hit=True). Bazar 6/10 müsbət (base "həmişə ▲").
    pairs = [
        (2.0, True), (1.0, True), (-1.0, True), (3.0, True), (0.5, True),
        (-2.0, True), (1.5, True), (-1.0, False), (-0.5, False), (2.0, False),
    ]
    s = accuracy._slice("Test", "test", 5, pairs)
    assert s["n"] == 10
    assert s["hitRate"] == 0.7  # 7/10
    assert s["baseRate"] == 0.6  # 6/10 müsbət gəlir
    assert s["delta"] == round(0.7 - 0.6, 3)
    assert s["insufficient"] is True  # n<20


def test_slice_sufficient_gate() -> None:
    pairs = [(1.0, True)] * 20  # hamısı düz, hamısı müsbət
    s = accuracy._slice("Big", "big", 30, pairs)
    assert s["n"] == 20
    assert s["insufficient"] is False  # n>=20
    assert s["hitRate"] == 1.0
    assert s["baseRate"] == 1.0
    assert s["delta"] == 0.0  # permabull ilə eyni → delta 0 (dürüst)


def test_slice_delta_can_be_negative() -> None:
    # Model 5/10 düz, amma bazar 8/10 müsbət → delta mənfi (dürüst kontekst).
    pairs = [(1.0, True)] * 5 + [(1.0, False)] * 3 + [(-1.0, False)] * 2
    s = accuracy._slice("Weak", "weak", 1, pairs)
    assert s["hitRate"] == 0.5
    assert s["baseRate"] == 0.8
    assert s["delta"] == round(0.5 - 0.8, 3)  # -0.3


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n✅ {len(fns)} test keçdi")
