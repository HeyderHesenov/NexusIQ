"""Proqnoz doğruluq motoru — forecast linklərini REAL qiymət hərəkəti ilə qiymətləndirir.

PULSUZ (LLM yox) — sırf qiymət riyaziyyatı, `analog._move_after` reuse.
Point-in-time təhlükəsiz: istiqamət (`scored_dir`) generasiya vaxtı dondurulub,
gəlir yalnız `published_at`-dan SONRAKI bağlanışlardan ölçülür (lookahead yox).

Yalnız üfüq TAM bağlananda (ret_30 mövcud) `scored_at` möhürlənir → tam slice.
"""
from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import select, update

from app.analytics import analog, assets
from app.db.session import AsyncSessionLocal
from app.models import NewsAsset

WINDOWS = (1, 5, 30)
# 30 ticarət günü ≈ 42-44 təqvim günü; buferlə 45 → seçilən sətirlərin çoxu hazır.
_MATURE_DAYS = 45
_CLOSES_TTL = 3600.0

# Proqnoz `published_at`-dan NƏ QƏDƏR sonra yaradılıbsa hələ də "proqnoz" sayılır.
#
# Niyə lazımdır: gəlir `published_at`-dan ölçülür (yuxarıdakı docstring "lookahead
# yox" deyir), amma `populate_forecast` `published_at`-ı XƏBƏRDƏN denormalizasiya
# edir — sətrin YARANMA vaxtından yox. `GET /news/{id}/forecast` isə on-demand,
# anonim və istənilən YAŞDA xəbər üçün çağırıla bilir. Yəni bu gün 2 illik
# məqaləyə yaradılan "proqnoz" dərhal yetişmiş sayılır və artıq BAŞ VERMİŞ qiymət
# hərəkəti ilə ballanır — modulun öz point-in-time iddiası pozulur.
#
# Hücum: köhnə `news_id`-ləri sayıb kütləvi proqnoz generasiya et → publik
# `/accuracy` scorecard-ının NÜMUNƏ TƏRKİBİNİ anonim şəkildə idarə et (_MIN_N=20
# əhəmiyyətsizcə aşılır) → etimad siqnalı kimi qurulmuş feature ləkələnir,
# üstəlik hər çağırış operatora fakturalanır.
#
# Marja: real axında istifadəçi TƏZƏ xəbəri açır → proqnoz saatlar içində yaranır,
# yəni bu qapı legitim yolu kəsmir və steady-state-də özü-özünü sağaldır.
_HONEST_LAG_DAYS = 2

_closes_cache: dict[str, tuple[float, pd.Series]] = {}


def _sym_for(key: str) -> str | None:
    """Reyestr açarı → Yahoo simvolu; coin (c_<base>) → <BASE>-USD."""
    meta = assets._BY_KEY.get(key)
    if meta:
        return meta[2]
    if key.startswith("c_"):
        return f"{key[2:].upper()}-USD"
    return None


async def _closes(sym: str) -> pd.Series:
    now = time.time()
    c = _closes_cache.get(sym)
    if c and now - c[0] < _CLOSES_TTL:
        return c[1]
    import asyncio

    s = await asyncio.to_thread(analog._fetch_closes, sym)
    if not s.empty:
        _closes_cache[sym] = (now, s)
    elif c:
        return c[1]
    return s


def _hit(scored_dir: str | None, ret: float | None) -> bool | None:
    """İstiqamət düz çıxdımı. mixed/neutral → istiqamət iddiası yox (None)."""
    if ret is None or scored_dir not in ("up", "down"):
        return None
    return ret > 0 if scored_dir == "up" else ret < 0


async def score_pending(limit: int = 300) -> dict:
    """Üfüqü bağlanmış qiymətləndirilməmiş forecast linklərini balla."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=_MATURE_DAYS)
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(
                    NewsAsset.id,
                    NewsAsset.asset_key,
                    NewsAsset.published_at,
                    NewsAsset.scored_dir,
                )
                .where(NewsAsset.source == "forecast")
                .where(NewsAsset.scored_at.is_(None))
                .where(NewsAsset.published_at <= cutoff)
                # YALNIZ həqiqi proqnozlar: nəticə məlum olduqdan SONRA
                # yaradılmış sətir proqnoz deyil (bax `_HONEST_LAG_DAYS`).
                .where(
                    NewsAsset.created_at
                    <= NewsAsset.published_at + timedelta(days=_HONEST_LAG_DAYS)
                )
                .limit(limit)
            )
        ).all()
        if not rows:
            return {"scored": 0}

        by_key: dict[str, list] = defaultdict(list)
        for r in rows:
            by_key[r.asset_key].append(r)

        now_dt = datetime.now(timezone.utc)
        scored = 0
        for key, items in by_key.items():
            sym = _sym_for(key)
            if not sym:
                continue
            closes = await _closes(sym)
            if closes.empty:
                continue
            for r in items:
                if r.published_at is None:
                    continue
                event_day = r.published_at.date()
                rets = {n: analog._move_after(closes, event_day, n) for n in WINDOWS}
                if rets[30] is None:  # üfüq hələ bağlanmayıb → sonra
                    continue
                await session.execute(
                    update(NewsAsset)
                    .where(NewsAsset.id == r.id)
                    .values(
                        ret_1=rets[1],
                        ret_5=rets[5],
                        ret_30=rets[30],
                        hit_1=_hit(r.scored_dir, rets[1]),
                        hit_5=_hit(r.scored_dir, rets[5]),
                        hit_30=_hit(r.scored_dir, rets[30]),
                        scored_at=now_dt,
                    )
                )
                scored += 1
        await session.commit()
        return {"scored": scored}


if __name__ == "__main__":
    import asyncio

    from app.db.session import engine

    async def _main() -> None:
        print("✅ Proqnoz scorer:", await score_pending())
        await engine.dispose()

    asyncio.run(_main())
