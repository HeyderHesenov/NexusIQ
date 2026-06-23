"""OpenAI text-embedding-3-small ilə chunk/sorğu embed-i."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from app.agents.llm import openai_client

EMBED_MODEL = "text-embedding-3-small"
_BATCH = 128

KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"
NPZ_PATH = Path(__file__).resolve().parent / "knowledge.npz"


async def embed_texts(texts: list[str]) -> np.ndarray:
    """Mətnləri batch-lərlə embed edir → [n, 1536] float32."""
    out: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        batch = texts[i : i + _BATCH]
        resp = await openai_client().embeddings.create(model=EMBED_MODEL, input=batch)
        out.extend(d.embedding for d in resp.data)
    return np.array(out, dtype=np.float32)


async def embed_query(text: str) -> np.ndarray:
    """Tək sorğunu embed edir → [1536] float32."""
    vecs = await embed_texts([text])
    return vecs[0]
