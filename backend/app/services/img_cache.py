"""Thumbnail proksisi — naşir şəklini serverdə kiçildib diskdə keşləyir.

Səbəb: naşirlərin `og:image`-i tam ölçülüdür (ölçdük: qızıl siyahısında 8 şəkil
= 1520 KB, biri tək başına 778 KB), kart isə 96×64-dür. Brauzer ~30× artıq bayt
çəkirdi. Burada bir dəfə kiçildilir, sonrakı hər baxış diskdən gəlir.

TƏHLÜKƏSİZLİK — bu AÇIQ PROKSİ DEYİL:
- Giriş `news.id`-dir, URL DEYİL. Yəni çağıran hansı hostun çəkiləcəyini seçə
  bilmir; URL yalnız öz DB sətrimizdən oxunur. (`next.config.mjs` wildcard
  `remotePatterns`-i məhz bu səbəbdən — attacker-supplied host — bağlayıb.)
- Saxlanan URL-in özü RSS-dən gəlir (attacker-adjacent), ona görə çəkiliş
  `netguard.safe_get` ilədir: daxili/metadata IP-lər və redirect hopları bloklanır.
- Bayt tavanı + Pillow-un decompression-bomb qoruması (MAX_IMAGE_PIXELS).
"""
from __future__ import annotations

import asyncio
import hashlib
import io
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from PIL import Image, UnidentifiedImageError

from app.core import netguard

# Kart ölçüləri: 96×64 (aktiv siyahısı) və 16/9 kartlar @2x DPR.
ALLOWED_W: frozenset[int] = frozenset({192, 384, 640, 960, 1280})
_MAX_BYTES = 12 * 1024 * 1024  # 12 MB-dan iri mənbə şəklini emal etmə
_TIMEOUT = 12.0
_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "img"

# AYRICA hovuz — `asyncio.to_thread` DEFOLT hovuzu işlədir, onu isə yfinance
# çağırışları (assets/market/analog/radar) doldurur: 8 CPU → cəmi 12 işçi.
# Ölçdük: prewarm zamanı KEŞDƏ OLAN şəkil 3ms əvəzinə 8s+ asılırdı, çünki
# oxu növbədə gözləyirdi. Şəkil işi öz hovuzunda → bazar yükündən asılı deyil.
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="imgcache")


async def _run(fn, *a):
    return await asyncio.get_running_loop().run_in_executor(_POOL, fn, *a)


def _path_for(news_id: int, w: int) -> Path:
    # id-ni hash-ə qatmaq keş qovluğunu bərabər paylayır (tək qovluqda 100k fayl olmasın).
    h = hashlib.sha256(f"{news_id}:{w}".encode()).hexdigest()
    return _CACHE_DIR / h[:2] / f"{h[2:18]}_{w}.webp"


def _resize(raw: bytes, w: int) -> bytes | None:
    """Baytları `w` eninə kiçildib WebP qaytarır. Yararsız şəkildə None."""
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()  # burada həm truncated, həm decompression-bomb tutulur
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        return None
    if im.width <= 1 or im.height <= 1:
        return None  # 1×1 tracking piksel — örtüyə buraxılsın
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    if im.width > w:
        im = im.resize((w, max(1, round(im.height * w / im.width))), Image.LANCZOS)
    if im.mode == "RGBA":
        im = im.convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=80, method=4)
    return buf.getvalue()


async def _fetch(url: str) -> bytes | None:
    async with httpx.AsyncClient(follow_redirects=False) as client:
        try:
            r = await netguard.safe_get(client, url, timeout=_TIMEOUT)
        except Exception:  # noqa: BLE001 — şəbəkə/SSL/timeout: örtüyə düş
            return None
    if r is None or r.status_code != 200:
        return None
    if len(r.content) > _MAX_BYTES:
        return None
    return r.content


async def get(news_id: int, url: str, w: int) -> bytes | None:
    """Keşdən oxu, yoxdursa çək-kiçilt-yaz. Alınmasa None (→ frontend örtüyü)."""
    path = _path_for(news_id, w)
    try:
        return await _run(path.read_bytes)
    except OSError:
        pass

    raw = await _fetch(url)
    if raw is None:
        return None
    out = await _run(_resize, raw, w)
    if out is None:
        return None

    def _write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(out)
        tmp.replace(path)  # atomik — yarımçıq fayl oxunmasın

    try:
        await _run(_write)
    except OSError:
        pass  # keş yazıla bilmirsə də cavabı ver
    return out
