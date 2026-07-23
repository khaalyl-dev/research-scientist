# Sprint 3 — Task: FactChecker Agent (US-05)

## Overview

### Objective

Detect cross-source contradictions by comparing claim embeddings (cosine > 0.85) and write them into `state["contradictions"]` in the format required by Zeineb’s Reasoning Agent.

| Field | Value |
|--------|-------|
| **Owner** | Khalil |
| **Estimate** | 4 hours |
| **User Story** | US-05 |
| **Status** | Completed |
| **Depends on** | Extractor claims + Embedder/FAISS (Sprint 2) + Zeineb Reasoning contract |

---

## Description

FactChecker runs after Extractor and before Reasoning. It pairs claims from **different sources** that share the same / similar entity and whose claim texts have cosine similarity ≥ **0.85**, then emits contradiction dicts.

### Zeineb contract (do not break)

```python
{
  "claim_a": str,
  "claim_b": str,
  "similarity_score": float,
  "source_a_id": str,
  "source_b_id": str,
  "explanation": str | None,
}
```

Optional extras for DB/UI: `claim_a_id`, `claim_b_id`, `entity`.

### Key Responsibilities

- Use `Embedder.encode` + `cosine_similarity` (injectable for tests)
- Ignore same-source pairs and identical claim text
- Persist via `save_contradiction()` when claim IDs exist
- Never crash the pipeline (US-13)

---

## Implementation

| File | Action |
|------|--------|
| `src/agents/fact_checker.py` | Created |
| `tests/unit/test_fact_checker.py` | Created |
| `src/db/crud.py` | Added `save_final_response` (session hygiene) |

### Run

```bash
pytest tests/unit/test_fact_checker.py -q
```

---

## Acceptance Criteria

- [x] Empty claims → empty contradictions
- [x] High-similarity different-source pairs flagged
- [x] Output matches Reasoning handoff fields
- [x] Unit tests pass offline (FakeEmbedder)

---

## Notes

Zeineb’s `reasoning.py` / `teacher.py` were **not** modified — only consumed via `graph.py`.
