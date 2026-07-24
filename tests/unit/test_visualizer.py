"""
Unit tests for the Pyvis visualizer.
"""

import pytest

from src.knowledge import KnowledgeGraph, KnowledgeGraphVisualizer, render_kg_html


def make_claim(
    entity: str = "RAG",
    claim: str = "RAG improves factuality",
    source_id: str = "s1",
    confidence: float = 0.9,
) -> dict:
    """Create a test claim."""
    return {
        "entity": entity,
        "claim": claim,
        "source_id": source_id,
        "confidence": confidence,
        "source_url": "https://example.com/1",
    }


class TestKnowledgeGraphVisualizer:
    """Tests for the KnowledgeGraphVisualizer class."""

    def test_initialization(self):
        """Should initialize with a KnowledgeGraph."""
        kg = KnowledgeGraph()
        visualizer = KnowledgeGraphVisualizer(kg)
        assert visualizer.kg is kg
        assert visualizer.net is None

    def test_render_empty_graph(self):
        """Should render empty state for empty graph."""
        kg = KnowledgeGraph()
        visualizer = KnowledgeGraphVisualizer(kg)
        html = visualizer.render()
        assert "No Graph Available" in html

    def test_render_with_nodes(self):
        """Should render graph with nodes."""
        claims = [
            make_claim("RAG", "RAG improves factuality", "s1", 0.9),
            make_claim("LLM", "LLMs are large", "s2", 0.8),
        ]
        kg = KnowledgeGraph()
        kg.build_from_claims(claims)
        visualizer = KnowledgeGraphVisualizer(kg)
        html = visualizer.render()

        assert kg.get_node_count() == 2
        assert "RAG" in html or "LLM" in html

    def test_get_color_by_confidence(self):
        """Should return correct colors based on confidence."""
        kg = KnowledgeGraph()
        visualizer = KnowledgeGraphVisualizer(kg)

        assert visualizer._get_color(0.9) == "#22c55e"  # green
        assert visualizer._get_color(0.7) == "#f59e0b"  # amber
        assert visualizer._get_color(0.3) == "#ef4444"  # red

    def test_render_kg_html_convenience(self):
        """Should render through convenience function."""
        claims = [make_claim("RAG", "RAG improves factuality", "s1", 0.9)]
        kg = KnowledgeGraph()
        kg.build_from_claims(claims)

        html = render_kg_html(kg, height="500px")
        assert "500px" in html or "No Graph" not in html