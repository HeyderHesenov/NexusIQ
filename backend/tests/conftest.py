"""Test infrastrukturu — REAL Postgres test DB (SQLite YOX).

Niyə real Postgres: NUMERIC NaN/Infinity müqayisə semantikası, JSONB, ON DELETE
CASCADE, SELECT FOR UPDATE, CHECK(email=lower(email)) — SQLite Postgres-in qırdığı
testləri keçərdi. Test DB `nexusiq_test` (TEST_DATABASE_URL ilə override).

Sxem `alembic upgrade head` ilə qurulur (create_all YOX → migrasiyalar da test altında).
Testlər arası TRUNCATE ... CASCADE.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _test_url() -> str:
    env = os.getenv("TEST_DATABASE_URL")
    if env:
        return env
    head, _, _name = settings.database_url.rpartition("/")
    return f"{head}/nexusiq_test"


TEST_URL = _test_url()


def _maint_url() -> str:
    head, _, _name = TEST_URL.rpartition("/")
    return f"{head}/postgres"


async def _ensure_database() -> None:
    eng = create_async_engine(_maint_url(), isolation_level="AUTOCOMMIT")
    try:
        async with eng.connect() as c:
            _, _, name = TEST_URL.rpartition("/")
            name = name.split("?")[0]
            exists = await c.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name}
            )
            if not exists:
                await c.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        await eng.dispose()


@pytest.fixture(scope="session")
def _migrated_db() -> str:
    """Test DB-ni yarat + alembic upgrade head (session başına bir dəfə)."""
    asyncio.run(_ensure_database())
    env = {**os.environ, "ALEMBIC_DB_URL": TEST_URL}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=_BACKEND_DIR,
        env=env,
        check=True,
        capture_output=True,
    )
    return TEST_URL


@pytest_asyncio.fixture
async def test_engine(_migrated_db):
    """Function-scope engine + təmiz vərəq (TRUNCATE ... CASCADE)."""
    eng = create_async_engine(TEST_URL)
    async with eng.begin() as c:
        # users CASCADE → identities/sessions/tokens hamısı təmizlənir.
        await c.execute(text("TRUNCATE users CASCADE"))
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(test_engine):
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db(session_factory):
    async with session_factory() as s:
        yield s


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    """AI klientlərini raise-ə çevir — heç bir test pul xərcləməsin."""

    def _boom(*_a, **_k):
        raise RuntimeError("Testdə LLM çağırışı qadağandır")

    monkeypatch.setattr("openai.AsyncOpenAI", _boom, raising=False)
    monkeypatch.setattr("anthropic.AsyncAnthropic", _boom, raising=False)


@pytest.fixture(autouse=True)
def _reset_ratelimit():
    """Modul-səviyyə in-memory state (limiter + budget keşləri) testlər arası sızmasın."""
    from app.core import budget, ratelimit

    store = ratelimit._store
    if hasattr(store, "_hits"):
        store._hits.clear()
        store._next_sweep = 0.0
    budget._clear_caches()
    yield


@pytest_asyncio.fixture
async def client(session_factory, monkeypatch):
    """Real app (ASGITransport) + test DB override + default Origin (CSRF Qat 1 keçir)."""
    from httpx import ASGITransport, AsyncClient

    from app.db.session import get_db
    from app.main import app

    # Auth üçün lazımi secret-lər + ucuz Argon2 (yoxsa hər login ~50-100ms).
    monkeypatch.setattr(settings, "jwt_secret", "test-jwt-secret-long-enough-32chars-000000")
    monkeypatch.setattr(settings, "csrf_secret", "test-csrf-secret-long-enough-000000")
    monkeypatch.setattr(settings, "cookie_secure", False)
    monkeypatch.setattr(settings, "argon2_time_cost", 1)
    monkeypatch.setattr(settings, "argon2_memory_kib", 64)
    monkeypatch.setattr(settings, "argon2_parallelism", 1)

    async def _override():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://localhost:3000",
        headers={"Origin": "http://localhost:3000"},
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def fast_argon2(monkeypatch):
    """Argon2-ni ucuzlaşdır (login/hash testləri sürətli olsun)."""
    monkeypatch.setattr(settings, "argon2_time_cost", 1)
    monkeypatch.setattr(settings, "argon2_memory_kib", 64)
    monkeypatch.setattr(settings, "argon2_parallelism", 1)
