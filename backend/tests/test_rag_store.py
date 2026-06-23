"""Vektor store cosine axtarış testi — API sorğusuz, sintetik vektorlar.

İşlət: backend/.venv/bin/python -m tests.test_rag_store
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from app.rag import store

CHUNKS = [
    {"id": "a", "title": "neft", "text": "neft qiyməti", "source": "x.md"},
    {"id": "b", "title": "qızıl", "text": "qızıl qiyməti", "source": "x.md"},
    {"id": "c", "title": "bitcoin", "text": "kripto", "source": "x.md"},
]
VECS = np.array(
    [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float32
)


def test_search_returns_nearest() -> None:
    st = store.VectorStore(CHUNKS, VECS)
    q = np.array([0.9, 0.1, 0.0], dtype=np.float32)
    res = st.search(q, k=1)
    assert res[0][0]["id"] == "a", res[0][0]["id"]


def test_search_orders_by_similarity() -> None:
    st = store.VectorStore(CHUNKS, VECS)
    q = np.array([0.0, 0.8, 0.2], dtype=np.float32)
    res = st.search(q, k=3)
    ids = [c["id"] for c, _ in res]
    assert ids[0] == "b" and ids[-1] == "a", ids


def test_save_load_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "k.npz"
        store.save(p, CHUNKS, VECS)
        st = store.load(p)
        assert st is not None
        res = st.search(np.array([0, 0, 1], dtype=np.float32), k=1)
        assert res[0][0]["id"] == "c"


def test_load_missing_returns_none() -> None:
    assert store.load(Path("/nonexistent/k.npz")) is None


def _run() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} keçdi.")


if __name__ == "__main__":
    _run()
