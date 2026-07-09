# Task 1: SQLAlchemy Models Setup

## Overview

**Objective:**  
Implement the SQLAlchemy ORM layer to store and manage research data in a SQLite database.

**Related User Stories:** US-02, US-04  
**Status:** ✅ Completed

---

## Description

Implemented the database models required for managing research sessions, sources, extracted claims, and detected contradictions using SQLAlchemy ORM.

SQLAlchemy enables interaction with database entities through Python objects while providing relationship management, type safety, and database portability.

---

## Implementation

### Models (`src/db/models.py`)

Implemented four ORM models:

- **ResearchSession**: Stores user research queries and session information.
- **Source**: Represents documents and external sources linked to research sessions.
- **Claim**: Stores extracted facts and confidence scores from sources.
- **Contradiction**: Tracks conflicts between claims.

### Database Layer (`src/db/database.py`)

Implemented:

- SQLite database engine configuration
- Session management with `get_db_session()`
- Streamlit-compatible database connection settings

---

## Testing

**Test File:** `tests/unit/test_models.py`

Validated:

✅ Table creation  
✅ Entity relationships  
✅ Claim contradiction linking  
✅ Cascade deletion behavior  

Verification:

```bash
python -c "from src.db.models import Base; print('Models OK')"
python -c "from src.db.database import get_db_session; print('DB OK')"
