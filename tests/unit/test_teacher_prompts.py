"""
Unit tests for level-specific prompts.
"""


from prompts.teacher_prompts import (
    BEGINNER_PROMPT,
    EXPERT_PROMPT,
    INTERMEDIATE_PROMPT,
    build_prompt_context,
    get_teacher_prompt,
)


class TestTeacherPrompts:
    """Tests for the level-specific prompt system."""

    def test_get_teacher_prompt_beginner(self):
        """Should return beginner prompt for 'beginner' level."""
        prompt = get_teacher_prompt("beginner")
        assert "patient, encouraging teacher" in prompt
        assert "simple, everyday language" in prompt

    def test_get_teacher_prompt_intermediate(self):
        """Should return intermediate prompt for 'intermediate' level."""
        prompt = get_teacher_prompt("intermediate")
        assert "knowledgeable educator" in prompt
        assert "Balance technical accuracy" in prompt

    def test_get_teacher_prompt_expert(self):
        """Should return expert prompt for 'expert' level."""
        prompt = get_teacher_prompt("expert")
        assert "senior researcher" in prompt
        assert "technically rigorous" in prompt

    def test_get_teacher_prompt_default(self):
        """Should return intermediate prompt for unknown level."""
        prompt = get_teacher_prompt("unknown")
        assert "knowledgeable educator" in prompt

    def test_build_prompt_context(self):
        """Should build the full prompt context."""
        context = build_prompt_context(
            user_level="beginner",
            query="What is RAG?",
            reasoning="# Answer Plan\n\nRAG combines retrieval and generation.",
            claims="- **RAG**: RAG improves factuality [s1]",
        )

        assert "template" in context
        assert "context" in context
        assert context["context"]["query"] == "What is RAG?"
        assert "RAG combines retrieval" in context["context"]["reasoning"]

    def test_beginner_prompt_has_analogies(self):
        """Beginner prompt should emphasize analogies."""
        assert "analogy" in BEGINNER_PROMPT.lower()

    def test_intermediate_prompt_has_balance(self):
        """Intermediate prompt should emphasize balance."""
        assert "Balance technical accuracy" in INTERMEDIATE_PROMPT

    def test_expert_prompt_has_technical_depth(self):
        """Expert prompt should emphasize technical depth."""
        assert "technically rigorous" in EXPERT_PROMPT
        assert "papers" in EXPERT_PROMPT
