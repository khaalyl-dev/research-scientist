# Sprint 2 — Task 5: Claims Storage in SQLite

## Overview

### Objective

Implement persistent storage for extracted claims by saving them to the SQLite database, enabling session history, exports, and cross-session memory.

| Field | Value |
|-------|-------|
| **Owner** | Zeineb |
| **User Story** | US-04 |
| **Status** | Completed |

## Description

The Claims Storage task adds persistence to the Extractor Agent's output. Without this, claims only exist in memory during a single pipeline run and are lost when the pipeline ends. This task ensures that all extracted claims are saved to the SQLite database, making them available for:

- **History page** — Users can view past research sessions
- **Exports** — Claims can be exported to CSV/JSON
- **Memory Agent (Sprint 4)** — Cross-session learning and contextual answers
- **Contradiction tracking** — Historical contradictions can be reviewed

## Key Responsibilities

- **Session creation** — Ensure a session exists in the database before saving claims
- **Claim persistence** — Save each extracted claim with its source_id, entity, claim text, and confidence score
- **Graceful degradation** — Database failures should not crash the pipeline (US-13)
- **Integration with Extractor** — Save claims immediately after extraction, before returning to the graph

## Why This Matters

Without persistent storage, the system would be a stateless query engine. With storage, it becomes a research companion that remembers what it has learned and can build on past knowledge.

## Implementation

### File Structure

| File | Description |
|------|-------------|
| `src/db/crud.py` | Database CRUD operations (create, read, update) |
| `src/agents/extractor.py` | Modified to save claims after extraction |
| `src/agents/graph.py` | Modified to create session before pipeline runs |

### CRUD Operations

The CRUD module provides functions for all database interactions:

| Function | Purpose |
|----------|---------|
| `create_session()` | Create a new research session in the database |
| `update_session_status()` | Update a session's status (running to completed to failed) |
| `save_source()` | Save a source to the database |
| `save_claims()` | Save extracted claims to the database |
| `save_contradiction()` | Save a detected contradiction |
| `get_session_by_id()` | Retrieve a session with all its relations |

### Integration with Extractor Agent

The Extractor Agent now saves claims immediately after extraction:

- Claims are parsed and validated from the LLM response
- The save function is called with the `session_id` and claims list
- If saving fails, a warning is logged but the pipeline continues
- Claims are still returned to the graph state (in-memory) regardless of database success

This ensures that even if the database is unavailable, the pipeline can still complete.

### Session Creation in Graph

The pipeline entry point now creates a session in the database before the pipeline starts:

- A `session_id` is generated
- The session is created with the query and user level
- The `session_id` is passed through the entire pipeline
- All claims are saved with the correct `session_id`

This fixes the issue where claims could not be saved because the session did not exist in the database.

## Integration with Existing Components

### Extractor Agent Integration

The Extractor Agent now saves claims after successful extraction. The save operation is wrapped in a try-catch block so that database failures do not interrupt the pipeline. A warning is logged if the save fails, but the claims are still returned to the graph state.

### Graph Pipeline Integration

The pipeline entry point now creates a database session before the first agent runs. This ensures that when the Extractor Agent attempts to save claims, the session already exists in the database.

## Testing

### Manual Verification

The storage was tested by:

- Running the pipeline and verifying a session is created in the database
- Extracting claims and verifying they are saved to the database
- Querying the database to confirm session and claims exist

### Verification Commands

The following commands were used to verify the implementation:

- Run the full pipeline to generate a session and claims
- Query the database to retrieve the session by its ID
- Confirm that the session exists and contains the correct query

### Expected Output

The session is found in the database with the correct query and user level.

## Issues Encountered and Resolutions

| Issue | Resolution |
|-------|------------|
| Session not found when saving claims | Created session in the pipeline entry point before the pipeline starts |
| Database writes could fail silently | Added try-catch with logging around all save operations |
| Claims not saved when extraction yields 0 claims | Only call the save function when claims list is non-empty |

## Files Modified and Created

| File | Action | Description |
|------|--------|-------------|
| `src/db/crud.py` | Created | Database CRUD operations for sessions, sources, claims, contradictions |
| `src/agents/extractor.py` | Modified | Added claim saving after extraction |
| `src/agents/graph.py` | Modified | Added session creation in the pipeline entry point |

## Handoff Notes for Khalil

### What is Ready

#### Database CRUD Module

- All database operations are implemented and tested
- The save claims function can be used to persist claims from any agent

#### Extractor Agent

- Claims are saved automatically after extraction
- Database failures do not crash the pipeline

### Important Notes

- Sessions must be created before saving claims — this is now handled in the pipeline entry point
- The save claims function expects `ClaimSchema` objects, not dictionaries
- Database paths are configured via the `SQLITE_PATH` environment variable

## Task Completion

### Delivered

- Full CRUD module for database operations
- Session creation integrated into the pipeline entry point
- Claims saved automatically after extraction
- Graceful degradation on database failures
- Session persistence verified

### Verification

The pipeline completes successfully with a session created in the database. Querying the database by session ID returns the correct session with the expected query.

## Status

**Task Completed**
