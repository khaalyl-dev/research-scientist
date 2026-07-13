# Sprint 2 — Task: Streamlit UI redesign (white theme)

## Overview

### Objective

Polish Accueil + Recherche into a clean, professional white UI with shared theme tokens, no page icons/emojis, and Streamlit light theme as the default.

| Field | Value |
|--------|-------|
| **Owner** | Khalil |
| **Estimate** | 2 hours |
| **User Story** | US-01 / US-07 (presentation) |
| **Status** | Completed |
| **Depends on** | Recherche page + agent streaming (Tasks 03–04) |

---

## Description

The Recherche pipeline UI worked functionally but looked like a default Streamlit scaffold (emoji nav icons, mixed chrome). This task adds a shared visual system and a white default theme so demos read as a product, not a prototype.

### Key Responsibilities

- Shared CSS theme module (`inject_theme()`, `hero()`)
- White / light surfaces as default (`.streamlit/config.toml` + CSS)
- Accueil brand-first hero + concise panels
- Recherche hero, metric cards, agent checklist dots, stream blocks
- Remove Streamlit page / nav icons (invalid non-emoji icons crashed `st.Page`)

### Why This Matters

Demo credibility: investors and partners see the research pipeline through the UI first. A consistent light theme and clear hierarchy make live agent progress easier to follow.

---

## Implementation

### File Structure

| File | Action | Description |
|------|--------|-------------|
| `app/components/theme.py` | Created | CSS tokens, `inject_theme()`, `hero()` |
| `.streamlit/config.toml` | Created | Light theme defaults (`base = "light"`, white background) |
| `app/main.py` | Modified | No `page_icon` / `st.Page` icons |
| `app/views/accueil.py` | Modified | Hero + white panels |
| `app/views/recherche.py` | Modified | Themed form, checklist, stream blocks, results |
| `app/components/agent_progress.py` | Modified | HTML checklist steps (`.ars-step`) instead of emoji status |

### Theme defaults

```toml
# .streamlit/config.toml
[theme]
base = "light"
primaryColor = "#0f766e"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f4f6f8"
textColor = "#111827"
font = "sans serif"
```

`config.toml` requires a **full Streamlit restart** (not just browser refresh).

### Run

```bash
streamlit run app/main.py
```

---

## Acceptance Criteria

- [x] No emoji / invalid icons on `st.Page` or `set_page_config`
- [x] Light/white theme is the default via `.streamlit/config.toml`
- [x] Accueil and Recherche call `inject_theme()`
- [x] Agent checklist uses styled steps (no emoji status glyphs)
- [x] UI remains usable on desktop and narrow widths

---

## Notes

- Do **not** commit `.env` (API keys). Keep secrets local only.
- Custom CSS complements Streamlit’s theme; both should stay light/white aligned.
