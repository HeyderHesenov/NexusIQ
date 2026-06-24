"""Anomaliya math testləri — xarici sorğusuz (sırf hesablama).

İşlət: backend/.venv/bin/python -m tests.test_anomaly
"""
from __future__ import annotations

from app.analytics import anomaly


def approx(a: float, b: float, tol: float = 0.05) -> bool:
    return abs(a - b) <= tol


def test_robust_z_detects_outlier() -> None:
    # Sabit seriya + sonda böyük sıçrayış → yüksək z.
    base = [0.001 * ((-1) ** i) for i in range(60)]  # ~0 ətrafında
    base.append(0.08)  # ekstremal son nöqtə
    z = anomaly.robust_z(base)
    assert z is not None and z > 5, f"gözlənilən z>5, alındı {z}"


def test_robust_z_quiet_series_low() -> None:
    # Tək ölçülü kiçik dəyişimlər → kiçik z.
    series = [0.001 * ((-1) ** i) for i in range(80)]
    z = anomaly.robust_z(series)
    assert z is not None and abs(z) < 3, f"sakit seriyada z kiçik olmalı, {z}"


def test_mad_zero_std_fallback() -> None:
    # Median ətrafı eyni → MAD=0; std fallback son nöqtəni tutmalı.
    series = [1.0] * 40 + [1.0, 1.0, 5.0]
    z = anomaly.robust_z(series)
    assert z is not None and z > 3, f"std fallback işləməli, {z}"


def test_flat_series_no_signal() -> None:
    # Tam sabit → MAD=0, std=0 → None (siqnal yox).
    assert anomaly.robust_z([2.0] * 50) is None


def test_too_short() -> None:
    assert anomaly.robust_z([0.1, 0.2]) is None


def test_evaluate_requires_volume_confirmation() -> None:
    # Qiymət sıçrayır amma həcm sakit → anomaliya YOX.
    closes = [100.0]
    for i in range(1, 90):
        closes.append(closes[-1] * (1 + 0.001 * ((-1) ** i)))
    closes.append(closes[-1] * 1.12)  # böyük qiymət sıçrayışı
    quiet_vol = [1000.0 + ((-1) ** i) for i in range(len(closes))]
    res, _meta = anomaly._evaluate("x", "X", "index", closes, quiet_vol, "2026-06-22")
    assert res is None, "həcm təsdiqi olmadan anomaliya olmamalı"


def test_evaluate_full_anomaly() -> None:
    closes = [100.0]
    for i in range(1, 90):
        closes.append(closes[-1] * (1 + 0.001 * ((-1) ** i)))
    closes.append(closes[-1] * 1.12)  # qiymət sıçrayışı
    vols = [1000.0 + ((-1) ** i) for i in range(90)]
    vols.append(9000.0)  # həcm sıçrayışı
    res, meta = anomaly._evaluate("gold", "Gold", "metal", closes, vols, "2026-06-22")
    assert res is not None, "anomaliya gözlənilirdi"
    assert res["severity"] in ("high", "extreme")
    assert res["change_pct"] > 10
    assert res["volume_z"] >= 2
    assert meta is not None and "severity" not in meta  # meta sub-həddi forması


def test_severity_bands() -> None:
    assert anomaly._severity(3.5) == "medium"
    assert anomaly._severity(4.5) == "high"
    assert anomaly._severity(6.0) == "extreme"
    assert anomaly._severity(-6.0) == "extreme"


def _run() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
        passed += 1
    print(f"\n{passed}/{len(tests)} keçdi.")


if __name__ == "__main__":
    _run()
