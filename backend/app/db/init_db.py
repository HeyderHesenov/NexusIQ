"""Cədvəlləri yaradır + kateqoriyaları seed edir.

İstifadə (backend/ qovluğundan):
    python -m app.db.init_db
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.constants import CATEGORY_LABELS
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.models import Category  # noqa: F401  (metadata qeydiyyatı üçün)
from app.models import News, NewsAsset, Source  # noqa: F401


async def create_tables() -> None:
    """Bütün cədvəlləri yaradır (yoxdursa)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_categories() -> None:
    """3 əsas kateqoriyanı əlavə edir (idempotent)."""
    async with AsyncSessionLocal() as session:
        for slug, label in CATEGORY_LABELS.items():
            exists = await session.scalar(
                select(Category).where(Category.slug == slug.value)
            )
            if exists is None:
                session.add(Category(slug=slug.value, label=label))
        await session.commit()


async def main() -> None:
    await create_tables()
    await seed_categories()
    print("✅ Cədvəllər yaradıldı + kateqoriyalar seed edildi.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
