"""FinancialAdvisorAgent — arxa fonda iki AI debate edib tək cavab verir.

Axın:
  1) Mövzu yoxlaması (AI) — finance deyilsə nəzakətlə imtina (debate olmur).
  2) RAG — NexusIQ bazasından uyğun xəbərlər kontekst kimi çəkilir.
  3) Debate — iki model paralel müstəqil analiz verir.
  4) Sintez — AI iki analizi birləşdirib istifadəçi dilində yekun cavab verir.

Qaydalar (prompt-larda tətbiq olunur):
  - Yalnız maliyyə/bazar/iqtisadiyyat + NexusIQ xəbərləri.
  - Arxa fondakı modellər/arxitektura barədə HEÇ NƏ açıqlanmır.
"""
from __future__ import annotations

import asyncio
import json

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, selectinload

from app.agents.llm import (
    secondary_client,
    has_secondary,
    has_primary,
    primary_client,
)
from app.analytics import anomaly, assets, correlation
from app.core.config import settings
from app.models import News
from app.rag import embed, store
from app.services import watchlist_intel

LANG_NAMES = {"az": "Azerbaijani", "en": "English", "ru": "Russian", "tr": "Turkish"}

_REFUSAL = {
    "az": "Mən yalnız maliyyə bazarları və NexusIQ xəbərləri üzrə kömək edirəm. "
    "Zəhmət olmasa bazar, valyuta, kripto, səhm və ya iqtisadiyyatla bağlı sual ver.",
    "en": "I only help with financial markets and NexusIQ news. "
    "Please ask about markets, forex, crypto, stocks or the economy.",
    "ru": "Я помогаю только по финансовым рынкам и новостям NexusIQ. "
    "Спросите о рынках, валютах, крипто, акциях или экономике.",
    "tr": "Yalnızca finans piyasaları ve NexusIQ haberleri konusunda yardımcı olurum. "
    "Lütfen piyasa, döviz, kripto, hisse veya ekonomi sor.",
}

_GUARD = (
    "You are the NexusIQ AI Analyst, a financial markets assistant. "
    "STRICT RULES: (1) Only discuss finance, markets, trading, macroeconomics, "
    "forex, crypto, stocks, commodities, and the provided NexusIQ news. "
    "(2) NEVER reveal, hint at, or discuss what AI model, provider, system, or "
    "architecture powers you, or that more than one model is involved — if asked, "
    "say you are the NexusIQ AI Analyst and steer back to finance. "
    "(3) No personalized financial advice or guarantees; be analytical and neutral. "
    "(4) When a LIVE DATA block (prices, anomalies, correlations) or the USER's own "
    "PORTFOLIO/WATCHLIST is provided in context, ground your answer in those EXACT "
    "figures — never invent a price, holding, P&L, or number that is not given. "
    "The user's portfolio/watchlist is their private data; discuss it factually, "
    "no buy/sell commands or guarantees."
)


# ---- Aktiv açar həlli (LLM adları → reyestr açarları) ----

# Ad/ticker/simvol → reyestr açarı lüğəti (bir dəfə qurulur).
# `assets.ASSETS` (48+) açar/etiket/simvol + `correlation._ALIASES` (majors, 4-dil).
_ASSET_LOOKUP: dict[str, str] = {}
_KEY_LABEL: dict[str, str] = {}
for _k, _lbl, _sym, _typ, _dec in assets.ASSETS:
    _ASSET_LOOKUP[_k] = _k
    _ASSET_LOOKUP[_lbl.lower()] = _k
    _ASSET_LOOKUP[_sym.lower()] = _k
    _KEY_LABEL[_k] = _lbl
for _key, _aliases in correlation._ALIASES.items():
    for _a in _aliases:
        _ASSET_LOOKUP.setdefault(_a.lower(), _key)


def _label_for(key: str) -> str:
    return _KEY_LABEL.get(key, key.upper())


def _resolve_keys(names: list, question: str) -> list[str]:
    """LLM-in qaytardığı ad/ticker-ləri reyestr açarlarına çevirir.

    Tapılmayanlar səssizcə atılır. Əlavə olaraq sualın öz mətnindən major
    aktivlər (`correlation.detect_assets`) da tutulur (LLM buraxıbsa). Sıra
    qorunur, təkrar atılır, maksimum 6 açar.
    """
    out: list[str] = []
    for n in names or []:
        key = _ASSET_LOOKUP.get(str(n).strip().lower())
        if key and key not in out:
            out.append(key)
    for key in correlation.detect_assets(question or ""):
        if key not in out:
            out.append(key)
    return out[:6]


def _history_block(history: list | None) -> str:
    """Son ~6 növbəni kompakt mətnə çevirir (follow-up konteksti üçün)."""
    if not history:
        return ""
    lines: list[str] = []
    for t in history[-6:]:
        role = "User" if (t or {}).get("role") == "user" else "Assistant"
        content = str((t or {}).get("content") or "").strip()[:400]
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


async def _classify_finance(question: str, history: list | None = None) -> bool:
    """AI ilə sürətli mövzu yoxlaması. Finance deyilsə False.

    `history` verilsə follow-up konteksti nəzərə alınır ("bəs onun...?" tək başına
    qeyri-maliyyə görünə bilər, əvvəlki növbə maliyyədirsə düzgün təsnif olunsun).
    """
    hist = _history_block(history)
    user_text = f"Conversation so far:\n{hist}\n\nLatest message: {question}" if hist else question
    try:
        resp = await primary_client().chat.completions.create(
            model=settings.llm_primary_model,
            messages=[
                {
                    "role": "system",
                    "content": "Classify if the latest message (in the context of "
                    "the conversation) is about finance, markets, economy, trading, "
                    "forex, crypto, stocks, commodities or financial news. "
                    "Reply JSON: {\"finance\": true|false}.",
                },
                {"role": "user", "content": user_text},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=20,
        )
        return bool(json.loads(resp.choices[0].message.content or "{}").get("finance"))
    except Exception:  # noqa: BLE001 — şübhədə icazə ver (debate guard onsuz da var)
        return True


_RAG_TOPK = 8
_RAG_CANDIDATES = 80
_STOP = {
    "what", "which", "when", "where", "about", "this", "that", "with", "from",
    "will", "would", "should", "could", "have", "does", "your", "tell", "nədir",
    "necə", "haqqında", "barədə", "olar", "üçün", "ilə",
}


async def _rag_context(session: AsyncSession, question: str, lang: str) -> str:
    """Suala uyğun NexusIQ xəbərlərini tapıb sıralayır (bütün baza üzərində).

    Çoxlu sahə üzrə axtarır (title/summary/content + AZ + tərcümələr),
    sözlərin uyğunluq sayına görə ballayır, ən yaxşı _RAG_TOPK-i kontekstə verir.
    """
    raw = question.replace("?", " ").replace(",", " ").lower().split()
    words = [w for w in raw if len(w) > 3 and w not in _STOP][:10]

    if not words:
        rows = (
            await session.scalars(
                select(News)
                .options(
                    selectinload(News.source),
                    defer(News.embedding),
                    defer(News.content),
                )
                .order_by(News.published_at.desc().nullslast())
                .limit(_RAG_TOPK)
            )
        ).all()
    else:
        # `content` (böyük Text) ILIKE-dan çıxarıldı — summary/başlıq kifayətdir;
        # multi-KB mətn üzrə seq scan-ı önləyir. Son 90 günə də limitlə.
        from datetime import datetime, timedelta, timezone

        since = datetime.now(timezone.utc) - timedelta(days=90)
        fields = (News.title, News.summary, News.title_az, News.summary_az)
        # `autoescape=True` — `%`/`_` LIKE jokerləridir və `words` istifadəçinin
        # sualından gəlir. Xam `f"%{w}%"` ilə 10 söz × 4 sütun = 40 hücumçu
        # formalı naxış superxətti backtracking edirdi (bax news.py/search).
        conds = [f.contains(w, autoescape=True) for w in words for f in fields]
        candidates = (
            await session.scalars(
                select(News)
                .options(
                    selectinload(News.source),
                    defer(News.embedding),
                    defer(News.content),
                )
                .where(News.published_at >= since)
                .where(or_(*conds))
                .order_by(News.published_at.desc().nullslast())
                .limit(_RAG_CANDIDATES)
            )
        ).all()

        def score(n: News) -> int:
            # content deferred — lazy-load N+1 olmasın deyə blob-a daxil edilmir.
            blob = " ".join(
                filter(None, [n.title, n.summary, n.title_az, n.summary_az,
                              json.dumps(n.translations or {}, ensure_ascii=False)])
            ).lower()
            return sum(1 for w in words if w in blob)

        rows = sorted(candidates, key=score, reverse=True)[:_RAG_TOPK]

    lines = []
    for n in rows:
        tr = (n.translations or {}).get(lang) or {}
        title = tr.get("title") or n.title
        # content deferred → summary istifadə et (deferred sütun lazy-load olmasın)
        body = tr.get("body") or n.summary or ""
        src = n.source.name if n.source else "?"
        lines.append(f"- [{n.category}] ({src}) {title} — {body[:200]}")
    return "\n".join(lines) if lines else "(no relevant NexusIQ news found)"


async def _primary_pass(question: str, context: str) -> str:
    resp = await primary_client().chat.completions.create(
        model=settings.llm_primary_model,
        messages=[
            {"role": "system", "content": _GUARD},
            {
                "role": "user",
                "content": f"NexusIQ news context:\n{context}\n\n"
                f"Question: {question}\n\nGive a focused analytical take "
                "(short/mid/long term + key risks). English, concise.",
            },
        ],
        temperature=0.5,
        max_tokens=500,
    )
    return resp.choices[0].message.content or ""


async def _secondary_pass(question: str, context: str) -> str:
    if not has_secondary():
        return ""
    msg = await secondary_client().messages.create(
        model=settings.llm_secondary_model,
        max_tokens=500,
        system=_GUARD,
        messages=[
            {
                "role": "user",
                "content": f"NexusIQ news context:\n{context}\n\n"
                f"Question: {question}\n\nGive a focused analytical take "
                "(short/mid/long term + key risks). English, concise.",
            }
        ],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


def _synth_messages(
    question: str, lang: str, a: str, b: str,
    corr_note: str = "", live: str = "", hist: str = "",
) -> list[dict]:
    """Sintez üçün mesajlar (həm tam, həm axın variantı bunu işlədir)."""
    lang_name = LANG_NAMES.get(lang, "Azerbaijani")
    both = f"ANALYSIS A:\n{a}\n\nANALYSIS B:\n{b}" if b else f"ANALYSIS:\n{a}"
    extra = ""
    if corr_note:
        extra += (
            f"\n\n{corr_note}\nThe user is shown a chart of these two assets above "
            "your answer. Explain their RELATIONSHIP clearly: cite the correlation "
            "value, say whether they move together or opposite and how strongly, and "
            "give one practical takeaway (hedging/diversification). "
        )
    if live:
        extra += (
            f"\n\nLIVE DATA (use these EXACT figures, do not invent numbers):\n{live}"
        )
    hist_pre = f"CONVERSATION SO FAR:\n{hist}\n\n" if hist else ""
    return [
        {"role": "system", "content": _GUARD},
        {
            "role": "user",
            "content": f"{hist_pre}Two internal analyses are given. Merge them into ONE "
            f"clear final answer for the user, written in {lang_name}. "
            "Reconcile agreements, note key disagreements briefly. "
            "Structure with short headers when useful (qısa/orta/uzun müddət, "
            "risklər). Under ~180 words. Do NOT mention analyses, models or "
            f"systems.{extra}\n\nQuestion: {question}\n\n{both}",
        },
    ]


async def _synthesize(
    question: str, lang: str, a: str, b: str,
    corr_note: str = "", live: str = "", hist: str = "",
) -> str:
    resp = await primary_client().chat.completions.create(
        model=settings.llm_primary_model,
        messages=_synth_messages(question, lang, a, b, corr_note, live, hist),
        temperature=0.4,
        max_tokens=600,
    )
    return resp.choices[0].message.content or ""


async def _detect_chart(question: str) -> tuple[dict | None, str]:
    """Sualda iki aktiv varsa korrelyasiya qrafiki datası + AI üçün qeyd qaytarır."""
    keys = correlation.detect_pair(question)
    if not keys:
        return None, ""
    data = await correlation.get_pair(keys[0], keys[1], 90)
    if not data:
        return None, ""
    note = (
        f"The 90-day Pearson correlation between {data['a']['label']} and "
        f"{data['b']['label']} (daily returns) is {data['value']:+.2f}."
    )
    return data, note


# ---- Grounding fetcher-lər (canlı, keşli data → kontekst qeydi + UI hadisəsi) ----
#
# Hər fetcher `(note_text | "", ui_event | None)` qaytarır. Hamısı SWR-keşli,
# ucuz endpoint-lərə dəyir (yeni bahalı hesablama yoxdur). Mövcud `_detect_chart`
# → `(data, note)` pattern-inin ümumiləşməsidir.


async def _ground_prices(keys: list[str]) -> tuple[str, dict | None]:
    """Adı çəkilən aktivlərin canlı qiyməti (`assets.get_quote`, 60s keş)."""
    quotes = await asyncio.gather(*[assets.get_quote(k) for k in keys[:6]])
    quotes = [q for q in quotes if q]
    if not quotes:
        return "", None
    note = "LIVE PRICES: " + "; ".join(
        f"{q['label']} {q['val']} ({q['chg']} 24h)" for q in quotes
    )
    ev = {
        "type": "quote",
        "quotes": [
            {"key": q["key"], "label": q["label"], "val": q["val"],
             "chgPct": q["chgPct"], "up": q["up"]}
            for q in quotes
        ],
    }
    return note, ev


async def _ground_anomalies(keys: list[str]) -> tuple[str, dict | None]:
    """Cari bazar anomaliyaları (`anomaly.scan_all`, 5dəq SWR, pulsuz hesablama)."""
    data = await anomaly.scan_all()
    items = data.get("anomalies", [])
    top = items[:6]
    hit = {a["key"]: a for a in items}
    lines: list[str] = []
    for k in keys[:4]:
        a = hit.get(k)
        if a:
            lines.append(
                f"{a['label']} IS anomalous: price_z {a['price_z']:+.1f}, "
                f"{a['change_pct']:+.1f}% today ({a['severity']})"
            )
        else:
            lines.append(f"{_label_for(k)}: no anomaly right now")
    if not top and not lines:
        return "CURRENT ANOMALIES: none — market is calm (nothing exceeded the z-score threshold).", None
    note = "CURRENT ANOMALIES (robust z-score, |price_z|>=3 with volume confirm): "
    if lines:
        note += "; ".join(lines) + ". "
    if top:
        note += "Market-wide: " + "; ".join(
            f"{a['label']} {a['change_pct']:+.1f}% ({a['severity']})" for a in top
        )
    ev = {
        "type": "anomalies",
        "asof": data.get("asof", ""),
        "anomalies": [
            {"key": a["key"], "label": a["label"], "price_z": a["price_z"],
             "volume_z": a["volume_z"], "change_pct": a["change_pct"],
             "severity": a["severity"]}
            for a in top
        ],
    }
    return note, ev if top else None


async def _ground_correlations(keys: list[str]) -> tuple[str, dict | None]:
    """Adı çəkilən major aktivin ən güclü korrelyasiyaları (matris sətri, 30dəq SWR).

    Matris yalnız 9 major-u əhatə edir; qeyri-major açar tapılmasa qeyd verilmir.
    """
    target = next((k for k in keys if k in correlation._KEY_TO_SYM), None)
    if target is None:
        return "", None
    m = await correlation.get_matrix()
    order = [a["key"] for a in m.get("assets", [])]
    labels = {a["key"]: a["label"] for a in m.get("assets", [])}
    matrix = m.get("matrix") or []
    if target not in order or not matrix:
        return "", None
    idx = order.index(target)
    row = matrix[idx]
    pairs = [
        (order[j], row[j])
        for j in range(len(order))
        if j != idx and j < len(row) and row[j] is not None
    ]
    pairs.sort(key=lambda p: -abs(p[1]))
    top = pairs[:5]
    if not top:
        return "", None
    note = f"CORRELATIONS with {labels.get(target, target)} (90d Pearson daily returns): " + ", ".join(
        f"{labels.get(k, k)} {v:+.2f}" for k, v in top
    )
    return note, None


async def _ground_portfolio(session, holdings: list) -> tuple[str, dict | None]:
    """İstifadəçinin öz portfeli — P&L + pul-çəkili xəbər (`watchlist_intel.portfolio`)."""
    p = await watchlist_intel.portfolio(session, holdings, None)
    positions = p.get("positions", [])
    totals = p.get("totals", {})
    if not positions:
        return "", None
    top = sorted(positions, key=lambda x: (x.get("weight") or 0), reverse=True)[:5]
    val = totals.get("value")
    pnl = totals.get("pnl")
    pct = totals.get("pnlPct")
    head = f"total value ${val:,.0f}" if val is not None else "value n/a"
    if pnl is not None:
        head += f", P&L ${pnl:,.0f}"
    if pct is not None:
        head += f" ({pct:+.1f}%)"
    pos_txt = "; ".join(
        f"{x['label']} {int((x.get('weight') or 0) * 100)}%"
        + (f" {x['pnlPct']:+.1f}%" if x.get("pnlPct") is not None else "")
        for x in top
    )
    note = f"USER PORTFOLIO: {head}. Positions: {pos_txt}."
    news = p.get("news", [])[:2]
    titles = [str(n.get("title") or "").strip()[:80] for n in news if n.get("title")]
    if titles:
        note += " Money-weighted news: " + "; ".join(titles) + "."
    ev = {
        "type": "portfolio",
        "portfolio": {
            "totals": {"value": val, "pnl": pnl, "pnlPct": pct},
            "positions": [
                {"key": x["key"], "label": x["label"], "value": x.get("value"),
                 "pnlPct": x.get("pnlPct"), "weight": x.get("weight"),
                 "chgPct": x.get("chgPct")}
                for x in top
            ],
        },
    }
    return note, ev


async def _ground_watchlist(session, keys: list[str], last_seen) -> tuple[str, dict | None]:
    """İstifadəçinin watchlist digest-i — 'sən yox ikən' sayları (`watchlist_intel.digest`)."""
    d = await watchlist_intel.digest(session, keys, last_seen)
    rows = d.get("assets", [])
    if not rows:
        return "", None
    since = d.get("sinceCount", 0)
    top = rows[:5]
    note = (
        f"USER WATCHLIST: {len(rows)} assets tracked, {since} new items since last "
        "visit. " + "; ".join(
            f"{a['label']} ({a.get('sinceCount', 0)} new / {a.get('count', 0)} total)"
            for a in top
        )
    )
    return note, None


async def _ground(
    session, signals: list[str], keys: list[str],
    holdings: list | None, watch_keys: list | None, last_seen,
) -> dict:
    """Plan siqnallarına görə fetcher-ləri paralel qoşur.

    Şəxsi siqnallar yalnız data varsa (holdings/watch_keys) işə düşür — məxfilik +
    lazımsız iş. Qaytarır {notes: [str], events: [dict]}.
    """
    tasks = []
    if "prices" in signals and keys:
        tasks.append(_ground_prices(keys))
    if "anomalies" in signals:
        tasks.append(_ground_anomalies(keys))
    if "correlations" in signals and keys:
        tasks.append(_ground_correlations(keys))
    if "portfolio" in signals and holdings:
        tasks.append(_ground_portfolio(session, holdings))
    if "watchlist" in signals and watch_keys:
        tasks.append(_ground_watchlist(session, watch_keys, last_seen))

    notes: list[str] = []
    events: list[dict] = []
    if not tasks:
        return {"notes": notes, "events": events}
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, Exception) or not res:
            continue
        note, ev = res
        if note:
            notes.append(note)
        if ev:
            events.append(ev)
    return {"notes": notes, "events": events}


# ---- RAG bilik bazası + marşrutlaşdırma ----

_KB_STORE: store.VectorStore | None = None
_KB_LOADED = False


def _kb() -> store.VectorStore | None:
    """knowledge.npz-i bir dəfə yükləyir (yoxdursa None)."""
    global _KB_STORE, _KB_LOADED
    if not _KB_LOADED:
        _KB_STORE = store.load(embed.NPZ_PATH)
        _KB_LOADED = True
    return _KB_STORE


_SIGNALS = {"prices", "anomalies", "correlations", "portfolio", "watchlist"}
_PLAN_DEFAULT = {"path": "discussion", "signals": [], "assets": []}


def _parse_plan(raw: str) -> dict:
    """Plan JSON-unu təhlükəsiz çevirir. Səhvdə default: discussion, siqnalsız."""
    try:
        obj = json.loads(raw or "{}")
    except Exception:  # noqa: BLE001
        return dict(_PLAN_DEFAULT)
    path = str(obj.get("path") or "").strip().lower()
    if path not in {"info", "chart", "discussion"}:
        path = "discussion"
    signals = [s for s in (obj.get("signals") or []) if s in _SIGNALS]
    raw_assets = obj.get("assets") or []
    asset_names = [str(a) for a in raw_assets if isinstance(a, (str, int, float))][:6]
    return {"path": path, "signals": signals, "assets": asset_names}


async def _plan(question: str, history: list | None = None) -> dict:
    """Tək çağırışla marşrut + grounding siqnalları + adı çəkilən aktivlər.

    Əvvəlki `_route`-u əvəz edir (əlavə LLM raundu YOX). Qaytarır:
    {path: info|chart|discussion, signals: [...], assets: [...]}.
    """
    hist = _history_block(history)
    user_text = f"Conversation so far:\n{hist}\n\nCurrent question: {question}" if hist else question
    try:
        resp = await primary_client().chat.completions.create(
            model=settings.llm_primary_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You plan how to answer a finance question. Reply JSON with 3 keys.\n"
                        "1) path: 'info' = definition/general explanation from a knowledge "
                        "base; 'chart' = asks to plot/compare TWO assets; 'discussion' = "
                        "analysis/opinion/outlook or any data-driven question.\n"
                        "2) signals: subset of ['prices','anomalies','correlations',"
                        "'portfolio','watchlist'] — which LIVE data helps. Use 'prices' if "
                        "it needs a current price/quote; 'anomalies' if it asks what is "
                        "moving/unusual or WHY an asset moved today; 'correlations' if it "
                        "asks what correlates with an asset; 'portfolio' if it refers to the "
                        "user's OWN portfolio/holdings/P&L/'my'; 'watchlist' if it refers to "
                        "the user's watchlist or 'what happened while I was away'. Empty if none.\n"
                        "3) assets: tickers/names explicitly referenced (e.g. ['BTC','NVDA']); "
                        "use conversation context to resolve pronouns; empty for pure "
                        "personal questions.\n"
                        'Reply: {"path":"...","signals":[...],"assets":[...]}.'
                    ),
                },
                {"role": "user", "content": user_text},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=120,
        )
        return _parse_plan(resp.choices[0].message.content or "")
    except Exception:  # noqa: BLE001
        return dict(_PLAN_DEFAULT)


async def _kb_chunks(question: str, k: int = 5) -> list[dict]:
    """Suala uyğun bilik chunk-larını qaytarır (store yoxdursa boş)."""
    st = _kb()
    if st is None:
        return []
    try:
        q = await embed.embed_query(question)
    except Exception:  # noqa: BLE001
        return []
    return [c for c, _ in st.search(q, k)]


def _kb_context(chunks: list[dict]) -> str:
    if not chunks:
        return "(no knowledge base entries)"
    return "\n".join(
        f"- {c['title']}: {c['text'].split(chr(10), 1)[-1][:300]}" for c in chunks
    )


def _rag_answer_messages(question: str, lang: str, kb_context: str) -> list[dict]:
    lang_name = LANG_NAMES.get(lang, "Azerbaijani")
    return [
        {"role": "system", "content": _GUARD},
        {
            "role": "user",
            "content": f"Finance knowledge base entries:\n{kb_context}\n\n"
            f"Question: {question}\n\nAnswer clearly in {lang_name} using the "
            "entries above. If they don't cover it, answer from general finance "
            "knowledge. Under ~150 words. Do NOT mention models or systems.",
        },
    ]


async def answer(
    question: str, lang: str, session: AsyncSession, *,
    history: list | None = None, holdings: list | None = None,
    watch_keys: list | None = None, last_seen=None,
) -> dict:
    """Marşrut: info → tək-model RAG, digər → grounded debate. {answer, refused}.

    Non-stream endpoint — zəngin UI hadisələri buraxılır (yalnız mətn cavab).
    """
    lang = lang if lang in LANG_NAMES else "az"
    if not has_primary():
        return {"answer": _REFUSAL[lang], "refused": True}
    if not await _classify_finance(question, history):
        return {"answer": _REFUSAL[lang], "refused": True}

    plan, kb = await asyncio.gather(_plan(question, history), _kb_chunks(question))
    kb_ctx = _kb_context(kb)
    signals = plan["signals"]
    keys = _resolve_keys(plan["assets"], question)
    hist_block = _history_block(history)

    # təmiz info (canlı siqnal yoxdur) → tək-model bilik cavabı (debate yoxdur).
    if plan["path"] == "info" and not signals:
        resp = await primary_client().chat.completions.create(
            model=settings.llm_primary_model,
            messages=_rag_answer_messages(question, lang, kb_ctx),
            temperature=0.3,
            max_tokens=400,
        )
        return {
            "answer": resp.choices[0].message.content or _REFUSAL[lang],
            "refused": False,
        }

    news_ctx, (_, corr_note), ground = await asyncio.gather(
        _rag_context(session, question, lang),
        _detect_chart(question),
        _ground(session, signals, keys, holdings, watch_keys, last_seen),
    )
    live = "\n".join(ground["notes"])
    context = f"{news_ctx}\n\nKNOWLEDGE:\n{kb_ctx}"
    if live:
        context += f"\n\nLIVE DATA:\n{live}"
    if hist_block:
        context = f"CONVERSATION SO FAR:\n{hist_block}\n\n{context}"
    primary_take, secondary_take = await asyncio.gather(
        _primary_pass(question, context), _secondary_pass(question, context)
    )
    final = await _synthesize(
        question, lang, primary_take, secondary_take, corr_note, live, hist_block
    )
    return {"answer": final or _REFUSAL[lang], "refused": False}


async def answer_stream(
    question: str, lang: str, session: AsyncSession, *,
    history: list | None = None, holdings: list | None = None,
    watch_keys: list | None = None, last_seen=None,
):
    """Axın variantı. NDJSON hadisələri verir:
    {type:chart|quote|anomalies|portfolio}, {type:delta,text}, {type:done,refused?}.

    Plan sualı təsnif edir: təmiz info → bilik bazasından tək-model cavab; digər →
    grounded debate (xəbər + bilik + canlı data + istifadəçi portfeli), sonra axın.
    """
    lang = lang if lang in LANG_NAMES else "az"

    if not has_primary() or not await _classify_finance(question, history):
        yield {"type": "delta", "text": _REFUSAL[lang]}
        yield {"type": "done", "refused": True}
        return

    plan, kb = await asyncio.gather(_plan(question, history), _kb_chunks(question))
    kb_ctx = _kb_context(kb)
    signals = plan["signals"]
    keys = _resolve_keys(plan["assets"], question)
    hist_block = _history_block(history)

    # təmiz info (canlı siqnal yoxdur) → birbaşa tək-model cavab (debate yoxdur).
    if plan["path"] == "info" and not signals:
        stream = await primary_client().chat.completions.create(
            model=settings.llm_primary_model,
            messages=_rag_answer_messages(question, lang, kb_ctx),
            temperature=0.3,
            max_tokens=400,
            stream=True,
        )
        got = False
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                got = True
                yield {"type": "delta", "text": delta}
        if not got:
            yield {"type": "delta", "text": _REFUSAL[lang]}
        yield {"type": "done"}
        return

    # grounded debate: xəbər + korrelyasiya qrafiki + canlı data fetcher-ləri paralel.
    news_ctx, (chart, corr_note), ground = await asyncio.gather(
        _rag_context(session, question, lang),
        _detect_chart(question),
        _ground(session, signals, keys, holdings, watch_keys, last_seen),
    )
    if chart is not None:
        yield {"type": "chart", "chart": chart}
    for ev in ground["events"]:
        yield ev

    live = "\n".join(ground["notes"])
    context = f"{news_ctx}\n\nKNOWLEDGE:\n{kb_ctx}"
    if live:
        context += f"\n\nLIVE DATA:\n{live}"
    if hist_block:
        context = f"CONVERSATION SO FAR:\n{hist_block}\n\n{context}"
    primary_take, secondary_take = await asyncio.gather(
        _primary_pass(question, context), _secondary_pass(question, context)
    )

    stream = await primary_client().chat.completions.create(
        model=settings.llm_primary_model,
        messages=_synth_messages(
            question, lang, primary_take, secondary_take, corr_note, live, hist_block
        ),
        temperature=0.4,
        max_tokens=600,
        stream=True,
    )
    got = False
    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            got = True
            yield {"type": "delta", "text": delta}
    if not got:
        yield {"type": "delta", "text": _REFUSAL[lang]}
    yield {"type": "done"}
