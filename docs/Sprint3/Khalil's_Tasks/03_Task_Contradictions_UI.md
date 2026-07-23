# Sprint 3 — Task: Contradictions UI (claim A vs claim B)

## Overview

### Objective

Surface FactChecker contradictions in Recherche as clear **claim A vs claim B** cards (US-05 UI acceptance).

| Field | Value |
|--------|-------|
| **Owner** | Khalil |
| **Estimate** | 2 hours |
| **User Story** | US-05 |
| **Status** | Completed |

---

## Description

| File | Action |
|------|--------|
| `app/components/citations.py` | `render_contradiction_cards()` |
| `app/views/recherche.py` | Expander when contradictions exist |
| `app/components/agent_progress.py` | Stream narrative shows A/B claims |

Each card shows cosine score, source ids, claim texts, and optional explanation.

---

## Acceptance Criteria

- [x] Metric already counted contradictions
- [x] Expander lists A vs B when `len(contradictions) > 0`
- [x] Streaming FactChecker block mentions claim pairs
