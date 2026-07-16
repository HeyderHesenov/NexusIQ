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
    det = await link_service.backfill_detected()
    fc = await link_service.backfill_forecast()
    print(
        f"✅ Link backfill bitdi — detected: {det['linked']} "
        f"({det['processed']} xəbər), forecast: {fc['linked']} ({fc['processed']} xəbər)"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
