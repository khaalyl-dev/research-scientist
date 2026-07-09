# Task 4: Brave Search Client

## Overview

**Objective:**
Implement the web-search half of source retrieval — searching Brave Search for a query, with automatic fallback to DuckDuckGo if Brave is unavailable or its free quota is exhausted.

**Related User Stories:** US-03, US-13
**Owner:** Zeineb
**Status:** Completed

## Description

The Researcher agent needs two search sources: arXiv for academic papers (Khalil's client) and general web search for everything else. This task covers the web-search client, built to degrade gracefully rather than fail the whole pipeline when an external API has problems.

**Scope boundary:** this client returns search hits only — `{title, url, description}` — not full page content. Fetching and cleaning the actual page text is a separate step (the BeautifulSoup scraper) that runs on the URLs this client returns, so the Researcher agent can cheaply decide which pages are worth scraping before paying that cost on every result.

## Implementation

### `src/clients/brave_client.py`

**`WebSearchResult`** — a lightweight Pydantic model for a single search hit, tagging its origin (`engine: "brave"` or `"duckduckgo"`) for downstream debugging and UI badges.

**`BraveSearchClient.search()`** — calls the Brave Search REST API (`X-Subscription-Token` header, 15-second timeout per US-03's acceptance criteria) and parses results into `WebSearchResult` objects. A malformed individual result is skipped with a warning rather than failing the whole call.

**Error handling**, following the plan's resilience strategy:

- 401/403 raises `BraveAuthError` — bad or missing API key
- 429 raises `BraveQuotaExceededError` — monthly quota exhausted
- 5xx raises `BraveAPIError` — generic server error
- Transient failures (timeouts, connection errors) are retried up to 3 times with exponential backoff via the shared `src/utils/retry.py` decorator

Auth and quota errors are deliberately **not** retried — a 401 or 429 will look identical on the third attempt as the first, so retrying wastes time before the fallback kicks in anyway.

**`web_search()`** — the public entry point. Tries Brave first; on any failure (auth error, quota exceeded, empty results, or retries exhausted after transient errors) falls back to DuckDuckGo automatically via the `ddgs` package. This matches US-13: the user sees a degraded result, never a hard error.

### Shared utilities introduced

Built ahead of schedule since the Brave client needed them immediately, and to avoid duplicating this logic in the arXiv client:

- `src/utils/retry.py` — `with_retry(*exception_types)`, a reusable 3-attempt exponential-backoff decorator
- `src/utils/logger.py` — `get_logger(__name__)`, consistent structured logging format across every module

### Notable implementation decisions

- **File naming:** the project structure originally listed this file as `tavily_client.py`, left over from an earlier draft that used the Tavily API. Renamed to `brave_client.py` to match the actual implementation.
- **Dependency swap:** `duckduckgo-search`, named in the original plan, is deprecated upstream and renamed to `ddgs`. `requirements.txt` uses `ddgs==9.*` instead, to avoid starting the project on an already-deprecated package.
- **Dependency injection for testability:** `web_search()` and `_duckduckgo_search()` accept an optional `ddgs_class` parameter rather than relying on monkey-patching the `ddgs` library internals in tests. Patching `ddgs.DDGS.text` directly was tried first and silently failed to intercept calls — the library binds some behavior at the instance level in ways that resist class-level patching. Injecting a fake class is more robust and makes the client's dependencies explicit in its signature.

## Testing

Covered in Task 6.

## Delivered

- `src/clients/brave_client.py` — Brave Search client with DuckDuckGo fallback
- `src/utils/retry.py` — shared retry decorator
- `src/utils/logger.py` — shared structured logger

**Status:** Completed
