"""
Knowledge Graph module using NetworkX.

Builds a graph from extracted claims where:
- Nodes = entities (concepts, technologies, methods)
- Edges = relationships (claims connect entities)
- Each node stores metadata: type, description, sources
- Each edge stores: claim text, confidence, source_id
"""

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import networkx as nx

from src.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeGraph:
    """
    Knowledge graph builder and manager using NetworkX.

    Attributes:
        graph: NetworkX Graph object
        session_id: Unique identifier for the session
    """

    def __init__(self, session_id: Optional[str] = None):
        self.graph = nx.Graph()
        self.session_id = session_id or str(uuid.uuid4())
        self._entity_cache: Dict[str, Set[str]] = {}

    def build_from_claims(self, claims: List[Dict[str, Any]]) -> int:
        """
        Build the knowledge graph from a list of claims.

        Args:
            claims: List of claim dictionaries with entity, claim, source_id, confidence

        Returns:
            Number of nodes added
        """
        if not claims:
            logger.warning("No claims provided to build graph")
            return 0

        nodes_added = 0

        for claim in claims:
            entity = claim.get("entity", "").strip()
            claim_text = claim.get("claim", "").strip()
            source_id = claim.get("source_id", "unknown")
            confidence = claim.get("confidence", 0.5)

            if not entity:
                continue

            # Add entity node
            if not self.graph.has_node(entity):
                self.graph.add_node(
                    entity,
                    type="entity",
                    description=claim_text[:200] if claim_text else "",
                    sources=[source_id] if source_id else [],
                    confidence=confidence,
                )
                nodes_added += 1
            else:
                existing_sources = self.graph.nodes[entity].get("sources", [])
                if source_id and source_id not in existing_sources:
                    existing_sources.append(source_id)
                    self.graph.nodes[entity]["sources"] = existing_sources

            # Track claims for entity
            if entity not in self._entity_cache:
                self._entity_cache[entity] = set()
            if claim_text:
                self._entity_cache[entity].add(claim_text)

        # Build edges between related entities
        self._build_edges()

        logger.info(
            f"Built knowledge graph: {self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges from {len(claims)} claims"
        )
        return nodes_added

    def _build_edges(self) -> None:
        """Build edges between entities that are related."""
        entities = list(self.graph.nodes)
        edges_added = 0

        for i, entity_a in enumerate(entities):
            for entity_b in entities[i + 1:]:
                if self._are_entities_related(entity_a, entity_b):
                    self.graph.add_edge(
                        entity_a,
                        entity_b,
                        relationship="related",
                        weight=0.5,
                    )
                    edges_added += 1

        if edges_added:
            logger.info(f"Added {edges_added} edges to knowledge graph")

    def _are_entities_related(self, entity_a: str, entity_b: str) -> bool:
        """Determine if two entities are related based on their claims."""
        claims_a = self._entity_cache.get(entity_a, set())
        claims_b = self._entity_cache.get(entity_b, set())

        if not claims_a or not claims_b:
            return False

        combined_a = " ".join(claims_a).lower()
        combined_b = " ".join(claims_b).lower()

        entity_a_lower = entity_a.lower()
        entity_b_lower = entity_b.lower()

        return entity_b_lower in combined_a or entity_a_lower in combined_b

    def add_entity(self, name: str, description: str = "", source_id: str = "") -> None:
        """Add a single entity to the graph."""
        if not self.graph.has_node(name):
            self.graph.add_node(
                name,
                type="entity",
                description=description[:200],
                sources=[source_id] if source_id else [],
                confidence=0.5,
            )
            logger.info(f"Added entity: {name}")

    def add_relationship(
        self,
        entity_a: str,
        entity_b: str,
        relationship: str = "related",
        weight: float = 0.5,
    ) -> None:
        """Add a relationship between two entities."""
        if not self.graph.has_node(entity_a):
            self.add_entity(entity_a)
        if not self.graph.has_node(entity_b):
            self.add_entity(entity_b)

        self.graph.add_edge(entity_a, entity_b, relationship=relationship, weight=weight)

    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get all nodes with their metadata."""
        return [
            {"id": node, **data}
            for node, data in self.graph.nodes(data=True)
        ]

    def get_edges(self) -> List[Dict[str, Any]]:
        """Get all edges with their metadata."""
        return [
            {"source": u, "target": v, **data}
            for u, v, data in self.graph.edges(data=True)
        ]

    def get_node_count(self) -> int:
        """Return the number of nodes in the graph."""
        return self.graph.number_of_nodes()

    def get_edge_count(self) -> int:
        """Return the number of edges in the graph."""
        return self.graph.number_of_edges()

    def export_json(self, filepath: Path) -> None:
        """
        Export the graph to a JSON file.

        Args:
            filepath: Path to save the JSON file
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "session_id": self.session_id,
            "nodes": self.get_nodes(),
            "edges": self.get_edges(),
            "metadata": {
                "node_count": self.get_node_count(),
                "edge_count": self.get_edge_count(),
            },
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported knowledge graph to {filepath}")

    @classmethod
    def import_json(cls, filepath: Path) -> "KnowledgeGraph":
        """
        Import a knowledge graph from a JSON file.

        Args:
            filepath: Path to the JSON file

        Returns:
            KnowledgeGraph instance
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        kg = cls(session_id=data.get("session_id"))

        for node_data in data.get("nodes", []):
            node_id = node_data.pop("id")
            kg.graph.add_node(node_id, **node_data)

        for edge_data in data.get("edges", []):
            source = edge_data.pop("source")
            target = edge_data.pop("target")
            kg.graph.add_edge(source, target, **edge_data)

        logger.info(f"Imported knowledge graph from {filepath}")
        return kg

    def to_vis_data(self) -> Dict[str, List]:
        """
        Convert the graph to a format compatible with pyvis/vis.js.

        Returns:
            Dictionary with nodes and edges lists
        """
        nodes = []
        for node, data in self.graph.nodes(data=True):
            nodes.append({
                "id": node,
                "label": node,
                "title": data.get("description", ""),
                "sources": data.get("sources", []),
                "confidence": data.get("confidence", 0.5),
                "size": 20 + (data.get("confidence", 0.5) * 20),
            })

        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                "from": u,
                "to": v,
                "label": data.get("relationship", "related"),
                "weight": data.get("weight", 0.5),
            })

        return {"nodes": nodes, "edges": edges}

    def clear(self) -> None:
        """Clear the graph."""
        self.graph.clear()
        self._entity_cache.clear()
        logger.info("Knowledge graph cleared")
