"""AI büdcə — qlobal cap + per-user cap + kill switch + weight + planlayıcı uçotu.

Kök səbəb: anonim bot /chat-ı pulsuz LLM proksisi kimi işlədir. Bu testlər admission
qapısını (dependency), qlobal cap-ı, DB kill switch-i və planlayıcının qlobal cap-a
sayılmasını pinləyir.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.core import budget
from app.core.config import settings
from app.models import AiUsage
from app.services import auth_service


async def _mk_user(db, email="bud@example.com"):
    u = await auth_service.create_user(db, email, password_hash="x")
    await db.commit()
    return u


def _req(user_id=None):
    st = SimpleNamespace()
    if user_id is not None:
        st.user_id = str(user_id)
    return SimpleNamespace(state=st)


async def test_records_usage_with_weight(db):
    u = await _mk_user(db)
    dep = budget.ai_budget("chat", weight=4)
    await dep(_req(u.id), db)
    row = await db.scalar(select(AiUsage).where(AiUsage.user_id == u.id))
    assert row is not None and row.weight == 4 and row.route == "chat"


async def test_per_user_cap(db, monkeypatch):
    monkeypatch.setattr(settings, "ai_daily_calls_per_user", 8)
    monkeypatch.setattr(settings, "ai_global_daily_calls", 100000)
    u = await _mk_user(db)
    dep = budget.ai_budget("chat", weight=4)
    await dep(_req(u.id), db)  # 4
    await dep(_req(u.id), db)  # 8
    with pytest.raises(HTTPException) as e:
        await dep(_req(u.id), db)  # 12 > 8 → 503
    assert e.value.status_code == 503
    assert e.value.detail["code"] == "ai_budget_exhausted"


async def test_global_cap_blocks_regardless_of_user_headroom(db, monkeypatch):
    monkeypatch.setattr(settings, "ai_global_daily_calls", 8)
    monkeypatch.setattr(settings, "ai_daily_calls_per_user", 100000)
    # Sistem (planlayıcı) istifadəsi qlobal cap-ı doldurur.
    await budget.record_usage(db, "scheduler.x", 8, user_id=None)
    await db.commit()
    budget._clear_caches()
    u = await _mk_user(db)  # user-in öz büdcəsi boşdur
    dep = budget.ai_budget("chat", weight=4)
    with pytest.raises(HTTPException) as e:
        await dep(_req(u.id), db)
    assert e.value.status_code == 503


async def test_scheduler_usage_counts_globally(db):
    await budget.record_usage(db, "scheduler.summary", 5, user_id=None)
    await db.commit()
    budget._clear_caches()
    assert await budget.global_daily_used(db) == 5


async def test_kill_switch_takes_effect_without_restart(db, monkeypatch):
    monkeypatch.setattr(settings, "ai_global_daily_calls", 100000)
    u = await _mk_user(db)
    dep = budget.ai_budget("chat", weight=1)
    await dep(_req(u.id), db)  # işləyir

    await budget.set_flag(db, "ai_enabled", "false", by="admin")
    await db.commit()
    with pytest.raises(HTTPException) as e:
        await dep(_req(u.id), db)  # kill switch → 503 (restart YOX)
    assert e.value.detail["code"] == "ai_disabled"

    await budget.set_flag(db, "ai_enabled", "true")
    await db.commit()
    await dep(_req(u.id), db)  # yenidən işləyir


async def test_anonymous_no_user_still_counts_global(db, monkeypatch):
    # user_id yoxdur (state boş) → per-user yoxlanmır, amma qlobal sayılır + yazılır.
    monkeypatch.setattr(settings, "ai_global_daily_calls", 100000)
    dep = budget.ai_budget("market_brief", weight=2)
    await dep(_req(user_id=None), db)
    total = await db.scalar(select(func.coalesce(func.sum(AiUsage.weight), 0)))
    assert total == 2
