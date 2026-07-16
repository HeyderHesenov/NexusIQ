"""asset_map normalizator testləri — xarici sorğusuz (sırf mətn/regex).

İşlət: backend/.venv/bin/python -m pytest tests/test_asset_map.py -q
   və ya: backend/.venv/bin/python -m tests.test_asset_map
"""
from __future__ import annotations

from app.analytics import asset_map


# ---- assets_in_text: dəqiqlik (yanlış tutma OLMAMALI) ----
def test_detect_names_and_caps_ticker() -> None:
    # "Micron" (SAFE ad) + "ARM" (CAPS ticker) — sıra ilə.
    assert asset_map.assets_in_text("Micron and ARM rally on AI demand") == ["mu", "arm"]


def test_no_false_positive_substring() -> None:
    # "harm" içində "arm" tutulmamalı; kiçik "arm" CAPS deyil.
    assert asset_map.assets_in_text("no harm done to the market") == []


def test_gold_medal_denied() -> None:
    assert asset_map.assets_in_text("She won a gold medal at the olympics") == []


def test_gold_price_matches() -> None:
    assert asset_map.assets_in_text("Gold prices surged to a record") == ["gold"]


def test_gold_azerbaijani() -> None:
    assert asset_map.assets_in_text("Qızıl bahalaşdı") == ["gold"]


def test_oil_painting_denied() -> None:
    assert asset_map.assets_in_text("A rare oil painting sold at auction") == []


def test_crude_oil_matches() -> None:
    assert asset_map.assets_in_text("Crude oil prices climbed") == ["oil"]


def test_metadata_denied_meta_company_matches() -> None:
    assert asset_map.assets_in_text("metadata schema migration") == []
    assert asset_map.assets_in_text("Meta Platforms beat estimates") == ["meta"]


def test_bare_ai_not_matched() -> None:
    # "artificial intelligence" / "AI" bare heç vaxt C3.ai deyil.
    assert asset_map.assets_in_text("The AI boom continues in 2026") == []
    assert asset_map.assets_in_text("C3.ai reported quarterly results") == ["aic3"]


def test_multi_asset_order() -> None:
    assert asset_map.assets_in_text("Bitcoin and Ethereum rallied") == ["btc", "eth"]


def test_forex_and_dxy() -> None:
    assert asset_map.assets_in_text("EUR/USD falls as DXY rises") == ["eurusd", "dxy"]


def test_solana_dedup() -> None:
    assert asset_map.assets_in_text("Solana SOL jumps 12%") == ["sol"]


def test_empty_input() -> None:
    assert asset_map.assets_in_text("") == []
    assert asset_map.assets_in_text("just some generic market commentary") == []


# ---- normalize_sym: proqnoz simvolları ----
def test_normalize_common_syms() -> None:
    assert asset_map.normalize_sym("S&P 500") == "spx"
    assert asset_map.normalize_sym("BTC") == "btc"
    assert asset_map.normalize_sym("EUR/USD") == "eurusd"
    assert asset_map.normalize_sym("Gold") == "gold"
    assert asset_map.normalize_sym("NASDAQ") == "ndx"
    assert asset_map.normalize_sym("SOL") == "sol"


def test_normalize_crypto_base_fallback() -> None:
    # Reyestrdə olmayan tanınan coin bazası → c_<base>.
    assert asset_map.normalize_sym("FET") == "c_fet"
    assert asset_map.normalize_sym("TAO") == "c_tao"


def test_normalize_unknown_none() -> None:
    assert asset_map.normalize_sym("USD/CNH") is None
    assert asset_map.normalize_sym("") is None
    assert asset_map.normalize_sym("SomeRandomThing") is None


def test_unmatched_syms_surfaced() -> None:
    pairs = [{"sym": "USD/CNH"}, {"sym": "BTC"}, {"sym": "ZZZZ"}]
    assert asset_map.unmatched_syms(pairs) == ["USD/CNH", "ZZZZ"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n✅ {len(fns)} test keçdi")
