# Sprint 2 — Task: Extra research sources (Wikipedia, Scholar, OpenAlex, PubMed)

## Overview

### Objective

Expand the Researcher beyond arXiv + Brave/DuckDuckGo so each investigation draws from Wikipedia, Semantic Scholar, OpenAlex, and PubMed (in parallel), with graceful degradation if any provider fails.

| Field | Value |
|--------|-------|
| **Owner** | Khalil |
| **Estimate** | 4 hours |
| **User Story** | US-03 |
| **Status** | Completed |
| **Depends on** | Researcher agent + SourceSchema |

---

## Description

Previously the Researcher only queried **arXiv** and the **web**. This task adds four more free providers so demos show richer, more diverse evidence:

| Provider | Client | `SourceType` | API key |
|----------|--------|--------------|---------|
| Wikipedia | `wikipedia_client.py` | `wikipedia` | none |
| Semantic Scholar | `scholar_client.py` | `scholar` | optional `SEMANTIC_SCHOLAR_API_KEY` |
| OpenAlex | `openalex_client.py` | `openalex` | optional `OPENALEX_MAILTO` |
| PubMed / NCBI | `pubmed_client.py` | `pubmed` | optional `NCBI_API_KEY` / `NCBI_EMAIL` |

Google Scholar has no official public API; **Semantic Scholar** is used as the academic “Scholar” source (same job: ranked papers + abstracts).

### Key Responsibilities

- New sync clients returning `list[SourceSchema]`, never raising
- Parallel fan-out inside `researcher_node` via `asyncio.gather` + `to_thread`
- Cap total sources (`MAX_TOTAL_SOURCES = 12`) after URL dedupe
- Extend `SourceType` enum + store as VARCHAR (Alembic migration)
- Update Planner prompt allowed `source_types`
- Unit tests with mocked HTTP / injected fakes

---

## Implementation

### File Structure

| File | Action |
|------|--------|
| `src/clients/wikipedia_client.py` | Created |
| `src/clients/scholar_client.py` | Created |
| `src/clients/openalex_client.py` | Created |
| `src/clients/pubmed_client.py` | Created |
| `src/agents/researcher.py` | Extended |
| `src/schemas/common.py` | New enum values |
| `src/db/models.py` | `native_enum=False` string storage |
| `src/db/migrations/versions/b7c8d9e0f1a2_widen_source_type.py` | Migration |
| `prompts/planner_prompt.txt` | Updated source_types |
| `.env.example` | Optional keys documented |
| `tests/unit/test_extra_source_clients.py` | Created |
| `tests/unit/test_researcher.py` | Updated |

### Per-sub-query caps

| Source | Max per sub-query |
|--------|-------------------|
| arXiv | 2 |
| Web | 1 |
| Wikipedia | 1 |
| Scholar | 1 |
| OpenAlex | 1 |
| PubMed | 1 |
| **Total after dedupe** | **12** |

### Migrate local DB

```bash
alembic upgrade head
# or recreate: delete data/research.db then restart the app / init_db
```

### Run tests

```bash
pytest tests/unit/test_researcher.py tests/unit/test_extra_source_clients.py -q
```

---

## Acceptance Criteria

- [x] Wikipedia / Scholar / OpenAlex / PubMed clients exist and degrade to `[]` on failure
- [x] Researcher gathers from all providers in parallel
- [x] Sources tagged with distinct `SourceType` values
- [x] Unit tests pass without live network
- [x] Planner prompt lists the new source types

---

## Notes

- Semantic Scholar may rate-limit (HTTP 429) without an API key — other providers still fill the list.
- OpenAlex prefers a contact email (`OPENALEX_MAILTO`) in the polite pool.
- PubMed is most useful for biomedical queries; empty results on pure CS topics are expected.
