"""
Unit tests for src/agents/researcher.py.

All three external dependencies (arXiv client, scraper, web search) are
injected as fakes — see researcher_node's arxiv_client/scraper/web_search_fn
parameters. Zero real network calls, zero dependency on Khalil's actual
client files being present or on his exact internal implementation, only
on the interface contract documented at the top of researcher.py.
"""

import uuid

from src.agents.researcher import researcher_node
from src.agents.state import GraphState
from src.clients.brave_client import WebSearchResult
from src.schemas.common import SessionStatus, SourceType, UserLevel
from src.schemas.source import SourceSchema


def make_state(session_id: str, query: str, user_level: UserLevel) -> GraphState:
    """Test-only factory matching the approved GraphState contract exactly
    (src/agents/state.py, approved proposal). Not a production helper —
    state.py stays exactly as approved, with no additions."""
    return {
        "query": query,
        "user_level": user_level,
        "session_id": session_id,
        "status": SessionStatus.running,
        "current_agent": "start",
        "retry_count": 0,
        "sub_queries": [],
        "sources": [],
        "claims": [],
        "contradictions": [],
        "has_contradictions": False,
        "reasoning": "",
        "final_response": "",
        "error": None,
    }


class FakeArxivClient:
    """Fake matching ArxivClient.search(query, max_results) -> list[SourceSchema]."""

    def __init__(self, sources_by_query: dict | None = None, raise_exc: Exception | None = None):
        self._sources_by_query = sources_by_query or {}
        self._raise_exc = raise_exc
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, max_results: int = 5) -> list[SourceSchema]:
        self.calls.append((query, max_results))
        if self._raise_exc:
            raise self._raise_exc
        return self._sources_by_query.get(query, [])[:max_results]


class FakeScraper:
    """Fake matching WebScraper.fetch(url) -> SourceSchema | None."""

    def __init__(self, fail_urls: set[str] | None = None, raise_on: set[str] | None = None):
        self._fail_urls = fail_urls or set()
        self._raise_on = raise_on or set()
        self.calls: list[str] = []

    def fetch(self, url: str) -> SourceSchema | None:
        self.calls.append(url)
        if url in self._raise_on:
            raise RuntimeError(f"scraper blew up on {url}")
        if url in self._fail_urls:
            return None
        return SourceSchema(
            id=str(uuid.uuid4()),  # ← ADD THIS!
            source_type=SourceType.web,
            title=f"scraped: {url}",
            url=url,
            content="scraped content, long enough to be plausible " * 3,
        )


def make_arxiv_source(query: str, suffix: str = "1") -> SourceSchema:
    return SourceSchema(
        id=str(uuid.uuid4()),  # ← ADD THIS!
        source_type=SourceType.arxiv,
        title=f"arXiv result for {query}",
        url=f"https://arxiv.org/abs/{suffix}",
        content="abstract content",
        published_year=2025,
    )


def make_web_search_fn(hits_by_query: dict):
    async def fake_web_search(query: str, count: int = 5) -> list[WebSearchResult]:
        return hits_by_query.get(query, [])[:count]

    return fake_web_search


# ---------------------------------------------------------------------------


class TestResearcherNode:
    async def test_aggregates_arxiv_and_web_sources(self):
        state = make_state("s1", "what is RAG?", UserLevel.beginner)
        state["sub_queries"] = ["RAG overview"]

        arxiv = FakeArxivClient({"RAG overview": [make_arxiv_source("RAG overview")]})
        hits = {
            "RAG overview": [
                WebSearchResult(title="hit", url="https://example.com/a", engine="brave")
            ]
        }
        result = await researcher_node(
            state,
            arxiv_client=arxiv,
            scraper=FakeScraper(),
            web_search_fn=make_web_search_fn(hits),
        )

        assert len(result["sources"]) == 2
        types = {s.source_type for s in result["sources"]}
        assert types == {SourceType.arxiv, SourceType.web}
        assert result["current_agent"] == "researcher"
        assert result["error"] is None

    async def test_runs_all_subqueries(self):
        state = make_state("s1", "q", UserLevel.beginner)
        state["sub_queries"] = ["sub-a", "sub-b", "sub-c"]

        arxiv = FakeArxivClient(
            {
                "sub-a": [make_arxiv_source("sub-a", "a")],
                "sub-b": [make_arxiv_source("sub-b", "b")],
                "sub-c": [make_arxiv_source("sub-c", "c")],
            }
        )
        result = await researcher_node(
            state, arxiv_client=arxiv, scraper=FakeScraper(), web_search_fn=make_web_search_fn({})
        )

        assert len(arxiv.calls) == 3  # one arXiv call per sub-query
        assert len(result["sources"]) == 3

    async def test_falls_back_to_main_query_when_no_subqueries(self):
        state = make_state("s1", "main question", UserLevel.beginner)
        state["sub_queries"] = []  # Planner hasn't run / produced nothing

        arxiv = FakeArxivClient({"main question": [make_arxiv_source("main question")]})
        result = await researcher_node(
            state, arxiv_client=arxiv, scraper=FakeScraper(), web_search_fn=make_web_search_fn({})
        )

        assert arxiv.calls == [("main question", 2)]
        assert len(result["sources"]) == 1

    async def test_deduplicates_sources_by_url(self):
        state = make_state("s1", "q", UserLevel.beginner)
        state["sub_queries"] = ["sub-a", "sub-b"]

        # Same arXiv paper surfaces for both sub-queries
        same_source = make_arxiv_source("dup", "same-id")
        arxiv = FakeArxivClient({"sub-a": [same_source], "sub-b": [same_source]})

        result = await researcher_node(
            state, arxiv_client=arxiv, scraper=FakeScraper(), web_search_fn=make_web_search_fn({})
        )

        assert len(result["sources"]) == 1

    async def test_scraper_returning_none_is_dropped_not_fatal(self):
        state = make_state("s1", "q", UserLevel.beginner)
        state["sub_queries"] = ["sub-a"]

        hits = {
            "sub-a": [
                WebSearchResult(title="ok", url="https://example.com/good", engine="brave"),
                WebSearchResult(title="bad", url="https://example.com/bad", engine="brave"),
            ]
        }
        scraper = FakeScraper(fail_urls={"https://example.com/bad"})

        result = await researcher_node(
            state,
            arxiv_client=FakeArxivClient(),
            scraper=scraper,
            web_search_fn=make_web_search_fn(hits),
        )

        assert len(result["sources"]) == 1
        assert result["sources"][0].url.__str__() == "https://example.com/good"

    async def test_scraper_exception_does_not_crash_other_branches(self):
        state = make_state("s1", "q", UserLevel.beginner)
        state["sub_queries"] = ["sub-a"]

        hits = {
            "sub-a": [
                WebSearchResult(title="ok", url="https://example.com/good", engine="brave"),
                WebSearchResult(title="crash", url="https://example.com/crash", engine="brave"),
            ]
        }
        scraper = FakeScraper(raise_on={"https://example.com/crash"})

        result = await researcher_node(
            state,
            arxiv_client=FakeArxivClient(),
            scraper=scraper,
            web_search_fn=make_web_search_fn(hits),
        )

        assert len(result["sources"]) == 1  # the good one survives

    async def test_arxiv_exception_does_not_crash_web_branch(self):
        state = make_state("s1", "q", UserLevel.beginner)
        state["sub_queries"] = ["sub-a"]

        hits = {
            "sub-a": [WebSearchResult(title="ok", url="https://example.com/good", engine="brave")]
        }

        arxiv = FakeArxivClient(raise_exc=RuntimeError("arXiv API down"))

        result = await researcher_node(
            state, arxiv_client=arxiv, scraper=FakeScraper(), web_search_fn=make_web_search_fn(hits)
        )

        assert len(result["sources"]) == 1
        assert result["sources"][0].source_type == SourceType.web

    async def test_zero_sources_populates_errors_not_exception(self):
        state = make_state("s1", "obscure query", UserLevel.beginner)
        state["sub_queries"] = ["obscure query"]

        result = await researcher_node(
            state,
            arxiv_client=FakeArxivClient(),
            scraper=FakeScraper(),
            web_search_fn=make_web_search_fn({}),
        )

        assert result["sources"] == []
        assert result["error"] is not None
        assert "zero usable sources" in result["error"]

    async def test_caps_total_sources_at_max(self):
        state = make_state("s1", "q", UserLevel.beginner)
        state["sub_queries"] = [f"sub-{i}" for i in range(10)]  # way more than MAX_TOTAL_SOURCES

        arxiv_sources = {f"sub-{i}": [make_arxiv_source(f"sub-{i}", str(i))] for i in range(10)}
        arxiv = FakeArxivClient(arxiv_sources)

        result = await researcher_node(
            state, arxiv_client=arxiv, scraper=FakeScraper(), web_search_fn=make_web_search_fn({})
        )

        from src.agents.researcher import MAX_TOTAL_SOURCES

        assert len(result["sources"]) <= MAX_TOTAL_SOURCES
