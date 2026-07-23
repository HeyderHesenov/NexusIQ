"""Anti-drift qoruyucu — hər route-un auth siyasəti (PUBLIC|USER) açıq cədvəllə tutuşdurulur.

"Birini unutduqmu?" sualını code-review sualından BUILD FAILURE-a çevirir: yeni və ya
təsnif edilməmiş route testi qırır (hələ yazılmamış route-lar üçün də). AI/write route-u
require_user-siz əlavə edilsə → dərhal qırılır.
"""
from __future__ import annotations

from fastapi.routing import APIRoute

from app.core.auth import require_user, require_user_allow_unverified
from app.main import app

_P = "/api/v1"

# require_user (və ya allow_unverified variantı) dependency ağacında varsa → USER.
USER: set[tuple[str, str]] = {
    ("DELETE", f"{_P}/me/alerts/{{alert_id}}"),
    ("DELETE", f"{_P}/me/bookmarks/{{news_id}}"),
    ("DELETE", f"{_P}/me/holdings/{{key}}"),
    ("DELETE", f"{_P}/me/saved-events/{{event_key}}"),
    ("DELETE", f"{_P}/me/watchlist/{{key}}"),
    ("GET", f"{_P}/analogs/search"),
    ("GET", f"{_P}/auth/me"),
    ("GET", f"{_P}/correlation/pair/explain"),
    ("GET", f"{_P}/market/brief"),
    ("GET", f"{_P}/me/alerts"),
    ("GET", f"{_P}/me/audit"),
    ("GET", f"{_P}/me/bookmarks"),
    ("GET", f"{_P}/me/holdings"),
    ("GET", f"{_P}/me/intel/asset/{{key}}"),
    ("GET", f"{_P}/me/intel/portfolio"),
    ("GET", f"{_P}/me/intel/watchlist"),
    ("GET", f"{_P}/me/prefs"),
    ("GET", f"{_P}/me/saved-events"),
    ("GET", f"{_P}/me/watchlist"),
    ("GET", f"{_P}/news/{{news_id}}/content"),
    ("GET", f"{_P}/news/{{news_id}}/forecast"),
    ("GET", f"{_P}/radar/{{key}}/about"),
    ("GET", f"{_P}/radar/{{key}}/explain"),
    ("GET", f"{_P}/auth/sessions"),
    ("DELETE", f"{_P}/auth/sessions/{{sid}}"),
    ("POST", f"{_P}/auth/logout-all"),
    ("POST", f"{_P}/auth/password"),
    ("POST", f"{_P}/chat"),
    ("POST", f"{_P}/chat/stream"),
    ("POST", f"{_P}/me/alerts"),
    ("POST", f"{_P}/me/bookmarks/{{news_id}}"),
    ("POST", f"{_P}/me/import"),
    ("POST", f"{_P}/me/saved-events"),
    ("POST", f"{_P}/me/watchlist/{{key}}"),
    ("POST", f"{_P}/push/subscribe"),
    ("POST", f"{_P}/push/test"),
    ("POST", f"{_P}/push/unsubscribe"),
    ("PUT", f"{_P}/me/holdings/{{key}}"),
    ("PUT", f"{_P}/me/prefs"),
}

PUBLIC: set[tuple[str, str]] = {
    ("GET", f"{_P}/accuracy"),
    ("GET", f"{_P}/anomalies"),
    ("GET", f"{_P}/anomalies/{{key}}/news"),
    ("GET", f"{_P}/assets"),
    ("GET", f"{_P}/assets/overview"),
    ("GET", f"{_P}/assets/{{key}}"),
    ("GET", f"{_P}/assets/{{key}}/news"),
    ("GET", f"{_P}/assets/{{key}}/quote"),
    ("GET", f"{_P}/auth/google/nonce"),
    ("GET", f"{_P}/correlation/matrix"),
    ("GET", f"{_P}/correlation/pair"),
    ("GET", f"{_P}/health"),
    ("GET", f"{_P}/health/db"),
    ("GET", f"{_P}/img/news/{{news_id}}"),
    ("GET", f"{_P}/market/calendar"),
    ("GET", f"{_P}/market/commodities"),
    ("GET", f"{_P}/market/crypto-calendar"),
    ("GET", f"{_P}/market/earnings"),
    ("GET", f"{_P}/market/feargreed"),
    ("GET", f"{_P}/market/majors-calendar"),
    ("GET", f"{_P}/market/metals"),
    ("GET", f"{_P}/market/powerlaw"),
    ("GET", f"{_P}/market/powerlaw/assets"),
    ("GET", f"{_P}/market/ticker"),
    ("GET", f"{_P}/news"),
    ("GET", f"{_P}/news/count"),
    ("GET", f"{_P}/news/search"),
    ("GET", f"{_P}/news/trending"),
    ("GET", f"{_P}/news/{{news_id}}"),
    ("GET", f"{_P}/news/{{news_id}}/analogs"),
    ("GET", f"{_P}/push/key"),
    ("GET", f"{_P}/radar"),
    ("GET", f"{_P}/radar/{{key}}"),
    # /auth/logout PUBLIC-dir (vaxtı keçmiş access ilə də çıxa bilməlisən — refresh cookie oxuyur).
    ("POST", f"{_P}/auth/google"),
    ("POST", f"{_P}/auth/login"),
    ("POST", f"{_P}/auth/logout"),
    ("POST", f"{_P}/auth/password-reset/confirm"),
    ("POST", f"{_P}/auth/password-reset/request"),
    ("POST", f"{_P}/auth/refresh"),
    ("POST", f"{_P}/auth/register"),
}

KNOWN = USER | PUBLIC


def _uses_require_user(route: APIRoute) -> bool:
    def walk(dep) -> bool:
        for d in dep.dependencies:
            if getattr(d, "call", None) in (require_user, require_user_allow_unverified):
                return True
            if walk(d):
                return True
        return False

    return walk(route.dependant)


def _actual() -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for r in app.routes:
        if isinstance(r, APIRoute) and r.path.startswith(_P):
            policy = "USER" if _uses_require_user(r) else "PUBLIC"
            for m in r.methods - {"HEAD", "OPTIONS"}:
                out[(m, r.path)] = policy
    return out


def test_no_unclassified_route():
    """Cədvəldə OLMAYAN route → FAIL (yeni route təsnif olunmalıdır)."""
    actual = _actual()
    unclassified = sorted(k for k in actual if k not in KNOWN)
    assert not unclassified, f"Təsnif edilməmiş route(lar): {unclassified}"


def test_no_stale_table_entry():
    """Cədvəldə var, app-da yoxdur → FAIL (silinmiş route cədvəldən çıxarılmalı)."""
    actual = _actual()
    stale = sorted(k for k in KNOWN if k not in actual)
    assert not stale, f"Köhnəlmiş cədvəl girişi: {stale}"


def test_policy_matches_table():
    """Hər route-un faktiki siyasəti cədvəllə üst-üstə düşməlidir."""
    actual = _actual()
    mismatches = []
    for key, pol in actual.items():
        expected = "USER" if key in USER else "PUBLIC"
        if pol != expected:
            mismatches.append((key, pol, expected))
    assert not mismatches, f"Siyasət uyğunsuzluğu (route, faktiki, gözlənilən): {mismatches}"
