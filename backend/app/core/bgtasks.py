"""Arxa plan task-ları — referansı saxla, istisnanı udma.

Niyə: `asyncio.create_task(...)` nəticəsi saxlanmasa, event loop task-a yalnız
ZƏİF referans tutur (CPython sənədlərinin açıq xəbərdarlığı) — yəni task işin
ortasında zibil yığana düşə bilər. Buradakı fəsad nəzəri deyil:

  - `swr._spawn`: GC olunmuş runner `store["_bg"] = True`-nu HƏMİŞƏLİK ilişdirər
    (`finally` heç vaxt işləməz) → həmin store üçün arxa plan yeniləməsi bir daha
    başlamaz, yəni keş əbədi bayat qalar.
  - `main.lifespan`: prewarm/catchup səssizcə yarımçıq qala bilər.

İkinci problem: çılpaq `create_task` istisnaları udur — task-ın nəticəsi heç vaxt
oxunmadığı üçün xəta yalnız "Task exception was never retrieved" kimi, çox vaxt
gec və qarışıq görünür. Burada `done` callback-i onu birbaşa loglayır.

`img_cache._inflight` bu köməkçiyə EHTİYAC DUYMUR — o, task-ı dict-də saxlayır
(güclü referans) və `add_done_callback` ilə çıxarır. Ona toxunulmur.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Coroutine

logger = logging.getLogger("nexusiq.bg")

# Güclü referanslar — task bitənə qədər GC-dən qorunur.
_tasks: set[asyncio.Task] = set()


def _on_done(task: asyncio.Task) -> None:
    _tasks.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error("Arxa plan task xətası (%s)", task.get_name(), exc_info=exc)


def spawn(coro: Coroutine[Any, Any, Any], *, name: str | None = None) -> asyncio.Task:
    """`create_task` + referans saxlama + istisna loglama."""
    task = asyncio.create_task(coro, name=name)
    _tasks.add(task)
    task.add_done_callback(_on_done)
    return task
