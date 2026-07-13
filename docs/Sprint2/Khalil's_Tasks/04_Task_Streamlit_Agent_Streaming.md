# Sprint 2 — Task: Streaming réponse agent par agent (Streamlit)

## Overview

### Objective

Stream each agent's contribution into the Recherche UI with `st.write_stream()` as soon as that agent finishes — not only the final Teacher answer.

| Field | Value |
|--------|-------|
| **Owner** | Khalil |
| **Estimate** | 3 hours |
| **User Story** | US-07 |
| **Status** | Completed |
| **Depends on** | Page Recherche + `stream_pipeline()` (Task 03) |

---

## Description

Task 03 added a progress checklist and a single streamed Teacher answer at the end. This task completes US-07 by streaming a **narrative block per agent** live in a dedicated “Flux agent par agent” panel:

```text
Planner stream  →  Researcher stream  →  Extractor stream(s)
    →  FactChecker stream  →  Reasoning stream  →  Teacher stream
```

### Key Responsibilities

- Build a markdown narrative for each agent from its partial output + accumulated state
- Call `st.write_stream(...)` immediately when that agent event arrives
- Keep markdown lists readable (line-based streaming for structured notes)
- Persist the streamed transcripts in `st.session_state` for replay on rerun
- Avoid re-streaming the Teacher answer twice in the summary section

### Why This Matters

US-07 explicitly asks for `st.write_stream()` and *no blank page > 5 seconds*. Progress icons alone are not enough for a demo — investors/users should *see* each agent produce content as the pipeline advances.

---

## Implementation

### File Structure

| File | Action | Description |
|------|--------|-------------|
| `app/components/agent_progress.py` | Extended | `build_agent_narrative`, `stream_agent_text`, `stream_lines` |
| `app/pages/recherche.py` | Modified | Live “Flux agent par agent” with per-agent `write_stream` |
| `tests/unit/test_agent_streaming.py` | Created | Narrative + stream helper unit tests |
| `docs/Sprint2/Khalil's_Tasks/04_Task_Streamlit_Agent_Streaming.md` | Created | This document |

### Narrative content by agent

| Agent | Streamed content |
|-------|------------------|
| Planner | Numbered sub-queries + preferred source types |
| Researcher | Source count + first titles/URLs |
| Extractor | Per-batch claims (+ cumulative total) — one stream per `Send()` branch |
| FactChecker | Contradiction count + short notes |
| Reasoner | Reasoning / synthesis text |
| Teacher | Full personalized `final_response` |

### Streaming strategy

- **Structured markdown** (headings / lists) → `stream_lines()` so list items are not split mid-line
- **Prose** → `stream_words()` for a typewriter feel
- Selector: `stream_agent_text(text)` chooses based on newlines / heading markers

### UI flow

1. Checklist + progress bar update (Task 03)
2. For each `event == "agent"` from `stream_pipeline()`:
   - mark agent running
   - `narrative = build_agent_narrative(...)`
   - `st.write_stream(stream_agent_text(narrative))`
   - append to `agent_streams`
3. On completion, show metrics + expanders
4. On Streamlit rerun, replay transcripts statically in an expander (no second animation)

---

## Testing

```bash
.venv/bin/pytest tests/unit/test_agent_streaming.py -v
```

Manual:

```bash
streamlit run app/main.py
```

1. Open **Recherche**
2. Submit a query
3. Confirm each agent section appears progressively under **Flux agent par agent**
4. Confirm Extractor may stream multiple times (one per parallel source)
5. Confirm final Teacher block streams last, then summary metrics appear

---

## Acceptance Criteria (US-07)

| Criterion | Status |
|-----------|--------|
| Uses `st.write_stream()` | Done (per agent) |
| Agent-by-agent response streaming | Done |
| Progress indicator still present | Done (Task 03) |
| No long blank wait | Done |

---

## Handoff Notes

- Narratives are UI-only; agents themselves are unchanged
- When Researcher / Teacher become fully real, the same `build_agent_narrative` paths pick up richer text automatically
- Keep Extractor free of `current_agent` writes (parallel `Send()` rule)

---

## Final Status

> **Task Completed**
