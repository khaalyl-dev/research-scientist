"""
Unit tests for src/agents/reasoning.py.

All tests use an injected fake LLM client — no real API calls, no API keys required.
"""


from src.agents.reasoning import (
    _build_fallback_plan,
    _extract_plan,
    _format_claims,
    _format_contradictions,
    reasoning_agent,
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
    claims=None,
    contradictions=None,
):
    """Create a test state dictionary."""
    return {
        "query": query,
        "user_level": user_level,
        "claims": claims or [],
        "contradictions": contradictions or [],
    }


def make_claim(entity: str, claim: str, confidence: float = 0.9, source_id: str = "s1"):
    """Create a test claim dictionary."""
    return {
        "entity": entity,
        "claim": claim,
        "confidence": confidence,
        "source_id": source_id,
    }


def make_contradiction(
    claim_a: str,
    claim_b: str,
    similarity_score: float = 0.87,
    source_a_id: str = "s1",
    source_b_id: str = "s2",
    explanation: str = "Sources disagree.",
):
    """Create a test contradiction dictionary."""
    return {
        "claim_a": claim_a,
        "claim_b": claim_b,
        "similarity_score": similarity_score,
        "source_a_id": source_a_id,
        "source_b_id": source_b_id,
        "explanation": explanation,
    }


class TestReasoningAgent:
    """Tests for the main reasoning_agent function."""

    def test_returns_reasoning_with_claims(self):
        """Happy path: reasoning with claims only."""
        claims = [
            make_claim("RAG", "RAG improves factuality"),
            make_claim("RAG", "RAG uses retrieval"),
        ]
        llm = FakeLLMClient(
            response="""# Answer Plan

## Introduction
RAG is a technique that combines retrieval and generation.

## Key Concepts
- RAG: Retrieval-Augmented Generation

## Evidence Summary
Multiple sources support RAG's effectiveness.

## Conclusion
RAG is an effective approach."""
        )
        state = make_state(claims=claims)

        result = reasoning_agent(state, llm_client=llm)

        assert "reasoning" in result
        assert "RAG" in result["reasoning"]
        assert result["current_agent"] == "reasoning"

    def test_handles_empty_claims(self):
        """Should handle empty claims gracefully."""
        llm = FakeLLMClient(response="# Answer Plan\n\nNo claims available.")
        state = make_state(claims=[])

        result = reasoning_agent(state, llm_client=llm)

        assert "reasoning" in result
        assert result["current_agent"] == "reasoning"

    def test_handles_contradictions(self):
        """Should include contradictions in the reasoning plan."""
        claims = [
            make_claim("RAG", "RAG improves factuality"),
            make_claim("RAG", "RAG can hallucinate"),
        ]
        contradictions = [
            make_contradiction(
                claim_a="RAG improves factuality",
                claim_b="RAG can hallucinate",
                similarity_score=0.87,
                explanation="Sources disagree on RAG's effectiveness.",
            )
        ]
        llm = FakeLLMClient(
            response="""# Answer Plan

## Introduction
RAG is a technique with some debate.

## Contradictions
Sources disagree on whether RAG improves factuality or causes hallucinations.

## Conclusion
Mixed evidence on RAG's effectiveness."""
        )
        state = make_state(claims=claims, contradictions=contradictions)

        result = reasoning_agent(state, llm_client=llm)

        assert "reasoning" in result
        assert (
        "contradictions" in result["reasoning"].lower()
        or "disagree" in result["reasoning"].lower()
    )

    def test_llm_failure_falls_back(self):
        """Should fall back to a simple plan when LLM fails."""
        claims = [make_claim("RAG", "RAG improves factuality")]
        llm = FakeLLMClient(raise_exc=RuntimeError("LLM unavailable"))
        state = make_state(claims=claims)

        result = reasoning_agent(state, llm_client=llm)

        assert "reasoning" in result
        assert "RAG" in result["reasoning"]
        assert "improves factuality" in result["reasoning"]
        assert result["current_agent"] == "reasoning"

    def test_empty_claims_fallback(self):
        """Fallback plan with no claims should indicate no data."""
        llm = FakeLLMClient(raise_exc=RuntimeError("LLM unavailable"))
        state = make_state(claims=[])

        result = reasoning_agent(state, llm_client=llm)

        assert "No claims available" in result["reasoning"]

    def test_contradictions_in_fallback(self):
        """Fallback plan should include contradictions if present."""
        claims = [make_claim("RAG", "RAG improves factuality")]
        contradictions = [
            make_contradiction(
                claim_a="RAG improves factuality",
                claim_b="RAG can hallucinate",
            )
        ]
        llm = FakeLLMClient(raise_exc=RuntimeError("LLM unavailable"))
        state = make_state(claims=claims, contradictions=contradictions)

        result = reasoning_agent(state, llm_client=llm)

        assert "contradictions" in result["reasoning"].lower()
        assert "1 contradictions" in result["reasoning"]


class TestFormatHelpers:
    """Tests for the formatting helper functions."""

    def test_format_claims_empty(self):
        """Empty claims should return a message."""
        assert _format_claims([]) == "No claims available."

    def test_format_claims_with_claims(self):
        """Claims should be formatted correctly."""
        claims = [
            make_claim("RAG", "RAG improves factuality", confidence=0.9, source_id="s1"),
            make_claim("Retrieval", "Retrieval is key", confidence=0.85, source_id="s2"),
        ]
        result = _format_claims(claims)

        assert "RAG" in result
        assert "factuality" in result
        assert "0.90" in result
        assert "Retrieval" in result

    def test_format_contradictions_empty(self):
        """Empty contradictions should return a message."""
        assert _format_contradictions([]) == "No contradictions detected."

    def test_format_contradictions_with_contradictions(self):
        """Contradictions should be formatted correctly."""
        contradictions = [
            make_contradiction(
                claim_a="RAG improves factuality",
                claim_b="RAG can hallucinate",
                similarity_score=0.87,
                explanation="Sources disagree.",
            )
        ]
        result = _format_contradictions(contradictions)

        assert "factuality" in result
        assert "hallucinate" in result
        assert "0.87" in result
        assert "Sources disagree" in result


class TestExtractPlan:
    """Tests for the plan extraction helper."""

    def test_extracts_clean_markdown(self):
        """Should clean markdown response."""
        response = """
        # Answer Plan

        ## Introduction
        This is a test plan.
        """
        result = _extract_plan(response)
        assert "# Answer Plan" in result
        assert "Introduction" in result

    def test_removes_code_fences(self):
        """Should remove markdown code fences."""
        response = "```markdown\n# Answer Plan\n\n## Introduction\n```"
        result = _extract_plan(response)
        assert "```" not in result
        assert "# Answer Plan" in result

    def test_handles_empty_response(self):
        """Should handle empty responses gracefully."""
        result = _extract_plan("")
        assert result == ""

    def test_handles_whitespace(self):
        """Should strip extra whitespace."""
        response = "   \n\n# Answer Plan\n\n   "
        result = _extract_plan(response)
        assert result == "# Answer Plan"


class TestFallbackPlan:
    """Tests for the fallback plan generator."""

    def test_builds_plan_with_claims(self):
        """Should build a plan from claims."""
        claims = [
            make_claim("RAG", "RAG improves factuality"),
            make_claim("Retrieval", "Retrieval is key"),
        ]
        result = _build_fallback_plan("What is RAG?", claims, [])

        assert "What is RAG?" in result
        assert "RAG" in result
        assert "Retrieval" in result
        assert "2 claims" in result

    def test_builds_plan_with_contradictions(self):
        """Should include contradictions in fallback plan."""
        claims = [make_claim("RAG", "RAG improves factuality")]
        contradictions = [
            make_contradiction(
                claim_a="RAG improves factuality",
                claim_b="RAG can hallucinate",
            )
        ]
        result = _build_fallback_plan("What is RAG?", claims, contradictions)

        assert "contradictions" in result.lower()

    def test_builds_plan_without_claims(self):
        """Should handle no claims."""
        result = _build_fallback_plan("What is RAG?", [], [])
        assert "No claims available" in result
