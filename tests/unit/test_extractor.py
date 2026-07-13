"""
Unit tests for src/agents/extractor.py.

The LLM is injected as a fake returning canned text — no real API calls,
no dependency on Khalil's/Zeineb's actual llm_client.py being importable
with real credentials.
"""

from src.agents.extractor import MAX_CLAIMS_PER_SOURCE, extractor_node
from src.schemas.common import SourceType


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


def make_send_state(
    content: str = "Some real content about RAG.", title: str = "RAG paper"
) -> dict:
    """Matches exactly what Send() constructs in graph.py: {"source": ..., "session_id": ...}"""
    return {
        "source": {
            "id": "src-1",
            "source_type": SourceType.arxiv.value,
            "title": title,
            "url": "https://arxiv.org/abs/1",
            "content": content,
            "published_year": 2025,
        },
        "session_id": "sess-1",
    }


class TestExtractorNode:
    def test_extracts_valid_claims_from_clean_json(self):
        llm = FakeLLMClient(
            response='[{"entity": "RAG", "claim": "RAG improves factuality", "confidence": 0.9}]'
        )
        result = extractor_node(make_send_state(), llm_client=llm)

        assert len(result["claims"]) == 1
        claim = result["claims"][0]
        assert claim["entity"] == "RAG"
        assert claim["confidence"] == 0.9
        assert claim["source_id"] == "src-1"
        assert claim["source_url"] == "https://arxiv.org/abs/1"

    def test_returns_claims_as_dicts_not_objects(self):
        llm = FakeLLMClient(response='[{"entity": "X", "claim": "Y", "confidence": 0.8}]')
        result = extractor_node(make_send_state(), llm_client=llm)
        assert isinstance(result["claims"][0], dict)

    def test_handles_markdown_fenced_json(self):
        llm = FakeLLMClient(
            response='```json\n[{"entity": "X", "claim": "Y", "confidence": 0.7}]\n```'
        )
        result = extractor_node(make_send_state(), llm_client=llm)
        assert len(result["claims"]) == 1

    def test_handles_prose_wrapped_around_json(self):
        llm = FakeLLMClient(
            response=(
                "Sure, here are the claims:\n"
                '[{"entity": "X", "claim": "Y", "confidence": 0.6}]\n'
                "Hope that helps!"
            )
        )
        result = extractor_node(make_send_state(), llm_client=llm)
        assert len(result["claims"]) == 1

    def test_empty_array_response_yields_no_claims(self):
        llm = FakeLLMClient(response="[]")
        result = extractor_node(make_send_state(), llm_client=llm)
        assert result["claims"] == []

    def test_completely_malformed_response_degrades_to_empty_not_exception(self):
        llm = FakeLLMClient(response="I cannot help with that request.")
        result = extractor_node(make_send_state(), llm_client=llm)
        assert result["claims"] == []

    def test_one_malformed_claim_does_not_discard_valid_siblings(self):
        llm = FakeLLMClient(
            response=(
                '[{"entity": "Good", "claim": "This one is valid", "confidence": 0.9}, '
                '{"entity": "Bad", "confidence": "not-a-number"}]'
                # missing "claim" AND bad confidence type
            )
        )
        result = extractor_node(make_send_state(), llm_client=llm)
        assert len(result["claims"]) == 1
        assert result["claims"][0]["entity"] == "Good"

    def test_confidence_out_of_range_is_dropped_not_fatal(self):
        llm = FakeLLMClient(
            response=(
                '[{"entity": "OK", "claim": "valid claim", "confidence": 0.5}, '
                '{"entity": "Bad", "claim": "invalid confidence", "confidence": 1.7}]'
            )
        )
        result = extractor_node(make_send_state(), llm_client=llm)
        assert len(result["claims"]) == 1
        assert result["claims"][0]["entity"] == "OK"

    def test_llm_exception_does_not_crash_returns_empty_claims(self):
        llm = FakeLLMClient(raise_exc=RuntimeError("Groq API down"))
        result = extractor_node(make_send_state(), llm_client=llm)
        assert result["claims"] == []

    def test_empty_source_content_skips_llm_call_entirely(self):
        llm = FakeLLMClient(
            response='[{"entity": "should not appear", "claim": "x", "confidence": 0.9}]'
        )
        result = extractor_node(make_send_state(content=""), llm_client=llm)
        assert result["claims"] == []
        assert llm.prompts_seen == []  # never even called the LLM

    def test_does_not_return_current_agent_key(self):
        """Regression guard for the exact bug documented in Task 1's
        'Issues Encountered' table: parallel Send() branches must not all
        write to a shared single-value key like current_agent."""
        llm = FakeLLMClient(response='[{"entity": "X", "claim": "Y", "confidence": 0.8}]')
        result = extractor_node(make_send_state(), llm_client=llm)
        assert "current_agent" not in result
        assert set(result.keys()) == {"claims"}

    def test_caps_claims_at_max_per_source(self):
        many_claims = [
            {"entity": f"E{i}", "claim": f"claim {i}", "confidence": 0.8} for i in range(20)
        ]
        import json

        llm = FakeLLMClient(response=json.dumps(many_claims))
        result = extractor_node(make_send_state(), llm_client=llm)
        assert len(result["claims"]) <= MAX_CLAIMS_PER_SOURCE

    def test_content_truncated_in_prompt_for_very_long_sources(self):
        long_content = "word " * 10_000  # way over the cap
        llm = FakeLLMClient(response="[]")
        extractor_node(make_send_state(content=long_content), llm_client=llm)
        assert (
            len(llm.prompts_seen[0]) < len(long_content) + 1000
        )  # prompt didn't balloon with full content
