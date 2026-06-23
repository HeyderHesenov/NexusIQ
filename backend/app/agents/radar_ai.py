"""RadarAI — kəşf edilmiş aktivin niyə perspektivli olduğunu GPT ilə izah edir.

On-demand (yalnız "AI izah" düyməsi) — API qənaəti. Tək GPT çağırışı → seçilmiş
dildə qısa, neytral izah (MC, gəlir/tema, momentum əsasında).
Nəticə (key, lang) üzrə yaddaşda keşlənir (1 saat).
"""
from __future__ import annotations

import time

from app.core.config import settings

_LANG_NAMES = {"az": "Azerbaijani", "en": "English", "ru": "Russian", "tr": "Turkish"}

_SYSTEM = (
    "You are a markets analyst for the NexusIQ terminal. You explain why a small, "
    "under-the-radar asset (micro-cap crypto or small-cap stock) currently stands "
    "out as a potential opportunity. 2-3 short sentences. Stay neutral and "
    "educational, give NO financial advice, invent no facts beyond the data given."
)

_TTL = 3600.0
_cache: dict[tuple[str, str], tuple[float, str]] = {}


def _prompt(item: dict, lang: str) -> str:
    lname = _LANG_NAMES.get(lang, "English")
    typ = item.get("type")
    lines = [
        f"Write entirely in {lname}. 2-3 short sentences, no preamble.",
        f"ASSET: {item.get('name') or item.get('label')} ({item.get('label')})",
        f"TYPE: {typ}",
        f"MARKET CAP: {item.get('mcapFmt')}",
        f"OPPORTUNITY SCORE: {item.get('score')}/100",
        f"24H CHANGE: {item.get('chg')}",
    ]
    if typ == "crypto":
        lines.append(f"CATEGORY: {item.get('category')}")
        lines.append(f"30-DAY PROTOCOL REVENUE: {item.get('revenueFmt')}")
        lines.append(
            "Explain why a revenue-generating micro-cap protocol at this size "
            "could be an early opportunity (real usage, fees, growth)."
        )
    else:
        lines.append(f"THEME: {item.get('theme')}")
        lines.append(
            "Explain the thesis: how this theme (e.g. AI demand → energy/chips) "
            "could drive this small-cap, and what the price trend suggests."
        )
    return "\n".join(lines)


async def explain(item: dict, lang: str) -> str | None:
    """Kəşf item-i üçün qısa AI izahı (keşli). Xəta/açar yoxdursa None."""
    from app.agents.llm import has_openai, openai_client

    lang = lang if lang in _LANG_NAMES else "az"
    ck = (item.get("key", ""), lang)
    hit = _cache.get(ck)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    if not has_openai():
        return None
    try:
        resp = await openai_client().chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": _prompt(item, lang)},
            ],
            temperature=0.5,
            max_tokens=240,
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception:  # noqa: BLE001
        return None
    if text:
        _cache[ck] = (time.time(), text)
    return text or None


# ---- "Haqqında" — ətraflı ümumi icmal (seçilmiş dildə) ----

_ABOUT_SYSTEM = (
    "You are a financial educator for the NexusIQ terminal. You write a clear, "
    "general overview of an asset for a curious retail reader. Be neutral and "
    "factual, give NO financial advice. Do NOT invent specifics: if a detail "
    "(e.g. a token burn schedule, exact dates, team names) is not widely known, "
    "say it is not publicly confirmed instead of guessing."
)

_ABOUT_TTL = 604_800.0  # 7 gün (haqqında məlumatı tez-tez dəyişmir)
_about_cache: dict[tuple[str, str], tuple[float, str]] = {}


def _about_prompt(item: dict, lang: str) -> str:
    lname = _LANG_NAMES.get(lang, "English")
    typ = item.get("type")
    lines = [
        f"Write entirely in {lname}. 3-5 short paragraphs, no headings, no preamble.",
        f"ASSET: {item.get('name') or item.get('label')} ({item.get('label')})",
        f"TYPE: {typ}",
        f"MARKET CAP: {item.get('mcapFmt')}",
    ]
    if typ == "crypto":
        lines.append(f"CATEGORY: {item.get('category')}")
        lines.append(
            "Cover: what this project is and who builds it (team/company/DAO); the "
            "problem it solves and its purpose; its tokenomics — supply model and "
            "whether the token is burned (mechanism and timing) if publicly known; "
            "and its overall vision and place in the market."
        )
    else:
        lines.append(f"THEME: {item.get('theme')}")
        lines.append(
            "Cover: what this company does and who runs it; its products and the "
            "problem it solves; how it fits its sector/theme; and its overall "
            "vision and growth outlook."
        )
    return "\n".join(lines)


async def about_stream(item: dict, lang: str):
    """Aktiv haqqında icmalı token-token axıdır (keşli 7 gün).

    Keşdə varsa bir parçada dərhal qaytarır (ani). Yoxdursa GPT-dən axıdır və
    sonda tam mətni keşləyir. Axın → istifadəçi mətni dərhal görməyə başlayır.
    """
    from app.agents.llm import has_openai, openai_client

    lang = lang if lang in _LANG_NAMES else "az"
    ck = (item.get("key", ""), lang)
    hit = _about_cache.get(ck)
    if hit and time.time() - hit[0] < _ABOUT_TTL:
        yield hit[1]
        return
    if not has_openai():
        return
    parts: list[str] = []
    try:
        stream = await openai_client().chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _ABOUT_SYSTEM},
                {"role": "user", "content": _about_prompt(item, lang)},
            ],
            temperature=0.4,
            max_tokens=480,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:  # usage/filter chunk — choices boş ola bilər
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                parts.append(delta)
                yield delta
    except Exception:  # noqa: BLE001
        return
    full = "".join(parts).strip()
    if full:
        _about_cache[ck] = (time.time(), full)
