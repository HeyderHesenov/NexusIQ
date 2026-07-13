"""Yüngül in-memory rate limiter — bahalı endpoint-lər üçün (per-IP sürüşən pəncərə).

Tək-proses demo üçün kifayətdir; xarici asılılıq yoxdur. Çoxlu instans/prod üçün
Redis-əsaslı limiter lazım olar.
"""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from app.core.config import settings

# bucket adı → (ip → [son sorğu vaxtları])
_HITS: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))


def _client_ip(request: Request) -> str:
    """Real IP — X-Forwarded-For-a YALNIZ etibarlı proksi arxasında inan.

    Spoofing qorunması: XFF istifadəçi tərəfindən sərbəst təyin edilə bilər.
    Proksi olmadan (trusted_proxy=False) hər sorğu üçün socket IP-ə güvən —
    əks halda hər sorğu unikal saxta IP göstərib limiti tamamilə keçə bilər.
    """
    if settings.trusted_proxy:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _sweep(bucket: dict[str, list[float]], cutoff: float) -> None:
    """Pəncərəsi tam boşalmış IP açarlarını at — yaddaş sonsuz böyüməsin."""
    stale = [ip for ip, ts in bucket.items() if not ts or ts[-1] <= cutoff]
    for ip in stale:
        bucket.pop(ip, None)


def rate_limit(name: str, limit: int, window: float = 60.0):
    """FastAPI dependency — `name` bucket-i üçün per-IP `limit`/`window`. Aşılırsa 429."""

    async def _dep(request: Request) -> None:
        ip = _client_ip(request)
        now = time.monotonic()
        cutoff = now - window
        bucket = _HITS[name]
        # Fürsətdən istifadə edib köhnəlmiş IP-ləri təmizlə (memory-DoS qoruması).
        _sweep(bucket, cutoff)
        hits = bucket[ip]
        # pəncərədən kənar köhnə vaxtları at
        hits[:] = [t for t in hits if t > cutoff]
        if len(hits) >= limit:
            retry = int(window - (now - hits[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Çox sayda sorğu — bir azdan yenidən cəhd et.",
                headers={"Retry-After": str(max(1, retry))},
            )
        hits.append(now)

    return _dep
