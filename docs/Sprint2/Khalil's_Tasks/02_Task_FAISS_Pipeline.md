# Sprint 2 — Task: FAISS Pipeline (Embedding + Index + Save/Load)

## Overview

### Objective

Build the local vector-search pipeline: embed text with sentence-transformers, index vectors in FAISS, and persist/reload indexes per research session.

| Field | Value |
|--------|-------|
| **Owner** | Khalil |
| **Estimate** | 5 hours |
| **Sprint** | 2 — Agents & Semantic Search |
| **Status** | Completed |

---

## Description

The FAISS pipeline is the semantic memory layer used by later agents (especially **FactChecker**, which needs cosine similarity > 0.85 between claims) and by Evidence Score consensus checks.

### Key Responsibilities

- **Embed** — wrap `all-MiniLM-L6-v2` (384-dim) behind a lazy `Embedder`.
- **Index** — store L2-normalized vectors in FAISS `IndexFlatIP` (inner product = cosine).
- **Search** — top-k nearest neighbors with optional `min_score` filter.
- **Save / load** — one index directory per `session_id` under `FAISS_INDEX_PATH`.
- **Chunk** — simple overlapping character chunking for long source text (`src/utils/text.py`).

### Why This Matters

Without FAISS + embeddings, FactChecker cannot compare claims semantically, and the MVP cannot meet the contradiction / consensus metrics from the project plan. The index must survive process restarts (reload from disk, do not rebuild silently).

### MVP Design Choices (from plan)

| Choice | Rationale |
|--------|-----------|
| Index **per session** (not global) | Small files, no cross-session bleed, simpler debugging |
| `IndexFlatIP` + L2-normalize | Exact cosine search; fine for < 10k vectors / session |
| Metadata JSON sidecar | FAISS stores vectors only — ids/texts must live beside the index |
| Lazy model load | Importing `embedder` must not download HuggingFace weights |

---

## Implementation

### File Structure

| File | Action | Description |
|------|--------|-------------|
| `src/embeddings/embedder.py` | Created | `Embedder` + `cosine_similarity()` |
| `src/embeddings/faiss_store.py` | Created | `FaissStore` add / search / save / load |
| `src/embeddings/__init__.py` | Created | Package exports |
| `src/utils/text.py` | Created | `clean_text` + `chunk_text` |
| `tests/unit/test_faiss_store.py` | Created | Unit tests (no model download) |
| `docs/Sprint2/Khalil's_Tasks/02_Task_FAISS_Pipeline.md` | Created | This document |

### Disk Layout

```text
data/faiss_index/{session_id}/
    index.faiss    # FAISS IndexFlatIP
    meta.json      # {dim, count, records: [{id, text, metadata}]}
```

Configured via `.env`:

```text
FAISS_INDEX_PATH=data/faiss_index/
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### Core APIs

```python
from src.embeddings import Embedder, FaissStore, cosine_similarity

embedder = Embedder()  # lazy-loads all-MiniLM-L6-v2
vectors = embedder.encode(["claim A", "claim B"])  # (2, 384), L2-normalized

store = FaissStore(dim=embedder.dimension)
store.add(vectors, ids=["c1", "c2"], texts=["claim A", "claim B"])
store.save("session-uuid")

loaded = FaissStore.load("session-uuid")
hits = loaded.search(embedder.encode("query claim")[0], top_k=5, min_score=0.85)
```

### `Embedder`

- Reads `EMBEDDING_MODEL` from the environment (default `all-MiniLM-L6-v2`).
- Accepts an injectable `model=` for unit tests (no network / no download).
- Always returns `float32` arrays with `normalize_embeddings=True`.

### `FaissStore`

- `add(embeddings, ids, texts=, metadatas=)` — validates shapes, re-normalizes.
- `search(query_embedding, top_k=, min_score=)` → `list[SearchResult]`.
- `save(session_id)` / `FaissStore.load(session_id)` — round-trip safe.
- Raises `FileNotFoundError` if the session index is missing.
- Raises on index/metadata count mismatch after load.

### Text chunking

```python
from src.utils.text import chunk_text

chunks = chunk_text(source_content, chunk_size=500, overlap=50)
```

Used when indexing long scraped pages into FAISS without a full tokenizer.

---

## Testing

`tests/unit/test_faiss_store.py` — fake SentenceTransformer + random vectors (CI-safe):

| Area | Coverage |
|------|----------|
| Text utils | clean / chunk / overlap validation |
| Cosine helper | identical / orthogonal / pairwise matrix |
| Embedder | batch encode, empty list, dimension |
| FaissStore | add/search, save/load roundtrip, filters, errors, clear |
| Integration (fake) | Embedder → Store → save → load → search |

```bash
.venv/bin/pytest tests/unit/test_faiss_store.py -v
```

---

## Handoff Notes

### Consumers

- **FactChecker (Sprint 3)** — use `Embedder.encode` + `cosine_similarity` (or FAISS `min_score=0.85`) on claim pairs.
- **Evidence Score** — consensus criterion (≥ 3 sources, cosine > 0.85) can reuse the same helpers.
- **Researcher / Extractor** — optional: index source chunks per session after retrieval.

### Important Notes

- Prefer `FaissStore.load(session_id)` over rebuilding when an index already exists.
- Keep vectors L2-normalized; do not switch to `IndexFlatL2` without updating FactChecker thresholds.
- First real `Embedder().encode(...)` downloads the model (~80MB) — fine for local/dev; mock in CI.

### Manual smoke check

```bash
.venv/bin/python3.12 -c "
from src.embeddings import Embedder, FaissStore
e = Embedder()
v = e.encode(['RAG uses retrieval', 'fine-tuning updates weights'])
s = FaissStore(dim=e.dimension)
s.add(v, ids=['a','b'], texts=['RAG uses retrieval', 'fine-tuning updates weights'])
s.save('demo')
print(FaissStore.load('demo').search(e.encode('retrieval augmented')[0], top_k=2))
"
```

---

## Task Completion

### Delivered

- Embedder (sentence-transformers wrapper)
- FAISS store with add / search / save / load
- Per-session disk layout under `data/faiss_index/`
- Text chunking utility
- Unit tests without model download
- Task documentation

### Verification

```text
.venv/bin/pytest tests/unit/test_faiss_store.py -v
→ all passed
```

---

## Final Status

> **Task Completed**
