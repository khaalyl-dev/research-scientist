"""
Researcher agent (US-03) — the second node in the pipeline.

Job: given the Planner's sub-queries, fetch candidate sources from BOTH
arXiv and the web (Brave Search + scraper), running everything concurrently
rather than one call after another, then hand a deduplicated list of
SourceSchema objects to the Extractor.

VERIFIED INTEGRATION — this file was tested directly against Khalil's real
src/clients/arxiv_client.py and src/clients/scraper.py (not an inferred
interface). Confirmed signatures:

    from src.clients.arxiv_client import ArxivClient
    ArxivClient(min_interval: float = 3.0).search(
    query: str, max_results: int = 5
) -> List[SourceSchema]
    # synchronous; internally throttled (~3s between calls) and retried
    # (tenacity, 3 attempts); never raises — returns [] on failure

    from src.clients.scraper import WebScraper
    WebScraper(timeout=15, max_content_chars=20000).fetch(url: str) -> Optional[SourceSchema]
    # synchronous; never raises — returns None on any failure

Verified end-to-end (see tests/unit/test_researcher.py and the manual
integration check in Task_Agent_Researcher.md) by mocking only the network
boundary of each real client (arxiv.Client.results, requests.Session.get)
and letting their actual parsing logic run — not by mocking the clients
themselves.

One real-world consequence worth knowing: `ArxivClient`'s default
`min_interval=3.0` means every arXiv call in a live pipeline run is
throttled to roughly one request per 3 seconds. With multiple sub-queries
each triggering their own arXiv call, this throttle — not network latency —
will likely be the dominant cost in the Researcher agent's total runtime.
Worth watching against the plan's <45s end-to-end target once real timing
data exists.

Why arXiv (sync) and Brave (async) can be mixed cleanly: `asyncio.to_thread`
runs the synchronous, rate-limited arXiv call in a worker thread so it
doesn't block the event loop, letting it run concurrently with the native
async Brave call instead of waiting for one to finish before starting the
other. That's the "orchestration parallèle" this task asks for.
"""

import asyncio

from src.agents.state import GraphState
from src.schemas.source import SourceSchema
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_ARXIV_PER_SUBQUERY = 2
MAX_WEB_PER_SUBQUERY = 2
MAX_TOTAL_SOURCES = 8  # matches the plan's success metric: 3-8 sources per query


async def _fetch_arxiv(arxiv_client, query: str, max_results: int) -> list[SourceSchema]:
    """Wrap the synchronous arXiv client so it runs in a thread instead of
    blocking the event loop, letting it run alongside the Brave call."""
    try:
        return await asyncio.to_thread(arxiv_client.search, query, max_results)
    except Exception as e:
        logger.warning(f"arXiv search failed for {query!r}: {e}")
        return []


async def _fetch_web(web_search_fn, scraper, query: str, count: int) -> list[SourceSchema]:
    """Get web search hits (title/url/snippet only — see brave_client.py's
    scope note), then scrape each URL in parallel to get full page content.
    A hit that fails to scrape (paywall, timeout, non-HTML) is dropped, not
    fatal — matches US-13's graceful degradation requirement."""
    try:
        hits = await web_search_fn(query, count=count)
    except Exception as e:
        logger.warning(f"Web search failed for {query!r}: {e}")
        return []

    scraped = await asyncio.gather(
        *(asyncio.to_thread(scraper.fetch, str(hit.url)) for hit in hits),
        return_exceptions=True,
    )

    sources = []
    for result in scraped:
        if isinstance(result, Exception):
            logger.warning(f"Scraping failed: {result}")
            continue
        if result is None:
            continue  # scraper's own signal for "couldn't extract usable content"
        sources.append(result)
    return sources


def _dedupe_by_url(sources: list[SourceSchema]) -> list[SourceSchema]:
    """The same URL can surface from two different sub-queries; keep the
    first occurrence only."""
    seen: set[str] = set()
    deduped = []
    for source in sources:
        key = str(source.url)
        if key not in seen:
            seen.add(key)
            deduped.append(source)
    return deduped


async def researcher_node(
    state: GraphState,
    arxiv_client=None,
    scraper=None,
    web_search_fn=None,
) -> dict:
    """The actual LangGraph node. Extra parameters default to the real
    clients but are injectable for testing — same pattern used in
    brave_client.py's `ddgs_class`, for the same reason: test the real
    orchestration logic without needing network access or Khalil's files
    physically present to import.
    """
    if arxiv_client is None:
        from src.clients.arxiv_client import ArxivClient

        arxiv_client = ArxivClient()
    if scraper is None:
        from src.clients.scraper import WebScraper

        scraper = WebScraper()
    if web_search_fn is None:
        from src.clients.brave_client import web_search

        web_search_fn = web_search

    sub_queries = state["sub_queries"] or [state["query"]]

    tasks = []
    for q in sub_queries:
        tasks.append(_fetch_arxiv(arxiv_client, q, MAX_ARXIV_PER_SUBQUERY))
        tasks.append(_fetch_web(web_search_fn, scraper, q, MAX_WEB_PER_SUBQUERY))

    results = await asyncio.gather(*tasks)

    all_sources: list[SourceSchema] = []
    for result in results:
        all_sources.extend(result)

    deduped = _dedupe_by_url(all_sources)[:MAX_TOTAL_SOURCES]

    error = None
    if not deduped:
        # Matches US-13: don't crash, respond with a disclaimer downstream instead.
        error = "Researcher found zero usable sources across all sub-queries"
        logger.warning(f"No sources found for query={state['query']!r}")

    return {
        "sources": deduped,
        "error": error,
        "current_agent": "researcher",
    }
