# Task 3: Pydantic Schemas for Agent State

## Overview

**Objective:**  
Create Pydantic schemas to define, validate, and manage the data exchanged between agents during a research session.

**Status:** ✅ Completed

---

## Description

Pydantic schemas were implemented to structure and validate the in-memory data flowing through the research pipeline.

They ensure that data exchanged between agents follows a consistent format and that invalid outputs are detected early.

Benefits:

- Automatic data validation
- Strong typing with Python type hints
- Clear validation errors
- Easy serialization for API and UI integration

---

## Implementation

### Common Schemas (`src/schemas/common.py`)

Implemented shared enumerations:

- `UserLevel` - Defines user expertise levels
- `SourceType` - Defines supported source categories
- `SessionStatus` - Tracks research session states

---

### Source Schema (`src/schemas/source.py`)

Implemented `SourceSchema` to validate source information:

- URL validation
- Source metadata handling
- Title, content, type, and publication year validation

---

### Claim Schema (`src/schemas/claim.py`)

Implemented `ClaimSchema` for extracted research facts:

- Entity validation
- Claim text validation
- Confidence score validation (0-1 range)

---

### Contradiction Schema (`src/schemas/contradiction.py`)

Implemented `ContradictionSchema` to represent conflicting information:

- Stores related claims
- Validates similarity scores
- Supports nested claim objects

---

### Session Schema (`src/schemas/session.py`)

Implemented `SessionSchema` as the complete research pipeline state:

- Research query information
- User level
- Sources
- Claims
- Contradictions
- Nested schema validation

---

## Data Layer Separation

Pydantic schemas and SQLAlchemy models serve different purposes:

| Layer | Purpose |
|---|---|
| Pydantic Schemas | In-memory data validation and agent communication |
| SQLAlchemy Models | Database persistence and relational data storage |

This separation improves maintainability by keeping pipeline state management independent from database storage.

---

## Testing

Validated:

✅ Valid data passes schema validation  
✅ Invalid confidence values are rejected  
✅ Invalid years are rejected  
✅ Nested session schemas work correctly  

Verification:

```bash
python -c "from src.schemas.claim import ClaimSchema; print('Schemas OK')"

python -c "from src.schemas.session import SessionSchema; print('Session OK')"

Delivered

✅ src/schemas/common.py - Shared enums
✅ src/schemas/source.py - Source validation schema
✅ src/schemas/claim.py - Claim validation schema
✅ src/schemas/contradiction.py - Contradiction schema
✅ src/schemas/session.py - Complete research session state schema
✅ Validation tests for all schemas

Status: ✅ Completed
