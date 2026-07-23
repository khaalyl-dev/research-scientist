"""
Tests for parallel Extractor fan-out via LangGraph Send() (Sprint 2).

No real LLM / network — planner + extractor are stubbed; researcher stub
already returns 3 dummy sources.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

from langgraph.types import Send

from src.agents.graph import (
    build_graph,
    create_extraction_jobs,
    dispatch_to_extractors,
)
from src.agents.state import GraphState
from src.schemas.common import SessionStatus, UserLevel
from src.schemas.source import SourceSchema


def _source(i: int) -> dict:
    return SourceSchema(
        id=f"src-{i}",
        url=f"https://example.com/{i}",
        title=f"Source {i}",
        source_type="arxiv",
        published_year=2024,
        content=f"Content about topic {i}.",
    ).model_dump()


class TestCreateExtractionJobs:
    def test_one_send_per_source(self):
        state = {
            "sources": [_source(1), _source(2), _source(3)],
            "session_id": "sess-1",
        }
        jobs = create_extraction_jobs(state)  # type: ignore[arg-type]
        assert isinstance(jobs, list)
        assert len(jobs) == 3
        assert all(isinstance(j, Send) for j in jobs)
        assert all(j.node == "extractor" for j in jobs)
        assert {j.arg["source"]["id"] for j in jobs} == {"src-1", "src-2", "src-3"}
        assert all(j.arg["session_id"] == "sess-1" for j in jobs)

    def test_empty_sources_routes_to_fact_checker(self):
        assert create_extraction_jobs({"sources": [], "session_id": "s"}) == "fact_checker"  # type: ignore[arg-type]

    def test_model_dump_sources_are_normalized_to_dicts(self):
        pydantic_sources = [
            SourceSchema(
                id="p1",
                url="https://example.com/p1",
                title="Pydantic Source",
                source_type="web",
                content="hello",
            )
        ]
        jobs = create_extraction_jobs(
            {"sources": pydantic_sources, "session_id": "s"}  # type: ignore[arg-type]
        )
        assert isinstance(jobs, list)
        assert isinstance(jobs[0].arg["source"], dict)
        assert jobs[0].arg["source"]["id"] == "p1"

    def test_dispatch_alias_matches(self):
        assert dispatch_to_extractors is create_extraction_jobs


class TestParallelExtractionGraph:
    def _initial_state(self) -> GraphState:
        return {
            "query": "What is RAG?",
            "user_level": UserLevel.beginner,
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

    def test_three_parallel_extractors_merge_claims(self):
        """3 sources → 3 Send() branches → claims merged via operator.add."""

        def fake_planner(state):
            return {
                "sub_queries": ["q1", "q2", "q3"],
                "source_types": ["arxiv", "web"],
                "current_agent": "planner",
                "status": SessionStatus.running.value,
            }

        async def fake_researcher(state):
            return {
                "sources": [_source(1), _source(2), _source(3)],
                "current_agent": "researcher",
                "error": None,
            }

        def fake_extractor(state):
            source = state["source"]
            return {
                "claims": [
                    {
                        "id": str(uuid.uuid4()),
                        "source_id": source["id"],
                        "source_url": source["url"],
                        "entity": f"E-{source['id']}",
                        "claim": f"Claim from {source['title']}",
                        "confidence": 0.9,
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "source_id": source["id"],
                        "source_url": source["url"],
                        "entity": f"E2-{source['id']}",
                        "claim": f"Second claim from {source['title']}",
                        "confidence": 0.8,
                    },
                ]
            }

        with (
            patch("src.agents.graph.planner_node", side_effect=fake_planner),
            patch(
                "src.agents.graph._sync_researcher_agent",
                side_effect=lambda state: {
                    "sources": [_source(1), _source(2), _source(3)],
                    "current_agent": "researcher",
                    "error": None,
                },
            ),
            patch("src.agents.graph.extractor_node", side_effect=fake_extractor),
            patch(
                "src.agents.graph.fact_checker_agent",
                side_effect=lambda state: {
                    "contradictions": [],
                    "has_contradictions": False,
                    "current_agent": "fact_checker",
                },
            ),
            patch(
                "src.agents.graph.reasoner_node",
                side_effect=lambda state: {
                    "reasoning": "plan",
                    "current_agent": "reasoner",
                },
            ),
            patch(
                "src.agents.graph.teacher_node",
                side_effect=lambda state: {
                    "final_response": "answer",
                    "current_agent": "teacher",
                    "status": SessionStatus.completed.value,
                },
            ),
            patch("src.agents.graph.create_session"),
        ):
            # Rebuild graph AFTER patches so nodes bind to fakes
            graph = build_graph()
            config = {"configurable": {"thread_id": "test-parallel-send"}}
            result = graph.invoke(self._initial_state(), config)

        # Fake researcher returns 3 sources; fake extractor returns 2 claims each
        assert len(result["sources"]) == 3
        assert len(result["claims"]) == 6
        source_ids = {c["source_id"] for c in result["claims"]}
        assert len(source_ids) == 3
        assert result["status"] == SessionStatus.completed.value
        assert result["final_response"]

    def test_zero_sources_skips_extractor_without_stall(self):
        def fake_planner(state):
            return {
                "sub_queries": ["q1"],
                "source_types": ["web"],
                "current_agent": "planner",
            }

        async def fake_researcher(state):
            return {"sources": [], "current_agent": "researcher", "error": "none"}

        with (
            patch("src.agents.graph.planner_node", side_effect=fake_planner),
            patch(
                "src.agents.graph._sync_researcher_agent",
                side_effect=lambda state: {
                    "sources": [],
                    "current_agent": "researcher",
                    "error": "none",
                },
            ),
            patch(
                "src.agents.graph.fact_checker_agent",
                side_effect=lambda state: {
                    "contradictions": [],
                    "has_contradictions": False,
                    "current_agent": "fact_checker",
                },
            ),
            patch(
                "src.agents.graph.reasoner_node",
                side_effect=lambda state: {
                    "reasoning": "plan",
                    "current_agent": "reasoner",
                },
            ),
            patch(
                "src.agents.graph.teacher_node",
                side_effect=lambda state: {
                    "final_response": "answer",
                    "current_agent": "teacher",
                    "status": SessionStatus.completed.value,
                },
            ),
            patch("src.agents.graph.create_session"),
        ):
            graph = build_graph()
            config = {"configurable": {"thread_id": "test-empty-sources"}}
            result = graph.invoke(self._initial_state(), config)

        assert result["sources"] == []
        assert result["claims"] == []
        assert result["status"] == SessionStatus.completed.value
