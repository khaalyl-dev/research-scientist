# Task 6: Unit Tests — Brave Search Client

## Overview

**Objective:**
Provide automated test coverage for the Brave Search client, verifying both its happy path and every failure/fallback mode, without depending on real network access or API keys.

**Related User Stories:** US-03, US-13
**Owner:** Zeineb
**Status:** Completed (Brave Search client — arXiv client tests owned by Khalil)

## Description

The plan's Sprint 1 backlog groups arXiv and Brave Search client tests under a single task. This document covers the Brave Search half; the arXiv client and its tests are Khalil's deliverable (`tests/unit/test_arxiv_client.py`).

A hard requirement for this suite: it must run identically in CI, with zero API keys configured and zero internet access. This shaped the two main testing decisions below.

## Implementation

### Test configuration (`pyproject.toml`)

Added `[tool.pytest.ini_options]` with `asyncio_mode = "auto"`, since the Brave client's core functions (`search`, `web_search`) are `async`. This requires the `pytest-asyncio` plugin to be installed — it is pinned in `requirements.txt` as `pytest-asyncio==0.24.*`.

### Shared fixtures (`tests/unit/conftest.py`)

- **`make_mock_response()`** — builds a fake HTTP response object exposing only what the client reads (`status_code`, `.json()`, `.raise_for_status()`), used to simulate every Brave API status code without a real HTTP call.
- **`FakeDDGS`** — a drop-in fake for the `ddgs.DDGS` class, injected via the client's `ddgs_class` parameter (see Task 4). This exists because monkey-patching `ddgs.DDGS.text` directly was attempted first and did not reliably intercept calls; dependency injection avoids fighting the third-party library's internals.

### Test suite (`tests/unit/test_brave_client.py`)

Seventeen tests, organized into three groups:

**`TestBraveSearchClient`** — the Brave call in isolation:

- Successful search parses results correctly and respects the `count` limit
- A malformed individual result (missing a required field) is skipped without raising
- HTTP 401 raises `BraveAuthError`, 429 raises `BraveQuotaExceededError`, 5xx raises `BraveAPIError` — verified as distinct exception types, since callers react differently to each
- A missing API key raises `BraveAuthError` before any HTTP call is made
- A timeout on the first attempt followed by success on the second confirms the retry decorator actually retries, not just catches
- Persistent timeouts confirm the client gives up after exactly three attempts, matching the plan's retry policy

**`TestWebSearchFallback`** — the public `web_search()` entry point:

- A successful Brave search does not invoke DuckDuckGo at all (verified with a fake that raises if called)
- Quota exceeded, missing API key, empty Brave results, and persistent timeouts all correctly trigger the DuckDuckGo fallback
- A malformed DuckDuckGo result is skipped without raising, mirroring the Brave-side behavior

**`TestWebSearchResultSchema`** — schema validation:

- An invalid URL is rejected at construction
- A minimal valid result is accepted with correct defaults

## A defect found and fixed during test-writing

The initial fallback logic in `web_search()` only caught `RetryError` when deciding whether to fall back to DuckDuckGo. In practice, `tenacity`'s `reraise=True` setting re-raises the *original* exception after retries are exhausted (for example, a raw `httpx.TimeoutException`), not a wrapped `RetryError`. This meant a persistently unreachable Brave API would have crashed the pipeline instead of falling back, directly contradicting US-13. The test `test_falls_back_after_repeated_timeouts` caught this; the fix was to also catch `httpx.HTTPError` in the fallback's exception handling.

## Results

- 17 tests, all passing
- 99% line coverage on `src/clients/brave_client.py` (the single uncovered line is the default real-`ddgs`-import branch, which by design never executes in tests since a fake class is always injected)
- Zero real network calls; zero dependency on API keys

Verification command:

```bash
pytest tests/unit/test_brave_client.py -v
pytest --cov=src.clients.brave_client --cov-report=term-missing tests/unit/test_brave_client.py
```

## Delivered

- `pyproject.toml` — pytest/asyncio configuration
- `tests/unit/conftest.py` — shared fixtures (`make_mock_response`, `FakeDDGS`)
- `tests/unit/test_brave_client.py` — 17 tests covering success, all error codes, retry behavior, and every fallback trigger
- `requirements.txt` — `pytest-asyncio==0.24.*` added as a required test dependency

**Status:** Completed
