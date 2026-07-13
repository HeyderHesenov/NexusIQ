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
_IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"', re.IGNORECASE)
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


def _extract_image(entry) -> str | None:
    """media:content, media:thumbnail, enclosure və ya <img>-dən şəkil tapır."""
    media = entry.get("media_content") or entry.get("media_thumbnail")
    if media and isinstance(media, list) and media[0].get("url"):
        return media[0]["url"]
    for link in entry.get("links", []):
        if link.get("rel") == "enclosure" and "image" in (link.get("type") or ""):
            return link.get("href")
    body = entry.get("summary") or (
        entry.get("content", [{}])[0].get("value") if entry.get("content") else ""
    )
    match = _IMG_RE.search(body or "")
    return match.group(1) if match else None


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
