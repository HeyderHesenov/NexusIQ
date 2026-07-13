"""Tarixi Analoq API — azad-mətn sorğusu (ayrıca kəşf səhifəsi üçün)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.agents.llm import has_primary
from app.analytics import analog
from app.core.ratelimit import rate_limit
from app.rag import embed

router = APIRouter()


_LANGS = {"az", "en", "ru", "tr"}


@router.get(
    "/search",
    dependencies=[Depends(rate_limit("analog_search", limit=15, window=60.0))],
)
async def search_analogs(
    q: str = Query(..., min_length=2, max_length=300),
    category: str = Query("", description="forex|us|crypto|commodities (opsional)"),
    k: int = Query(5, ge=1, le=12),
    lang: str = Query("az"),
) -> dict:
    """Azad mətni embed edib bənzər keçmiş hadisələri + nəticələrini qaytarır."""
    if not has_primary():
        return {"ready": False}
    lang = lang if lang in _LANGS else "az"
    vec = await embed.embed_query(q)
    return await analog.analogs_for(
        vec, q, None, category, exclude_id=None, k=k, lang=lang
    )
