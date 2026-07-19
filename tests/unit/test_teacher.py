"""
Unit tests for src/agents/teacher.py.

All tests use an injected fake LLM client — no real API calls, no API keys required.
"""

import pytest

from src.agents.teacher import (
    teacher_agent,
    _format_claims_with_sources,
    _format_sources,
    _clean_response,
    _ensure_citations,
    _build_fallback_response,
)


class FakeLLMClient:
    """Fake LLM client for testing — returns canned responses or raises exceptions."""

    def __init__(self, response: str = "", raise_exc: Exception | None = None):
        self.response = response
        self.raise_exc = raise_exc
        self.calls = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        if self.raise_exc:
            raise self.raise_exc
        return self.response


def make_state(
    query: str = "What is RAG?",
    user_level: str = "intermediate",
    reasoning: str = "# Answer Plan\n\nRAG combines retrieval and generation.",
    claims=None,
    sources=None,
):
    """Create a test state dictionary."""
    return {
        "query": query,
        "user_level": user_level,
        "reasoning": reasoning,
        "claims": claims or [],
        "sources": sources or [],
    }


def make_claim(entity: str, claim: str, confidence: float = 0.9, source_id: str = "s1", source_url: str = "https://example.com/1"):
    """Create a test claim dictionary."""
    return {
        "entity": entity,
        "claim": claim,
        "confidence": confidence,
        "source_id": source_id,
        "source_url": source_url,
    }


def make_source(source_id: str = "s1", title: str = "Test Source", url: str = "https://example.com/1", source_type: str = "web"):
    """Create a test source dictionary."""
    return {
        "id": source_id,
        "title": title,
        "url": url,
        "source_type": source_type,
        "published_year": 2024,
    }


class TestTeacherAgent:
    """Tests for the main teacher_agent function."""

    def test_teacher_generates_beginner_response(self):
        """Should generate a beginner-level response."""
        claims = [make_claim("RAG", "RAG improves factuality")]
        sources = [make_source()]
        llm = FakeLLMClient(
            response="""## Introduction to RAG
RAG is a simple technology that helps AI find and use information.

## Key Points
RAG improves factuality [s1].

## Sources
[s1] Test Source: https://example.com/1"""
        )
        state = make_state(user_level="beginner", claims=claims, sources=sources)

        result = teacher_agent(state, llm_client=llm)

        assert "final_response" in result
        assert result["current_agent"] == "teacher"
        assert result["status"] == "completed"

    def test_teacher_generates_intermediate_response(self):
        """Should generate an intermediate-level response."""
        claims = [make_claim("RAG", "RAG improves factuality")]
        sources = [make_source()]
        llm = FakeLLMClient(
            response="""## Introduction to RAG
RAG is a technique that combines retrieval and generation.

## Key Points
RAG improves factual accuracy in LLMs [s1]."""
        )
        state = make_state(user_level="intermediate", claims=claims, sources=sources)

        result = teacher_agent(state, llm_client=llm)

        assert "final_response" in result

    def test_teacher_generates_expert_response(self):
        """Should generate an expert-level response."""
        claims = [make_claim("RAG", "RAG improves factuality")]
        sources = [make_source()]
        llm = FakeLLMClient(
            response="""## Introduction to RAG
Retrieval-Augmented Generation (Lewis et al., 2020) addresses parametric knowledge limitations.

## Technical Analysis
RAG improves factuality [s1]."""
        )
        state = make_state(user_level="expert", claims=claims, sources=sources)

        result = teacher_agent(state, llm_client=llm)

        assert "final_response" in result

    def test_handles_empty_claims(self):
        """Should handle empty claims gracefully."""
        llm = FakeLLMClient(response="# Answer\n\nNo claims available.")
        state = make_state(claims=[])

        result = teacher_agent(state, llm_client=llm)

        assert "final_response" in result

    def test_llm_failure_falls_back(self):
        """Should fall back when LLM fails."""
        claims = [make_claim("RAG", "RAG improves factuality")]
        llm = FakeLLMClient(raise_exc=RuntimeError("LLM unavailable"))
        state = make_state(claims=claims)

        result = teacher_agent(state, llm_client=llm)

        assert "final_response" in result
        assert "RAG" in result["final_response"]

    def test_ensures_citations_are_present(self):
        """Should add a note if no citations are present."""
        claims = [make_claim("RAG", "RAG improves factuality")]
        response = "# Answer\n\nRAG improves factuality."
        result = _ensure_citations(response, claims)

        assert "based on 1 claim(s)" in result

    def test_skips_citations_if_present(self):
        """Should not add extra citations if already present."""
        claims = [make_claim("RAG", "RAG improves factuality")]
        response = "# Answer\n\nRAG improves factuality [s1]."
        result = _ensure_citations(response, claims)

        assert "based on" not in result


class TestFormatHelpers:
    """Tests for formatting helper functions."""

    def test_format_claims_with_sources(self):
        """Should format claims with sources correctly."""
        claims = [
            make_claim("RAG", "RAG improves factuality", confidence=0.9, source_id="s1"),
            make_claim("RAG", "RAG reduces hallucinations", confidence=0.85, source_id="s2"),
        ]
        result = _format_claims_with_sources(claims)

        assert "RAG" in result
        assert "factuality" in result
        assert "0.90" in result
        assert "hallucinations" in result
        assert "0.85" in result

    def test_format_claims_empty(self):
        """Should handle empty claims."""
        result = _format_claims_with_sources([])
        assert result == "No claims available."

    def test_format_sources(self):
        """Should format sources correctly."""
        sources = [make_source(source_id="s1", title="Test Paper", url="https://example.com/1", source_type="arxiv")]
        state = {"sources": sources}
        result = _format_sources(state)

        assert "[s1]" in result
        assert "Test Paper" in result
        assert "https://example.com/1" in result
        assert "arxiv" in result

    def test_format_sources_empty(self):
        """Should handle empty sources."""
        state = {"sources": []}
        result = _format_sources(state)
        assert result == ""

    def test_clean_response_removes_fences(self):
        """Should remove markdown code fences."""
        response = "```markdown\n# Answer\n\nContent\n```"
        result = _clean_response(response)
        assert "```" not in result
        assert "# Answer" in result

    def test_clean_response_strips_whitespace(self):
        """Should strip extra whitespace."""
        response = "   \n\n# Answer\n\n   "
        result = _clean_response(response)
        assert result == "# Answer"

    def test_build_fallback_response(self):
        """Should build a fallback response from claims."""
        claims = [make_claim("RAG", "RAG improves factuality")]
        result = _build_fallback_response("What is RAG?", "", claims, "beginner")

        assert "What is RAG?" in result
        assert "RAG" in result
        assert "[s1]" in result