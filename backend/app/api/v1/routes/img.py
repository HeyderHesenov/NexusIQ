"""Thumbnail proksisi route-u — `/img/news/{id}?w=192`.

Giriş URL deyil, `news.id`-dir → açıq proksi deyil (bax: services/img_cache).
Alınmayan hallar 404 qaytarır; frontend `NewsImage` onu `onError` ilə tutub
brendli örtüyü göstərir, yəni boş kart yenə mümkün deyil.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.imagejunk import clean_image
from app.core.ratelimit import rate_limit
from app.db.session import get_db
from app.models import News
from app.services import img_cache

router = APIRouter()

# `immutable, 1 il` QAZANILMAMIŞDIR: brauzerin gördüyü URL (`/img/news/{id}?w=`)
# `image_url` dəyişəndə (backfill/yenidən scrape/`_JUNK`-a əlavə) EYNİ qalır →
# köhnə bayt bir il ilişib qalardı və serverdə geri qaytarma leveri OLMAZDI.
# Disk keşi açarında URL var (özünü invalidasiya edir), brauzer isə gündə bir
# dəfə yoxlayır; `stale-while-revalidate` sürəti saxlayır (bayat nüsxə dərhal
# verilir, yenilənmə arxa planda).
_CACHE_CONTROL = "public, max-age=86400, stale-while-revalidate=604800"


@router.get(
    "/news/{news_id}",
    dependencies=[Depends(rate_limit("img_proxy", limit=300, window=60.0))],
)
async def news_image(
    news_id: int,
    w: int = Query(640),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Xəbərin örtük şəkli — `w` eninə kiçildilmiş WebP, diskdə keşli."""
    if w not in img_cache.ALLOWED_W:
        # Sərbəst `w` keş kardinallığını partladardı → yalnız kart ölçüləri.
        raise HTTPException(status_code=400, detail="Dəstəklənməyən en")
    url = clean_image(
        await db.scalar(select(News.image_url).where(News.id == news_id))
    )
    if not url:
        raise HTTPException(status_code=404, detail="Şəkil yoxdur")
    path = await img_cache.get_path(news_id, url, w)
    if path is None:
        # Bütün uğursuzluqlar EYNİ 404-dür (yoxdur/non-200/iri/şəbəkə) — daxili
        # vəziyyəti sızdırmasın. Frontend `NewsImage` bunu örtüklə əvəzləyir.
        raise HTTPException(status_code=404, detail="Şəkil alınmadı")
    return FileResponse(
        path,
        media_type="image/webp",
        headers={"Cache-Control": _CACHE_CONTROL},
    )
