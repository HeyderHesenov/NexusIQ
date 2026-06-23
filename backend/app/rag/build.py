"""Bilik bazasını embed edib knowledge.npz qurur.

İşlət: backend/.venv/bin/python -m app.rag.build
"""
from __future__ import annotations

import asyncio

from app.rag import chunk, embed, store


async def main() -> None:
    chunks = chunk.load_chunks(embed.KNOWLEDGE_DIR)
    print(f"{len(chunks)} chunk yükləndi, embed olunur…")
    vectors = await embed.embed_texts([c["text"] for c in chunks])
    store.save(embed.NPZ_PATH, chunks, vectors)
    print(f"{embed.NPZ_PATH} yazıldı ({vectors.shape}).")


if __name__ == "__main__":
    asyncio.run(main())
