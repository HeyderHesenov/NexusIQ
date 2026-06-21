"""Sentiment + Market Impact Score — pulsuz heuristik (AI tələb etmir).

Başlıq + xülasə mətnindən leksikon əsaslı qiymətləndirmə:
  - sentiment: -1..1 (mənfi ↔ müsbət)
  - impact: 0..100 (bazara potensial təsir)

Mənbə xəbərlər İngiliscədir, ona görə leksikon əsasən İngiliscədir.
Deterministik və sürətli — bütün bazanı saniyələrlə ballaya bilir.
"""
from __future__ import annotations

import re

# Müsbət / mənfi siqnal sözləri (kök formada — substring yoxlanır).
_POSITIVE = {
    "surge", "surges", "soar", "soars", "rally", "rallies", "jump", "jumps",
    "gain", "gains", "rise", "rises", "rising", "climb", "climbs", "beat",
    "beats", "record high", "all-time high", "boost", "boosts", "optimism",
    "growth", "bullish", "profit", "profits", "upgrade", "upgrades", "rebound",
    "recover", "recovery", "outperform", "strong", "stronger", "wins", "win",
    "approve", "approval", "boom", "soaring", "breakthrough", "high",
}
_NEGATIVE = {
    "crash", "crashes", "plunge", "plunges", "plummet", "fall", "falls",
    "falling", "drop", "drops", "decline", "declines", "loss", "losses",
    "miss", "misses", "fear", "fears", "recession", "war", "ban", "bans",
    "default", "slump", "bearish", "sink", "sinks", "tumble", "tumbles",
    "cut", "cuts", "downgrade", "sell-off", "selloff", "crisis", "weak",
    "weaker", "warning", "warn", "lawsuit", "fraud", "collapse", "slide",
    "slides", "low", "lows", "halt", "risk", "risks", "concern", "concerns",
}

# Yüksək təsirli terminlər (makro / bazar hərəkətediciləri).
_IMPACT_TERMS = {
    "fed", "federal reserve", "rate", "rates", "interest rate", "inflation",
    "cpi", "ppi", "gdp", "ecb", "boe", "boj", "jobs", "payroll", "unemployment",
    "recession", "war", "crash", "record", "billion", "trillion", "sec",
    "etf", "halving", "default", "crisis", "tariff", "sanction", "election",
    "earnings", "bankruptcy", "merger", "acquisition", "ipo", "downgrade",
    "stimulus", "yield", "treasury", "opec", "oil", "powell", "rate cut",
    "rate hike",
}

_PERCENT = re.compile(r"\d+(\.\d+)?\s?%")
_BIGNUM = re.compile(r"\$?\d[\d,]*\.?\d*\s?(billion|trillion|million|bn|tn)", re.I)


def _blob(title: str, summary: str | None) -> str:
    return f"{title} {summary or ''}".lower()


def score_text(
    title: str, summary: str | None, category: str | None = None
) -> tuple[float, float]:
    """(sentiment[-1..1], impact[0..100]) qaytarır."""
    text = _blob(title, summary)
    if not text.strip():
        return 0.0, 0.0

    pos = sum(1 for w in _POSITIVE if w in text)
    neg = sum(1 for w in _NEGATIVE if w in text)

    # Sentiment: müsbət/mənfi balansı, [-1..1]-ə sıxılır.
    total = pos + neg
    sentiment = 0.0 if total == 0 else (pos - neg) / total
    # Çox az siqnal varsa yumşalt (gücləndirməni şişirtmə).
    if total == 1:
        sentiment *= 0.6
    sentiment = round(max(-1.0, min(1.0, sentiment)), 2)

    # Impact: terminlər + faiz/böyük rəqəm + ümumi siqnal sıxlığı.
    impact_hits = sum(1 for w in _IMPACT_TERMS if w in text)
    has_percent = bool(_PERCENT.search(text))
    has_bignum = bool(_BIGNUM.search(text))

    raw = (
        impact_hits * 14
        + total * 6
        + (18 if has_percent else 0)
        + (16 if has_bignum else 0)
    )
    # Güclü sentiment özü təsiri artırır.
    raw += int(abs(sentiment) * 12)
    impact = round(min(100.0, float(raw)), 1)
    return sentiment, impact
