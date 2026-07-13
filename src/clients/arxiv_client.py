"""
arXiv client — Task: "arXiv client" (US-03, Sprint 1)

Responsibilities (per MVP_Plan_Final.pdf, section 4 & 6):
  - Search arXiv for a given query
  - Parse metadata into the shared Source schema
  - Respect arXiv's rate limit (max ~3 req/sec) via a small throttle
  - Retry on transient network errors (tenacity, exponential backoff)
  - Never raise on a single-source failure — the pipeline degrades
    gracefully (returns an empty list instead of crashing the app)

Usage:
    from src.clients.arxiv_client import ArxivClient

    client = ArxivClient()
    sources = client.search("retrieval augmented generation", max_results=5)
    for s in sources:
        print(s.title, s.url)
"""

from __future__ import annotations

import logging
import time
from typing import List

import arxiv
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.schemas.common import SourceType
from src.schemas.source import SourceSchema

logger = logging.getLogger(__name__)

# arXiv's public API asks for no more than 1 request / 3 seconds when you
# are not using their bulk endpoints. We throttle a little more gently
# than that ceiling to stay safely inside the guideline.
_MIN_SECONDS_BETWEEN_REQUESTS = 3.0


class ArxivClient:
    """Thin, defensive wrapper around the official `arxiv` Python package."""

    def __init__(self, min_interval: float = _MIN_SECONDS_BETWEEN_REQUESTS) -> None:
        self._min_interval = min_interval
        self._last_request_ts: float = 0.0
        # arxiv.Client handles paging / delays internally too, but we keep
        # our own throttle since we may call `search()` many times across
        # a single multi-sub-query research session.
        self._client = arxiv.Client(page_size=25, delay_seconds=3, num_retries=2)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def search(self, query: str, max_results: int = 5) -> List[SourceSchema]:
        """
        Search arXiv and return a list of Source objects.
        Never raises: on failure, logs the error and returns [].
        """
        if not query or not query.strip():
            return []

        self._throttle()

        try:
            results = self._search_with_retry(query=query, max_results=max_results)
        except Exception as exc:  # noqa: BLE001 - graceful degradation is intentional
            logger.warning("arXiv search failed for query=%r: %s", query, exc)
            return []

        sources = [self._to_source(r) for r in results]
        logger.info("arXiv search: query=%r -> %d results", query, len(sources))
        return sources

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _search_with_retry(self, query: str, max_results: int):
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        # arxiv.Client.results() returns a generator; materialize it here
        # so retry can actually catch network errors raised during iteration.
        return list(self._client.results(search))

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_ts
        wait_for = self._min_interval - elapsed
        if wait_for > 0:
            time.sleep(wait_for)
        self._last_request_ts = time.monotonic()

    @staticmethod
    def _to_source(result: "arxiv.Result") -> SourceSchema:
        # NOTE: SourceSchema has no dedicated `authors` field, so we fold
        # the author list into `content` (which is required, min_length=1).
        # If you later add an `authors` field to SourceSchema, move this
        # back out into its own field instead.
        abstract = (result.summary or "").strip().replace("\n", " ")
        authors = ", ".join(a.name for a in result.authors)
        content = f"Authors: {authors}\n\n{abstract}" if authors else abstract

        return SourceSchema(
            source_type=SourceType.arxiv,
            title=result.title.strip(),
            url=result.entry_id,  # canonical arxiv.org/abs/... URL, HttpUrl validates it
            published_year=result.published.year if result.published else None,
            content=content or "No abstract available.",
        )


# ---------------------------------------------------------------------- #
# Manual smoke test: `python -m src.clients.arxiv_client`
# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_client = ArxivClient()
    demo_results = demo_client.search("large language model hallucination", max_results=3)
    for src in demo_results:
        print(f"- {src.title} ({src.published_year}) -> {src.url}")
        print(f"  content preview: {src.content[:120]}...")
