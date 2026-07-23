# Sprint 3 — Task: Wire FactChecker + Reasoning + Teacher into LangGraph

## Overview

### Objective

Replace Sprint 2 stubs in `graph.py` with the real FactChecker (Khalil) and Zeineb’s Reasoning / Teacher agents so Streamlit produces a real personalized answer.

| Field | Value |
|--------|-------|
| **Owner** | Khalil |
| **Estimate** | 2 hours |
| **User Story** | US-05 + US-06 |
| **Status** | Completed |
| **Depends on** | FactChecker + Zeineb Reasoning/Teacher |

---

## Description

`graph.py` previously defined local stubs that shadowed Zeineb’s modules. This task imports:

- `fact_checker_agent` from `src.agents.fact_checker`
- `reasoning_agent` from `src.agents.reasoning` (via thin `reasoner_node` wrapper)
- `teacher_agent` from `src.agents.teacher` (via thin `teacher_node` wrapper)

Wrappers also:

- Build/export Zeineb’s `KnowledgeGraph` JSON under `data/graphs/{session_id}.json`
- Persist Teacher `final_response` + mark session completed

### Files

| File | Action |
|------|--------|
| `src/agents/graph.py` | Modified — real agents wired |
| `tests/unit/test_parallel_extraction.py` | Updated stubs for new nodes |
| `tests/integration/...` | Patched FC/Reasoning/Teacher for offline CI |

### Do NOT touch

- `src/agents/reasoning.py`
- `src/agents/teacher.py`
- `prompts/teacher_prompts.py`
- Zeineb unit tests / Sprint3 docs

---

## Acceptance Criteria

- [x] Pipeline order: Planner → Researcher → Extractor → FactChecker → Reasoner → Teacher
- [x] No stub final answer in live runs (when Groq is configured)
- [x] Existing parallel-extraction tests still pass
