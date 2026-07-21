"""Thumbnail proksisi — naşir şəklini serverdə kiçildib diskdə keşləyir.

Səbəb: naşirlərin `og:image`-i tam ölçülüdür (ölçdük: qızıl siyahısında 8 şəkil
= 1520 KB, biri tək başına 778 KB), kart isə 96×64-dür. Brauzer ~30× artıq bayt
çəkirdi. Burada bir dəfə kiçildilir, sonrakı hər baxış diskdən gəlir.

TƏHLÜKƏSİZLİK — bu AÇIQ PROKSİ DEYİL, amma "təxirə salınmış proksi"dir:
- Giriş `news.id`-dir, URL DEYİL → çağıran hansı hostun çəkiləcəyini seçə bilmir.
  (`next.config.mjs` wildcard `remotePatterns`-i məhz attacker-supplied host
  səbəbindən bağlayıb.)
- LAKİN çağıran HANSI saxlanmış URL-in və NƏ QƏDƏR TEZ çəkiləcəyini seçir, URL-in
  özü isə RSS/og:image-dən gəlir (attacker-adjacent). Ona görə hər çəkiliş
  `netguard.safe_get` ilədir və aşağıdakı tavanlar məcburidir.

Tavanlar (hər biri AYRI bir hücum oxudur — biri digərini əvəz etmir):
- `_MAX_BYTES` — AXIN zamanı (netguard `max_bytes`), yükləmədən sonra yox. Bu
  DoS/soket tavanıdır, bomba qoruyucusu DEYİL — ona görə real naşir originalını
  boğmayacaq qədər səxavətli olmalıdır (ölçdük: Yahoo `s.yimg.com/os/creatr-*`
  şəkilləri 25 MB gəlir; 12 MB tavan onları kəsib kartı placeholder-ə salırdı).
  Əsl bomba qoruyucusu aşağıdakı `_MAX_PIXELS`-dir (decode-dən SONRA).
- `_MAX_PIXELS` — decompression bomba. Bayt tavanı bunu TUTMUR: sıxılma nisbətini
  hücumçu seçir (ölçdük: 435 KB PNG = 144M piksel ≈ 432 MB raster). Pillow-un
  öz `MAX_IMAGE_PIXELS`-i də tutmur — 89M-dən 2× böyük olana qədər yalnız
  XƏBƏRDARLIQ verib şəkli DEKOD EDİR.
- `_TOTAL_DEADLINE` — httpx read-timeout XƏBƏRDARLIQ: o, chunk-lar ARASINDAKI
  fasilədir, ümumi vaxt deyil. Baytı damcı-damcı verən server əbədi bağlayardı.
- `_FETCH_SEM` — eyni anda gedən kənar sorğu sayı (rate-limit tək başına bəs
  etmir: 300/dəq × 12s = onlarla asılı soket).
- Neqativ keş — uğursuz çəkiliş də yadda saxlanır, yoxsa ölü URL HƏR sorğuda
  yenidən çəkilərdi (keş yalnız uğuru saxlayırdı = bahalı yol qorunmamış qalırdı).
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import httpx
from PIL import Image, UnidentifiedImageError

from app.core import netguard

# Yalnız frontend-in REAL istədiyi enlər: 192 (aktiv siyahısı), 640 (NewsCard),
# 1280 (xəbər detalı). Artıq en = pulsuz keş şişməsi (enumerasiya × en).
ALLOWED_W: frozenset[int] = frozenset({192, 640, 1280})

_MAX_BYTES = 32 * 1024 * 1024  # naşir originalları böyük ola bilir (Yahoo ~25 MB);
#                                soket/DoS tavanı, bomba qoruyucusu deyil (bax `_MAX_PIXELS`).
_MAX_PIXELS = 40_000_000
_TIMEOUT = 12.0
_TOTAL_DEADLINE = 20.0
# Blip ilə ölü URL eyni şey DEYİL. Ölçüldü: id 4074 (CoinDesk) upstream tam
# sağlamdır (200, 1920×1080), amma bir keçici blip w=192 və w=640-ı — frontend-in
# işlətdiyi məhz iki eni — 15 dəqiqəlik örtüyə saldı (w=1280 təmiz qaldı).
_NEG_TTL_HARD = 900.0  # 404/410/dekod-xətası/SSRF — naşir tərəfi, sabit
_NEG_TTL_SOFT = 90.0  # 403/429/5xx/timeout/şəbəkə — keçici, tez təkrar cəhd
_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "img"

# AYRICA hovuz — `asyncio.to_thread` DEFOLT hovuzu işlədir, onu isə yfinance
# çağırışları (assets/market/analog/radar) doldurur: 8 CPU → cəmi 12 işçi.
# Ölçdük: prewarm zamanı KEŞDƏ OLAN şəkil 3ms əvəzinə 8s+ asılırdı. Burada
# YALNIZ kiçiltmə işlənir; keş oxunuşu `FileResponse`-a verilir (hovuzsuz),
# yoxsa ucuz oxu bahalı LANCZOS-un arxasında növbəyə düşərdi.
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="imgresize")
_FETCH_SEM = asyncio.Semaphore(8)

_neg: dict[str, float] = {}  # keş açarı → neqativ nəticənin bitmə vaxtı
_inflight: dict[str, asyncio.Task] = {}  # eyni açara paralel iş birləşdirilir
_client: httpx.AsyncClient | None = None


def _http() -> httpx.AsyncClient:
    """Paylaşılan klient — hər sorğuda yenisi TLS handshake-i təkrarlayırdı."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            follow_redirects=False,
            limits=httpx.Limits(max_connections=16, max_keepalive_connections=8),
        )
    return _client


async def aclose() -> None:
    """Tətbiq bağlananda klienti təmiz bağla (lifespan hook-u üçün)."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


def _key(news_id: int, url: str, w: int) -> str:
    # URL açara DAXİLDİR: `immutable, 1 il` başlığı yalnız məzmun açarla tam
    # müəyyən olanda dürüstdür. URL dəyişsə (backfill/yenidən scrape) köhnə
    # bayt əbədi verilərdi və geri qaytarma leveri OLMAZDI.
    return hashlib.sha256(f"{news_id}:{w}:{url}".encode()).hexdigest()


def path_for(news_id: int, url: str, w: int) -> Path:
    h = _key(news_id, url, w)
    return _CACHE_DIR / h[:2] / f"{h[2:18]}_{w}.webp"


def _resize(raw: bytes, w: int) -> bytes | None:
    """Baytları `w` eninə kiçildib WebP qaytarır. Yararsız/bombada None."""
    try:
        im = Image.open(io.BytesIO(raw))
        # JPEG-i libjpeg-in öz DCT miqyaslaması ilə kiçik açır (pik yaddaş + CPU
        # dərhal aşağı düşür); digər formatlarda (PNG/WebP/GIF) təsirsizdir.
        im.draft("RGB", (w, w))
        # Piksel tavanı `load()`-DAN ƏVVƏL, amma `draft()`-DAN SONRA: `load()`-un
        # AYIRACAĞI raster ölçüsü budur. Beləcə real BÖYÜK foto keçir (Yahoo
        # 7954×5305=42M → draft sonrası 995×664=0.7M), draft kiçiltməyən bomba
        # (nəhəng başlıqlı PNG/WebP və ya scale-siz JPEG) isə dekoddan ƏVVƏL tutulur.
        # 40M piksel (~120MB raster) yaddaş büdcəsi olduğu kimi qalır — sadəcə
        # düzgün nöqtədə yoxlanır. (Əvvəl draft-dan əvvəl yoxlanırdı → 42M-lik real
        # Yahoo fotosunu kəsib kartı placeholder-ə salırdı.)
        if im.width * im.height > _MAX_PIXELS:
            return None
        im.load()  # truncated fayl burada tutulur
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        return None
    if im.width <= 1 or im.height <= 1:
        return None  # 1×1 tracking piksel — örtüyə buraxılsın
    if im.mode != "RGB":
        im = im.convert("RGB")
    if im.width > w:
        im = im.resize((w, max(1, round(im.height * w / im.width))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=80, method=4)
    return buf.getvalue()


async def _fetch(url: str) -> tuple[bytes | None, bool]:
    """(baytlar, keçici?) — keçici xəta qısa TTL ilə keşlənir, sərt xəta uzun."""
    async with _FETCH_SEM:
        try:
            r = await asyncio.wait_for(
                netguard.safe_get(
                    _http(), url, timeout=_TIMEOUT, max_bytes=_MAX_BYTES
                ),
                timeout=_TOTAL_DEADLINE,
            )
        except Exception:  # noqa: BLE001 — DNS/TCP/TLS/timeout → KEÇİCİ
            return None, True
    if r is None:
        # `safe_get`-in None-u SİYASƏT verdiktidir (qadağan host, `max_bytes`
        # tavanı, çox redirect) — URL dəyişməyincə dəyişməz, yəni sərt.
        return None, False
    if r.status_code != 200:
        # 403/429/5xx = naşirin ani vəziyyəti; 404/410 = həqiqətən yoxdur.
        return None, r.status_code in (403, 408, 425, 429) or r.status_code >= 500
    return r.content, False


async def _build(news_id: int, url: str, w: int, path: Path) -> tuple[Path | None, bool]:
    raw, transient = await _fetch(url)
    if raw is None:
        return None, transient
    out = await asyncio.get_running_loop().run_in_executor(_POOL, _resize, raw, w)
    if not out:
        return None, False  # dekod alınmadı — bayt dəyişməyincə dəyişməz

    def _write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        # tmp adı UNİKAL olmalıdır: (id,w)-dan determinik ad paralel yazıcıları
        # eyni fayla salır → biri truncate edərkən digəri replace edə bilər və
        # 0-baytlıq fayl `immutable, 1 il` ilə yayımlanardı.
        tmp = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        try:
            tmp.write_bytes(out)
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)

    try:
        await asyncio.get_running_loop().run_in_executor(_POOL, _write)
    except OSError:
        return None, True  # disk problemi — keçici
    return path, False


_MAX_CACHE_BYTES = 1_500_000_000  # ~1.5 GB


def _prune_sync() -> int:
    """Həcm tavanı aşılıbsa ən köhnə-toxunulmuş faylları sil (LRU, atime).

    Keş öz-özünə dayanmır: yazı = |xəbər| × |ALLOWED_W| və planlayıcı saatda yeni
    xəbər gətirir. Tavansız o, Postgres ilə eyni diski doldurardı.
    """
    files: list[tuple[float, int, Path]] = []
    total = 0
    for p in _CACHE_DIR.rglob("*.webp"):
        try:
            st = p.stat()
        except OSError:
            continue
        files.append((st.st_atime, st.st_size, p))
        total += st.st_size
    if total <= _MAX_CACHE_BYTES:
        return 0
    files.sort()  # ən köhnə toxunuş əvvəl
    removed = 0
    for _atime, size, p in files:
        if total <= _MAX_CACHE_BYTES * 0.8:  # hər dövr silməmək üçün 80%-ə en
            break
        try:
            p.unlink()
        except OSError:
            continue
        total -= size
        removed += 1
    return removed


async def prune() -> int:
    """Planlayıcı üçün — budamanı öz hovuzunda işlədir (event loop-u bloklamaz)."""
    return await asyncio.get_running_loop().run_in_executor(_POOL, _prune_sync)


async def get_path(news_id: int, url: str, w: int) -> Path | None:
    """Keşdəki faylın yolu; yoxdursa çək-kiçilt-yaz. Alınmasa None (→ örtük)."""
    path = path_for(news_id, url, w)
    if path.is_file() and path.stat().st_size > 0:
        return path  # ucuz stat — hovuza girmir

    key = _key(news_id, url, w)
    now = time.monotonic()
    if (exp := _neg.get(key)) and exp > now:
        return None  # yaxınlarda alınmadı — kənar mənbəni yenidən döymə
    if len(_neg) > 4096:  # sadə həcm qapağı
        _neg.clear()

    task = _inflight.get(key)
    if task is None:  # single-flight: eyni açara N sorğu = 1 çəkiliş
        task = asyncio.create_task(_build(news_id, url, w, path))
        _inflight[key] = task
        task.add_done_callback(lambda _t, k=key: _inflight.pop(k, None))
    try:
        result, transient = await asyncio.shield(task)
    except Exception:  # noqa: BLE001
        result, transient = None, True
    if result is None:
        _neg[key] = time.monotonic() + (_NEG_TTL_SOFT if transient else _NEG_TTL_HARD)
    return result
