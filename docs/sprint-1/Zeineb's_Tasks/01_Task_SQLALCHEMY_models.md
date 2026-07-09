# Task 1: SQLAlchemy Models Setup

## Overview

**Objective:**
Implement the SQLAlchemy ORM layer to store and manage research data in a SQLite database.

**Related User Stories:** US-02, US-04
**Owner:** Zeineb
**Status:** Completed

## Description

Implemented the database models required for managing research sessions, sources, extracted claims, and detected contradictions using SQLAlchemy ORM (2.0 typed style).

SQLAlchemy enables interaction with database entities through Python objects while providing relationship management, type safety, and database portability. The 2.0 `Mapped` / `mapped_column` style was used specifically for autocomplete support and mypy type-checking, which matters for a two-person team moving fast across the same codebase.

## Implementation

### Models (`src/db/models.py`)

Implemented four ORM models:

- **`ResearchSession`**: Stores the user's research query, personalization level, and session lifecycle status (`running` / `completed` / `failed`).
- **`Source`**: Represents a document (arXiv paper or web page) linked to a session. Stores the full cleaned text directly in SQLite, along with type, URL, publication year, and a quality score.
- **`Claim`**: Stores extracted facts from a source, in the format `{entity, claim, confidence, source_id}`.
- **`Contradiction`**: Tracks a detected disagreement between two claims, referenced via `claim_a_id` and `claim_b_id` (both foreign keys into the `claims` table).

Relationships implemented:

```
sessions 1---* sources 1---* claims
   |                            |
   1---* contradictions --------(claim_a / claim_b, both FK -> claims)
```

Cascade delete is configured on `sessions -> sources` and `sessions -> contradictions`, so deleting a session cleans up its dependent rows automatically.

Shared enums (`UserLevel`, `SourceType`, `SessionStatus`) live in `src/schemas/common.py` rather than being defined locally in `models.py`. This keeps the persistence layer and the in-memory agent-state layer (Pydantic schemas, see Task 3) using the exact same vocabulary, so the two layers cannot drift out of sync on allowed values.

### Database Layer (`src/db/database.py`)

Implemented:

- SQLite engine configuration, reading the database path from `SQLITE_PATH` in `.env` (single source of truth, also used by Alembic — see Task 2).
- `check_same_thread=False` on the engine, required because Streamlit can invoke the database from different threads during streaming callbacks. Acceptable for a single-user MVP; would need a proper connection pool for multi-user use.
- `get_db_session()`, a context-managed session factory that guarantees the connection is closed even if an error occurs mid-transaction.
- `init_db()` as a development convenience (`Base.metadata.create_all`) — superseded by Alembic for real schema management, kept only as a fast local sanity check.

## Testing

Validated via a live in-memory SQLite database exercising every relationship end to end:

- Table creation for all four models
- `session.sources`, `source.claims`, and `contradiction.claim_a` / `claim_b` relationship traversal
- Insert and read consistency for a full session graph (one session, one source, two claims, one contradiction)

Verification commands:

```bash
python -c "from src.db.models import Base; print('Models OK')"
python -c "from src.db.database import get_db_session; print('DB OK')"
```

## Delivered

- `src/db/models.py` — four ORM models with relationships
- `src/db/database.py` — engine and session factory
- `src/schemas/common.py` — shared enums used by both this layer and the Pydantic schemas

**Status:** Completed
