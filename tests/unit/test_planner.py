"""
Unit tests for src/agents/planner.py (US-02).

The LLM is injected as a fake returning canned text — no real API calls.
"""

from unittest.mock import patch

from src.agents.planner import (
    MAX_SUB_QUERIES,
    MIN_SUB_QUERIES,
    parse_planner_response,
    planner_node,
)
from src.schemas.common import UserLevel


class FakeLLMClient:
    def __init__(self, response: str = "[]", raise_exc: Exception | None = None):
        self._response = response
        self._raise_exc = raise_exc
        self.prompts_seen: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts_seen.append(prompt)
        if self._raise_exc:
            raise self._raise_exc
        return self._response


def make_state(query: str = "What is RAG?") -> dict:
    return {
        "query": query,
        "user_level": UserLevel.beginner,
        "session_id": "sess-planner-1",
        "sub_queries": [],
        "source_types": [],
    }


VALID_RESPONSE = """
{
  "sub_queries": [
    "RAG definition and architecture",
    "RAG vs fine-tuning comparison",
    "RAG retrieval methods and vector databases",
    "RAG evaluation metrics and benchmarks"
  ],
  "source_types": ["arxiv", "web"]
}
"""


class TestParsePlannerResponse:
    def test_parses_clean_json_object(self):
        queries, types = parse_planner_response(VALID_RESPONSE, "What is RAG?")
        assert MIN_SUB_QUERIES <= len(queries) <= MAX_SUB_QUERIES
        assert "RAG definition and architecture" in queries
        assert types == ["arxiv", "web"]

    def test_handles_markdown_fenced_json(self):
        raw = f"```json\n{VALID_RESPONSE}\n```"
        queries, _ = parse_planner_response(raw, "What is RAG?")
        assert len(queries) == 4

    def test_handles_prose_wrapped_json(self):
        raw = f"Sure, here is the plan:\n{VALID_RESPONSE}\nGood luck!"
        queries, _ = parse_planner_response(raw, "What is RAG?")
        assert len(queries) >= MIN_SUB_QUERIES

    def test_accepts_bare_json_array(self):
        raw = '["angle A", "angle B", "angle C"]'
        queries, types = parse_planner_response(raw, "What is RAG?")
        assert queries == ["angle A", "angle B", "angle C"]
        assert "arxiv" in types

    def test_clamps_more_than_five_to_five(self):
        raw = {
            "sub_queries": [f"q{i}" for i in range(10)],
            "source_types": ["arxiv"],
        }
        import json

        queries, _ = parse_planner_response(json.dumps(raw), "What is RAG?")
        assert len(queries) == MAX_SUB_QUERIES

    def test_pads_fewer_than_three_to_three(self):
        raw = '{"sub_queries": ["only one"], "source_types": ["web"]}'
        queries, _ = parse_planner_response(raw, "What is RAG?")
        assert len(queries) == MIN_SUB_QUERIES

    def test_malformed_response_uses_fallback(self):
        queries, types = parse_planner_response("I cannot help with that.", "What is RAG?")
        assert len(queries) == MIN_SUB_QUERIES
        assert all("What is RAG?" in q for q in queries)
        assert types == ["arxiv", "web"]

    def test_dedupes_near_identical_queries(self):
        raw = '{"sub_queries": ["RAG overview", "rag overview", "RAG methods", "RAG apps"]}'
        queries, _ = parse_planner_response(raw, "What is RAG?")
        assert len(queries) >= MIN_SUB_QUERIES
        assert len({q.lower() for q in queries}) == len(queries)


class TestPlannerNode:
    def test_returns_three_to_five_sub_queries(self):
        llm = FakeLLMClient(response=VALID_RESPONSE)
        with patch("src.agents.planner.save_sub_queries") as mock_save:
            result = planner_node(make_state(), llm_client=llm)

        assert MIN_SUB_QUERIES <= len(result["sub_queries"]) <= MAX_SUB_QUERIES
        assert result["current_agent"] == "planner"
        assert result["source_types"] == ["arxiv", "web"]
        mock_save.assert_called_once()
        assert mock_save.call_args[0][0] == "sess-planner-1"

    def test_prompt_includes_user_query_and_level(self):
        llm = FakeLLMClient(response=VALID_RESPONSE)
        with patch("src.agents.planner.save_sub_queries"):
            planner_node(make_state("Hallucination mitigation in LLMs"), llm_client=llm)

        assert "Hallucination mitigation in LLMs" in llm.prompts_seen[0]
        assert "beginner" in llm.prompts_seen[0]

    def test_llm_failure_falls_back_without_crash(self):
        llm = FakeLLMClient(raise_exc=RuntimeError("Groq API down"))
        with patch("src.agents.planner.save_sub_queries"):
            result = planner_node(make_state(), llm_client=llm)

        assert len(result["sub_queries"]) == MIN_SUB_QUERIES
        assert result["current_agent"] == "planner"

    def test_db_save_failure_does_not_crash(self):
        llm = FakeLLMClient(response=VALID_RESPONSE)
        with patch(
            "src.agents.planner.save_sub_queries",
            side_effect=RuntimeError("DB locked"),
        ):
            result = planner_node(make_state(), llm_client=llm)
        assert len(result["sub_queries"]) >= MIN_SUB_QUERIES

    def test_skips_db_save_when_no_session_id(self):
        llm = FakeLLMClient(response=VALID_RESPONSE)
        state = make_state()
        state["session_id"] = None
        with patch("src.agents.planner.save_sub_queries") as mock_save:
            planner_node(state, llm_client=llm)
        mock_save.assert_not_called()
