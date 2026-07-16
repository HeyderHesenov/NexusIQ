"""Mövcud korpusa xəbər↔aktiv detected linklərini yazır (birdəfəlik backfill).

Sıfır AI xərci — yalnız deterministik mətn aşkarlaması (asset_map). Şəxsi digest
ship günü data ilə açılsın deyə. İdempotent (təkrar-təhlükəsiz).

İstifadə (backend/ qovluğundan):
    python -m app.analytics.backfill_links
"""
from __future__ import annotations

import asyncio

from app.db.session import engine
from app.services import link_service


async def main() -> None:
    stats = await link_service.backfill_detected()
    print(
        f"✅ Link backfill bitdi — işlənən xəbər: {stats['processed']}, "
        f"yazılan link: {stats['linked']}"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
