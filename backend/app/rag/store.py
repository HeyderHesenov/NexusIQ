"""Yaddaşda numpy vektor store — cosine top-k axtarış."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def _normalize(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return m / norms


def _cosine(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    q = query / (np.linalg.norm(query) or 1.0)
    return matrix @ q


class VectorStore:
    """Chunk-lar + L2-normalize edilmiş vektorlar; cosine axtarış."""

    def __init__(self, chunks: list[dict], vectors: np.ndarray) -> None:
        self.chunks = chunks
        self.vectors = _normalize(vectors.astype(np.float32))

    def search(self, query_vec: np.ndarray, k: int = 5) -> list[tuple[dict, float]]:
        if not self.chunks:
            return []
        scores = _cosine(query_vec.astype(np.float32), self.vectors)
        idx = np.argsort(-scores)[:k]
        return [(self.chunks[i], float(scores[i])) for i in idx]


def save(path: Path, chunks: list[dict], vectors: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        path,
        vectors=vectors.astype(np.float32),
        chunks=np.array(json.dumps(chunks, ensure_ascii=False)),
    )


def load(path: Path) -> VectorStore | None:
    if not Path(path).exists():
        return None
    data = np.load(path, allow_pickle=False)
    chunks = json.loads(str(data["chunks"]))
    return VectorStore(chunks, data["vectors"])
