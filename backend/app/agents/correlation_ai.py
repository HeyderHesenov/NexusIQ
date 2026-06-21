"""CorrelationAgent — iki aktiv arası korrelyasiyanı izah edir (GPT + fallback).

AI varsa qısa, neytral izah verir; yoxdursa dəyərə əsaslanan şablon mətn.
(a|b|yuvarlaq dəyər|lang) üzrə keşlənir.
"""
from __future__ import annotations

from app.agents.llm import has_openai, openai_client
from app.core.config import settings

_LANG_NAMES = {"az": "Azerbaijani", "en": "English", "ru": "Russian", "tr": "Turkish"}
_cache: dict[str, str] = {}

_SYSTEM = (
    "You are a markets educator for the NexusIQ terminal. Explain the statistical "
    "correlation between two assets in 2-3 short sentences for a retail trader: what "
    "the value means (direction + strength) and one practical takeaway (e.g. "
    "diversification or hedging). Educational only, NO financial advice. Write in the "
    "requested language. Azerbaijani (az) is NOT Turkish — true Azerbaijani uses 'ə'. "
    "Plain text only, no markdown."
)


def _strength(value: float, lang: str) -> str:
    """Dəyər → söz (güc + istiqamət), 4 dildə fallback üçün."""
    a = abs(value)
    table = {
        "az": ("güclü", "orta", "zəif", "demək olar əlaqəsiz", "müsbət", "mənfi"),
        "en": ("strong", "moderate", "weak", "almost none", "positive", "negative"),
        "ru": ("сильная", "умеренная", "слабая", "почти отсутствует", "положительная", "отрицательная"),
        "tr": ("güçlü", "orta", "zayıf", "neredeyse yok", "pozitif", "negatif"),
    }
    strong, moderate, weak, none_, pos, neg = table.get(lang, table["az"])
    mag = strong if a >= 0.6 else moderate if a >= 0.3 else weak if a >= 0.1 else none_
    direction = pos if value >= 0 else neg
    return f"{mag} {direction}"


def _fallback(label_a: str, label_b: str, value: float, lang: str) -> str:
    """AI yoxdursa dəyərə əsaslanan izah."""
    desc = _strength(value, lang)
    templates = {
        "az": (
            f"{label_a} və {label_b} arasında {value:+.2f} korrelyasiya var — {desc} əlaqə. "
            f"{'Birlikdə hərəkət etməyə meyllidirlər' if value >= 0.1 else 'Əks istiqamətdə hərəkət edirlər' if value <= -0.1 else 'Müstəqil hərəkət edirlər'}. "
            "Diversifikasiya üçün aşağı korrelyasiyalı aktivlər faydalıdır."
        ),
        "en": (
            f"{label_a} and {label_b} have a {value:+.2f} correlation — a {desc} relationship. "
            f"{'They tend to move together' if value >= 0.1 else 'They tend to move opposite' if value <= -0.1 else 'They move independently'}. "
            "Low-correlation assets help diversification."
        ),
        "ru": (
            f"Корреляция {label_a} и {label_b} составляет {value:+.2f} — {desc} связь. "
            f"{'Движутся в одном направлении' if value >= 0.1 else 'Движутся в противоположных направлениях' if value <= -0.1 else 'Движутся независимо'}. "
            "Активы с низкой корреляцией полезны для диверсификации."
        ),
        "tr": (
            f"{label_a} ve {label_b} arasında {value:+.2f} korelasyon var — {desc} ilişki. "
            f"{'Birlikte hareket etme eğilimindeler' if value >= 0.1 else 'Ters yönde hareket ederler' if value <= -0.1 else 'Bağımsız hareket ederler'}. "
            "Düşük korelasyonlu varlıklar çeşitlendirmeye yardımcı olur."
        ),
    }
    return templates.get(lang, templates["az"])


async def explain(label_a: str, label_b: str, value: float, lang: str = "az") -> str:
    """İki aktivin korrelyasiyası üçün qısa izah (keşli)."""
    lang = lang if lang in _LANG_NAMES else "az"
    cache_key = f"{label_a}|{label_b}|{round(value, 1)}|{lang}"
    if cache_key in _cache:
        return _cache[cache_key]

    if not has_openai():
        text = _fallback(label_a, label_b, value, lang)
        _cache[cache_key] = text
        return text

    try:
        resp = await openai_client().chat.completions.create(
            model=settings.openai_model,
            temperature=0.4,
            max_tokens=220,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Assets: {label_a} and {label_b}. Pearson correlation of daily "
                        f"returns: {value:+.2f}. Respond in {_LANG_NAMES[lang]}."
                    ),
                },
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            text = _fallback(label_a, label_b, value, lang)
    except Exception:
        text = _fallback(label_a, label_b, value, lang)

    _cache[cache_key] = text
    return text
