# Task 5: README and Architecture Documentation

## Overview

**Objective:**
Produce project documentation covering setup, usage, and system design, so any team member (or a new contributor) can get the project running and understand how it is built without needing a walkthrough.

**Related User Stories:** —
**Owner:** Zeineb
**Status:** Completed

## Description

Two documents were produced, each with a distinct purpose:

- **`README.md`** — practical, task-oriented. Covers what the system does, how to install and configure it, how to run it, how to test it, and the sprint-by-sprint roadmap.
- **`architecture.md`** — explanatory, design-oriented. Covers how the pieces fit together, the reasoning behind key technical decisions, the database schema, and a running decisions log.

Keeping these separate avoids the common failure mode of a README that is either too shallow to explain design choices or too long to be a usable quick-start guide.

## Implementation

### `README.md`

- Full feature list (what the MVP does, explicitly scoped against what it does not)
- Pipeline overview (the six-agent sequence, in brief)
- Tech stack table with rationale for each choice
- Live project status table, updated as work lands, distinguishing completed from pending components
- Setup instructions: virtual environment, dependency install, `.env` configuration, database initialization
- Test running instructions
- Migration workflow
- Code quality commands (`black`, `ruff`, `mypy`)
- Full project directory structure with inline comments
- Sprint-by-sprint roadmap table (all four sprints, not just the current one)
- Success metrics table, taken directly from the project plan

### `architecture.md`

- ASCII system diagram: Streamlit frontend to LangGraph pipeline to storage layer (FAISS, SQLite, NetworkX) to external APIs
- Explicit agent execution order, noting that extraction is parallelized per source via LangGraph's `Send()` API rather than run sequentially
- A dedicated section explaining why the codebase has two representations of the same concepts (Pydantic schemas versus SQLAlchemy models) rather than one
- Database schema diagram and per-table notes
- The external API resilience strategy (retry, fail-fast, fallback, graceful degradation) as a reusable pattern, with a pointer to the Brave client as the reference implementation
- The Evidence Score formula from the Research Notebook feature, documented ahead of its Sprint 4 implementation so the schemas already carry the fields it needs
- A decisions log: short, dated entries explaining non-obvious choices (UUID storage format, `check_same_thread=False`, file naming corrections against the original plan, the `ddgs` package swap)

## Testing

Documentation was validated against the actual repository state rather than the aspirational plan — every setup command in the README was run and confirmed working (virtual environment creation, dependency install, `.env` configuration, `alembic upgrade head`, `pytest tests/unit/`) before being written down, so a new contributor following it should not hit a command that fails.

## Delivered

- `README.md`
- `architecture.md`

**Status:** Completed
