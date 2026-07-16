"""NewsCollectorAgent — RSS feed-lərini çəkir, parse edir, normallaşdırır.

Bazaya yazmır; yalnız təmiz `NormalizedNews` siyahısı qaytarır.
Saxlama məntiqi services/news_service.py-dədir (məsuliyyət ayrılığı).
"""
from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

import feedparser
import httpx
from dateutil import parser as date_parser

from app.core.constants import Category
from app.ingestion.sources import FEEDS, FeedSource

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
# Tək-dırnaq + lazy-load atributları (data-src/data-lazy-src) — köhnə variant yalnız
# cüt-dırnaqlı `src`-i tuturdu, halbuki müasir WordPress temaları lazy-load işlədir.
_IMG_RE = re.compile(
    r'<img\b[^>]*?\b(?:data-lazy-src|data-src|src)\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_SRCSET_RE = re.compile(
    r'<img\b[^>]*?\bsrcset\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE
)
_IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")
# DAR siyahı — yalnız təsdiqlənmiş izləmə bikonları/avatarlar. Naşir zibili (sayt
# loqosu və s.) BURA AİD DEYİL: o, `imagejunk`-da serializasiya qatında süzülür.
_SKIP = (
    "facebook.com/tr",
    "google-analytics",
    "doubleclick",
    "scorecardresearch",
    "/gravatar.com/",
    "feedburner",
)
_USER_AGENT = "NexusIQ/1.0 (+local news aggregator)"


@dataclass
class NormalizedNews:
    """Mənbədən asılı olmayan, təmiz xəbər formatı."""

    title: str
    url: str
    summary: str | None
    image_url: str | None
    published_at: datetime | None
    category: Category
    source_name: str
    dedup_hash: str


def _clean_text(raw: str | None) -> str | None:
    """HTML tag-larını çıxarır, boşluqları normallaşdırır."""
    if not raw:
        return None
    text = _WS_RE.sub(" ", _TAG_RE.sub(" ", raw)).strip()
    return text or None


def _canonical_url(url: str) -> str:
    """Query/fragment-i atır — eyni xəbərin variantlarını birləşdirir."""
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def _dedup_hash(url: str, title: str) -> str:
    """Kanonik URL əsaslı unikal hash; URL yoxdursa başlığa düşür."""
    basis = _canonical_url(url) if url else title.strip().lower()
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _parse_date(entry) -> datetime | None:
    """published / updated sahəsindən tarix çıxarır (UTC)."""
    struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if struct:
        return datetime(*struct[:6], tzinfo=timezone.utc)
    raw = entry.get("published") or entry.get("updated")
    if raw:
        try:
            dt = date_parser.parse(raw)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, OverflowError):
            return None
    return None


def _ok(url: str | None) -> str | None:
    """URL-i normallaşdırır; yararsızdırsa None (protokol-nisbi, data:, bikon)."""
    if not url:
        return None
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url  # protokol-nisbi — əks halda tam itirilirdi
    if not url.startswith(("http://", "https://")):
        return None  # `data:` URI-ləri və nisbi yolları rədd edir
    return None if any(p in url.lower() for p in _SKIP) else url


def _looks_img(url: str) -> bool:
    return url.lower().split("?")[0].endswith(_IMG_EXT)


def _from_body(html: str | None) -> str | None:
    if not html:
        return None
    # BÜTÜN <img>-ləri gəz, ilkini yox: gövdənin birinci şəkli çox vaxt izləmə
    # bikonu və ya avatar olur, real foto isə arxasınca gəlir.
    for m in _IMG_RE.finditer(html):
        if u := _ok(m.group(1)):
            return u
    for m in _SRCSET_RE.finditer(html):  # srcset: "url 1x, url 2x" → ilk URL
        if u := _ok(m.group(1).split(",")[0].strip().split()[0]):
            return u
    return None


def _extract_image(entry) -> str | None:
    """media:content/thumbnail, enclosure və ya gövdə <img>-dən şəkil tapır.

    Precedence (media → enclosure → gövdə) qəsdən saxlanılır — dəyişsə sınamadığım
    naşirlərdə regres ola bilər. Düzəldilən üç dəlik:
    1. `media_content or media_thumbnail` LİSTƏ səviyyəsində bağlanırdı: urlsuz
       `media_content[0]` bütün tier-i öldürür və `media_thumbnail` heç yoxlanmırdı.
    2. Enclosure yalnız MIME-ə baxırdı. Investing RSS real .jpg-ni
       `type='text/html; charset=utf-8'` kimi ETİKETLƏYİR → foto atılırdı (ölçüldü:
       10 girişin 2-si; həmin fayllar `image_url IS NULL` sətirlərinin səbəbidir).
    3. `summary or content` — `summary` demək olar həmişə truthy olduğu üçün
       `content:encoded` HEÇ VAXT skan olunmurdu, halbuki WordPress feed-lərində
       (Mining.com) əsas foto məhz oradadır.
    """
    for key in ("media_content", "media_thumbnail"):
        for m in entry.get(key) or []:
            if isinstance(m, dict) and (u := _ok(m.get("url"))):
                return u

    for link in entry.get("links", []):
        if link.get("rel") != "enclosure":
            continue
        href = _ok(link.get("href"))
        if href and ("image" in (link.get("type") or "") or _looks_img(href)):
            return href

    # content:encoded ƏVVƏL (daha tam sənəd), sonra summary — qısa-qapanma yox.
    contents = entry.get("content") or []
    for c in contents:
        if isinstance(c, dict) and (u := _from_body(c.get("value"))):
            return u
    return _from_body(entry.get("summary"))


def _normalize_entry(entry, source: FeedSource) -> NormalizedNews | None:
    """Bir feed entry-sini NormalizedNews-a çevirir. Naqis olarsa None."""
    title = _clean_text(entry.get("title"))
    url = (entry.get("link") or "").strip()
    if not title or not url:
        return None
    return NormalizedNews(
        title=title[:500],
        url=url[:1000],
        summary=_clean_text(entry.get("summary")),
        image_url=_extract_image(entry),
        published_at=_parse_date(entry),
        category=source.category,
        source_name=source.name,
        dedup_hash=_dedup_hash(url, title),
    )


async def fetch_feed(
    client: httpx.AsyncClient, source: FeedSource
) -> list[NormalizedNews]:
    """Bir mənbəni çəkib normallaşdırır. Xəta olarsa boş siyahı."""
    try:
        resp = await client.get(source.rss_url, timeout=20.0)
        resp.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException):
        return []

    # feedparser saf-Python və yavaşdır (~30-200ms) — event loop-u bloklamasın.
    parsed = await asyncio.to_thread(feedparser.parse, resp.content)
    items: list[NormalizedNews] = []
    for entry in parsed.entries:
        item = _normalize_entry(entry, source)
        if item:
            items.append(item)
    return items


async def collect_all() -> list[NormalizedNews]:
    """Bütün mənbələri PARALEL çəkir, feed daxilində dublikatları təmizləyir."""
    headers = {"User-Agent": _USER_AGENT}
    seen: set[str] = set()
    out: list[NormalizedNews] = []
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        # Ardıcıl deyil paralel — dövr sum(latency) yox max(latency) çəkir.
        results = await asyncio.gather(
            *(fetch_feed(client, source) for source in FEEDS)
        )
    for items in results:
        for item in items:
            if item.dedup_hash in seen:
                continue
            seen.add(item.dedup_hash)
            out.append(item)
    return out
