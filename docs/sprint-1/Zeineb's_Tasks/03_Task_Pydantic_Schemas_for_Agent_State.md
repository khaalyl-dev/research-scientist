# Task 3: Pydantic Schemas for Agent State

## Overview

**Objective:**
Define the in-memory data schemas that will flow between agents as LangGraph's shared pipeline state, validated independently of the persistence layer.

**Related User Stories:** US-01, US-04, US-05, US-06
**Owner:** Zeineb
**Status:** Completed

## Description

While `src/db/models.py` (Task 1) defines how research data is *persisted*, agents need a lighter, validated representation to pass data *between each other* during a single pipeline run — before, or instead of, anything being written to the database.

Four Pydantic models were implemented, each mirroring one of the SQLAlchemy models but shaped for in-memory use: nested rather than relational, cheap to copy, and JSON-serializable for streaming and LangGraph checkpointing.

## Why a separate layer from the database models

| | Pydantic schemas (`src/schemas/`) | SQLAlchemy models (`src/db/models.py`) |
|---|---|---|
| Lives | In memory, during one pipeline run | Persisted, in `data/research.db` |
| Used by | Agents passing state to each other | History page, exports, cross-session memory |
| Validated | On construction | On write |
| Shape | Nested (a session embeds its sources, claims, etc.) | Relational (foreign keys, SQLAlchemy relationships) |

Forcing a single class to serve both purposes means either the database layer fights the ORM's relational model, or the in-memory agent state carries database-only concerns (session lifecycle, cascade rules) that agents do not need. The two layers share their vocabulary through `src/schemas/common.py` (see Task 1), so they cannot drift apart on allowed values even though their shapes differ.

## Implementation

### `src/schemas/source.py` — `SourceSchema`

Represents a document found by the Researcher agent. Validates `url` as an `HttpUrl`, constrains `published_year` to a sane range, and requires non-empty `content`. Carries its own `id` (not a database foreign key) so downstream agents can reference "which source did this claim come from" while everything is still in memory.

### `src/schemas/claim.py` — `ClaimSchema`

Matches US-04's required format exactly: `{entity, claim, confidence, source_url}`. Also carries `source_id` for reliable in-memory linking (URL string comparison is unreliable — trailing slashes, tracking parameters). Confidence is constrained to `0.0–1.0`; an `is_low_confidence` property flags claims below 0.5 for exclusion by the Teacher agent, per the plan's extraction-quality risk mitigation.

### `src/schemas/contradiction.py` — `ContradictionSchema`

Embeds the two full `ClaimSchema` objects (not just their ids), so the UI can render "claim A (source X) vs claim B (source Y)" (US-05) without a separate lookup. Carries a `divergence_score` and an optional LLM-generated `explanation`.

### `src/schemas/session.py` — `SessionSchema`

The top-level container for one research session's in-memory state — the closest existing structure to what will become LangGraph's `GraphState` TypedDict in Sprint 2. Holds `sub_queries` (from the Planner), and progressively-filled `sources`, `claims`, and `contradictions` lists, plus `final_response` and `evidence_score` once the Teacher agent completes. A `mark_completed()` helper centralizes the three-field update (response, score, status, timestamp) that closes out a session.

## Testing

Validated by constructing a full in-memory session end to end — sub-queries, two sources, two claims, one contradiction, then marking it completed — and confirming:

- All nested relationships resolve correctly (`session.claims`, `contradiction.claim_a`, etc.)
- JSON serialization succeeds (`model_dump_json()`), required for LangGraph streaming/checkpointing
- Validation genuinely rejects invalid data: a claim with `confidence=1.5` and a source with a malformed URL both raise `ValidationError` immediately at construction, rather than surfacing as an unexplained failure several agents downstream

## Delivered

- `src/schemas/common.py` — shared enums (`UserLevel`, `SourceType`, `SessionStatus`)
- `src/schemas/source.py` — `SourceSchema`
- `src/schemas/claim.py` — `ClaimSchema`
- `src/schemas/contradiction.py` — `ContradictionSchema`
- `src/schemas/session.py` — `SessionSchema`

**Handoff note for Sprint 2:** `src/agents/state.py` (the LangGraph `GraphState` TypedDict) should wrap `SessionSchema` plus pipeline-control fields (retry counts, last agent run). `SessionSchema` already carries every field the pipeline needs, so that step is expected to be plumbing rather than new schema design.

**Status:** Completed
