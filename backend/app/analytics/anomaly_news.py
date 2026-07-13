"""Anomaliya ↔ xəbər: bir aktivin anomaliyasının ehtimal olunan xəbər səbəbi.

Tam PULSUZ — LLM/embedding sorğusu yox. Aktivin ləqəbləri üzrə son xəbərlərdə
açar-söz uyğunluğu (advisor RAG ilə eyni ILIKE naxışı). Anomaliyalar az olduğu
üçün lazy, per-asset çağırılır.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, selectinload

from app.analytics.assets import ASSETS
from app.analytics.correlation import _ALIASES
from app.models import News

# key → label. Ləqəb yoxdursa uyğunlaşdırma termini label-dən qurulur.
_LABELS: dict[str, str] = {key: label for key, label, _sym, _typ, _dec in ASSETS}

# Ticker-i adi ingilis sözü olan aktivlər — ad ilə əvəzlə (yanlış tutmanı önlə).
_NAME_OVERRIDE: dict[str, list[str]] = {
    "now": ["servicenow"],
    "ai": ["c3.ai", "c3 ai"],
    "mu": ["micron"],
}


def _terms_for(key: str) -> list[str]:
    """Aktiv üçün axtarış terminləri — çoxdilli ləqəblər, yoxsa label/ad.

    Symbol kökü (ETF proksi tickerləri: ALI, LIT, HG…) İSTİFADƏ EDİLMİR — qısa və
    ambiqualdır, substring kimi yanlış tutur. Söz-sərhədi uyğunluğu (aşağıda)
    qısa tickerlərin də yanlış tutmasının qarşısını alır.
    """
    if key in _ALIASES:
        return _ALIASES[key]
    if key in _NAME_OVERRIDE:
        return _NAME_OVERRIDE[key]
    label = _LABELS.get(key)
    return [label.lower()] if label else []


async def news_for_asset(
    session: AsyncSession, key: str, days: int = 7, k: int = 3
) -> list[News]:
    """Aktivi qeyd edən son xəbərlər — anomaliyanın ehtimal səbəbi (boş ola bilər).

    Söz-sərhədi (Postgres `~*` + `\\y`) ilə uyğunlaşdırır ki, "arm" → "harm",
    "ali" → "Alphabet" kimi substring yanlışları olmasın.
    """
    terms = _terms_for(key)
    if not terms:
        return []
    pattern = r"\y(" + "|".join(re.escape(t) for t in terms) + r")\y"
    fields = (News.title, News.summary, News.title_az, News.summary_az)
    conds = [f.op("~*")(pattern) for f in fields]
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        await session.scalars(
            select(News)
            .options(
                selectinload(News.source),
                defer(News.embedding),
                defer(News.forecast),
                defer(News.content_tr),
                defer(News.content),
            )
            .where(News.published_at >= since)
            .where(or_(*conds))
            .order_by(
                News.published_at.desc().nullslast(),
                News.impact_score.desc().nullslast(),
            )
            .limit(k)
        )
    ).all()
    return list(rows)
