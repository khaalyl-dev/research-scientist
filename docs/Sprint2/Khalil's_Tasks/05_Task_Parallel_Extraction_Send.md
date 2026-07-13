# Sprint 2 — Task: Extraction parallèle via `Send()` (LangGraph)

## Overview

### Objective

Fan out the Extractor so **one LangGraph `Send()` job runs per source in parallel**, then merge all claims into `GraphState["claims"]` via the `operator.add` reducer — cutting extraction latency vs sequential processing (~40% for 5 sources per the project plan).

| Field | Value |
|--------|-------|
| **Owner** | Khalil + Zeineb (binôme) |
| **Estimate** | 3 hours |
| **User Story** | US-04 |
| **Status** | Completed |
| **Depends on** | GraphState + Extractor Agent |

---

## Description

LangGraph’s map-reduce pattern:

```text
Researcher
    │
    ▼
create_extraction_jobs()  →  Send("extractor", {source, session_id}) × N
    │
    ├─ Extractor (source 1) ─┐
    ├─ Extractor (source 2) ─┼─▶ claims merged with operator.add
    └─ Extractor (source N) ─┘
              │
              ▼
         FactChecker
```

### Key Responsibilities

- Emit **one `Send()` per source** after the Researcher
- Pass only `{source: dict, session_id}` into each Extractor branch (not full `GraphState`)
- Normalize Pydantic `SourceSchema` → `dict` before `Send`
- Route **directly to FactChecker** when there are zero sources (empty fan-out must not stall)
- Keep Extractor returns limited to `{"claims": [...]}` (no `current_agent`)
- Prove merge behaviour with unit/integration tests

---

## Implementation

### File Structure

| File | Action | Description |
|------|--------|-------------|
| `src/agents/graph.py` | Hardened | `create_extraction_jobs` / `dispatch_to_extractors`, empty-source path |
| `src/agents/extractor.py` | Doc fix | Points at the real fan-out helper name |
| `tests/unit/test_parallel_extraction.py` | Created | Send fan-out + merge + empty-source tests |
| `docs/Sprint2/Khalil's_Tasks/05_Task_Parallel_Extraction_Send.md` | Created | This document |

### `create_extraction_jobs(state)`

```python
# N sources → N parallel Extractor tasks
[Send("extractor", {"source": source_dict, "session_id": ...}), ...]

# 0 sources → skip extraction
"fact_checker"
```

Wired as:

```python
builder.add_conditional_edges(
    "researcher",
    create_extraction_jobs,
    ["extractor", "fact_checker"],
)
builder.add_edge("extractor", "fact_checker")
```

Alias: `dispatch_to_extractors = create_extraction_jobs` (name used in Extractor docs).

### Claim merging

`GraphState.claims` is declared as:

```python
claims: Annotated[list[ClaimSchema], operator.add]
```

Each parallel branch returns only new claims; LangGraph concatenates them. `stream_pipeline()` mirrors that concat when accumulating UI state.

---

## Testing

```bash
.venv/bin/pytest tests/unit/test_parallel_extraction.py -v
```

| Test | Purpose |
|------|---------|
| `test_one_send_per_source` | Fan-out cardinality + payload shape |
| `test_empty_sources_routes_to_fact_checker` | No stall on empty list |
| `test_model_dump_sources_are_normalized_to_dicts` | Pydantic → dict for Extractor |
| `test_three_parallel_extractors_merge_claims` | 3×2 claims → 6 in final state |
| `test_zero_sources_skips_extractor_without_stall` | End-to-end empty path completes |

---

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| One Extractor instance per source via `Send()` | Done |
| Claims merged across parallel branches | Done |
| Empty sources do not hang the graph | Done |
| Extractor payload is a dict source | Done |
| Tests cover fan-out + merge | Done |

---

## Handoff Notes

- Real Researcher must return sources as dicts (`.model_dump()`) or rely on the fan-out normalizer
- Never return `current_agent` from `extractor_node` under parallel `Send()`
- Streamlit already streams one Extractor narrative per `Send()` completion (Task 04)

---

## Final Status

> **Task Completed**
