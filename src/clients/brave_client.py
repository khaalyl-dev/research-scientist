"""
Brave Search client — Task: "Client Brave Search (search + fallback DuckDuckGo)"
(US-03, Sprint 1, per MVP_Plan_Final.pdf section 2/4)

Responsibilities:
  - Search the web via the Brave Search API (free tier, 2000 req/month)
  - Raise typed exceptions for auth / quota / server errors so callers
    (and the fallback logic below) can react precisely instead of on a
    generic Exception
  - Retry on network timeouts (tenacity, up to 3 attempts)
  - `web_search()` is the public entry point: try Brave first, and
    transparently fall back to DuckDuckGo (`duckduckgo-search`) if Brave
    is unavailable, unauthenticated, rate-limited, erroring, or returns
    zero results — so the rest of the pipeline never has to care which
    engine actually answered.

Env:
    BRAVE_API_KEY   Read via os.getenv("BRAVE_API_KEY"). If unset, Brave
                    is skipped entirely and DuckDuckGo is used directly.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional, Type, Union

import httpx
from pydantic import BaseModel, HttpUrl, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

try:
    from duckduckgo_search import DDGS
except ImportError:  # pragma: no cover - package name changed to `ddgs` in some envs
    from ddgs import DDGS  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
_REQUEST_TIMEOUT_SECONDS = 10.0


# --------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------- #
class BraveAPIError(Exception):
    """Base class for anything that goes wrong calling the Brave API."""


class BraveAuthError(BraveAPIError):
    """Missing or invalid BRAVE_API_KEY (HTTP 401, or no key at all)."""


class BraveQuotaExceededError(BraveAPIError):
    """Brave's free-tier quota is exhausted (HTTP 429)."""


# --------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------- #
class WebSearchResult(BaseModel):
    title: str
    url: HttpUrl
    engine: str
    description: str = ""
    published_date: Optional[str] = None


# --------------------------------------------------------------------- #
# Brave client
# --------------------------------------------------------------------- #
class BraveSearchClient:
    def __init__(self, api_key: Optional[str], timeout: float = _REQUEST_TIMEOUT_SECONDS) -> None:
        self.api_key = api_key
        self.timeout = timeout

    async def search(self, query: str, count: int = 5) -> list[WebSearchResult]:
        if not self.api_key:
            raise BraveAuthError("BRAVE_API_KEY is not set.")

        response = await self._get(query, count)

        if response.status_code == 401:
            raise BraveAuthError("Invalid Brave API key.")
        if response.status_code == 429:
            raise BraveQuotaExceededError("Brave API quota exceeded.")
        if response.status_code >= 500:
            raise BraveAPIError(f"Brave API server error: {response.status_code}")
        if response.status_code != 200:
            raise BraveAPIError(f"Unexpected Brave API status: {response.status_code}")

        payload = response.json()
        raw_results = payload.get("web", {}).get("results", [])[:count]

        results: list[WebSearchResult] = []
        for item in raw_results:
            try:
                results.append(
                    WebSearchResult(
                        title=item.get("title", ""),
                        url=item["url"],
                        description=item.get("description", ""),
                        published_date=item.get("published_date"),
                        engine="brave",
                    )
                )
            except (KeyError, ValidationError) as exc:
                logger.debug("Skipping malformed Brave result %r: %s", item, exc)
                continue

        return results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(httpx.TimeoutException),
        reraise=True,
    )
    async def _get(self, query: str, count: int) -> httpx.Response:
        headers = {"X-Subscription-Token": self.api_key, "Accept": "application/json"}
        params = {"q": query, "count": count}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await client.get(BRAVE_ENDPOINT, headers=headers, params=params)


# --------------------------------------------------------------------- #
# DuckDuckGo fallback
# --------------------------------------------------------------------- #
def _duckduckgo_search(
    query: str, count: int, ddgs_class: Union[Type[Any], Any]
) -> list[WebSearchResult]:
    # Accept either the class (production default -> instantiate it) or
    # an already-constructed instance (test doubles like FakeDDGS).
    ddgs_instance = ddgs_class() if isinstance(ddgs_class, type) else ddgs_class

    raw_results = ddgs_instance.text(query, max_results=count)

    results: list[WebSearchResult] = []
    for item in raw_results:
        try:
            results.append(
                WebSearchResult(
                    title=item.get("title", ""),
                    url=item["href"],
                    description=item.get("body", ""),
                    engine="duckduckgo",
                )
            )
        except (KeyError, ValidationError) as exc:
            logger.debug("Skipping malformed DuckDuckGo result %r: %s", item, exc)
            continue

    return results


# --------------------------------------------------------------------- #
# Public entry point — Brave first, DuckDuckGo fallback
# --------------------------------------------------------------------- #
async def web_search(
    query: str,
    count: int = 5,
    ddgs_class: Union[Type[Any], Any] = DDGS,
) -> list[WebSearchResult]:
    api_key = os.getenv("BRAVE_API_KEY")

    try:
        client = BraveSearchClient(api_key=api_key)
        results = await client.search(query, count=count)
        if results:
            return results
        logger.info("Brave Search returned 0 results for %r, falling back to DuckDuckGo.", query)
    except (BraveAPIError, httpx.TimeoutException) as exc:
        logger.warning("Brave Search failed (%s), falling back to DuckDuckGo.", exc)

    return _duckduckgo_search(query, count, ddgs_class)


# ---------------------------------------------------------------------- #
# Manual smoke test: `python -m src.clients.brave_client`
# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def _demo() -> None:
        demo_results = await web_search("retrieval augmented generation", count=3)
        for r in demo_results:
            print(f"[{r.engine}] {r.title} -> {r.url}")

    asyncio.run(_demo())