"""
Unit tests for src/agents/researcher.py.

External clients are injected as fakes — zero real network calls.
"""

import uuid

from src.agents.researcher import researcher_node
from src.agents.state import GraphState
from src.clients.brave_client import WebSearchResult
from src.schemas.common import SessionStatus, SourceType, UserLevel
from src.schemas.source import SourceSchema


def make_state(session_id: str, query: str, user_level: UserLevel) -> GraphState:
    return {
        "query": query,
        "user_level": user_level,
        "session_id": session_id,
        "status": SessionStatus.running,
        "current_agent": "start",
        "retry_count": 0,
        "sub_queries": [],
        "source_types": [],
        "sources": [],
        "claims": [],
        "contradictions": [],
        "has_contradictions": False,
        "reasoning": "",
        "final_response": "",
        "error": None,
    }


class FakeSearchClient:
    """Fake matching *.search(query, max_results) -> list[SourceSchema]."""

    def __init__(self, sources_by_query: dict | None = None, raise_exc: Exception | None = None):
        self._sources_by_query = sources_by_query or {}
        self._raise_exc = raise_exc
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, max_results: int = 5) -> list[SourceSchema]:
        self.calls.append((query, max_results))
        if self._raise_exc:
            raise self._raise_exc
        return self._sources_by_query.get(query, [])[:max_results]


FakeArxivClient = FakeSearchClient


class FakeScraper:
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
            id=str(uuid.uuid4()),
            source_type=SourceType.web,
            title=f"scraped: {url}",
            url=url,
            content="scraped content, long enough to be plausible " * 3,
        )


def make_source(query: str, source_type: SourceType, suffix: str = "1") -> SourceSchema:
    host = {
        SourceType.arxiv: "arxiv.org/abs",
        SourceType.web: "example.com",
        SourceType.wikipedia: "en.wikipedia.org/wiki",
        SourceType.scholar: "semanticscholar.org/paper",
        SourceType.openalex: "openalex.org/works",
        SourceType.pubmed: "pubmed.ncbi.nlm.nih.gov",
    }[source_type]
    return SourceSchema(
        id=str(uuid.uuid4()),
        source_type=source_type,
        title=f"{source_type.value} result for {query}",
        url=f"https://{host}/{suffix}",
        content="content body",
        published_year=2025,
    )


def make_arxiv_source(query: str, suffix: str = "1") -> SourceSchema:
    return make_source(query, SourceType.arxiv, suffix)


def make_web_search_fn(hits_by_query: dict):
    async def fake_web_search(query: str, count: int = 5) -> list[WebSearchResult]:
        return hits_by_query.get(query, [])[:count]

    return fake_web_search


def _empty_extras():
    return {
        "wikipedia_client": FakeSearchClient(),
        "scholar_client": FakeSearchClient(),
        "openalex_client": FakeSearchClient(),
        "pubmed_client": FakeSearchClient(),
    }


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
            **_empty_extras(),
        )

        assert len(result["sources"]) == 2
        types = {s.source_type for s in result["sources"]}
        assert types == {SourceType.arxiv, SourceType.web}
        assert result["current_agent"] == "researcher"
        assert result["error"] is None

    async def test_aggregates_new_providers(self):
        state = make_state("s1", "q", UserLevel.beginner)
        state["sub_queries"] = ["RAG"]

        result = await researcher_node(
            state,
            arxiv_client=FakeSearchClient(),
            scraper=FakeScraper(),
            web_search_fn=make_web_search_fn({}),
            wikipedia_client=FakeSearchClient(
                {"RAG": [make_source("RAG", SourceType.wikipedia, "RAG")]}
            ),
            scholar_client=FakeSearchClient(
                {"RAG": [make_source("RAG", SourceType.scholar, "abc")]}
            ),
            openalex_client=FakeSearchClient(
                {"RAG": [make_source("RAG", SourceType.openalex, "W1")]}
            ),
            pubmed_client=FakeSearchClient(
                {"RAG": [make_source("RAG", SourceType.pubmed, "123")]}
            ),
        )

        types = {s.source_type for s in result["sources"]}
        assert types == {
            SourceType.wikipedia,
            SourceType.scholar,
            SourceType.openalex,
            SourceType.pubmed,
        }
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
            state,
            arxiv_client=arxiv,
            scraper=FakeScraper(),
            web_search_fn=make_web_search_fn({}),
            **_empty_extras(),
        )

        assert len(arxiv.calls) == 3
        assert len(result["sources"]) == 3

    async def test_falls_back_to_main_query_when_no_subqueries(self):
        state = make_state("s1", "main question", UserLevel.beginner)
        state["sub_queries"] = []

        arxiv = FakeArxivClient({"main question": [make_arxiv_source("main question")]})
        result = await researcher_node(
            state,
            arxiv_client=arxiv,
            scraper=FakeScraper(),
            web_search_fn=make_web_search_fn({}),
            **_empty_extras(),
        )

        assert arxiv.calls == [("main question", 2)]
        assert len(result["sources"]) == 1

    async def test_deduplicates_sources_by_url(self):
        state = make_state("s1", "q", UserLevel.beginner)
        state["sub_queries"] = ["sub-a", "sub-b"]

        same_source = make_arxiv_source("dup", "same-id")
        arxiv = FakeArxivClient({"sub-a": [same_source], "sub-b": [same_source]})

        result = await researcher_node(
            state,
            arxiv_client=arxiv,
            scraper=FakeScraper(),
            web_search_fn=make_web_search_fn({}),
            **_empty_extras(),
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
            **_empty_extras(),
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
            **_empty_extras(),
        )

        assert len(result["sources"]) == 1

    async def test_arxiv_exception_does_not_crash_web_branch(self):
        state = make_state("s1", "q", UserLevel.beginner)
        state["sub_queries"] = ["sub-a"]

        hits = {
            "sub-a": [WebSearchResult(title="ok", url="https://example.com/good", engine="brave")]
        }

        arxiv = FakeArxivClient(raise_exc=RuntimeError("arXiv API down"))

        result = await researcher_node(
            state,
            arxiv_client=arxiv,
            scraper=FakeScraper(),
            web_search_fn=make_web_search_fn(hits),
            **_empty_extras(),
        )

        assert len(result["sources"]) == 1
        assert result["sources"][0].source_type == SourceType.web

    async def test_provider_exception_does_not_crash_others(self):
        state = make_state("s1", "q", UserLevel.beginner)
        state["sub_queries"] = ["sub-a"]

        result = await researcher_node(
            state,
            arxiv_client=FakeSearchClient(
                {"sub-a": [make_arxiv_source("sub-a")]}
            ),
            scraper=FakeScraper(),
            web_search_fn=make_web_search_fn({}),
            wikipedia_client=FakeSearchClient(raise_exc=RuntimeError("wiki down")),
            scholar_client=FakeSearchClient(),
            openalex_client=FakeSearchClient(),
            pubmed_client=FakeSearchClient(),
        )

        assert len(result["sources"]) == 1
        assert result["sources"][0].source_type == SourceType.arxiv

    async def test_zero_sources_populates_errors_not_exception(self):
        state = make_state("s1", "obscure query", UserLevel.beginner)
        state["sub_queries"] = ["obscure query"]

        result = await researcher_node(
            state,
            arxiv_client=FakeArxivClient(),
            scraper=FakeScraper(),
            web_search_fn=make_web_search_fn({}),
            **_empty_extras(),
        )

        assert result["sources"] == []
        assert result["error"] is not None
        assert "zero usable sources" in result["error"]

    async def test_caps_total_sources_at_max(self):
        state = make_state("s1", "q", UserLevel.beginner)
        state["sub_queries"] = [f"sub-{i}" for i in range(10)]

        arxiv_sources = {f"sub-{i}": [make_arxiv_source(f"sub-{i}", str(i))] for i in range(10)}
        arxiv = FakeArxivClient(arxiv_sources)

        result = await researcher_node(
            state,
            arxiv_client=arxiv,
            scraper=FakeScraper(),
            web_search_fn=make_web_search_fn({}),
            **_empty_extras(),
        )

        from src.agents.researcher import MAX_TOTAL_SOURCES

        assert len(result["sources"]) <= MAX_TOTAL_SOURCES
