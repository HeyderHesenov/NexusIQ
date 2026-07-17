"""Xəbər API route-ları — siyahı, axtarış, tək xəbər."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, selectinload, undefer
from sqlalchemy.orm.attributes import flag_modified

from app.agents.forecast_ai import forecast_impact
from app.agents.llm import has_primary
from app.agents.news_ai import translate_full
from app.core.constants import Category
from app.core.ratelimit import rate_limit
from app.db.session import get_db
from app.models import News
from app.schemas.news import NewsOut, _excerpt

_LANGS = {"az", "en", "ru", "tr"}

# Eyni (xəbər, dil) üçün paralel proqnoz sorğularını birləşdirir —
# prefetch (hover) + səhifə açılışı eyni AI çağırışını paylaşır (təkrar xərc yox).
_forecast_inflight: dict[tuple[int, str], "asyncio.Future[dict | None]"] = {}

router = APIRouter()

# selectinload — source adını lazy-load xətası olmadan gətirir.
# Siyahıda istifadə olunmayan ağır JSONB sütunlarını (1536-float embedding,
# forecast, content_tr, tam content) TƏXİRƏ SAL — hər sətir üçün megabaytlarla
# lazımsız JSON detoast/decode etmə (event loop-u bloklayır).
_HEAVY = (
    defer(News.embedding),
    defer(News.forecast),
    defer(News.content_tr),
    defer(News.content),
)
_BASE = select(News).options(selectinload(News.source), *_HEAVY)


@router.get("", response_model=list[NewsOut])
async def list_news(
    category: Category | None = Query(None, description="Tab filtri"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0, le=100_000),
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


@router.get(
    "/search",
    response_model=list[NewsOut],
    # Axtarış 4 sütun üzrə indekssiz ILIKE seq-scan edir (aparıcı `%` btree
    # indeksini onsuz da işlədə bilmir). Endpoint TAMAMİLƏ limitsiz idi.
    dependencies=[Depends(rate_limit("news_search", limit=30, window=60.0))],
)
async def search_news(
    q: str = Query(..., min_length=1, max_length=100, description="Axtarış sözü"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[NewsOut]:
    """Başlıq/xülasə üzrə axtarış (orijinal + AZ)."""
    # `contains(..., autoescape=True)` — `%` və `_` LIKE jokerləridir. Xam
    # `f"%{q}%"` ilə `q=%` HƏR sətri tuturdu, `q=%_%_%_%` isə 4 sütun üzrə
    # superxətti backtracking-ə məcbur edirdi (CPU, data sızması yox).
    # Eyni qoru `imagejunk.junk_sql`-də artıq düzgün tətbiq olunub — köçürülür.
    term = q.strip()
    stmt = (
        _BASE.where(
            or_(
                News.title.contains(term, autoescape=True),
                News.summary.contains(term, autoescape=True),
                News.title_az.contains(term, autoescape=True),
                News.summary_az.contains(term, autoescape=True),
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
    # Tək element content göstərir → onu geri undefer et (embedding təxirdə qalır).
    stmt = _BASE.where(News.id == news_id).options(undefer(News.content))
    news = (await db.scalars(stmt)).first()
    if news is None:
        raise HTTPException(status_code=404, detail="Xəbər tapılmadı")
    return NewsOut.from_model(news, with_content=True)


@router.get(
    "/{news_id}/content",
    dependencies=[Depends(rate_limit("news_ai", limit=20, window=60.0))],
)
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

    if not has_primary():
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


@router.get("/{news_id}/analogs")
async def get_analogs(
    news_id: int,
    k: int = Query(5, ge=1, le=12),
    lang: str = Query("az"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Tarixi Analoqlar — bənzər keçmiş hadisələr + aktivin sonrakı hərəkəti.

    Başlıqlar seçilmiş dilə lokallaşır; rəqəmlər dil-müstəqil. AI çağırışı yoxdur.
    """
    from app.analytics import analog

    lang = lang if lang in _LANGS else "az"
    news = await db.get(News, news_id)
    if news is None:
        raise HTTPException(status_code=404, detail="Xəbər tapılmadı")
    return await analog.analogs_for_news(news, k=k, lang=lang)


@router.get(
    "/{news_id}/forecast",
    dependencies=[Depends(rate_limit("news_ai", limit=20, window=60.0))],
)
async def get_forecast(
    news_id: int,
    lang: str = Query("az"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """AI bazar proqnozu — dil üzrə keşlənir, yoxdursa AI ilə yaradılır."""
    lang = lang if lang in _LANGS else "az"
    news = await db.get(News, news_id)
    if news is None:
        raise HTTPException(status_code=404, detail="Xəbər tapılmadı")

    cached = (news.forecast or {}).get(lang)
    if cached:
        return {"ready": True, **cached}

    if not has_primary():
        return {"ready": False}

    # Eyni xəbər üçün artıq bir çağırış gedirsə (prefetch), onu gözlə.
    key = (news_id, lang)
    inflight = _forecast_inflight.get(key)
    if inflight is not None:
        fc = await inflight
        return {"ready": True, **fc} if fc else {"ready": False}

    fut: "asyncio.Future[dict | None]" = asyncio.get_event_loop().create_future()
    _forecast_inflight[key] = fut
    try:
        fc = await forecast_impact(news.title, news.summary, news.category, lang)
        if fc:
            store = dict(news.forecast or {})
            store[lang] = fc
            news.forecast = store
            flag_modified(news, "forecast")
            await db.commit()
            # Proqnozun göstərdiyi aktivləri link et (doğruluq kartının datası).
            from app.services import link_service

            await link_service.populate_forecast(db, news, fc.get("pairs") or [])
            await db.commit()
        if not fut.done():
            fut.set_result(fc)
    except Exception:  # noqa: BLE001
        if not fut.done():
            fut.set_result(None)
        raise
    finally:
        _forecast_inflight.pop(key, None)

    return {"ready": True, **fc} if fc else {"ready": False}
