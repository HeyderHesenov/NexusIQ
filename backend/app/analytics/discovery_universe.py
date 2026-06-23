"""Kəşf reyestri — tematik small-cap səbətlər (səhm + əmtəə).

Saf data: tema → ticker siyahısı. Məntiq yoxdur. Bilinməyən, kiçik kapitallı,
perspektivli adlar araşdırılıb tematik qruplaşdırılır. MC həddi runtime-da
(discovery_stocks) yoxlanır — şişmiş/delist olanlar avtomatik atılır.

Tema = istifadəçinin "trend → subsektor → şirkət" məntiqi (AI→enerji/çip→...).
"""
from __future__ import annotations

# Səhm temaları (hədəf MC ≤ $1B small-cap).
STOCK_THEMES: dict[str, list[str]] = {
    "ai_data": ["BBAI", "SOUN", "GFAI", "VERI", "DMTK", "CXAI", "AISP", "LTRX"],
    "semis": ["INDI", "NVTS", "LASR", "POET", "AOSL", "MTSI", "ICHR", "PRSO", "ATOM"],
    "robotics": ["SERV", "OUST", "LIDR", "REKR", "KSCP", "ARBE", "NNDM", "MARK"],
    "battery_energy": ["STEM", "SLDP", "ENVX", "MVST", "WATT", "BLNK", "FCEL", "AMPX", "SES"],
    "space": ["SPIR", "RDW", "BKSY", "LUNR", "MNTS"],
    "quantum": ["QUBT", "RGTI", "ARQQ", "QMCO"],
    "nuclear": ["NNE", "LTBR", "NPWR"],
    "biotech": ["MNKD"],
}

# Pin edilmiş ticker-lər — MC həddini keçsə belə Radarda həmişə görünür
# (istifadəçinin xüsusi istəyi ilə seçilmiş adlar).
PINNED: set[str] = {"MNKD"}

# Əmtəə temaları — niş əmtəəni istismar edən small-cap mədən/enerji şirkətləri.
COMMODITY_THEMES: dict[str, list[str]] = {
    "uranium": ["UEC", "UUUU", "DNN", "UROY", "EU", "WWR", "URG"],
    "lithium": ["SGML", "ATLX", "CRML", "LITM", "PLL"],
    "rare_earth": ["TMRC", "UAMY", "NB", "ARU"],
    "copper": ["TGB", "ERO", "WRN", "NGD", "HBM"],
    "gold_silver": ["GORO", "USAS", "MUX", "GATO", "SVM", "EXK", "FSM"],
    "oil_gas": ["REI", "EPM", "CRK", "SM", "BATL"],
}

# category → {theme: [ticker]}
THEMES: dict[str, dict[str, list[str]]] = {
    "stock": STOCK_THEMES,
    "commodity": COMMODITY_THEMES,
}


def universe(category: str) -> dict[str, str]:
    """category üçün {ticker: theme} düz xəritəsi (dublikatsız)."""
    out: dict[str, str] = {}
    for theme, tickers in THEMES.get(category, {}).items():
        for t in tickers:
            out.setdefault(t, theme)
    return out
