"""og:image backfill — şəkli olmayan xəbərlər üçün məqalə səhifəsindən şəkil çəkir.

Naşirin `og:image`/`twitter:image` meta teqi — paylaşım üçün təqdim etdiyi şəkil.
İstifadə (backend/ qovluğundan):
    python -m app.ingestion.enrich_images
"""
from __future__ import annotations

import asyncio
import re

import httpx
from sqlalchemy import select

from app.core import netguard
from app.db.session import AsyncSessionLocal, engine
from app.models import News

_UA = {"User-Agent": "Mozilla/5.0 (NexusIQ news aggregator)"}
_CONCURRENCY = 8

_OG = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]*'
    r'content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_OG_REV = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*'
    r'(?:property|name)=["\'](?:og:image|twitter:image)["\']',
    re.IGNORECASE,
)


def _head_html(html: str) -> str:
    """og:image/twitter:image HƏMİŞƏ <head>-dədir. Bəzi naşirlərin <head>-i çox
    şişikdir (məs. FXStreet ~200KB preload/meta) və og:image sabit 200KB kəsimdən
    KƏNARDA qalır → tapılmır. Ona görə bütün <head>-i götür (</head>-ə qədər),
    tapılmasa pataloji səhifələr üçün 1MB təhlükəsiz tavan.
    """
    end = html.lower().find("</head>")
    if end != -1:
        return html[: end + 7]
    return html[:1_000_000]


def _extract(html: str) -> str | None:
    m = _OG.search(html) or _OG_REV.search(html)
    if not m:
        return None
    url = m.group(1).strip()
    return url if url.startswith("http") else None


async def _fetch(sem, client, row_id, url):
    async with sem:
        try:
            # SSRF-təhlükəsiz — daxili/metadata ünvanlara redirect bloklanır.
            r = await netguard.safe_get(client, url, timeout=15.0)
            if r is None:
                return row_id, None
            r.raise_for_status()
            return row_id, _extract(_head_html(r.text))
        except (httpx.HTTPError, httpx.TimeoutException):
            return row_id, None


async def backfill(limit: int = 1000) -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        rows = (
            await session.scalars(
                select(News)
                .where(News.image_url.is_(None))
                .order_by(News.published_at.desc().nullslast())
                .limit(limit)
            )
        ).all()
        targets = [(n.id, n.url) for n in rows]

    if not targets:
        return {"checked": 0, "found": 0}

    sem = asyncio.Semaphore(_CONCURRENCY)
    async with httpx.AsyncClient(headers=_UA, follow_redirects=False) as client:
        results = await asyncio.gather(
            *(_fetch(sem, client, rid, url) for rid, url in targets)
        )

    found = 0
    ids = [rid for rid, img in results if img]
    async with AsyncSessionLocal() as session:
        by_id = {
            n.id: n
            for n in (
                await session.scalars(select(News).where(News.id.in_(ids)))
            ).all()
        }
        for row_id, img in results:
            news = by_id.get(row_id)
            if img and news is not None:
                news.image_url = img[:1000]
                found += 1
        await session.commit()
    return {"checked": len(targets), "found": found}


async def main() -> None:
    stats = await backfill()
    print(f"✅ Şəkil backfill — yoxlanan: {stats['checked']}, tapılan: {stats['found']}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
