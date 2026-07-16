"""Aktiv normalizatoru — sərbəst mətn / proqnoz simvolu → reyestr açarı.

`correlation.detect_assets` yalnız 9 aktivi tanıyır; bu modul TAM reyestrə
(`assets.ASSETS`, ~48 statik açar) genişləndirir və dəqiqlik qorunması əlavə edir.

Dəqiqlik strategiyası (yanlış tutmanı önləmək — trust-kritik feature):
  - SAFE ləqəblər (uzun adlar + toqquşmayan tickerlər): söz-sərhədi ilə,
    hərf-həssaslığı olmadan tutulur (`nvidia`, `micron`, `eur/usd`, `bitcoin`).
  - CAPS tickerlər (qısa, adi sözlə toqquşan: ARM, MU, SOL, HYPE...): YALNIZ
    orijinal mətndə tam BÖYÜK-HƏRF standalone token kimi tutulur.
  - DENY-context (oil/gold/meta kimi düzgün adi sözlər): söz-sərhədi ilə tutulur,
    amma "gold medal", "oil painting", "metadata" kimi ifadələr vetolayır.
  - Bare "AI", "NOW", "CRM" heç vaxt tək-başına tutulmur (çox generik) — yalnız
    ad forması ("c3.ai", "servicenow", "salesforce").

Uyğunlaşmayan simvol ATILMIR → `unmatched_syms` ilə səthə çıxarılır.
Aşkarlama YALNIZ statik reyestr üzərində (dinamik coinlər çox toqquşan) — amma
`normalize_sym` təmiz proqnoz simvolları üçün `c_<base>` coin açarını da qaytara bilir.
"""
from __future__ import annotations

import re

from app.analytics import assets, correlation

# ---- SAFE ləqəblər: söz-sərhədi, hərf-həssas deyil (ad + toqquşmayan ticker) ----
# 9 major üçün korrelyasiya ləqəblərini (çoxdilli) təməl götür.
_SAFE_ALIASES: dict[str, list[str]] = {
    "btc": ["btc", "bitcoin", "биткоин", "bitkoin"],
    "eth": ["eth", "ethereum", "ether", "эфир"],
    "sol": ["solana"],
    "xrp": ["xrp", "ripple"],
    "hype": ["hyperliquid"],
    "aster": ["aster dex"],
    # İndekslər
    "spx": ["s&p 500", "s&p500", "sp500", "spx", "s&p"],
    "ndx": ["nasdaq 100", "nasdaq", "ndx"],
    "dji": ["dow jones", "djia", "dow"],
    "rut": ["russell 2000", "russell"],
    "vix": ["vix", "volatility index"],
    "ftse": ["ftse 100", "ftse"],
    "dax": ["dax 40", "dax"],
    "cac": ["cac 40"],
    "nikkei": ["nikkei 225", "nikkei"],
    "hsi": ["hang seng"],
    "stoxx": ["euro stoxx 50", "euro stoxx", "stoxx"],
    "tsx": ["s&p/tsx", "tsx composite"],
    # Forex (pair-formaları aşağıda proqramla əlavə olunur; majorlara adlar)
    "eurusd": ["euro"],
    "usdjpy": ["japanese yen"],
    # Əmtəələr / metallar
    "oil": ["wti oil", "wti", "crude oil", "crude", "oil", "neft", "petrol", "нефть"],
    "brent": ["brent crude", "brent"],
    "natgas": ["natural gas", "nat gas", "natgas"],
    "heatingoil": ["heating oil"],
    "gasoline": ["gasoline", "rbob"],
    "gold": ["gold", "qızıl", "qizil", "altın", "altin", "xau", "золото"],
    "silver": ["silver", "gümüş", "gumus", "xag", "серебро"],
    "platinum": ["platinum", "platin"],
    "palladium": ["palladium", "palladi"],
    "copper": ["copper", "mis", "медь"],
    "aluminum": ["aluminum", "aluminium", "alüminium"],
    "lithium": ["lithium", "litium", "литий"],
    "uranium": ["uranium", "uran"],
    "steel": ["steel", "polad"],
    "rareearth": ["rare earth", "rare earths", "nadir torpaq"],
    "nickel": ["nickel", "никель"],
    # Səhmlər — adlar SAFE, toqquşan tickerlər CAPS/DENY-də
    "nvda": ["nvidia", "nvda"],
    "msft": ["microsoft", "msft"],
    "googl": ["alphabet", "google", "googl", "goog"],
    "amzn": ["amazon", "amzn"],
    "meta": ["meta platforms", "facebook", "instagram"],
    "amd": ["advanced micro devices", "amd"],
    "avgo": ["broadcom", "avgo"],
    "tsm": ["tsmc", "taiwan semiconductor", "tsm"],
    "pltr": ["palantir", "pltr"],
    "arm": ["arm holdings"],
    "mu": ["micron"],
    "smci": ["super micro", "supermicro", "smci"],
    "orcl": ["oracle", "orcl"],
    "crm": ["salesforce"],
    "now": ["servicenow"],
    "aic3": ["c3.ai", "c3 ai", "c3ai"],
    "dxy": ["dxy", "dollar index", "dollar indeksi", "индекс доллара"],
}

# CAPS tickerlər — YALNIZ orijinal mətndə tam böyük-hərf standalone token.
_CAPS_TICKERS: dict[str, list[str]] = {
    "sol": ["SOL"],
    "hype": ["HYPE"],
    "meta": ["META"],
    "amd": ["AMD"],
    "arm": ["ARM"],
    "mu": ["MU"],
}

# DENY-context — bu ifadələr olduqda həmin açarın SAFE uyğunluğunu vetola.
_DENY_CONTEXT: dict[str, list[str]] = {
    "gold": ["gold medal", "gold medalist", "olympic gold", "goldman"],
    "oil": ["oil painting", "oil paint", "essential oil", "cooking oil", "olive oil"],
    "meta": [
        "metadata", "meta data", "meta-analysis", "meta analysis",
        "meta description", "meta tag", "meta title", "metaverse",
    ],
}

_WORD = "a-z0-9əğıöşçü"  # söz simvolları (az hərfləri daxil)


def _forex_pair_forms(label: str) -> list[str]:
    """"EUR/USD" → ["eur/usd", "eurusd", "eur usd", "eur-usd"]."""
    base = label.lower().replace("/", "")
    if len(base) != 6:
        return [label.lower()]
    a, b = base[:3], base[3:]
    return [f"{a}/{b}", f"{a}{b}", f"{a} {b}", f"{a}-{b}"]


def _build() -> tuple[dict[str, re.Pattern], dict[str, re.Pattern], dict[str, str]]:
    """Açar üzrə SAFE regex + CAPS regex + ləqəb→açar dəqiq xəritəsi qur."""
    safe = {k: list(v) for k, v in _SAFE_ALIASES.items()}
    # Forex pair-formalarını reyestrdən proqramla əlavə et.
    for key, label, _sym, typ, _dec in assets.ASSETS:
        if typ == "forex":
            safe.setdefault(key, [])
            for form in _forex_pair_forms(label):
                if form not in safe[key]:
                    safe[key].append(form)

    safe_re: dict[str, re.Pattern] = {}
    exact: dict[str, str] = {}
    for key, aliases in safe.items():
        # Uzundan qısaya — uzun ləqəb əvvəl tutulsun.
        ordered = sorted(set(aliases), key=len, reverse=True)
        pat = "|".join(re.escape(a) for a in ordered)
        safe_re[key] = re.compile(
            rf"(?<![{_WORD}])(?:{pat})(?![{_WORD}])", re.IGNORECASE
        )
        for a in ordered:
            exact.setdefault(a.lower(), key)

    caps_re: dict[str, re.Pattern] = {}
    for key, tickers in _CAPS_TICKERS.items():
        pat = "|".join(re.escape(t) for t in tickers)
        caps_re[key] = re.compile(rf"(?<![A-Za-z0-9])(?:{pat})(?![A-Za-z0-9])")
        for t in tickers:
            exact.setdefault(t.lower(), key)
    # Açar özü də dəqiq uyğunluq (məs. "btc", "nvda").
    for key in safe:
        exact.setdefault(key, key)
    return safe_re, caps_re, exact


_SAFE_RE, _CAPS_RE, _EXACT = _build()

# Reyestr crypto bazası → açar (BTC→btc). Digər tanınan bazalar → c_<base>.
_BASE_TO_KEY: dict[str, str] = {}
for _k, _lbl, _sym, _typ, _dec in assets.ASSETS:
    if _typ == "crypto" and _sym.endswith("-USD"):
        _BASE_TO_KEY[_sym.split("-")[0].upper()] = _k
_KNOWN_BASES = set(assets._REGISTRY_BASES) | set(assets._FORCE_BASES)


def _deny_cleaned(low: str, key: str) -> str:
    """DENY açarı üçün mətndən veto-ifadələrini çıxarılmış nüsxə (lokal veto)."""
    deny = _DENY_CONTEXT.get(key)
    if not deny:
        return low
    out = low
    for phrase in deny:
        out = out.replace(phrase, " ")
    return out


def assets_in_text(text: str) -> list[str]:
    """Mətndə tanınan reyestr açarları — ilk görünmə sırası ilə, deduplənmiş.

    Statik reyestr üzərində; dəqiqlik qorunması (SAFE/CAPS/DENY) tətbiq olunur.
    """
    if not text:
        return []
    low = text.lower()
    hits: list[tuple[int, str]] = []
    seen: set[str] = set()

    # 1) SAFE pass (hərf-həssas deyil, söz-sərhədi, DENY vetosu).
    for key, rx in _SAFE_RE.items():
        target = _deny_cleaned(low, key) if key in _DENY_CONTEXT else low
        m = rx.search(target)
        if m:
            hits.append((m.start(), key))
            seen.add(key)

    # 2) CAPS pass (orijinal mətn, tam böyük-hərf ticker).
    for key, rx in _CAPS_RE.items():
        if key in seen:
            continue
        m = rx.search(text)
        if m:
            hits.append((m.start(), key))
            seen.add(key)

    hits.sort()
    return [k for _, k in hits]


def normalize_sym(free_text: str) -> str | None:
    """Bir proqnoz simvolunu ("S&P 500", "BTC", "EUR/USD") reyestr açarına çevir.

    Uyğun yoxdursa None (çağıran `unmatched_syms`-ə salır). Tanınan crypto bazası
    reyestrdə yoxdursa `c_<base>` coin açarı qaytarır (scorer `<base>-USD` çözür).
    """
    if not free_text:
        return None
    token = re.sub(r"\s+", " ", free_text.strip()).lower()
    if not token:
        return None
    # 1) Dəqiq ləqəb uyğunluğu.
    if token in _EXACT:
        return _EXACT[token]
    # 2) Söz-sərhədi aşkarlaması (mətn içində).
    found = assets_in_text(free_text)
    if found:
        return found[0]
    # 3) Crypto baza fallback (təmiz ticker → coin açarı).
    base = re.sub(r"[^A-Za-z0-9]", "", free_text.strip()).upper()
    if 2 <= len(base) <= 6 and base in _KNOWN_BASES:
        return _BASE_TO_KEY.get(base, f"c_{base.lower()}")
    return None


def unmatched_syms(pairs: list[dict]) -> list[str]:
    """Proqnoz pairs-dən açara çevrilə bilməyən simvollar (səthə çıxarmaq üçün)."""
    out: list[str] = []
    seen: set[str] = set()
    for p in pairs or []:
        sym = (p or {}).get("sym")
        if not sym or sym in seen:
            continue
        seen.add(sym)
        if normalize_sym(sym) is None:
            out.append(sym)
    return out
