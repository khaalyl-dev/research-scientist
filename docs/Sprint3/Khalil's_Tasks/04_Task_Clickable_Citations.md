# Sprint 3 — Task: Clickable citations in Streamlit

## Overview

### Objective

Turn Teacher `[source_id]` markers into clickable markdown links using Researcher URLs — without changing Zeineb’s Teacher citation logic.

| Field | Value |
|--------|-------|
| **Owner** | Khalil |
| **Estimate** | 2 hours |
| **User Story** | US-06 (citations UX) |
| **Status** | Completed |

---

## Description

Zeineb’s Teacher already emits `[s1]`-style markers and a Sources list. This task only **post-processes** `final_response` in the UI:

```python
linkify_citations(final_response, sources)
```

| File | Action |
|------|--------|
| `app/components/citations.py` | `linkify_citations`, `build_source_url_map` |
| `app/views/recherche.py` | Render linked markdown |

Existing markdown links `[label](url)` are left untouched.

### Do NOT touch

- `src/agents/teacher.py`
- `prompts/teacher_prompts.py`
- `tests/unit/test_teacher*.py`

---

## Acceptance Criteria

- [x] Known source ids become `[id](url)`
- [x] Unknown ids stay as plain `[id]`
- [x] Teacher module unchanged
