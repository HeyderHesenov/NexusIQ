"""Rate limiter — bahalı endpoint-lər üçün (per-IP / per-user sürüşən pəncərə).

Store abstraksiyası (`RateLimitStore`) ilə: bu gün in-memory sürüşən-pəncərə-log,
sonra Redis — **çağırı yerləri dəyişmədən**. Ona görə `hit()` BİRİNCİ GÜNDƏN async-dir
(Redis əlavə olunanda hər call site-ı sync→async məcbur etməmək üçün).

Tək-proses reallıq: `dev.sh` uvicorn-u `--workers`-siz işlədir. `--workers N` əlavə
olunsa hər limit səssizcə N× olur (login lockout DB-də olduğu üçün ondan sağ çıxır).
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Literal, Protocol

from fastapi import HTTPException, Request, status

from app.core.clientip import client_ip
from app.core.config import settings

# Sweep amortizasiyası: hər sorğuda O(n) skan ETMƏ — botnet altında CPU-DoS olardı.
_SWEEP_INTERVAL = 60.0   # saniyə: bu qədərdən bir bir dəfə köhnə açarları təmizlə
_STALE_AFTER = 3600.0    # ən böyük pəncərədən (100/saat) böyük — idle açarları at


class RateLimitStore(Protocol):
    async def hit(self, key: str, limit: int, window: float) -> tuple[bool, int]:
        """(allowed, retry_after_seconds) qaytarır. allowed=False → limit aşıldı."""
        ...


class InMemoryStore:
    """Sürüşən-pəncərə-log. Amortizasiya olunmuş sweep ilə (per-request O(n) yox)."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._next_sweep: float = 0.0

    def _sweep(self, now: float) -> None:
        cutoff = now - _STALE_AFTER
        stale = [k for k, ts in self._hits.items() if not ts or ts[-1] <= cutoff]
        for k in stale:
            self._hits.pop(k, None)

    async def hit(self, key: str, limit: int, window: float) -> tuple[bool, int]:
        now = time.monotonic()
        if now >= self._next_sweep:
            self._sweep(now)
            self._next_sweep = now + _SWEEP_INTERVAL
        cutoff = now - window
        hits = self._hits[key]
        hits[:] = [t for t in hits if t > cutoff]
        if len(hits) >= limit:
            retry = int(window - (now - hits[0])) + 1
            return False, max(1, retry)
        hits.append(now)
        return True, 0


def _make_store() -> RateLimitStore:
    backend = settings.ratelimit_backend
    if backend == "memory":
        return InMemoryStore()
    # RedisStore sonra bura düşəcək — call site-lar toxunulmadan.
    raise RuntimeError(f"Naməlum RATELIMIT_BACKEND: {backend!r}")


# İmport vaxtı bir dəfə seçilir (settings.ratelimit_backend).
_store: RateLimitStore = _make_store()

Scope = Literal["ip", "user", "user_or_ip"]


def _scope_key(request: Request, scope: Scope) -> str:
    """Rate-limit açarının subyekt hissəsi. `user` scope Addım 10-da `require_user`
    tərəfindən `request.state.user_id` qoyulanda işləyir; yoxdursa IP-ə düşür."""
    if scope in ("user", "user_or_ip"):
        uid = getattr(request.state, "user_id", None)
        if uid:
            return f"u:{uid}"
        if scope == "user":
            # user scope amma auth yoxdur → yenə IP (fail-safe, heç vaxt boş açar yox)
            return f"ip:{client_ip(request)}"
    return f"ip:{client_ip(request)}"


def rate_limit(name: str, limit: int, window: float = 60.0, *, scope: Scope = "ip"):
    """FastAPI dependency — `name` bucket-i üçün `limit`/`window`. Aşılırsa 429.

    `scope="ip"` (default) bütün mövcud call site-ları eyni saxlayır.
    """

    async def _dep(request: Request) -> None:
        key = f"{name}|{_scope_key(request, scope)}"
        allowed, retry = await _store.hit(key, limit, window)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Çox sayda sorğu — bir azdan yenidən cəhd et.",
                headers={"Retry-After": str(retry)},
            )

    return _dep
