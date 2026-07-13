# Sprint 2 — Task: Tests d'intégration Planner → Researcher → Extractor

## Overview

### Objective

Prove the Sprint 2 core pipeline handoff with automated tests: **Planner → Researcher → Extractor** produces `sub_queries` → `sources` → `claims` without live network or Groq.

| Field | Value |
|--------|-------|
| **Owner** | Khalil |
| **Estimate** | 2 hours |
| **User Story** | US-02 + US-03 + US-04 |
| **Status** | Completed |
| **Depends on** | Planner, Researcher, Extractor, LangGraph `Send()` |

---

## Description

Unit tests cover each agent in isolation. These **integration** tests wire the real node functions together (and once through `build_graph().invoke`) with injectable / patched fakes so CI stays offline.

```text
query
  → planner_node        → sub_queries (3–5)
  → researcher_node     → sources (dicts)
  → create_extraction_jobs / Send()
  → extractor_node × N  → claims (merged)
```

### What is asserted

1. **Sequential chain** — real `planner_node` → `researcher_node` → N× `extractor_node`
2. **Send() contract** — one job per source; extractor returns only `{"claims": [...]}`
3. **LangGraph invoke** — full graph reaches Teacher stubs with claims linked to source ids
4. **Graceful degradation** — Planner LLM failure still yields fallback sub-queries and sources

---

## Implementation

### File Structure

| File | Action |
|------|--------|
| `tests/integration/test_planner_researcher_extractor.py` | Created |
| `tests/integration/__init__.py` | Created |
| `docs/Sprint2/Khalil's_Tasks/08_Task_Integration_Planner_Researcher_Extractor.md` | Created |

### Run

```bash
pytest tests/integration/test_planner_researcher_extractor.py -q
# or all tests
pytest tests/ -q
```

### Fakes used

| Dependency | Fake |
|------------|------|
| Planner / Extractor LLM | `FakeLLM` / `RoutingLLM` |
| arXiv / Wiki / Scholar / … | `FakeSearchClient` |
| Web search + scraper | async hits + `FakeScraper` |
| SQLite writes | `patch(save_sub_queries/save_source/save_claims)` |

---

## Acceptance Criteria

- [x] Integration tests pass with no API keys / no network
- [x] Handoff `sub_queries → sources → claims` is verified
- [x] Graph-level invoke covers Planner → Researcher → Extractor
- [x] Planner LLM failure path still completes the pipeline

---

## Notes

- FactChecker / Reasoning / Teacher remain stubs; tests only require them to finish the graph.
- Live end-to-end against Groq + arXiv stays a **manual** Streamlit check, not CI.
