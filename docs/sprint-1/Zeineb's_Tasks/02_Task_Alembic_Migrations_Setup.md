# Task 2: Alembic Migrations Setup

## Overview

**Objective:**
Configure Alembic to manage database schema versioning through reversible, version-controlled migrations.

**Related User Stories:** —
**Owner:** Zeineb
**Status:** Completed

## Description

Alembic was integrated with SQLAlchemy to manage database schema changes in a safe and structured way, replacing the `init_db()` shortcut used during initial development.

It provides:

- Version-controlled database schema changes
- Automated migration generation via diffing against the ORM models
- Database upgrade and rollback support
- Safe schema evolution without manual SQL

## Implementation

### Alembic Configuration (`alembic.ini`)

- `script_location` set to `src/db/migrations`
- No hardcoded database URL — the `sqlalchemy.url` field is intentionally left blank in `alembic.ini` and set dynamically at runtime (see below), so the configuration file and `.env` can never drift out of sync.

### Migration Environment (`src/db/migrations/env.py`)

Implemented:

- Loading `SQLITE_PATH` from `.env` via `python-dotenv`, and building the database URL from it — the same variable `src/db/database.py` uses, so both layers always point at the same file.
- Pointing Alembic's `target_metadata` at `Base.metadata` from `src/db/models.py`, enabling `--autogenerate` to diff the live database against the ORM models and write migration scripts automatically.
- `render_as_batch=True`, set in both the online and offline migration functions. This is required specifically for SQLite: unlike Postgres, SQLite does not support most `ALTER TABLE` operations natively (no drop column, no column type changes). Batch mode works around this by rebuilding the table under the hood. Omitting this flag would cause any future migration that alters a column to fail silently on SQLite while appearing to work in testing against other databases.

### Initial Migration

Created `src/db/migrations/versions/edca06fe3eb4_initial_schema.py`:

- `upgrade()` creates all four tables (`sessions`, `sources`, `claims`, `contradictions`) in foreign-key-safe dependency order.
- `downgrade()` drops them in reverse order.

## Testing

Validated directly against a real SQLite file (not just in-memory):

- `alembic upgrade head` creates all four tables plus Alembic's own `alembic_version` tracking table.
- `alembic downgrade base` fully reverses the migration, leaving only `alembic_version`.
- Re-running `alembic upgrade head` after a downgrade succeeds cleanly, confirming the migration is safely repeatable.

Verification commands:

```bash
alembic upgrade head
python -c "from src.db.database import get_db_session; print('DB migrated')"
```

## Workflow for future schema changes

```bash
# 1. Edit src/db/models.py
# 2. Generate the migration diff
alembic revision --autogenerate -m "describe your change"
# 3. Review the generated file in src/db/migrations/versions/ before applying —
#    autogenerate is not perfect, especially for renames.
# 4. Apply it
alembic upgrade head
```

## Delivered

- `alembic.ini` — Alembic configuration, no hardcoded credentials
- `src/db/migrations/env.py` — migration environment, wired to `.env` and the ORM metadata
- `src/db/migrations/versions/edca06fe3eb4_initial_schema.py` — initial schema migration, upgrade and downgrade both verified

**Status:** Completed
