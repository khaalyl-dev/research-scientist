# Sprint 2 — Task: Agent Planner (Query → Sub-queries)

## Overview

### Objective

Implement the Planner Agent that decomposes a natural-language research question into **3–5 focused sub-queries**, identifies preferred source types (`arxiv` / `web`), persists the plan in SQLite, and surfaces it in the Streamlit UI.

| Field | Value |
|--------|-------|
| **Owner** | Khalil |
| **Estimate** | 5 hours |
| **User Story** | US-02 |
| **Status** | Completed |

---

## Description

The Planner Agent is the **first node** in the LangGraph pipeline. It turns one user question into a small set of searchable sub-queries that the Researcher runs in parallel across arXiv and the web.

### Key Responsibilities

- **Query decomposition** — call `LLMClient.generate()` with a dedicated prompt and produce 3–5 distinct, searchable sub-queries.
- **Source-type hints** — identify whether `arxiv`, `web`, or both are most useful for the topic (stored in `state["source_types"]`).
- **Robust JSON parsing** — handle markdown fences, prose wrapping, bare JSON arrays, and malformed output without crashing.
- **Clamp & pad** — never return fewer than 3 or more than 5 sub-queries; pad with deterministic fallbacks when needed.
- **SQLite logging** — persist the sub-query list on the session row (`sessions.sub_queries`).
- **UI visibility** — show sub-queries in a Streamlit expander (US-02 acceptance criterion).
- **Graceful degradation (US-13)** — if Groq and Ollama both fail, fall back to a heuristic 3-query plan and keep the pipeline running.

### Why This Matters

Without the Planner, the Researcher either searches only the raw user string or relies on stub sub-queries. Real decomposition improves coverage (definitions, methods, comparisons, limitations) and is a DoD / US-02 requirement: *“La question est décomposée en 3–5 sous-requêtes affichées dans l'UI.”*

### Pipeline Position

```text
Planner  →  Researcher  →  Extractor (parallel)  →  FactChecker  →  Reasoner  →  Teacher
```

---

## Implementation

### File Structure

| File | Action | Description |
|------|--------|-------------|
| `src/agents/planner.py` | Created | Planner node + JSON parsing + fallback |
| `prompts/planner_prompt.txt` | Created | External LLM prompt template |
| `src/agents/graph.py` | Modified | Wired `planner_node`; renamed node `reasoning` → `reasoner` |
| `src/agents/state.py` | Modified | Added `source_types: list[str]` |
| `src/db/models.py` | Modified | Added `ResearchSession.sub_queries` (Text / JSON) |
| `src/db/crud.py` | Modified | Added `save_sub_queries()` |
| `src/db/migrations/versions/a1b2c3d4e5f6_add_sessions_sub_queries.py` | Created | Alembic migration |
| `app/main.py` | Modified | Expander for Planner sub-queries before search |
| `tests/unit/test_planner.py` | Created | 13 unit tests |

### Core Logic — `planner_node()`

```python
planner_node(state: GraphState, llm_client=None) -> dict
```

1. Reads `query`, `user_level`, and `session_id` from `GraphState`.
2. Builds the prompt from `prompts/planner_prompt.txt` (query + level + min/max bounds).
3. Calls `LLMClient.generate(prompt)` (injectable for tests — same pattern as Extractor / Researcher).
4. Parses the response into `(sub_queries, source_types)` via `parse_planner_response()`.
5. On any LLM exception → heuristic fallback of 3 sub-queries.
6. Calls `save_sub_queries(session_id, sub_queries)` when a session exists.
7. Returns only the keys it owns:

```python
{
    "sub_queries": [...],      # 3–5 strings
    "source_types": [...],     # e.g. ["arxiv", "web"]
    "current_agent": "planner",
    "status": "running",
}
```

### Expected LLM Output Format

```json
{
  "sub_queries": [
    "first focused search query",
    "second focused search query",
    "third focused search query"
  ],
  "source_types": ["arxiv", "web"]
}
```

A bare JSON array of strings is also accepted for robustness.

### Robust Parsing

`_extract_json()` / `parse_planner_response()` handle:

| Input quirk | Behavior |
|-------------|----------|
| Markdown-fenced JSON | Stripped, then parsed |
| Prose around JSON | First `{...}` or `[...]` block extracted |
| Bare `["q1", "q2", "q3"]` | Treated as sub-queries; source types default to both |
| > 5 sub-queries | Clamped to 5 |
| < 3 sub-queries | Padded with fallback suffixes |
| Near-duplicates | Deduped case-insensitively |
| Garbage / empty | Full heuristic fallback (3 queries) |

### Fallback Plan

When the LLM is unavailable or unparseable:

```text
"{query} — overview and definition"
"{query} — key methods and approaches"
"{query} — applications and use cases"
```

### SQLite Persistence (US-02)

- Column: `sessions.sub_queries` (`Text`, nullable) — JSON array string.
- CRUD: `save_sub_queries(session_id, sub_queries)`.
- Migration: `a1b2c3d4e5f6` (revises `edca06fe3eb4`).

```bash
alembic upgrade head
```

### Graph Wiring Notes

- Entry point remains `planner`.
- Node id for the Reasoning stub was renamed from `reasoning` → `reasoner` because LangGraph forbids a node name that collides with a `GraphState` key (`reasoning: str`).

### Streamlit (US-02 expander)

On form submit, `app/main.py`:

1. Calls `planner_node(...)`.
2. Shows an expander: **Sous-requêtes du Planner (N)** with the list + preferred source types.
3. Uses the sub-queries (with the original query) for arXiv search.

---

## Testing

### Unit Tests

`tests/unit/test_planner.py` — 13 tests, fake injectable LLM (no API keys):

| Test | Purpose |
|------|---------|
| `test_parses_clean_json_object` | Happy path |
| `test_handles_markdown_fenced_json` | Real LLM formatting quirk |
| `test_handles_prose_wrapped_json` | Real LLM formatting quirk |
| `test_accepts_bare_json_array` | Alternate LLM shape |
| `test_clamps_more_than_five_to_five` | US-02 upper bound |
| `test_pads_fewer_than_three_to_three` | US-02 lower bound |
| `test_malformed_response_uses_fallback` | US-13 |
| `test_dedupes_near_identical_queries` | Avoid redundant Researcher calls |
| `test_returns_three_to_five_sub_queries` | End-to-end node contract |
| `test_prompt_includes_user_query_and_level` | Prompt wiring |
| `test_llm_failure_falls_back_without_crash` | US-13 |
| `test_db_save_failure_does_not_crash` | Persistence must not break the graph |
| `test_skips_db_save_when_no_session_id` | UI path without a DB session |

```bash
.venv/bin/pytest tests/unit/test_planner.py -v
```

---

## Integration with Existing Components

| Dependency | Role |
|------------|------|
| `LLMClient` (Task 3) | Groq primary + Ollama fallback |
| `GraphState` (Task 1) | Reads `query` / `user_level`; writes `sub_queries` / `source_types` |
| Researcher Agent | Consumes `state["sub_queries"]` (falls back to `query` if empty) |
| `create_session` / `save_sub_queries` | Session lifecycle + US-02 logging |

---

## Acceptance Criteria (US-02)

| Criterion | Status |
|-----------|--------|
| 3 to 5 sub-queries generated | Done |
| Visible in the UI (expander) | Done (`app/main.py`) |
| Logged in SQLite | Done (`sessions.sub_queries`) |

---

## Handoff Notes

### What's Ready

- `planner_node` is the real graph entry agent (stub removed).
- Researcher can keep consuming `list[str]` sub-queries unchanged.
- `source_types` is available on state for later Researcher filtering if desired (currently informational / UI caption).

### Important Notes

- Always inject `llm_client` in unit tests — never hit Groq/Ollama from CI.
- Return dictionaries / plain lists only (msgpack / checkpointing rule from Task 1).
- Do not name LangGraph nodes after `GraphState` keys (`reasoning` was the trap; use `reasoner`).

### How to Try Manually

```bash
# After alembic upgrade head + Streamlit restart:
streamlit run app/main.py
# Enter a question → expander shows 3–5 Planner sub-queries
```

Or via the pipeline entry point:

```python
from src.agents.graph import run_pipeline
result = run_pipeline("What is RAG?", user_level="beginner")
print(result["sub_queries"])
```

---

## Task Completion

### Delivered

- Planner Agent with Groq/Ollama-backed decomposition
- Prompt file under `prompts/`
- 3–5 clamp + heuristic fallback
- SQLite column + migration + CRUD
- Streamlit expander
- Graph wiring + `reasoner` rename
- 13 unit tests

### Verification

```text
.venv/bin/pytest tests/unit/test_planner.py -v
→ 13 passed
```

---

## Final Status

> **Task Completed**
