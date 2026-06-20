"""EventBriefAgent — iqtisadi təqvim hadisəsi haqqında izahlı brief (GPT).

Bir GPT çağırışı → {what, higher, lower, pairs:[{sym, bias, reason}]} seçilmiş dildə.
On-demand çağırılır, (title|country|lang) üzrə yaddaşda keşlənir
(izah indikator üçün sabitdir, forecast/previous frontend-də göstərilir).
"""
from __future__ import annotations

import json

from openai import AsyncOpenAI

from app.core.config import settings

_LANG_NAMES = {
    "az": "Azerbaijani",
    "en": "English",
    "ru": "Russian",
    "tr": "Turkish",
}
_BIAS = {"up", "down", "mixed"}
_cache: dict[str, dict] = {}

_SYSTEM = (
    "You are a macro/markets educator for the NexusIQ terminal. You explain an "
    "economic calendar release clearly and neutrally for a retail trader: what it "
    "is, why it matters, and how a surprise vs. forecast typically moves currencies. "
    "Educational only, NO financial advice or guarantees. Write in the requested "
    "language. Azerbaijani (az) is NOT Turkish — true Azerbaijani uses 'ə'. "
    "Output ONLY valid JSON."
)


def _prompt(title: str, country: str, impact: str, lang: str) -> str:
    lname = _LANG_NAMES.get(lang, "English")
    return (
        f"Write entirely in {lname}.\n"
        f"Economic event: '{title}' (currency/region: {country}, impact: {impact}).\n"
        "Explain it. Return JSON exactly like:\n"
        "{"
        '"what":"2-3 sentences: what this indicator is, its purpose/logic, why markets watch it",'
        '"higher":"what a HIGHER-than-forecast reading usually signals + typical market reaction",'
        '"lower":"what a LOWER-than-forecast reading usually signals + typical reaction",'
        '"pairs":[{"sym":"EUR/USD","bias":"up","reason":"how this pair tends to move on a HIGHER reading and why"}]'
        "}\n"
        "Pick 3-4 most relevant pairs/instruments. bias is the pair's direction on a "
        "HIGHER-than-expected reading: one of up, down, mixed. Keep each field concise."
    )


async def event_brief(
    title: str,
    country: str,
    impact: str,
    lang: str,
    client: AsyncOpenAI | None = None,
) -> dict | None:
    """{what, higher, lower, pairs} qaytarır. Keşlənir. Xəta → None."""
    from app.agents.llm import openai_client

    key = f"{title}|{country}|{lang}"
    if key in _cache:
        return _cache[key]

    cli = client or openai_client()
    try:
        resp = await cli.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": _prompt(title, country, impact, lang)},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=700,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
    except Exception:  # noqa: BLE001
        return None

    what = data.get("what")
    if not isinstance(what, str) or not what.strip():
        return None
    pairs = []
    for p in data.get("pairs") or []:
        sym, bias, reason = p.get("sym"), p.get("bias"), p.get("reason")
        if not (isinstance(sym, str) and isinstance(reason, str)):
            continue
        pairs.append(
            {
                "sym": sym.strip()[:16],
                "bias": bias if bias in _BIAS else "mixed",
                "reason": reason.strip(),
            }
        )
    out = {
        "what": what.strip(),
        "higher": (data.get("higher") or "").strip(),
        "lower": (data.get("lower") or "").strip(),
        "pairs": pairs[:4],
    }
    _cache[key] = out
    return out
