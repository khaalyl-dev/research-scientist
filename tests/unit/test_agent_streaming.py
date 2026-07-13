"""
Unit tests for agent streaming helpers (US-07) — no Streamlit runtime needed.
"""

from app.components.agent_progress import (
    build_agent_narrative,
    stream_agent_text,
    stream_lines,
    stream_words,
)


class TestBuildAgentNarrative:
    def test_planner_lists_sub_queries(self):
        text = build_agent_narrative(
            "planner",
            {},
            {
                "sub_queries": ["RAG overview", "RAG vs fine-tuning"],
                "source_types": ["arxiv", "web"],
            },
        )
        assert "### Planner" in text
        assert "RAG overview" in text
        assert "arxiv" in text

    def test_researcher_lists_sources(self):
        text = build_agent_narrative(
            "researcher",
            {},
            {
                "sources": [
                    {"title": "Paper A", "url": "https://example.com/a"},
                    {"title": "Paper B", "url": "https://example.com/b"},
                ]
            },
        )
        assert "### Researcher" in text
        assert "Paper A" in text
        assert "**2**" in text

    def test_extractor_shows_batch_and_total(self):
        text = build_agent_narrative(
            "extractor",
            {"claims": [{"entity": "RAG", "claim": "helps", "confidence": 0.9}]},
            {
                "claims": [
                    {"entity": "RAG", "claim": "helps", "confidence": 0.9},
                    {"entity": "FAISS", "claim": "fast", "confidence": 0.8},
                ]
            },
        )
        assert "### Extractor" in text
        assert "+**1**" in text
        assert "total cumulé **2**" in text
        assert "RAG" in text

    def test_fact_checker_empty_contradictions(self):
        text = build_agent_narrative(
            "fact_checker",
            {},
            {"contradictions": [], "has_contradictions": False},
        )
        assert "### FactChecker" in text
        assert "**0**" in text

    def test_reasoner_and_teacher_include_body(self):
        reasoning = build_agent_narrative(
            "reasoner", {"reasoning": "Plan: define then compare."}, {}
        )
        assert "Plan: define then compare." in reasoning

        teacher = build_agent_narrative(
            "teacher",
            {},
            {"final_response": "# Answer\n\nRAG retrieves context."},
        )
        assert "### Teacher" in teacher
        assert "RAG retrieves context." in teacher


class TestStreamHelpers:
    def test_stream_words_yields_all_tokens(self):
        chunks = list(stream_words("hello world", delay_s=0))
        assert "".join(chunks) == "hello world"

    def test_stream_lines_preserves_newlines(self):
        text = "a\nb\n"
        assert "".join(stream_lines(text, delay_s=0)) == text

    def test_stream_agent_text_uses_lines_for_markdown(self):
        text = "### Title\n\n- item\n"
        assert "".join(stream_agent_text(text)) == text
