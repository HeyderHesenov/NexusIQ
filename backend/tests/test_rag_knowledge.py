"""Bilik bazasının bütövlük testi — xarici sorğusuz.

İşlət: backend/.venv/bin/python -m tests.test_rag_knowledge
"""
from __future__ import annotations

from pathlib import Path

from app.rag import chunk

KNOWLEDGE = Path(__file__).resolve().parents[1] / "app" / "rag" / "knowledge"


def test_three_files_exist() -> None:
    names = {p.name for p in KNOWLEDGE.glob("*.md")}
    assert {"terms.md", "assets.md", "impact.md"} <= names, names


def test_enough_chunks() -> None:
    chunks = chunk.load_chunks(KNOWLEDGE)
    assert len(chunks) >= 60, f"gözlənilən ≥60 chunk, alındı {len(chunks)}"


def test_no_empty_chunks() -> None:
    for c in chunk.load_chunks(KNOWLEDGE):
        assert len(c["text"]) > 20, f"boş chunk: {c['id']}"


def _run() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} keçdi.")


if __name__ == "__main__":
    _run()
