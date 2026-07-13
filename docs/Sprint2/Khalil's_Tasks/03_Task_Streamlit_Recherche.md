# Sprint 2 — Task: Page Streamlit « Recherche » (progression par agent)

## Overview

### Objective

Build the main **Recherche** Streamlit page that runs the LangGraph pipeline and shows **live progress agent by agent** (US-07), so the UI never sits on a blank spinner for the whole run.

| Field | Value |
|--------|-------|
| **Owner** | Khalil |
| **Estimate** | 4 hours |
| **User Story** | US-07 (partial) + US-01 / US-02 |
| **Status** | Completed |

---

## Description

Sprint 1 only had a single `app/main.py` that called arXiv/scraper directly. Sprint 2 needs a dedicated Recherche page that:

1. Accepts a question + user level
2. Runs `Planner → Researcher → Extractor → FactChecker → Reasoner → Teacher`
3. Updates a checklist / progress bar after **each** agent finishes
4. Shows intermediate artifacts (sub-queries, source/claim counts)
5. Streams the final Teacher response with `st.write_stream()`

### Key Responsibilities

- **Multipage navigation** — `st.navigation` with Accueil + Recherche (default).
- **Live pipeline streaming** — consume `stream_pipeline()` (`stream_mode="updates"`) instead of blocking `invoke()`.
- **Per-agent checklist** — ⬜ pending / ⏳ running / ✅ done / ❌ error for all six agents.
- **Progress bar** — fraction of agents completed (`PIPELINE_AGENTS`).
- **Intermediate details** — Planner sub-queries, source/claim counts in an expander.
- **Result summary** — metrics + expanders for sub-queries, sources, claims.
- **Progressive final answer** — `st.write_stream(stream_words(...))` (US-07).
- **Session reuse** — store last result in `st.session_state` so Streamlit reruns do not re-run the pipeline.

### Why This Matters

US-07 requires: *indicateur de progression par étape agent* and *pas de page blanche > 5 secondes*. Blocking on `graph.invoke()` alone fails that bar. Streaming node updates via LangGraph keeps the UI alive and makes the multi-agent system demoable.

### Pipeline Position (UI view)

```text
[Form: query + level]
        │
        ▼
 stream_pipeline()  ──▶  checklist + progress + st.status
        │
        ▼
 [Sub-queries · Sources · Claims · Réponse streamée]
```

---

## Implementation

### File Structure

| File | Action | Description |
|------|--------|-------------|
| `app/main.py` | Rewritten | `st.navigation` entry (Accueil + Recherche) |
| `app/__init__.py` | Created | Makes `app` importable as a package |
| `app/views/__init__.py` | Created | Pages package |
| `app/views/accueil.py` | Created | Landing / roadmap |
| `app/views/recherche.py` | Created | Recherche page + pipeline progress |
| `app/components/__init__.py` | Created | Components package |
| `app/components/agent_progress.py` | Created | Checklist / progress helpers + `stream_words` |
| `src/agents/graph.py` | Modified | `stream_pipeline()`, `PIPELINE_AGENTS`, shared initial state |
| `src/agents/__init__.py` | Modified | Export `stream_pipeline` / `PIPELINE_AGENTS` |
| `docs/Sprint2/Khalil's_Tasks/03_Task_Streamlit_Recherche.md` | Created | This document |

### Navigation

```python
st.navigation([
    st.Page(render_accueil_page, title="Accueil", icon="🏠"),
    st.Page(render_recherche_page, title="Recherche", icon="🔍", default=True),
])
```

Run:

```bash
streamlit run app/main.py
```

### Streaming the graph — `stream_pipeline()`

Yields dict events:

| Event | Payload |
|-------|---------|
| `start` | `session_id`, agent id list |
| `agent` | `agent`, `output` (partial), `state` (accumulated) |
| `done` | final `state` |
| `error` | `error`, partial `state` |

Uses LangGraph `stream_mode="updates"`. Claims from parallel Extractor `Send()` branches are accumulated manually in the generator (same semantics as `operator.add` on `GraphState`).

Ordered agents (`PIPELINE_AGENTS`):

1. `planner`
2. `researcher`
3. `extractor`
4. `fact_checker`
5. `reasoner`
6. `teacher`

### Progress UI pieces

| Widget | Role |
|--------|------|
| `st.progress` | Fraction of agents completed |
| Checklist (`agent_progress.py`) | ⬜ / ⏳ / ✅ / ❌ per agent |
| `st.status` | Live log line when each agent finishes |
| Expander « Détails intermédiaires » | Sub-queries + running counts |
| Metrics row | Sub-queries / sources / claims / contradictions |
| `st.write_stream` | Progressive final Teacher answer |

Result payload is stored in `st.session_state["last_pipeline_result"]`.

### Helper module — `app/components/agent_progress.py`

- `init_agent_statuses()` → all `"pending"`
- `render_agent_checklist(statuses, current=)`
- `progress_fraction(statuses)`
- `stream_words(text)` — word generator for `st.write_stream`

---

## Testing

### Manual

```bash
streamlit run app/main.py
```

1. Open **Recherche** (default page)
2. Enter e.g. `What is RAG?`, level Intermédiaire
3. Click **Rechercher**
4. Confirm checklist advances through all six agents
5. Confirm Planner sub-queries appear in the details expander
6. Confirm final response streams in the **Réponse** section
7. Trigger a Streamlit rerun (e.g. resize) — last result should still display without re-running the pipeline

### Dependencies for a live run

- `GROQ_API_KEY` in `.env` (or Ollama with `GROQ_FALLBACK=ollama`) for Planner / Extractor
- Researcher / FactChecker / Reasoner / Teacher may still be stubs — the progress UI still advances through every node

---

## Acceptance Criteria (US-07 / plan)

| Criterion | Status |
|-----------|--------|
| Dedicated Recherche page | Done |
| Progress indicator per agent | Done |
| No long blank wait (stream updates) | Done |
| Sub-queries visible (US-02) | Done |
| Final answer via `st.write_stream` | Done |
| `streamlit run app/main.py` starts | Done |

---

## Issues Encountered & Resolutions

| Issue | Resolution |
|-------|------------|
| Page file named `01_recherche.py` is not importable | Renamed to `recherche.py` and loaded via `st.Page(callable)` |
| `stream_mode="updates"` overwrites claims across parallel Extractors | Manual list concat in `stream_pipeline` for the `claims` key |
| Streamlit rerun would re-execute the whole pipeline | Cache last result in `st.session_state["last_pipeline_result"]` |

---

## Handoff Notes

### What's Ready

- Recherche is the default landing experience for demos
- `stream_pipeline()` is reusable by other pages / CLI smokers
- Checklist labels live in one place: `PIPELINE_AGENTS` in `graph.py`

### Important Notes

- Next related task: fuller **streaming réponse agent par agent** polish if product wants each agent’s prose streamed, not only the final Teacher answer
- When the real async `researcher_node` is wired into the graph, progress events stay the same — only node runtime changes
- Do not put `current_agent` on Extractor returns (parallel `Send()` conflict — Task 1)

---

## Task Completion

### Delivered

- Multipage Streamlit app (Accueil + Recherche)
- Live per-agent progress (checklist + progress bar + status log)
- `stream_pipeline()` generator on the LangGraph graph
- Intermediate artifacts + metrics
- Final answer via `st.write_stream`
- Task documentation

### Verification

```bash
streamlit run app/main.py
# Recherche → submit a query → checklist completes → réponse streamée
```

---

## Final Status

> **Task Completed**
