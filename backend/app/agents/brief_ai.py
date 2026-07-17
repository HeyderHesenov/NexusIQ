"""BriefAgent — istənilən təqvim elementi üçün izahlı analiz (AI).

Vahid struktur, hər növ (event/earnings/unlock/cryptoEvent/asset) üçün uyğun
prompt: {what, scenarios:[{label,dir,text}], pairsNote, pairs:[{sym,bias,reason}]}.
On-demand çağırılır, (kind|name|sym|lang) üzrə yaddaşda keşlənir.
"""
from __future__ import annotations

import json

from app.agents.llm import PrimaryClient

from app.core.config import settings

_LANG_NAMES = {
    "az": "Azerbaijani",
    "en": "English",
    "ru": "Russian",
    "tr": "Turkish",
}
_DIR = {"up", "down", "mixed"}
_BIAS = {"up", "down", "mixed"}
# Sadə LRU-vari keş — açar user-controlled (name/sym), ona görə tavan qoyulur
# (limitsiz artım = memory-DoS). Tavan aşılanda ən köhnə açar atılır.
_cache: dict[str, dict] = {}
_CACHE_MAX = 512


def _cache_put(key: str, value: dict) -> None:
    if key in _cache:
        del _cache[key]
    elif len(_cache) >= _CACHE_MAX:
        _cache.pop(next(iter(_cache)), None)  # ən köhnə (FIFO)
    _cache[key] = value

# Hər növ üçün xüsusi təlimat (modelə İngiliscə, çıxış seçilmiş dildə).
_KIND_INSTR = {
    "event": (
        "an economic data release. Two scenarios: an ABOVE-forecast reading and a "
        "BELOW-forecast reading. Affected pairs = major currency pairs for this region."
    ),
    "earnings": (
        "a company's upcoming quarterly earnings report. Two scenarios: an earnings "
        "BEAT (above estimates) and a MISS (below). Affected = the stock itself, close "
        "sector peers, and the most relevant index (S&P 500 / NASDAQ)."
    ),
    "unlock": (
        "a crypto token unlock — vested tokens entering circulation, increasing supply. "
        "Two scenarios: the unlocked tokens are SOLD into the market (supply pressure), "
        "vs ABSORBED/staked (muted impact). Affected = the token vs USD and related assets."
    ),
    "cryptoEvent": (
        "a scheduled crypto event (e.g. Bitcoin halving, XRP escrow release, BNB burn, "
        "token unlock). Two scenarios: a bullish vs a bearish interpretation. "
        "Affected = the coin vs USD and related major coins."
    ),
    "asset": (
        "a tradable commodity/asset. Two scenarios: the key drivers that push its price "
        "UP, and the drivers that push it DOWN. Affected = the asset and correlated "
        "instruments (e.g. USD, related commodities)."
    ),
}

_SYSTEM = (
    "You are a markets educator for the NexusIQ terminal. You explain a calendar item "
    "clearly and neutrally for a retail trader. Educational only, NO financial advice "
    "or guarantees. Write in the requested language. Azerbaijani (az) is NOT Turkish — "
    "true Azerbaijani uses 'ə'. Output ONLY valid JSON."
)


def _prompt(kind: str, name: str, sym: str, meta: str, lang: str) -> str:
    lname = _LANG_NAMES.get(lang, "English")
    instr = _KIND_INSTR.get(kind, _KIND_INSTR["event"])
    ident = name + (f" ({sym})" if sym else "") + (f" — {meta}" if meta else "")
    return (
        f"Write entirely in {lname}.\n"
        f"Subject: {ident}.\n"
        f"This is {instr}\n\n"
        "Return JSON exactly like:\n"
        "{"
        '"what":"2-3 sentences: what this is, its purpose/logic, why markets watch it",'
        '"scenarios":[{"label":"short scenario name","dir":"up","text":"DETAILED explanation"},'
        '{"label":"...","dir":"down","text":"..."}],'
        '"pairsNote":"short label of the reference scenario the pair biases assume",'
        '"pairs":[{"sym":"EUR/USD","bias":"up","reason":"how/why this instrument tends to move"}]'
        "}\n"
        "Rules: exactly 2 scenarios. Each scenario `text` must be RICH and educational — "
        "4-6 sentences covering: (1) what this outcome concretely means, (2) the mechanism / "
        "WHY it moves markets, (3) the typical direction AND likely magnitude of the reaction, "
        "(4) which assets/sectors react most, and (5) one nuance or caveat (e.g. when the "
        "usual reaction may not hold). dir = up if the scenario is bullish for the subject, "
        "else down. pairs (3-4): bias (up/down/mixed) is each instrument's direction under "
        "the FIRST scenario; pairsNote names that scenario. `what` stays concise; the depth "
        "goes into the scenarios."
    )


async def market_brief(
    kind: str,
    name: str,
    sym: str = "",
    meta: str = "",
    lang: str = "az",
    client: PrimaryClient | None = None,
) -> dict | None:
    """{what, scenarios, pairsNote, pairs} qaytarır. Keşlənir. Xəta → None."""
    from app.agents.llm import primary_client

    # `kind` prompt seçimini idarə edir — whitelist-dən kənar dəyər `event`-ə
    # düşür. Açara XAM `kind` yazmaq keş açarını 24 simvolluq sərbəst mətnlə
    # şişirdərdi (eyni prompt, saysız açar); normallaşdırılmış dəyər yazılır.
    kind = kind if kind in _KIND_INSTR else "event"

    # `meta` AÇARA DA daxil olmalıdır, çünki `_prompt`-a DAXİL OLUR (`ident`).
    # Əvvəl açar `kind|name|sym|lang` idi: eyni ada, fərqli `meta` ilə gələn iki
    # sorğu eyni yazını bölüşürdü. Nəticə: hücumçu inyeksiyalı `meta` ilə
    # çağırır → cavab `earnings|NVIDIA|NVDA|az` açarında keşlənir → təqvimdən
    # NVIDIA-ya klikləyən real istifadəçi hücumçunun mətnini NexusIQ-un öz AI
    # analizi kimi görür (bütün istifadəçilərə, restarta qədər).
    # Həm də adi funksional bug idi: iki fərqli rüb bir yazını bölüşürdü.
    key = f"{kind}|{name}|{sym}|{meta}|{lang}"
    if key in _cache:
        return _cache[key]

    cli = client or primary_client()
    try:
        resp = await cli.chat.completions.create(
            model=settings.llm_primary_model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": _prompt(kind, name, sym, meta, lang)},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=1400,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
    except Exception:  # noqa: BLE001
        return None

    what = data.get("what")
    if not isinstance(what, str) or not what.strip():
        return None

    scenarios = []
    for s in (data.get("scenarios") or [])[:2]:
        label, sdir, text = s.get("label"), s.get("dir"), s.get("text")
        if not (isinstance(label, str) and isinstance(text, str)):
            continue
        scenarios.append(
            {
                "label": label.strip(),
                "dir": sdir if sdir in _DIR else "mixed",
                "text": text.strip(),
            }
        )

    pairs = []
    for p in data.get("pairs") or []:
        psym, bias, reason = p.get("sym"), p.get("bias"), p.get("reason")
        if not (isinstance(psym, str) and isinstance(reason, str)):
            continue
        pairs.append(
            {
                "sym": psym.strip()[:16],
                "bias": bias if bias in _BIAS else "mixed",
                "reason": reason.strip(),
            }
        )

    out = {
        "what": what.strip(),
        "scenarios": scenarios,
        "pairsNote": (data.get("pairsNote") or "").strip(),
        "pairs": pairs[:4],
    }
    _cache_put(key, out)
    return out
