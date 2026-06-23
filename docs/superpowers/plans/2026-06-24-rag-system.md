# Real RAG System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace keyword news-search in the AI Assistant with a real vector RAG over a curated finance knowledge base, plus a router that sends simple questions to a cheap RAG path and charts/news-discussion to the existing dual-AI debate.

**Architecture:** Curated markdown knowledge base → `##`-chunked → OpenAI `text-embedding-3-small` → numpy `.npz` store loaded in-process. A GPT router classifies each question (`info` / `chart` / `discussion`); `info` uses a single-GPT RAG answer, the others use the existing GPT+Claude debate now enriched with retrieved chunks. Same NDJSON stream protocol — frontend unchanged.

**Tech Stack:** Python 3.13, FastAPI, OpenAI SDK (chat + embeddings), numpy (already installed). Tests: plain-assert modules run via `python -m tests.test_X` (project convention, no pytest).

## Global Constraints

- Max response latency: 10 seconds.
- Never reveal model/provider/architecture (existing `_GUARD`).
- No secrets in git: `knowledge.npz` and `.env` git-ignored.
- Terse code, no dead code, no over-engineering.
- Tests are plain-assert modules with a `_run()` + `__main__` block, run via `backend/.venv/bin/python -m tests.test_X` (match `tests/test_anomaly.py`).
- Embedding model: `text-embedding-3-small`. Vector store: numpy in-process. Knowledge base authored as curated markdown.
- Run python via `backend/.venv/bin/python` from inside `backend/`.

---

### Task 1: Markdown chunk parser

**Files:**
- Create: `backend/app/rag/__init__.py`
- Create: `backend/app/rag/chunk.py`
- Test: `backend/tests/test_rag_chunk.py`

**Interfaces:**
- Produces: `Chunk` = dict `{"id": str, "title": str, "text": str, "source": str}`; `parse_markdown(text: str, source: str) -> list[Chunk]`; `load_chunks(knowledge_dir: Path) -> list[Chunk]`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_rag_chunk.py
"""RAG chunk parser testləri — xarici sorğusuz.

İşlət: backend/.venv/bin/python -m tests.test_rag_chunk
"""
from __future__ import annotations

from app.rag import chunk

SAMPLE = """# Terms

## P/E nisbəti
Qiymət/qazanc nisbəti. Səhmin bahalığını ölçür.

## RSI
Nisbi güc indeksi. 70+ həddən artıq alınıb.
"""


def test_parse_splits_on_h2() -> None:
    chunks = chunk.parse_markdown(SAMPLE, "terms.md")
    assert len(chunks) == 2, f"gözlənilən 2, alındı {len(chunks)}"


def test_chunk_has_title_and_text() -> None:
    chunks = chunk.parse_markdown(SAMPLE, "terms.md")
    assert chunks[0]["title"] == "P/E nisbəti"
    assert "Qiymət/qazanc" in chunks[0]["text"]
    assert chunks[0]["source"] == "terms.md"


def test_chunk_id_is_unique() -> None:
    chunks = chunk.parse_markdown(SAMPLE, "terms.md")
    ids = [c["id"] for c in chunks]
    assert len(set(ids)) == len(ids)


def test_text_includes_title() -> None:
    # Embedding üçün başlıq mətnə daxil olmalıdır.
    chunks = chunk.parse_markdown(SAMPLE, "terms.md")
    assert "P/E" in chunks[0]["text"]


def _run() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} keçdi.")


if __name__ == "__main__":
    _run()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m tests.test_rag_chunk`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.rag'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/rag/__init__.py
"""RAG: curated finans bilik bazası üzərində vektor axtarış."""
```

```python
# backend/app/rag/chunk.py
"""Markdown bilik fayllarını `##` başlıqlar üzrə chunk-lara bölür."""
from __future__ import annotations

import re
from pathlib import Path

Chunk = dict  # {"id", "title", "text", "source"}

_H2 = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def parse_markdown(text: str, source: str) -> list[Chunk]:
    """Mətni `## başlıq` blokları üzrə chunk-lara bölür.

    Hər chunk-ın mətni başlığı + gövdəni əhatə edir (embedding üçün).
    İlk `##`-dən əvvəlki giriş (məs. `# Terms`) atılır.
    """
    chunks: list[Chunk] = []
    matches = list(_H2.finditer(text))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        slug = re.sub(r"\W+", "-", title.lower()).strip("-")
        chunks.append(
            {
                "id": f"{source}#{i}-{slug}"[:80],
                "title": title,
                "text": f"{title}\n{body}",
                "source": source,
            }
        )
    return chunks


def load_chunks(knowledge_dir: Path) -> list[Chunk]:
    """knowledge_dir-dəki bütün .md fayllarını oxuyub chunk-lara bölür."""
    chunks: list[Chunk] = []
    for path in sorted(knowledge_dir.glob("*.md")):
        chunks.extend(parse_markdown(path.read_text(encoding="utf-8"), path.name))
    return chunks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m tests.test_rag_chunk`
Expected: PASS — `4/4 keçdi.`

- [ ] **Step 5: Commit**

```bash
git add backend/app/rag/__init__.py backend/app/rag/chunk.py backend/tests/test_rag_chunk.py
git commit -m "feat(rag): markdown chunk parser"
git push
```

---

### Task 2: Curated knowledge base content

**Files:**
- Create: `backend/app/rag/knowledge/terms.md`
- Create: `backend/app/rag/knowledge/assets.md`
- Create: `backend/app/rag/knowledge/impact.md`
- Test: `backend/tests/test_rag_knowledge.py`

**Interfaces:**
- Consumes: `chunk.load_chunks` (Task 1).
- Produces: `backend/app/rag/knowledge/` directory of curated markdown. Each file uses `# Title` then repeated `## entry` blocks.

Content is authored by Claude (curated). `terms.md`: ≥40 finance terms (P/E, EPS, RSI, MACD, hedge, liquidity, inflation, CPI, yield curve, beta, volatility, market cap, dividend, short selling, leverage, etc.) each as `## Term` + 2-4 sentence meaning. `assets.md`: each asset class (stocks, indices, forex, commodities, crypto) — what it is and what moves it; reference the NexusIQ asset registry (`app/analytics/assets.py`). `impact.md`: event→asset rules with direction, strength, reason (Fed rate ↑ → DXY ↑ / gold ↓; OPEC cut → oil ↑; high CPI → indices ↓; risk-off → VIX ↑, BTC ↓).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_rag_knowledge.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m tests.test_rag_knowledge`
Expected: FAIL — `assert {...} <= set()` (files missing)

- [ ] **Step 3: Author the knowledge files**

Write `terms.md`, `assets.md`, `impact.md` as curated markdown (format above). Example shape for `terms.md`:

```markdown
# Maliyyə Terminləri

## P/E nisbəti (Qiymət/Qazanc)
Səhmin qiymətinin bir səhmə düşən qazanca nisbəti. Yüksək P/E baha
qiymətləndirməyə və ya yüksək böyümə gözləntisinə işarə edir. Sahə ortalaması
ilə müqayisə edilir.

## RSI (Nisbi Güc İndeksi)
0-100 arası momentum osilatoru. 70+ həddən artıq alınıb (geri dönüş riski),
30- həddən artıq satılıb. Trend gücünü ölçmür, momentumu ölçür.
```

Author ≥40 entries in `terms.md`, full asset-class coverage in `assets.md`, ≥15 event→asset rules in `impact.md`, so total chunks ≥60.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m tests.test_rag_knowledge`
Expected: PASS — `3/3 keçdi.`

- [ ] **Step 5: Commit**

```bash
git add backend/app/rag/knowledge backend/tests/test_rag_knowledge.py
git commit -m "feat(rag): curated finance knowledge base"
git push
```

---

### Task 3: Vector store (numpy cosine)

**Files:**
- Create: `backend/app/rag/store.py`
- Test: `backend/tests/test_rag_store.py`

**Interfaces:**
- Consumes: `Chunk` (Task 1).
- Produces:
  - `save(path: Path, chunks: list[Chunk], vectors: np.ndarray) -> None`
  - `VectorStore` with `.search(query_vec: np.ndarray, k: int = 5) -> list[tuple[Chunk, float]]` (cosine, descending).
  - `load(path: Path) -> VectorStore | None` (returns `None` if file missing).
  - `_cosine(query: np.ndarray, matrix: np.ndarray) -> np.ndarray` (1-D scores).

Vectors stored L2-normalized so cosine = dot product.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_rag_store.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m tests.test_rag_store`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.rag.store'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/rag/store.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m tests.test_rag_store`
Expected: PASS — `4/4 keçdi.`

- [ ] **Step 5: Commit**

```bash
git add backend/app/rag/store.py backend/tests/test_rag_store.py
git commit -m "feat(rag): numpy cosine vector store"
git push
```

---

### Task 4: Embedding + build CLI

**Files:**
- Create: `backend/app/rag/embed.py`
- Create: `backend/app/rag/build.py`
- Modify: `backend/.gitignore` (create if absent) — add `app/rag/knowledge.npz`

**Interfaces:**
- Consumes: `openai_client` (`app/agents/llm.py`), `chunk.load_chunks`, `store.save`.
- Produces:
  - `embed_texts(texts: list[str]) -> np.ndarray` (async, batched, shape `[n, 1536]`).
  - `embed_query(text: str) -> np.ndarray` (async, shape `[1536]`).
  - `KNOWLEDGE_DIR` and `NPZ_PATH` path constants (re-used by Task 5).
  - `build.py` `__main__`: loads chunks, embeds, saves `knowledge.npz`.

No unit test (requires live OpenAI). Verified by running the build CLI manually in Step 3.

- [ ] **Step 1: Write the embedding module**

```python
# backend/app/rag/embed.py
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
```

- [ ] **Step 2: Write the build CLI**

```python
# backend/app/rag/build.py
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
```

- [ ] **Step 3: Git-ignore the artifact and run the build**

Add to `backend/.gitignore` (create the file if it does not exist):

```
app/rag/knowledge.npz
```

Run: `cd backend && .venv/bin/python -m app.rag.build`
Expected: prints `N chunk yükləndi…` then `…knowledge.npz yazıldı ((N, 1536)).` with N ≥ 60.

- [ ] **Step 4: Verify retrieval end-to-end**

Run:
```bash
cd backend && .venv/bin/python -c "
import asyncio, numpy as np
from app.rag import embed, store
async def m():
    st = store.load(embed.NPZ_PATH); assert st
    q = await embed.embed_query('P/E nisbəti nədir?')
    for c,s in st.search(q,3): print(round(s,3), c['title'])
asyncio.run(m())
"
```
Expected: top result title relates to P/E with score > 0.4.

- [ ] **Step 5: Commit**

```bash
git add backend/app/rag/embed.py backend/app/rag/build.py backend/.gitignore
git commit -m "feat(rag): embedding module + build CLI"
git push
```

---

### Task 5: Router + RAG-answer in advisor

**Files:**
- Modify: `backend/app/agents/advisor.py`
- Test: `backend/tests/test_rag_router.py`

**Interfaces:**
- Consumes: `embed.embed_query`, `embed.NPZ_PATH`, `store.load`, existing `_GUARD`, `_classify_finance`, `_detect_chart`, `_synth_messages`, `_gpt_pass`, `_claude_pass`, `_rag_context`.
- Produces:
  - `_parse_route(raw: str) -> str` — maps router JSON to `"info" | "chart" | "discussion"`; defaults to `"discussion"` on bad input. **Pure, unit-tested.**
  - `_route(question: str) -> str` — async GPT classifier wrapping `_parse_route`.
  - `_kb_chunks(question: str, k: int) -> list[dict]` — async; embeds query, searches lazily-loaded module-level store; returns `[]` if store missing or embed fails.
  - `_kb_context(chunks: list[dict]) -> str` — formats chunks as bullet context.
  - `_rag_answer_messages(question, lang, kb_context) -> list[dict]` — single-GPT RAG answer messages.
  - Updated `answer_stream` / `answer` using the router.

- [ ] **Step 1: Write the failing test (pure route parser)**

```python
# backend/tests/test_rag_router.py
"""Router parse testi — GPT sorğusuz (sırf parse məntiqi).

İşlət: backend/.venv/bin/python -m tests.test_rag_router
"""
from __future__ import annotations

from app.agents import advisor


def test_parse_info() -> None:
    assert advisor._parse_route('{"path": "info"}') == "info"


def test_parse_chart() -> None:
    assert advisor._parse_route('{"path": "chart"}') == "chart"


def test_parse_discussion() -> None:
    assert advisor._parse_route('{"path": "discussion"}') == "discussion"


def test_parse_garbage_defaults_discussion() -> None:
    assert advisor._parse_route("not json") == "discussion"


def test_parse_unknown_defaults_discussion() -> None:
    assert advisor._parse_route('{"path": "weather"}') == "discussion"


def _run() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} keçdi.")


if __name__ == "__main__":
    _run()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m tests.test_rag_router`
Expected: FAIL — `AttributeError: module 'app.agents.advisor' has no attribute '_parse_route'`

- [ ] **Step 3: Add router + RAG-answer to advisor.py**

Add imports near the top (after existing imports):

```python
from app.rag import embed, store
```

Add a lazily-loaded module-level store and the new helpers (place above `answer`):

```python
_KB_STORE: store.VectorStore | None = None
_KB_LOADED = False


def _kb() -> store.VectorStore | None:
    """knowledge.npz-i bir dəfə yükləyir (yoxdursa None)."""
    global _KB_STORE, _KB_LOADED
    if not _KB_LOADED:
        _KB_STORE = store.load(embed.NPZ_PATH)
        _KB_LOADED = True
    return _KB_STORE


def _parse_route(raw: str) -> str:
    """Router JSON-unu yola çevirir. Səhvdə təhlükəsiz default: discussion."""
    try:
        path = (json.loads(raw or "{}").get("path") or "").strip().lower()
    except Exception:  # noqa: BLE001
        return "discussion"
    return path if path in {"info", "chart", "discussion"} else "discussion"


async def _route(question: str) -> str:
    """GPT ilə sualı təsnif edir: info | chart | discussion."""
    try:
        resp = await openai_client().chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "Classify a finance question into one path. "
                    "'info' = definition/general explanation answerable from a "
                    "knowledge base. 'chart' = asks to plot/compare two assets or "
                    "show a graph. 'discussion' = analysis/opinion about news or an "
                    "asset's outlook. Reply JSON: {\"path\":\"info|chart|discussion\"}.",
                },
                {"role": "user", "content": question},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=20,
        )
        return _parse_route(resp.choices[0].message.content or "")
    except Exception:  # noqa: BLE001
        return "discussion"


async def _kb_chunks(question: str, k: int = 5) -> list[dict]:
    """Suala uyğun bilik chunk-larını qaytarır (store yoxdursa boş)."""
    st = _kb()
    if st is None:
        return []
    try:
        q = await embed.embed_query(question)
    except Exception:  # noqa: BLE001
        return []
    return [c for c, _ in st.search(q, k)]


def _kb_context(chunks: list[dict]) -> str:
    if not chunks:
        return "(no knowledge base entries)"
    return "\n".join(f"- {c['title']}: {c['text'].split(chr(10), 1)[-1][:300]}" for c in chunks)


def _rag_answer_messages(question: str, lang: str, kb_context: str) -> list[dict]:
    lang_name = LANG_NAMES.get(lang, "Azerbaijani")
    return [
        {"role": "system", "content": _GUARD},
        {
            "role": "user",
            "content": f"Finance knowledge base entries:\n{kb_context}\n\n"
            f"Question: {question}\n\nAnswer clearly in {lang_name} using the "
            "entries above. If they don't cover it, answer from general finance "
            "knowledge. Under ~150 words. Do NOT mention models or systems.",
        },
    ]
```

- [ ] **Step 4: Run the router test to verify it passes**

Run: `cd backend && .venv/bin/python -m tests.test_rag_router`
Expected: PASS — `5/5 keçdi.`

- [ ] **Step 5: Wire the router into `answer_stream` and `answer`**

Replace the body of `answer_stream` (after the `_classify_finance` guard) so that `info` uses the RAG path and `chart`/`discussion` use debate enriched with KB chunks:

```python
async def answer_stream(question: str, lang: str, session: AsyncSession):
    import asyncio

    lang = lang if lang in LANG_NAMES else "az"
    if not has_openai() or not await _classify_finance(question):
        yield {"type": "delta", "text": _REFUSAL[lang]}
        yield {"type": "done", "refused": True}
        return

    path, kb = await asyncio.gather(_route(question), _kb_chunks(question))
    kb_ctx = _kb_context(kb)

    if path == "info":
        stream = await openai_client().chat.completions.create(
            model=settings.openai_model,
            messages=_rag_answer_messages(question, lang, kb_ctx),
            temperature=0.3,
            max_tokens=400,
            stream=True,
        )
        got = False
        async for chunk_ in stream:
            delta = chunk_.choices[0].delta.content if chunk_.choices else None
            if delta:
                got = True
                yield {"type": "delta", "text": delta}
        if not got:
            yield {"type": "delta", "text": _REFUSAL[lang]}
        yield {"type": "done"}
        return

    # chart / discussion → debate (xəbər + bilik konteksti)
    news_ctx, (chart, corr_note) = await asyncio.gather(
        _rag_context(session, question, lang), _detect_chart(question)
    )
    if chart is not None:
        yield {"type": "chart", "chart": chart}
    context = f"{news_ctx}\n\nKNOWLEDGE:\n{kb_ctx}"
    gpt_take, claude_take = await asyncio.gather(
        _gpt_pass(question, context), _claude_pass(question, context)
    )
    stream = await openai_client().chat.completions.create(
        model=settings.openai_model,
        messages=_synth_messages(question, lang, gpt_take, claude_take, corr_note),
        temperature=0.4,
        max_tokens=600,
        stream=True,
    )
    got = False
    async for chunk_ in stream:
        delta = chunk_.choices[0].delta.content if chunk_.choices else None
        if delta:
            got = True
            yield {"type": "delta", "text": delta}
    if not got:
        yield {"type": "delta", "text": _REFUSAL[lang]}
    yield {"type": "done"}
```

Update the non-stream `answer` the same way (router → `info` returns single-GPT RAG answer, else debate with combined context):

```python
async def answer(question: str, lang: str, session: AsyncSession) -> dict:
    import asyncio

    lang = lang if lang in LANG_NAMES else "az"
    if not has_openai():
        return {"answer": _REFUSAL[lang], "refused": True}
    if not await _classify_finance(question):
        return {"answer": _REFUSAL[lang], "refused": True}

    path, kb = await asyncio.gather(_route(question), _kb_chunks(question))
    kb_ctx = _kb_context(kb)

    if path == "info":
        resp = await openai_client().chat.completions.create(
            model=settings.openai_model,
            messages=_rag_answer_messages(question, lang, kb_ctx),
            temperature=0.3,
            max_tokens=400,
        )
        return {"answer": resp.choices[0].message.content or _REFUSAL[lang], "refused": False}

    news_ctx, (_, corr_note) = await asyncio.gather(
        _rag_context(session, question, lang), _detect_chart(question)
    )
    context = f"{news_ctx}\n\nKNOWLEDGE:\n{kb_ctx}"
    gpt_take, claude_take = await asyncio.gather(
        _gpt_pass(question, context), _claude_pass(question, context)
    )
    final = await _synthesize(question, lang, gpt_take, claude_take, corr_note)
    return {"answer": final or _REFUSAL[lang], "refused": False}
```

- [ ] **Step 6: Re-run all RAG tests**

Run:
```bash
cd backend && .venv/bin/python -m tests.test_rag_chunk && .venv/bin/python -m tests.test_rag_knowledge && .venv/bin/python -m tests.test_rag_store && .venv/bin/python -m tests.test_rag_router
```
Expected: every module prints `N/N keçdi.`

- [ ] **Step 7: Commit**

```bash
git add backend/app/agents/advisor.py backend/tests/test_rag_router.py
git commit -m "feat(rag): question router + single-GPT RAG path in advisor"
git push
```

---

### Task 6: End-to-end verification

**Files:** none (verification only).

- [ ] **Step 1: Ensure the store is built**

Run: `cd backend && .venv/bin/python -m app.rag.build`
Expected: `…knowledge.npz yazıldı` (re-run safe).

- [ ] **Step 2: Start the backend**

Run (background): `cd backend && .venv/bin/uvicorn app.main:app --port 8001`
Expected: startup log, no RAG import errors.

- [ ] **Step 3: Test the three paths via the stream endpoint**

Run each and confirm a sensible streamed answer in <10s:
```bash
# info path (definition)
curl -sN -X POST localhost:8001/api/v1/chat/stream -H 'content-type: application/json' \
  -d '{"message":"RSI nədir?","lang":"az"}' | tail -5
# chart path (two assets)
curl -sN -X POST localhost:8001/api/v1/chat/stream -H 'content-type: application/json' \
  -d '{"message":"BTC və qızılı müqayisə et","lang":"az"}' | head -3
# discussion path (news/outlook)
curl -sN -X POST localhost:8001/api/v1/chat/stream -H 'content-type: application/json' \
  -d '{"message":"Fed faiz qərarı bazarlara necə təsir edər?","lang":"az"}' | tail -5
```
Expected: info → definition answer; chart → first line is a `{"type":"chart"...}` event; discussion → analytical answer. Each completes under 10s.

- [ ] **Step 4: Confirm no secret/artifact committed**

Run: `cd /Users/heyderhesenov/Desktop/NexusIQ && git status --porcelain && git check-ignore backend/app/rag/knowledge.npz`
Expected: `knowledge.npz` is ignored; working tree clean.

- [ ] **Step 5: Log to memory**

Create `memory/rag-system.md` (project type) summarizing: numpy in-process RAG over curated `app/rag/knowledge/*.md`, `text-embedding-3-small`, router (`info`→RAG, `chart`/`discussion`→debate), rebuild via `python -m app.rag.build`, `knowledge.npz` git-ignored. Add a one-line pointer in `memory/MEMORY.md`.

---

## Self-Review

**Spec coverage:** RAG path (Task 5), debate path with KB enrichment (Task 5), curated knowledge base authored by Claude (Task 2), numpy store (Task 3), OpenAI embedding (Task 4), router classification (Task 5), latency verification (Task 6), error fallbacks — store-missing/embed-fail/router-fail all default safely (Tasks 3, 5). Same NDJSON protocol preserved (Task 5). All spec sections covered.

**Placeholder scan:** No TBD/TODO; all code blocks are complete. Knowledge content is authored in Task 2 (curation, not a placeholder).

**Type consistency:** `Chunk` dict shape `{id,title,text,source}` consistent across chunk/store/embed. `embed.NPZ_PATH` / `embed.KNOWLEDGE_DIR` defined in Task 4, consumed in Task 5. `_parse_route` returns the same three literals used in `_route` and the `answer*` branches. `store.load` returns `VectorStore | None`, handled in `_kb`.
