"""Thumbnail proksisi route-u — `/img/news/{id}?w=192`.

Giriş URL deyil, `news.id`-dir → açıq proksi deyil (bax: services/img_cache).
Alınmayan hallar 404 qaytarır; frontend `NewsImage` onu `onError` ilə tutub
brendli örtüyü göstərir, yəni boş kart yenə mümkün deyil.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.imagejunk import clean_image
from app.core.ratelimit import rate_limit
from app.db.session import get_db
from app.models import News
from app.services import img_cache

router = APIRouter()

# Şəkil məzmunu id+en ilə tam müəyyəndir → uzun immutable keş.
_CACHE_CONTROL = "public, max-age=31536000, immutable"


@router.get(
    "/news/{news_id}",
    dependencies=[Depends(rate_limit("img_proxy", limit=300, window=60.0))],
)
async def news_image(
    news_id: int,
    w: int = Query(640),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Xəbərin örtük şəkli — `w` eninə kiçildilmiş WebP, diskdə keşli."""
    if w not in img_cache.ALLOWED_W:
        # Sərbəst `w` keş kardinallığını partladardı → yalnız kart ölçüləri.
        raise HTTPException(status_code=400, detail="Dəstəklənməyən en")
    url = clean_image(
        await db.scalar(select(News.image_url).where(News.id == news_id))
    )
    if not url:
        raise HTTPException(status_code=404, detail="Şəkil yoxdur")
    data = await img_cache.get(news_id, url, w)
    if data is None:
        raise HTTPException(status_code=404, detail="Şəkil alınmadı")
    return Response(
        content=data,
        media_type="image/webp",
        headers={"Cache-Control": _CACHE_CONTROL},
    )
