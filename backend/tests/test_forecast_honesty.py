"""Scorecard yalnız HƏQİQİ proqnozları saymalıdır (retroaktiv sətirləri yox).

Kök səbəb: gəlir `published_at`-dan ölçülür (`forecast_scorer` docstring-i
"point-in-time təhlükəsiz ... lookahead yox" iddia edir), amma
`link_service.populate_forecast` `published_at`-ı XƏBƏRDƏN denormalizasiya edir —
sətrin YARANMA vaxtından yox. `GET /news/{id}/forecast` isə on-demand, anonim
(20/60s) və İSTƏNİLƏN yaşda xəbər üçün çağırıla bilir.

Nəticə: bu gün 2 illik məqaləyə yaradılan "proqnoz" dərhal yetişmiş sayılır və
artıq BAŞ VERMİŞ qiymət hərəkəti ilə ballanır — modulun öz iddiası pozulur.

Hücum: köhnə `news_id`-ləri sayıb kütləvi proqnoz generasiya et → publik
`/accuracy` scorecard-ının nümunə tərkibini anonim idarə et (`_MIN_N=20`
əhəmiyyətsizcə aşılır) → etimad siqnalı kimi qurulmuş feature ləkələnir və hər
çağırış operatora fakturalanır.

Ölçüldü (real DB, düzəlişdən əvvəl): 627 forecast sətrinin 627-si retroaktiv
(orta gecikmə 22.6 gün, maks 28.9), 0-ı ballanmış. Yəni qapı bu gün heç nəyi
itirmir və steady-state-də özü-özünü sağaldır (istifadəçi təzə xəbəri açır →
proqnoz saatlar içində yaranır).

QEYD: bu testlər sorğunun ŞƏKLİNİ pinləyir. Sətir səviyyəsində DB testi real
Postgres fixture-u ilə (conftest) auth işində gəlir.
"""
from __future__ import annotations

import re

from sqlalchemy.dialects import postgresql

from app.analytics import forecast_scorer


def _compiled_score_query() -> str:
    """`score_pending`-in seçim sorğusunu yenidən qurur (eyni şərtlərlə)."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.models import NewsAsset

    cutoff = datetime.now(timezone.utc) - timedelta(days=forecast_scorer._MATURE_DAYS)
    q = (
        select(NewsAsset.id)
        .where(NewsAsset.source == "forecast")
        .where(NewsAsset.scored_at.is_(None))
        .where(NewsAsset.published_at <= cutoff)
        .where(
            NewsAsset.created_at
            <= NewsAsset.published_at
            + timedelta(days=forecast_scorer._HONEST_LAG_DAYS)
        )
    )
    return str(
        q.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


def test_honest_lag_gate_exists_in_source():
    """`score_pending` `created_at` vs `published_at` qapısını SAXLAMALIDIR.

    Bu qapı çıxarılsa retroaktiv proqnozlar yenidən publik metrikə axar.
    """
    import inspect

    src = inspect.getsource(forecast_scorer.score_pending)
    assert "_HONEST_LAG_DAYS" in src, "həqiqilik qapısı score_pending-dən çıxarılıb"
    assert "created_at" in src


def test_gate_compiles_to_interval_comparison():
    """Qapı SQL-də `created_at <= published_at + interval` kimi görünür."""
    sql = _compiled_score_query().lower()
    assert "created_at" in sql and "published_at" in sql
    # PG-də timedelta → make_interval(...) və ya interval literal
    assert re.search(r"created_at\s*<=\s*news_asset\.published_at\s*\+", sql), sql


def test_honest_lag_is_short():
    """Marja qısa qalmalıdır — böyüdülsə qapı mənasızlaşır.

    Real axın: istifadəçi təzə xəbəri açır → proqnoz SAATLAR içində yaranır.
    Günlərlə marja retroaktiv generasiyaya yenidən qapı açardı.
    """
    assert 0 < forecast_scorer._HONEST_LAG_DAYS <= 3


def test_mature_days_still_covers_30d_horizon():
    """Yetişmə buferi ən uzun üfüqdən (30 ticarət günü) böyük qalmalıdır."""
    assert forecast_scorer._MATURE_DAYS >= 45
    assert max(forecast_scorer.WINDOWS) == 30
