"""
Researcher agent (US-03) — the second node in the pipeline.

Fetches candidate sources in parallel from:
  - arXiv
  - Web (Brave → DuckDuckGo + scraper)
  - Wikipedia
  - Semantic Scholar
  - OpenAlex
  - PubMed

Then deduplicates by URL and caps the total count for the Extractor.
"""

from __future__ import annotations

import asyncio

from src.agents.state import GraphState
from src.schemas.source import SourceSchema
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_ARXIV_PER_SUBQUERY = 2
MAX_WEB_PER_SUBQUERY = 1
MAX_WIKI_PER_SUBQUERY = 1
MAX_SCHOLAR_PER_SUBQUERY = 1
MAX_OPENALEX_PER_SUBQUERY = 1
MAX_PUBMED_PER_SUBQUERY = 1
MAX_TOTAL_SOURCES = 12


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

    sub_queries = state["sub_queries"] or [state["query"]]

    tasks = []
    for q in sub_queries:
        tasks.append(_fetch_client(arxiv_client, q, MAX_ARXIV_PER_SUBQUERY, "arXiv"))
        tasks.append(_fetch_web(web_search_fn, scraper, q, MAX_WEB_PER_SUBQUERY))
        tasks.append(
            _fetch_client(wikipedia_client, q, MAX_WIKI_PER_SUBQUERY, "Wikipedia")
        )
        tasks.append(
            _fetch_client(scholar_client, q, MAX_SCHOLAR_PER_SUBQUERY, "Semantic Scholar")
        )
        tasks.append(
            _fetch_client(openalex_client, q, MAX_OPENALEX_PER_SUBQUERY, "OpenAlex")
        )
        tasks.append(_fetch_client(pubmed_client, q, MAX_PUBMED_PER_SUBQUERY, "PubMed"))

    results = await asyncio.gather(*tasks)

    all_sources: list[SourceSchema] = []
    for result in results:
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
