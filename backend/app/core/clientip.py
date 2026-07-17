"""Real klient IP-nin təyini — limiter və auth logger üçün TƏK mənbə.

X-Forwarded-For spoofing-ə qarşı: XFF-i istifadəçi sərbəst təyin edə bilər, ona görə
YALNIZ öz etibarlı proksilərimizin əlavə etdiyi girişlərə güvənirik.

`trusted_proxy_hops` = XFF-ə əlavə edən (append) öz proksilərimizin sayı:
- `0` (default) → XFF tam iqnor, socket peer istifadə olunur. Lokal/proksisiz üçün.
- `N ≥ 1` → `xff[-N]` (rightmost-untrusted): öz proksilərimizin əlavə etdiyi N girişi
  atıb ondan əvvəlkini götür. Klassik "leftmost" xətası (xff[0]) tam saxta-nəzarətlidir.

**Vacib:** Next `/backend` rewrite proksisi XFF-ə HOP DEYİL — o, XFF-i dəyişmədən ötürür
(əlavə etmir). Yəni `hops` yalnız XFF-ə *append edən* proksiləri sayır (edge/nginx/CF),
Next-i YOX. Bunu bir vahid səhv salmaq real klient IP ilə proksi IP-si arasındakı fərqdir.
"""
from __future__ import annotations

import ipaddress
import logging

from fastapi import Request

from app.core.config import settings

logger = logging.getLogger("nexusiq.clientip")


def _peer(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _parse_ip(value: str) -> str | None:
    """Port şəkilçisini soy, IP-ni validasiya et. Parse olunmursa None."""
    v = value.strip()
    if not v:
        return None
    # [2001:db8::1]:443 → 2001:db8::1
    if v.startswith("[") and "]" in v:
        v = v[1 : v.index("]")]
    # 1.2.3.4:5678 → 1.2.3.4  (yalnız IPv4 kimi görünəndə; IPv6-da iki nöqtə çoxdur)
    elif v.count(":") == 1:
        v = v.split(":", 1)[0]
    try:
        return str(ipaddress.ip_address(v))
    except ValueError:
        return None


def client_ip(request: Request) -> str:
    """Rate-limit / audit üçün real klient IP-si."""
    hops = settings.trusted_proxy_hops
    if hops <= 0:
        return _peer(request)

    fwd = request.headers.get("x-forwarded-for")
    if not fwd:
        return _peer(request)

    parts = [p for p in (s.strip() for s in fwd.split(",")) if p]
    if len(parts) < hops:
        # Miskonfiqurasiya — gözlədiyimizdən az proksi girişi. Sorğu deyil, quraşdırma xətası.
        logger.warning(
            "XFF girişləri (%d) < trusted_proxy_hops (%d) — miskonfiqurasiya; peer-ə düşülür",
            len(parts),
            hops,
        )
        return _peer(request)

    ip = _parse_ip(parts[-hops])
    return ip or _peer(request)
