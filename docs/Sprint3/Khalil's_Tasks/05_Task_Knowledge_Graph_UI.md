# Sprint 3 — Task: Knowledge Graph consumer page (pyvis)

## Overview

### Objective

Consume Zeineb’s NetworkX `KnowledgeGraph` (`build_from_claims`, `to_vis_data`, `export_json` / `import_json`) and show an interactive **Graphe** page after a Recherche run.

| Field | Value |
|--------|-------|
| **Owner** | Khalil (UI consumer) — backend by Zeineb |
| **Estimate** | 3 hours |
| **User Story** | US-09 |
| **Status** | Completed |

---

## Description

README assigns Pyvis to Zeineb; her task delivered the NetworkX backend + `to_vis_data()`. This page is the thin Streamlit consumer so Sprint 3 has a visible graph without rewriting her module.

### Flow

1. After Reasoning, `reasoner_node` builds KG from claims → `data/graphs/{session_id}.json`
2. Recherche stores `last_session_id` / `last_claims` in `st.session_state`
3. **Graphe** page loads JSON (or rebuilds from claims) and renders pyvis HTML

| File | Action |
|------|--------|
| `app/views/graphe.py` | Created |
| `app/main.py` | Nav entry `Graphe` |
| `src/agents/graph.py` | Export KG after Reasoning |

### Do NOT touch

- `src/knowledge/graph.py`
- `tests/unit/test_knowledge_graph.py`
- Zeineb Sprint3 docs

---

## Acceptance Criteria

- [x] Graphe page in navigation
- [x] Uses Zeineb `to_vis_data()` / `import_json`
- [x] Empty state guides user to run Recherche first
