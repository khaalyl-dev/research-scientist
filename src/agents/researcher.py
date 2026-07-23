"""
Researcher agent (US-03) — the second node in the pipeline.

Fetches candidate sources from arXiv, web, Wikipedia, Semantic Scholar,
OpenAlex, and (when relevant) PubMed — then deduplicates by URL.

Performance notes:
  - Fast providers (Wikipedia, OpenAlex, web) run in parallel per sub-query.
  - Rate-limited APIs (arXiv, Semantic Scholar) run **once** on the primary
    query and are serialized so we do not stampede into HTTP 429 storms.
  - PubMed only runs for biomedical-looking queries.
"""

from __future__ import annotations

import asyncio
import re

from src.agents.state import GraphState
from src.schemas.source import SourceSchema
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_ARXIV = 3
MAX_WEB_PER_SUBQUERY = 1
MAX_WIKI_PER_SUBQUERY = 1
MAX_SCHOLAR = 2
MAX_OPENALEX_PER_SUBQUERY = 1
MAX_PUBMED = 2
MAX_TOTAL_SOURCES = 12

# Kept for tests that import the old constant name
MAX_ARXIV_PER_SUBQUERY = MAX_ARXIV

_BIOMED_RE = re.compile(
    r"\b(pubmed|clinical|medical|medicine|disease|patient|therapy|"
    r"drug|cancer|genom|protein|bio(?:logy|medical)|pharma|diagnos)\b",
    re.IGNORECASE,
)


async def _fetch_client(client, query: str, max_results: int, label: str) -> list[SourceSchema]:
    """Run a sync client.search(...) in a worker thread; never raise."""
    try:
        return await asyncio.to_thread(client.search, query, max_results)
    except Exception as e:
        logger.warning(f"{label} search failed for {query!r}: {e}")
        return []


async def _fetch_web(web_search_fn, scraper, query: str, count: int) -> list[SourceSchema]:
    """Brave/DDG hits → scrape full page content in parallel."""
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
            continue
        sources.append(result)
    return sources


def _dedupe_by_url(sources: list[SourceSchema]) -> list[SourceSchema]:
    seen: set[str] = set()
    deduped = []
    for source in sources:
        key = str(source.url)
        if key not in seen:
            seen.add(key)
            deduped.append(source)
    return deduped


def _is_biomedical(text: str) -> bool:
    return bool(_BIOMED_RE.search(text or ""))


def _default_clients() -> dict:
    from src.clients.arxiv_client import ArxivClient
    from src.clients.openalex_client import OpenAlexClient
    from src.clients.pubmed_client import PubMedClient
    from src.clients.scholar_client import SemanticScholarClient
    from src.clients.scraper import WebScraper
    from src.clients.wikipedia_client import WikipediaClient

    return {
        "arxiv": ArxivClient(),
        "wikipedia": WikipediaClient(),
        "scholar": SemanticScholarClient(),
        "openalex": OpenAlexClient(),
        "pubmed": PubMedClient(),
        "scraper": WebScraper(),
    }


async def researcher_node(
    state: GraphState,
    arxiv_client=None,
    scraper=None,
    web_search_fn=None,
    wikipedia_client=None,
    scholar_client=None,
    openalex_client=None,
    pubmed_client=None,
) -> dict:
    """LangGraph node — injectable clients for unit tests."""
    defaults = None

    def _need(name: str, current):
        nonlocal defaults
        if current is not None:
            return current
        if defaults is None:
            defaults = _default_clients()
        return defaults[name]

    arxiv_client = _need("arxiv", arxiv_client)
    scraper = _need("scraper", scraper)
    wikipedia_client = _need("wikipedia", wikipedia_client)
    scholar_client = _need("scholar", scholar_client)
    openalex_client = _need("openalex", openalex_client)
    pubmed_client = _need("pubmed", pubmed_client)

    if web_search_fn is None:
        from src.clients.brave_client import web_search

        web_search_fn = web_search

    main_query = (state.get("query") or "").strip()
    sub_queries = state.get("sub_queries") or []
    sub_queries = [q for q in sub_queries if isinstance(q, str) and q.strip()]
    if not sub_queries:
        sub_queries = [main_query] if main_query else []

    primary = main_query or (sub_queries[0] if sub_queries else "")

    # --- Fast path: wiki / openalex / web per sub-query (true parallel) ---
    fast_tasks = []
    for q in sub_queries:
        fast_tasks.append(
            _fetch_client(wikipedia_client, q, MAX_WIKI_PER_SUBQUERY, "Wikipedia")
        )
        fast_tasks.append(
            _fetch_client(openalex_client, q, MAX_OPENALEX_PER_SUBQUERY, "OpenAlex")
        )
        fast_tasks.append(_fetch_web(web_search_fn, scraper, q, MAX_WEB_PER_SUBQUERY))

    # --- Slow / rate-limited APIs: once on the primary query, serialized ---
    slow_tasks = []
    if primary:
        slow_tasks.append(_fetch_client(arxiv_client, primary, MAX_ARXIV, "arXiv"))
        slow_tasks.append(
            _fetch_client(scholar_client, primary, MAX_SCHOLAR, "Semantic Scholar")
        )
        if _is_biomedical(primary) or any(_is_biomedical(q) for q in sub_queries):
            slow_tasks.append(
                _fetch_client(pubmed_client, primary, MAX_PUBMED, "PubMed")
            )
        else:
            logger.info("Skipping PubMed (query does not look biomedical)")

    fast_results, slow_results = await asyncio.gather(
        asyncio.gather(*fast_tasks) if fast_tasks else asyncio.sleep(0, result=[]),
        # Run slow APIs sequentially to avoid arXiv/Scholar 429 storms
        _run_sequential(slow_tasks),
    )

    all_sources: list[SourceSchema] = []
    for result in list(fast_results) + list(slow_results):
        all_sources.extend(result)

    deduped = _dedupe_by_url(all_sources)[:MAX_TOTAL_SOURCES]

    error = None
    if not deduped:
        error = "Researcher found zero usable sources across all sub-queries"
        logger.warning(f"No sources found for query={state['query']!r}")
    else:
        by_type: dict[str, int] = {}
        for s in deduped:
            key = getattr(s.source_type, "value", s.source_type)
            by_type[str(key)] = by_type.get(str(key), 0) + 1
        logger.info(
            "Researcher gathered %d source(s) for %d sub-quer(y/ies): %s",
            len(deduped),
            len(sub_queries),
            by_type,
        )

    return {
        "sources": deduped,
        "error": error,
        "current_agent": "researcher",
    }


async def _run_sequential(tasks: list) -> list:
    """Await coroutines one-by-one (rate-limited providers)."""
    results = []
    for coro in tasks:
        results.append(await coro)
    return results
