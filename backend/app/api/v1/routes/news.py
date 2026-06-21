"""Xəbər API route-ları — siyahı, axtarış, tək xəbər."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.agents.forecast_ai import forecast_impact
from app.agents.llm import has_openai
from app.agents.news_ai import translate_full
from app.core.constants import Category
from app.db.session import get_db
from app.models import News
from app.schemas.news import NewsOut, _excerpt

_LANGS = {"az", "en", "ru", "tr"}

router = APIRouter()

# selectinload — source adını lazy-load xətası olmadan gətirir.
_BASE = select(News).options(selectinload(News.source))


@router.get("", response_model=list[NewsOut])
async def list_news(
    category: Category | None = Query(None, description="Tab filtri"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[NewsOut]:
    """Xəbər siyahısı — ən yenidən köhnəyə. category verilsə filtrlənir."""
    stmt = _BASE
    if category is not None:
        stmt = stmt.where(News.category == category.value)
    stmt = stmt.order_by(News.published_at.desc().nullslast()).limit(limit).offset(offset)
    rows = (await db.scalars(stmt)).all()
    return [NewsOut.from_model(n) for n in rows]


@router.get("/count")
async def count_news(
    category: Category | None = Query(None, description="Tab filtri"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Kateqoriya üzrə ümumi xəbər sayı — səhifələmə üçün."""
    stmt = select(func.count(News.id))
    if category is not None:
        stmt = stmt.where(News.category == category.value)
    return {"total": (await db.scalar(stmt)) or 0}


@router.get("/search", response_model=list[NewsOut])
async def search_news(
    q: str = Query(..., min_length=1, description="Axtarış sözü"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[NewsOut]:
    """Başlıq/xülasə üzrə axtarış (orijinal + AZ)."""
    pattern = f"%{q.strip()}%"
    stmt = (
        _BASE.where(
            or_(
                News.title.ilike(pattern),
                News.summary.ilike(pattern),
                News.title_az.ilike(pattern),
                News.summary_az.ilike(pattern),
            )
        )
        .order_by(News.published_at.desc().nullslast())
        .limit(limit)
    )
    rows = (await db.scalars(stmt)).all()
    return [NewsOut.from_model(n) for n in rows]


@router.get("/trending", response_model=list[NewsOut])
async def trending_news(
    category: Category | None = Query(None, description="Tab filtri (opsional)"),
    limit: int = Query(10, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
) -> list[NewsOut]:
    """Ən təsirli xəbərlər — impact_score + təzəlik üzrə sıralanır.

    Əvvəlcə son 7 günə baxır; az olsa ümumi ən təsirliyə düşür.
    """
    from datetime import datetime, timedelta, timezone

    since = datetime.now(timezone.utc) - timedelta(days=7)
    order = (
        News.impact_score.desc().nullslast(),
        News.published_at.desc().nullslast(),
    )
    stmt = _BASE.where(News.published_at >= since)
    if category is not None:
        stmt = stmt.where(News.category == category.value)
    rows = (await db.scalars(stmt.order_by(*order).limit(limit))).all()

    if len(rows) < limit:
        stmt2 = _BASE
        if category is not None:
            stmt2 = stmt2.where(News.category == category.value)
        rows = (await db.scalars(stmt2.order_by(*order).limit(limit))).all()
    return [NewsOut.from_model(n) for n in rows]


@router.get("/{news_id}", response_model=NewsOut)
async def get_news(
    news_id: int, db: AsyncSession = Depends(get_db)
) -> NewsOut:
    """Tək xəbər (tam səhifə üçün)."""
    news = (await db.scalars(_BASE.where(News.id == news_id))).first()
    if news is None:
        raise HTTPException(status_code=404, detail="Xəbər tapılmadı")
    return NewsOut.from_model(news, with_content=True)


@router.get("/{news_id}/content")
async def get_translated_content(
    news_id: int,
    lang: str = Query("az"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Orijinal mətnin seçilmiş dilə tərcüməsi — dil üzrə keşlənir."""
    lang = lang if lang in _LANGS else "az"
    news = await db.get(News, news_id)
    if news is None:
        raise HTTPException(status_code=404, detail="Xəbər tapılmadı")

    source = _excerpt(news.content) or news.summary or ""
    if not source.strip():
        return {"ready": True, "text": ""}

    # Mənbə İngiliscədir — en seçilibsə tərcüməsiz qaytar.
    if lang == "en":
        return {"ready": True, "text": source}

    cached = (news.content_tr or {}).get(lang)
    if cached:
        return {"ready": True, "text": cached}

    if not has_openai():
        return {"ready": True, "text": source}  # fallback: orijinal

    translated = await translate_full(source, lang)
    if not translated:
        return {"ready": True, "text": source}

    store = dict(news.content_tr or {})
    store[lang] = translated
    news.content_tr = store
    flag_modified(news, "content_tr")
    await db.commit()
    return {"ready": True, "text": translated}


@router.get("/{news_id}/forecast")
async def get_forecast(
    news_id: int,
    lang: str = Query("az"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """AI bazar proqnozu — dil üzrə keşlənir, yoxdursa GPT ilə yaradılır."""
    lang = lang if lang in _LANGS else "az"
    news = await db.get(News, news_id)
    if news is None:
        raise HTTPException(status_code=404, detail="Xəbər tapılmadı")

    cached = (news.forecast or {}).get(lang)
    if cached:
        return {"ready": True, **cached}

    if not has_openai():
        return {"ready": False}

    fc = await forecast_impact(news.title, news.summary, news.category, lang)
    if not fc:
        return {"ready": False}

    store = dict(news.forecast or {})
    store[lang] = fc
    news.forecast = store
    flag_modified(news, "forecast")
    await db.commit()
    return {"ready": True, **fc}
