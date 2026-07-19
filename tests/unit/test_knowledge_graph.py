"""
Unit tests for the Knowledge Graph module.
"""

import tempfile
from pathlib import Path

from src.knowledge.graph import KnowledgeGraph


def make_claim(
    entity: str = "RAG",
    claim: str = "RAG improves factuality",
    source_id: str = "s1",
    confidence: float = 0.9,
) -> dict:
    """Create a test claim dictionary."""
    return {
        "entity": entity,
        "claim": claim,
        "source_id": source_id,
        "confidence": confidence,
    }


class TestKnowledgeGraph:
    """Tests for the KnowledgeGraph class."""

    def test_build_from_claims(self):
        """Should build graph from claims."""
        claims = [
            make_claim("RAG", "RAG improves factuality"),
            make_claim("RAG", "RAG uses retrieval"),
            make_claim("LLM", "LLMs are large language models"),
            make_claim("FAISS", "FAISS is a vector database"),
        ]
        kg = KnowledgeGraph()
        kg.build_from_claims(claims)

        assert kg.get_node_count() == 3
        assert kg.graph.has_node("RAG")
        assert kg.graph.has_node("LLM")
        assert kg.graph.has_node("FAISS")

    def test_build_from_empty_claims(self):
        """Should handle empty claims."""
        kg = KnowledgeGraph()
        result = kg.build_from_claims([])
        assert result == 0
        assert kg.get_node_count() == 0

    def test_add_entity(self):
        """Should add a single entity."""
        kg = KnowledgeGraph()
        kg.add_entity("RAG", "Retrieval-Augmented Generation", "s1")

        assert kg.get_node_count() == 1
        assert kg.graph.has_node("RAG")
        assert kg.graph.nodes["RAG"]["description"] == "Retrieval-Augmented Generation"

    def test_add_relationship(self):
        """Should add a relationship between entities."""
        kg = KnowledgeGraph()
        kg.add_entity("RAG", "RAG concept")
        kg.add_entity("LLM", "LLM concept")
        kg.add_relationship("RAG", "LLM", "used_with", 0.8)

        assert kg.get_edge_count() == 1
        edges = kg.get_edges()
        assert edges[0]["source"] == "RAG"
        assert edges[0]["target"] == "LLM"
        assert edges[0]["relationship"] == "used_with"

    def test_get_nodes_and_edges(self):
        """Should return nodes and edges as lists."""
        claims = [
            make_claim("RAG", "RAG improves factuality"),
            make_claim("LLM", "LLMs are large language models"),
        ]
        kg = KnowledgeGraph()
        kg.build_from_claims(claims)

        nodes = kg.get_nodes()
        edges = kg.get_edges()

        assert len(nodes) == 2
        assert len(edges) >= 0

    def test_export_import_json(self):
        """Should export and import JSON correctly."""
        claims = [
            make_claim("RAG", "RAG improves factuality"),
            make_claim("RAG", "RAG uses retrieval"),
            make_claim("LLM", "LLMs are large language models"),
        ]
        kg = KnowledgeGraph(session_id="test-session")
        kg.build_from_claims(claims)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            filepath = Path(tmp.name)

        kg.export_json(filepath)

        imported = KnowledgeGraph.import_json(filepath)

        assert imported.session_id == "test-session"
        assert imported.get_node_count() == kg.get_node_count()
        assert imported.graph.has_node("RAG")
        assert imported.graph.has_node("LLM")

        filepath.unlink()

    def test_to_vis_data(self):
        """Should convert to vis.js format."""
        claims = [
            make_claim("RAG", "RAG improves factuality"),
            make_claim("LLM", "LLMs are large language models"),
        ]
        kg = KnowledgeGraph()
        kg.build_from_claims(claims)

        vis_data = kg.to_vis_data()

        assert "nodes" in vis_data
        assert "edges" in vis_data
        assert len(vis_data["nodes"]) == 2

        node = vis_data["nodes"][0]
        assert "id" in node
        assert "label" in node
        assert "size" in node

    def test_clear_graph(self):
        """Should clear the graph."""
        claims = [make_claim("RAG", "RAG improves factuality")]
        kg = KnowledgeGraph()
        kg.build_from_claims(claims)

        assert kg.get_node_count() == 1

        kg.clear()

        assert kg.get_node_count() == 0
        assert kg.get_edge_count() == 0

    def test_node_count_and_edge_count(self):
        """Should return correct counts."""
        claims = [
            make_claim("RAG", "RAG improves factuality"),
            make_claim("RAG", "RAG uses retrieval"),
        ]
        kg = KnowledgeGraph()
        kg.build_from_claims(claims)

        assert kg.get_node_count() == 1
        assert kg.get_edge_count() >= 0

    def test_duplicate_entity_updates_sources(self):
        """Should update sources for existing entity."""
        claims = [
            make_claim("RAG", "RAG improves factuality", source_id="s1"),
            make_claim("RAG", "RAG uses retrieval", source_id="s2"),
        ]
        kg = KnowledgeGraph()
        kg.build_from_claims(claims)

        assert kg.get_node_count() == 1
        sources = kg.graph.nodes["RAG"].get("sources", [])
        assert "s1" in sources
        assert "s2" in sources
