"""yfinance-i HTTP/1.1-ə məcbur edən paylaşılan session.

NƏ ÜÇÜN: yfinance 1.4.1 defolt olaraq `curl_cffi` `Session(impersonate="chrome")`
qurur — bu isə HTTP/2 (nghttp2) işlədir. `curl_cffi`-nin nghttp2 native kodu müəyyən
Yahoo cavablarında **SIGBUS (Bus error)** verir; çağırış `asyncio.to_thread` işçisində
olduğu üçün native crash BÜTÜN backend prosesini öldürür → watchdog restart → şəkillər/
xəbərlər bir müddət itir → təkrarlanır. Crash YALNIZ HTTP/2 yolundadır; HTTP/1.1-ə
keçəndə həmin kod heç çağırılmır. TLS impersonation qalır → Yahoo bloklamır.

Empirik təsdiq (query1.finance.yahoo.com): chrome default → `http_version=3` (HTTP/2);
chrome + FORCE V1_1 → `http_version=2` (HTTP/1.1); hər ikisi status 200 + data.

NECƏ: yfinance-in `new_session()` fabrikini BÜTÜN namespace-lərində HTTP/1.1 session
qaytaran fabrikə əvəz edirik. Bu TƏK nəzarət nöqtəsidir: hər `session or new_session()`
(multi/base/data/history) bizimkini alır — ~15 çağırış yerini əl ilə keçirməyə (və birini
buraxıb `YfData` singleton-unu təzə HTTP/2 session ilə zəhərləməyə) ehtiyac yoxdur.
"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger("nexusiq.yf")

_lock = threading.Lock()
_session = None


def get_session():
    """Paylaşılan curl_cffi session — impersonate=chrome, HTTP/1.1-ə kilidli.

    curl_cffi Session defolt olaraq thread-lokal curl handle işlədir
    (`use_thread_local_curl=True`) → `to_thread` işçilərindən paralel istifadə
    təhlükəsizdir (yfinance onsuz da tək singleton session-u bütün thread-lərdə bölüşür).
    """
    global _session
    if _session is None:
        with _lock:
            if _session is None:
                from curl_cffi import CurlHttpVersion
                from curl_cffi import requests as cffi
                from curl_cffi.const import CurlOpt

                _session = cffi.Session(
                    impersonate="chrome",
                    curl_options={CurlOpt.HTTP_VERSION: int(CurlHttpVersion.V1_1)},
                )
    return _session


def install() -> None:
    """yfinance-in `new_session`-unu HTTP/1.1 fabrikinə əvəz et. İdempotentdir.

    Startup-da, HƏR YANSI yfinance çağırışından ƏVVƏL çağırılmalıdır (main.py lifespan).
    yfinance strukturu dəyişsə/yoxdursa səssiz keçir — app yenə işləyir (sadəcə fix yoxdur).
    """
    try:
        import yfinance._http as _http
        import yfinance.base as _base
        import yfinance.data as _data
        import yfinance.multi as _multi
        from yfinance.scrapers import history as _history
    except Exception as e:  # yfinance yoxdur/strukturu dəyişib
        logger.warning("yfinance HTTP/1.1 patch tətbiq olunmadı: %s", e)
        return

    patched = 0
    for mod in (_http, _base, _data, _multi, _history):
        if hasattr(mod, "new_session"):
            mod.new_session = get_session
            patched += 1

    # Əgər YfData singleton-u artıq (defolt HTTP/2 session ilə) yaranıbsa, onu da keçir.
    try:
        _data.YfData(session=get_session())
    except Exception:
        pass

    logger.info("yfinance HTTP/1.1 session tətbiq olundu (%d namespace)", patched)
