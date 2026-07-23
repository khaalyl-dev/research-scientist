"""
Integration tests: Planner → Researcher → Extractor (Sprint 2).

Runs the *real* agent nodes in sequence (and once via LangGraph), with
injectable fakes for LLM / search / DB — no live network or Groq calls.

Verifies the handoff contract:
  query → sub_queries → sources → claims
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import pytest

from src.agents.extractor import extractor_node
from src.agents.graph import build_graph, create_extraction_jobs
from src.agents.planner import planner_node
from src.agents.researcher import researcher_node
from src.agents.state import GraphState
from src.clients.brave_client import WebSearchResult
from src.schemas.common import SessionStatus, SourceType, UserLevel
from src.schemas.source import SourceSchema

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeLLM:
    """Returns canned text; tracks prompts for assertions."""

    def __init__(self, response: str):
        self._response = response
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._response


class RoutingLLM:
    """One client for both Planner and Extractor (used in graph invoke)."""

    def __init__(self, planner_response: str, extractor_response: str):
        self.planner_response = planner_response
        self.extractor_response = extractor_response
        self.calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt[:80])
        # Planner prompt asks for sub_queries JSON; Extractor asks for claims array
        if "sub_queries" in prompt or "Decompose" in prompt or "Planner Agent" in prompt:
            return self.planner_response
        return self.extractor_response


class FakeSearchClient:
    def __init__(self, sources_by_query: dict | None = None):
        self._sources_by_query = sources_by_query or {}
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, max_results: int = 5) -> list[SourceSchema]:
        self.calls.append((query, max_results))
        return list(self._sources_by_query.get(query, []))[:max_results]


class FakeScraper:
    def fetch(self, url: str) -> SourceSchema | None:
        return SourceSchema(
            id=str(uuid.uuid4()),
            source_type=SourceType.web,
            title=f"Scraped {url}",
            url=url,
            content="Web page explaining retrieval-augmented generation in detail.",
        )


def _make_source(query: str, stype: SourceType, suffix: str) -> SourceSchema:
    return SourceSchema(
        id=str(uuid.uuid4()),
        source_type=stype,
        title=f"{stype.value}: {query}",
        url=f"https://example.com/{stype.value}/{suffix}",
        content=(
            f"Academic content about {query}. "
            "RAG retrieves documents before generating answers."
        ),
        published_year=2024,
    )


PLANNER_JSON = json.dumps(
    {
        "sub_queries": [
            "Retrieval Augmented Generation definition",
            "RAG architecture components",
            "RAG evaluation metrics",
        ],
        "source_types": ["arxiv", "scholar", "wikipedia", "web"],
    }
)

EXTRACTOR_JSON = json.dumps(
    [
        {
            "entity": "RAG",
            "claim": "RAG retrieves external documents before generating an answer.",
            "confidence": 0.92,
        },
        {
            "entity": "LLM",
            "claim": "Large language models can hallucinate without retrieval.",
            "confidence": 0.85,
        },
    ]
)


def _initial_state(query: str = "What is RAG?") -> GraphState:
    return {
        "query": query,
        "user_level": UserLevel.intermediate,
        "session_id": str(uuid.uuid4()),
        "status": SessionStatus.running.value,
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


def _empty_provider() -> FakeSearchClient:
    return FakeSearchClient()


async def _fake_web_search(query: str, count: int = 5) -> list[WebSearchResult]:
    return [
        WebSearchResult(
            title="RAG overview",
            url=f"https://example.com/web/{query.replace(' ', '-')[:40]}",
            engine="brave",
            description="Web hit",
        )
    ][:count]


# ---------------------------------------------------------------------------
# 1) Sequential node-chain (real agents, injectable deps)
# ---------------------------------------------------------------------------


class TestPlannerResearcherExtractorChain:
    @pytest.mark.asyncio
    async def test_handoff_query_to_subqueries_to_sources_to_claims(self):
        state = _initial_state()
        planner_llm = FakeLLM(PLANNER_JSON)
        extractor_llm = FakeLLM(EXTRACTOR_JSON)

        with patch("src.agents.planner.save_sub_queries") as mock_save_sq:
            plan = planner_node(state, llm_client=planner_llm)

        assert plan["current_agent"] == "planner"
        assert 3 <= len(plan["sub_queries"]) <= 5
        assert mock_save_sq.called
        state = {**state, **plan}

        # Researcher: one arXiv hit per sub-query + wiki on first only
        arxiv_map = {
            sq: [_make_source(sq, SourceType.arxiv, f"a{i}")]
            for i, sq in enumerate(plan["sub_queries"])
        }
        wiki = FakeSearchClient(
            {
                plan["sub_queries"][0]: [
                    _make_source(plan["sub_queries"][0], SourceType.wikipedia, "wiki")
                ]
            }
        )

        research = await researcher_node(
            state,
            arxiv_client=FakeSearchClient(arxiv_map),
            scraper=FakeScraper(),
            web_search_fn=_fake_web_search,
            wikipedia_client=wiki,
            scholar_client=_empty_provider(),
            openalex_client=_empty_provider(),
            pubmed_client=_empty_provider(),
        )

        assert research["current_agent"] == "researcher"
        assert research["error"] is None
        assert len(research["sources"]) >= 3
        sources = [
            s.model_dump() if hasattr(s, "model_dump") else s for s in research["sources"]
        ]
        state = {**state, **research, "sources": sources}

        # Fan-out contract: one extractor job per source
        jobs = create_extraction_jobs(state)  # type: ignore[arg-type]
        assert isinstance(jobs, list)
        assert len(jobs) == len(sources)

        all_claims: list[dict] = []
        with (
            patch("src.agents.extractor.save_source"),
            patch("src.agents.extractor.save_claims"),
        ):
            for job in jobs:
                out = extractor_node(job.arg, llm_client=extractor_llm)
                assert "claims" in out
                assert "current_agent" not in out  # parallel-safe return
                all_claims.extend(out["claims"])

        assert len(all_claims) >= 2
        assert all(c.get("entity") for c in all_claims)
        assert all(c.get("source_id") for c in all_claims)
        assert {c["source_id"] for c in all_claims} <= {s["id"] for s in sources}

    @pytest.mark.asyncio
    async def test_zero_sources_skips_extraction_jobs(self):
        state = _initial_state("obscure xyzzy query")
        with patch("src.agents.planner.save_sub_queries"):
            plan = planner_node(state, llm_client=FakeLLM(PLANNER_JSON))
        state = {**state, **plan}

        async def empty_web(query: str, count: int = 5) -> list:
            return []

        research = await researcher_node(
            state,
            arxiv_client=_empty_provider(),
            scraper=FakeScraper(),
            web_search_fn=empty_web,
            wikipedia_client=_empty_provider(),
            scholar_client=_empty_provider(),
            openalex_client=_empty_provider(),
            pubmed_client=_empty_provider(),
        )
        state = {**state, **research, "sources": []}

        assert create_extraction_jobs(state) == "fact_checker"  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2) LangGraph invoke: real Planner + Researcher + Extractor wiring
# ---------------------------------------------------------------------------


class TestGraphPlannerResearcherExtractor:
    def test_graph_runs_planner_researcher_extractor(self):
        """Full graph invoke with real nodes; LLM + search + DB mocked."""
        routing_llm = RoutingLLM(PLANNER_JSON, EXTRACTOR_JSON)
        session_id = str(uuid.uuid4())

        sub_queries = [
            "Retrieval Augmented Generation definition",
            "RAG architecture components",
            "RAG evaluation metrics",
        ]
        arxiv_map = {
            sq: [_make_source(sq, SourceType.arxiv, f"g{i}")]
            for i, sq in enumerate(sub_queries)
        }

        async def researched(state):
            result = await researcher_node(
                state,
                arxiv_client=FakeSearchClient(arxiv_map),
                scraper=FakeScraper(),
                web_search_fn=_fake_web_search,
                wikipedia_client=_empty_provider(),
                scholar_client=_empty_provider(),
                openalex_client=_empty_provider(),
                pubmed_client=_empty_provider(),
            )
            sources = result.get("sources") or []
            result["sources"] = [
                s.model_dump() if hasattr(s, "model_dump") else s for s in sources
            ]
            return result

        def sync_researcher(state):
            import asyncio

            return asyncio.run(researched(state))

        initial = _initial_state()
        initial["session_id"] = session_id

        with (
            patch("src.clients.llm_client.LLMClient", return_value=routing_llm),
            patch("src.agents.planner.save_sub_queries"),
            patch("src.agents.extractor.save_source"),
            patch("src.agents.extractor.save_claims"),
            patch("src.agents.graph.create_session"),
            patch("src.agents.graph._sync_researcher_agent", side_effect=sync_researcher),
        ):
            graph = build_graph()
            result = graph.invoke(
                initial,
                {"configurable": {"thread_id": f"itest-{session_id}"}},
            )

        assert len(result["sub_queries"]) >= 3
        assert len(result["sources"]) >= 1
        assert len(result["claims"]) >= 1
        # Pipeline continued past Extractor (stubs for later agents)
        assert result["status"] == SessionStatus.completed.value
        assert result.get("final_response")

        # Claims reference researched sources
        source_ids = {s["id"] if isinstance(s, dict) else s.id for s in result["sources"]}
        for claim in result["claims"]:
            assert claim["source_id"] in source_ids

    def test_graph_degrades_when_planner_llm_fails(self):
        """Planner fallback still feeds Researcher → Extractor."""

        class BoomLLM:
            def generate(self, prompt: str) -> str:
                if "sub_queries" in prompt or "Planner Agent" in prompt:
                    raise RuntimeError("Groq down")
                return EXTRACTOR_JSON

        async def researched(state):
            # Use planner's fallback sub_queries (from state after planner ran)
            queries = state.get("sub_queries") or [state["query"]]
            arxiv = FakeSearchClient(
                {q: [_make_source(q, SourceType.arxiv, "fb")] for q in queries}
            )
            result = await researcher_node(
                state,
                arxiv_client=arxiv,
                scraper=FakeScraper(),
                web_search_fn=_fake_web_search,
                wikipedia_client=_empty_provider(),
                scholar_client=_empty_provider(),
                openalex_client=_empty_provider(),
                pubmed_client=_empty_provider(),
            )
            result["sources"] = [
                s.model_dump() if hasattr(s, "model_dump") else s
                for s in (result.get("sources") or [])
            ]
            return result

        def sync_researcher(state):
            import asyncio

            return asyncio.run(researched(state))

        with (
            patch("src.clients.llm_client.LLMClient", return_value=BoomLLM()),
            patch("src.agents.planner.save_sub_queries"),
            patch("src.agents.extractor.save_source"),
            patch("src.agents.extractor.save_claims"),
            patch("src.agents.graph.create_session"),
            patch("src.agents.graph._sync_researcher_agent", side_effect=sync_researcher),
        ):
            graph = build_graph()
            result = graph.invoke(
                _initial_state("Hallucination in LLMs"),
                {"configurable": {"thread_id": "itest-planner-fallback"}},
            )

        assert len(result["sub_queries"]) >= 3  # heuristic fallback
        assert len(result["sources"]) >= 1
        assert result["status"] == SessionStatus.completed.value
