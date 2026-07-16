"""og:image backfill — şəkli olmayan xəbərlər üçün məqalə səhifəsindən şəkil çəkir.

Naşirin `og:image`/`twitter:image` meta teqi — paylaşım üçün təqdim etdiyi şəkil.
İstifadə (backend/ qovluğundan):
    python -m app.ingestion.enrich_images

HƏDƏF SEÇİMİ: şəkilsiz (NULL) sətirlər + naşir zibili (`imagejunk`) olan sətirlər.
Zibil sətirləri ona görə yenidən skan olunur ki, bir sıra naşirlərdə RSS-in verdiyi
şəkil sayt loqosudur, məqalənin ÖZ og:image-i isə real fotodur (ölçüldü: OilPrice
5 zibil sətrinin 3-ü elə mövcud kodla bərpa olunur; Mining.com paywall
interstitialına görə yazı-turasıdır → 6 cəhddə ~98%).

CƏHD İZLƏMƏSİ MƏCBURİDİR: əvvəl yalnız `image_url IS NULL` seçilirdi və marker
yox idi → həmin sətirlər hər dövrdə (saatda 2 dəfə + hər restartda, konkurentlik
8 ilə) yenidən çəkilirdi. 31 Investing sətri üçün bu, saatda ~60 sorğu deməkdir və
hamısı 403 qaytarır. `image_attempts`/`image_attempted_at` o döngəni dayandırır —
yəni bu izləmə yük ƏLAVƏ ETMİR, mövcud yükü kəskin azaldır.
"""
from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from sqlalchemy import func, or_, select, text

from app.core import netguard
from app.core.imagejunk import junk_sql
from app.db.session import AsyncSessionLocal, engine
from app.models import News

_UA = {"User-Agent": "Mozilla/5.0 (NexusIQ news aggregator)"}
_CONCURRENCY = 8
_MAX_ATTEMPTS = 6  # backoff 1h,2h,4h,8h,16h,32h → sonra sətir buraxılır
_MAX_BODY = 2_000_000  # `_head_html` yalnız <head> istəyir; tam səhifə lazım deyil

# Fotosu STRUKTUR olaraq olmayan URL-lər — çəkmək mənasızdır.
# Yahoo `/research/reports/` = ödənişli ARGUS analitik hesabatları; ölçdüm: 58/58
# belədir, og:image-ləri default loqodur, JSON-LD-ləri yoxdur.
_SKIP_URL = ("finance.yahoo.com/research/reports/",)


@dataclass(frozen=True)
class HostPolicy:
    """Per-host nəzakət limiti."""

    concurrency: int = 8
    delay: float = 0.0
    max_per_cycle: int | None = None


# investing.com bot-blokludur (403). Onu döymək mənasızdır və TƏHLÜKƏLİdir: şəkil
# CDN-i (`i-invdn-com`) reputasiyanı əsas domenlə bölüşür → aqressiv skan HAZIRDA
# işləyən Investing şəkillərini də 403-ə sala bilər. Ona görə: dövrdə 5 sətir,
# birbir, 6 saniyə aralıqla. Bu rəqəmləri sonradan "artırma".
_POLICIES: dict[str, HostPolicy] = {
    "www.investing.com": HostPolicy(concurrency=1, delay=6.0, max_per_cycle=5),
}
_DEFAULT_POLICY = HostPolicy(concurrency=_CONCURRENCY)

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


async def _fetch(client, row_id, url):
    try:
        # SSRF-təhlükəsiz — daxili/metadata ünvanlara redirect bloklanır.
        r = await netguard.safe_get(client, url, timeout=15.0, max_bytes=_MAX_BODY)
        if r is None:
            return row_id, None
        r.raise_for_status()
        return row_id, _extract(_head_html(r.text))
    except Exception:
        # BİR pis URL (SSL/timeout/SSRF-blok/parse/403) BÜTÜN batch-i çökürtməsin —
        # həmişə (id, None) qaytar. Dayanıqlılıq: gather return_exceptions ilə birgə.
        # 403 daimi verdikt DEYİL: sətrin cəhd sayı artır, backoff onu daşıyır.
        return row_id, None


async def _run_host(client, host: str, items: list[tuple[int, str]]):
    """Bir host üçün nəzakət siyasəti ilə çəkiliş."""
    pol = _POLICIES.get(host, _DEFAULT_POLICY)
    if pol.max_per_cycle:
        items = items[: pol.max_per_cycle]
    sem = asyncio.Semaphore(pol.concurrency)

    async def one(rid: int, url: str):
        async with sem:
            res = await _fetch(client, rid, url)
            if pol.delay:
                await asyncio.sleep(pol.delay)  # semafor daxilində → real aralıq
            return res

    return await asyncio.gather(
        *(one(rid, url) for rid, url in items), return_exceptions=True
    )


def _targets_query(limit: int, since_id: int | None):
    """Şəkilsiz VƏ YA zibil-şəkilli, cəhd büdcəsi bitməmiş, backoff-u dolmuş sətirlər."""
    backoff = func.now() - (
        text("interval '1 hour'") * func.power(2, News.image_attempts)
    )
    q = select(News).where(
        or_(News.image_url.is_(None), junk_sql(News.image_url)),
        News.image_attempts < _MAX_ATTEMPTS,
        or_(
            News.image_attempted_at.is_(None),
            News.image_attempted_at < backoff,
        ),
        *[News.url.notlike(f"%{p}%") for p in _SKIP_URL],
    )
    if since_id is not None:
        q = q.where(News.id > since_id)
    return q.order_by(News.published_at.desc().nullslast()).limit(limit)


async def backfill(limit: int = 1000, since_id: int | None = None) -> dict[str, int]:
    """Şəkilsiz xəbərlərə og:image doldurur.

    since_id verilsə YALNIZ o id-dən böyük (təzə ingest olunmuş) sətirləri hədəfləyir —
    ingest_once bunu əvvəlcə çağırır ki, ən yeni xəbərlər minlik backloqu gözləmədən
    saniyələr içində şəkil alsın (newest-first səhifədə lag pəncərəsi olmasın).
    """
    async with AsyncSessionLocal() as session:
        rows = (await session.scalars(_targets_query(limit, since_id))).all()
        targets = [(n.id, n.url) for n in rows]

    if not targets:
        return {"checked": 0, "found": 0}

    by_host: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for rid, url in targets:
        by_host[(urlparse(url).hostname or "").lower()].append((rid, url))

    async with httpx.AsyncClient(headers=_UA, follow_redirects=False) as client:
        # Hostlar paralel, host DAXİLİNDƏ öz siyasəti ilə.
        per_host = await asyncio.gather(
            *(_run_host(client, h, items) for h, items in by_host.items()),
            return_exceptions=True,
        )
    # return_exceptions=True → gözlənilməz istisnalar (məs. CancelledError) tuple deyil;
    # onları at, yalnız düzgün (id, img) nəticələri saxla.
    results = [
        r for group in per_host if isinstance(group, list) for r in group
        if isinstance(r, tuple)
    ]

    found = 0
    attempted = [rid for rid, _img in results]
    async with AsyncSessionLocal() as session:
        by_id = {
            n.id: n
            for n in (
                await session.scalars(select(News).where(News.id.in_(attempted)))
            ).all()
        }
        for row_id, img in results:
            news = by_id.get(row_id)
            if news is None:
                continue
            # İNVARİANT: cəhd HƏR hədəf üçün yazılır — tapılsın/tapılmasın. Döngə
            # yalnız bununla dayanır (`max_per_cycle` ilə kəsilənlərə toxunulmur:
            # onlar çəkilmədi, ona görə cəhd də sayılmır).
            news.image_attempts = (news.image_attempts or 0) + 1
            news.image_attempted_at = func.now()
            if img:
                news.image_url = img[:1000]
                found += 1
        await session.commit()
    return {"checked": len(results), "found": found}


async def main() -> None:
    stats = await backfill()
    print(f"✅ Şəkil backfill — yoxlanan: {stats['checked']}, tapılan: {stats['found']}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
