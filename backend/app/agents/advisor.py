"""FinancialAdvisorAgent — arxa fonda iki AI debate edib tək cavab verir.

Axın:
  1) Mövzu yoxlaması (GPT) — finance deyilsə nəzakətlə imtina (debate olmur).
  2) RAG — NexusIQ bazasından uyğun xəbərlər kontekst kimi çəkilir.
  3) Debate — GPT və Claude paralel müstəqil analiz verir.
  4) Sintez — GPT iki analizi birləşdirib istifadəçi dilində yekun cavab verir.

Qaydalar (prompt-larda tətbiq olunur):
  - Yalnız maliyyə/bazar/iqtisadiyyat + NexusIQ xəbərləri.
  - Arxa fondakı modellər/arxitektura barədə HEÇ NƏ açıqlanmır.
"""
from __future__ import annotations

import json

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, selectinload

from app.agents.llm import (
    anthropic_client,
    has_anthropic,
    has_openai,
    openai_client,
)
from app.analytics import correlation
from app.core.config import settings
from app.models import News
from app.rag import embed, store

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
    "(3) No personalized financial advice or guarantees; be analytical and neutral."
)


async def _classify_finance(question: str) -> bool:
    """GPT ilə sürətli mövzu yoxlaması. Finance deyilsə False."""
    try:
        resp = await openai_client().chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "Classify if the user message is about finance, "
                    "markets, economy, trading, forex, crypto, stocks, commodities "
                    "or financial news. Reply JSON: {\"finance\": true|false}.",
                },
                {"role": "user", "content": question},
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
                .options(selectinload(News.source), defer(News.embedding))
                .order_by(News.published_at.desc().nullslast())
                .limit(_RAG_TOPK)
            )
        ).all()
    else:
        fields = (News.title, News.summary, News.content, News.title_az, News.summary_az)
        conds = [f.ilike(f"%{w}%") for w in words for f in fields]
        candidates = (
            await session.scalars(
                select(News)
                .options(selectinload(News.source), defer(News.embedding))
                .where(or_(*conds))
                .order_by(News.published_at.desc().nullslast())
                .limit(_RAG_CANDIDATES)
            )
        ).all()

        def score(n: News) -> int:
            blob = " ".join(
                filter(None, [n.title, n.summary, n.content, n.title_az, n.summary_az,
                              json.dumps(n.translations or {}, ensure_ascii=False)])
            ).lower()
            return sum(1 for w in words if w in blob)

        rows = sorted(candidates, key=score, reverse=True)[:_RAG_TOPK]

    lines = []
    for n in rows:
        tr = (n.translations or {}).get(lang) or {}
        title = tr.get("title") or n.title
        body = tr.get("body") or n.summary or n.content or ""
        src = n.source.name if n.source else "?"
        lines.append(f"- [{n.category}] ({src}) {title} — {body[:200]}")
    return "\n".join(lines) if lines else "(no relevant NexusIQ news found)"


async def _gpt_pass(question: str, context: str) -> str:
    resp = await openai_client().chat.completions.create(
        model=settings.openai_model,
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


async def _claude_pass(question: str, context: str) -> str:
    if not has_anthropic():
        return ""
    msg = await anthropic_client().messages.create(
        model=settings.anthropic_model,
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
    question: str, lang: str, a: str, b: str, corr_note: str = ""
) -> list[dict]:
    """Sintez üçün mesajlar (həm tam, həm axın variantı bunu işlədir)."""
    lang_name = LANG_NAMES.get(lang, "Azerbaijani")
    both = f"ANALYSIS A:\n{a}\n\nANALYSIS B:\n{b}" if b else f"ANALYSIS:\n{a}"
    extra = ""
    if corr_note:
        extra = (
            f"\n\n{corr_note}\nThe user is shown a chart of these two assets above "
            "your answer. Explain their RELATIONSHIP clearly: cite the correlation "
            "value, say whether they move together or opposite and how strongly, and "
            "give one practical takeaway (hedging/diversification). "
        )
    return [
        {"role": "system", "content": _GUARD},
        {
            "role": "user",
            "content": f"Two internal analyses are given. Merge them into ONE "
            f"clear final answer for the user, written in {lang_name}. "
            "Reconcile agreements, note key disagreements briefly. "
            "Structure with short headers when useful (qısa/orta/uzun müddət, "
            "risklər). Under ~180 words. Do NOT mention analyses, models or "
            f"systems.{extra}\n\nQuestion: {question}\n\n{both}",
        },
    ]


async def _synthesize(question: str, lang: str, a: str, b: str, corr_note: str = "") -> str:
    resp = await openai_client().chat.completions.create(
        model=settings.openai_model,
        messages=_synth_messages(question, lang, a, b, corr_note),
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


def _parse_route(raw: str) -> str:
    """Router JSON-unu yola çevirir. Səhvdə təhlükəsiz default: discussion."""
    try:
        path = (json.loads(raw or "{}").get("path") or "").strip().lower()
    except Exception:  # noqa: BLE001
        return "discussion"
    return path if path in {"info", "chart", "discussion"} else "discussion"


async def _route(question: str) -> str:
    """GPT ilə sualı təsnif edir: info | chart | discussion."""
    try:
        resp = await openai_client().chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "Classify a finance question into one path. "
                    "'info' = definition/general explanation answerable from a "
                    "knowledge base. 'chart' = asks to plot/compare two assets or "
                    "show a graph. 'discussion' = analysis/opinion about news or an "
                    "asset's outlook. Reply JSON: {\"path\":\"info|chart|discussion\"}.",
                },
                {"role": "user", "content": question},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=20,
        )
        return _parse_route(resp.choices[0].message.content or "")
    except Exception:  # noqa: BLE001
        return "discussion"


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


async def answer(question: str, lang: str, session: AsyncSession) -> dict:
    """Marşrut: info → tək-GPT RAG, chart/discussion → debate. {answer, refused}."""
    import asyncio

    lang = lang if lang in LANG_NAMES else "az"
    if not has_openai():
        return {"answer": _REFUSAL[lang], "refused": True}
    if not await _classify_finance(question):
        return {"answer": _REFUSAL[lang], "refused": True}

    path, kb = await asyncio.gather(_route(question), _kb_chunks(question))
    kb_ctx = _kb_context(kb)

    if path == "info":
        resp = await openai_client().chat.completions.create(
            model=settings.openai_model,
            messages=_rag_answer_messages(question, lang, kb_ctx),
            temperature=0.3,
            max_tokens=400,
        )
        return {
            "answer": resp.choices[0].message.content or _REFUSAL[lang],
            "refused": False,
        }

    news_ctx, (_, corr_note) = await asyncio.gather(
        _rag_context(session, question, lang), _detect_chart(question)
    )
    context = f"{news_ctx}\n\nKNOWLEDGE:\n{kb_ctx}"
    gpt_take, claude_take = await asyncio.gather(
        _gpt_pass(question, context), _claude_pass(question, context)
    )
    final = await _synthesize(question, lang, gpt_take, claude_take, corr_note)
    return {"answer": final or _REFUSAL[lang], "refused": False}


async def answer_stream(question: str, lang: str, session: AsyncSession):
    """Axın variantı. NDJSON hadisələri verir:
    {type:chart,chart}, {type:delta,text}, {type:done,refused?}.

    Router sualı təsnif edir: info → bilik bazasından tək-GPT cavab; chart/
    discussion → arxa fonda debate (xəbər + bilik konteksti), sonra token axını.
    """
    import asyncio

    lang = lang if lang in LANG_NAMES else "az"

    if not has_openai() or not await _classify_finance(question):
        yield {"type": "delta", "text": _REFUSAL[lang]}
        yield {"type": "done", "refused": True}
        return

    path, kb = await asyncio.gather(_route(question), _kb_chunks(question))
    kb_ctx = _kb_context(kb)

    # info → bilik bazasından birbaşa tək-GPT cavab (debate yoxdur).
    if path == "info":
        stream = await openai_client().chat.completions.create(
            model=settings.openai_model,
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

    # chart / discussion → debate (xəbər + bilik konteksti).
    news_ctx, (chart, corr_note) = await asyncio.gather(
        _rag_context(session, question, lang), _detect_chart(question)
    )
    if chart is not None:
        yield {"type": "chart", "chart": chart}

    context = f"{news_ctx}\n\nKNOWLEDGE:\n{kb_ctx}"
    gpt_take, claude_take = await asyncio.gather(
        _gpt_pass(question, context), _claude_pass(question, context)
    )

    stream = await openai_client().chat.completions.create(
        model=settings.openai_model,
        messages=_synth_messages(question, lang, gpt_take, claude_take, corr_note),
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
