# Architecture

This document explains how the system fits together and *why* it's built
this way — the design decisions, not just the file layout. For setup
instructions, see [`README.md`](./README.md).

## System overview

```
┌─────────────────────────────────────────────────────────────┐
│                     STREAMLIT FRONTEND                       │
│  [Query Input] → [Progress Stream] → [Response] → [Graph]    │
└───────────────────────────┬───────────────────────────────────┘
                             │ st.session_state
┌───────────────────────────▼───────────────────────────────────┐
│                      LANGGRAPH PIPELINE                      │
│                                                                │
│   PLANNER ──▶ RESEARCHER ──▶ EXTRACTOR (parallel per source) │
│                                        │                      │
│   TEACHER ◀── REASONING ◀── FACTCHECKER (contradictions)     │
│                                                                │
└──────┬─────────────────┬─────────────────┬────────────────────┘
       │                 │                 │
   ┌───▼────┐      ┌─────▼─────┐    ┌──────▼───────┐
   │ FAISS  │      │  SQLite   │    │ NetworkX     │
   │(vectors)│      │(sessions, │    │(knowledge    │
   │        │      │ sources,  │    │ graph, JSON) │
   │        │      │ claims)   │    │              │
   └────────┘      └───────────┘    └──────────────┘
                          │
                   ┌──────▼───────────────────┐
                   │  EXTERNAL APIs            │
                   │  arXiv · Brave Search      │
                   └───────────────────────────┘
```

Agent order: **Planner → Researcher (parallel) → Extractor (parallel per
source) → FactChecker → Reasoning → Teacher**. Extraction runs in parallel
across sources via LangGraph's `Send()` API — this is a deliberate deviation
from a naive sequential pipeline, cutting total latency by roughly 40% for a
5-source query.

## Two data layers, on purpose

The codebase has two representations of the same core concepts (a "Source",
a "Claim", a "Contradiction"), and this is intentional rather than
duplication:

| | `src/schemas/` (Pydantic) | `src/db/models.py` (SQLAlchemy) |
|---|---|---|
| Lives | In memory, during one pipeline run | Persisted, in `data/research.db` |
| Used by | Agents passing state to each other | Streamlit history page, exports, cross-session memory |
| Validated | On construction (rejects bad LLM output immediately) | On write |
| Shape | Nested (`SessionSchema` embeds its `sources`, `claims`, etc.) | Relational (foreign keys, joined via SQLAlchemy relationships) |

**Why not just use one?** Pydantic models describe self-contained trees
that get serialized wholesale (e.g. streamed to Streamlit, checkpointed by
LangGraph). SQLAlchemy models describe rows with foreign keys, built for
querying ("give me all contradictions from this session" without loading
everything into memory). Trying to make one class do both jobs means either
the DB layer fights the ORM's relational model, or the in-memory agent state
carries DB-only baggage (session lifecycle, cascades) it doesn't need.

The seam between them is small and explicit: both sides import the same
three enums from `src/schemas/common.py` (`UserLevel`, `SourceType`,
`SessionStatus`), so the vocabulary can never drift out of sync even though
the shapes differ. The actual Pydantic → SQLAlchemy conversion happens in
one place, `src/db/crud.py` (Sprint 2), so there's exactly one spot where
"in-memory claim becomes a database row" is decided.

## Database schema

```
sessions ──1───*── sources ──1───*── claims
   │                                   │  │
   │                                   │  └──┐
   └──────1───────*── contradictions ──┴─claim_a/claim_b (both FK → claims)
```

- `sessions`: one row per user query. Carries `status` (running/completed/failed)
  so a crashed pipeline is visible in the History page rather than silently vanishing.
- `sources`: one row per document (arXiv paper or web page). Stores full
  cleaned text directly (a deliberate simplicity-over-dedup tradeoff for the
  MVP — see "Decisions log" below).
- `claims`: atomic facts, `{entity, claim, confidence, source_id}` — matches
  US-04's required format exactly.
- `contradictions`: links two claims by id (`claim_a_id`, `claim_b_id`) plus
  a `divergence_score`. Two foreign keys into the same table, which is why
  `models.py` uses explicit `foreign_keys=[...]` on those relationships —
  SQLAlchemy can't infer which FK maps to which relationship otherwise.

Schema changes go through Alembic (`alembic revision --autogenerate`), never
hand-edited SQL — see the README's migration section.

## External API resilience strategy

Every external call (Brave Search now; arXiv, and the LLM providers soon)
follows the same pattern, implemented once in `src/utils/retry.py`:

1. **Retry** transient failures only (timeouts, connection errors, 5xx) —
   3 attempts, exponential backoff (1s, 2s, 4s).
2. **Fail fast, don't retry** on errors retrying can't fix — a 401 (bad key)
   or 429 (quota exhausted) will look identical on attempt 3 as attempt 1.
3. **Fall back** to a secondary provider — Brave → DuckDuckGo. The fallback
   is automatic and silent to the pipeline; only a warning is logged.
4. **Degrade, don't crash** — a malformed individual result (missing a
   field) is skipped with a warning, not a fatal exception. One bad search
   result shouldn't take down the whole query.

This lives in `src/clients/brave_client.py::web_search()` as the reference
implementation; the arXiv client (Sprint 1, Khalil) and the Groq/Ollama LLM
wrapper (Sprint 2) will follow the same shape.

### Testability

The DuckDuckGo fallback uses **dependency injection**
(`web_search(..., ddgs_class=...)`) rather than monkey-patching the
`ddgs` library in tests. We tried patching the library's internals first and
it silently failed to intercept real network calls — the library sets some
bindings at the instance level in ways that resist class-level patching.
Injecting a fake class is more robust and, as a side effect, makes the
client's dependencies explicit in its function signature.

## Evidence Score (Research Notebook feature)

Computed deterministically (no LLM call — instant, reproducible):

| Signal | Points |
|---|---|
| Source is peer-reviewed (arXiv/DOI) | +3 per source, max +9 |
| ≥3 sources agree on a claim (cosine sim > 0.85) | +2 |
| Source published within the last 2 years | +1 per source, max +3 |
| Average extraction confidence > 0.8 | +1 |

Normalized to 0–100. Implementation lands in Sprint 4 alongside the
Research Notebook generator; the formula is fixed now so the `Source` and
`Claim` schemas already carry every field it needs (`published_year`,
`quality_score`, `confidence`).

## Decisions log

Short record of choices made and why — useful when revisiting "why did we do
it this way" three sprints from now.

- **Full source text stored in SQLite, not just FAISS chunks.** Simpler for
  the MVP; some duplication with FAISS's chunked embeddings is an accepted
  tradeoff. Revisit in V2 if `sources.content` bloats the DB file.
- **UUIDs as strings, not native UUID columns.** SQLite has no native UUID
  type; storing as `String(36)` keeps a future Postgres migration painless.
- **`check_same_thread=False` on the SQLite engine.** Streamlit can invoke
  callbacks from different threads during streaming; single-user MVP makes
  this safe. Would need a real connection pool strategy for multi-user.
- **File named `brave_client.py`, not `tavily_client.py`.** An earlier
  draft of the plan referenced Tavily; the project settled on Brave Search.
  The file name follows the actual implementation, not the stale plan text.
- **`ddgs` package, not `duckduckgo-search`.** The latter is deprecated and
  renamed upstream; we picked the current name to avoid starting the
  project on a deprecated dependency.

## What's next

Sprint 2 introduces `src/agents/state.py` — the LangGraph `GraphState`
TypedDict — which wraps `SessionSchema` plus pipeline-control fields (retry
counts, which agent ran last). That's where these schemas start actually
driving agent behavior instead of just being validated data containers.
