"""
Knowledge Graph module using NetworkX.
"""

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import networkx as nx

from src.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeGraph:
    def __init__(self, session_id: Optional[str] = None):
        self.graph = nx.Graph()
        self.session_id = session_id or str(uuid.uuid4())
        self._entity_cache: Dict[str, Set[str]] = {}

    def build_from_claims(self, claims: List[Dict[str, Any]]) -> int:
        """Build graph from claims."""
        if not claims:
            return 0

        nodes_added = 0

        for claim in claims:
            entity = claim.get("entity", "").strip()
            claim_text = claim.get("claim", "").strip()
            source_id = claim.get("source_id", "unknown")
            source_url = claim.get("source_url", "")
            confidence = claim.get("confidence", 0.5)

            if not entity:
                continue

            # Determine source type from URL
            source_type = self._get_source_type(source_url)

            # Add node
            if not self.graph.has_node(entity):
                self.graph.add_node(
                    entity,
                    type="entity",
                    description=claim_text[:200] if claim_text else "",
                    sources=[source_id],
                    confidence=confidence,
                    source_type=source_type,
                )
                nodes_added += 1
            else:
                existing = self.graph.nodes[entity].get("sources", [])
                if source_id not in existing:
                    existing.append(source_id)
                    self.graph.nodes[entity]["sources"] = existing

            if entity not in self._entity_cache:
                self._entity_cache[entity] = set()
            if claim_text:
                self._entity_cache[entity].add(claim_text)

        self._build_edges()
        logger.info(f"Graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
        return nodes_added

    def _build_edges(self) -> None:
        """Build edges between related entities."""
        entities = list(self.graph.nodes)
        for i, a in enumerate(entities):
            for b in entities[i + 1:]:
                if self._are_related(a, b):
                    self.graph.add_edge(a, b, relationship="related", weight=0.5)

    def _are_related(self, a: str, b: str) -> bool:
        """Check if two entities are related."""
        claims_a = self._entity_cache.get(a, set())
        claims_b = self._entity_cache.get(b, set())
        if not claims_a or not claims_b:
            return False
        combined = " ".join(claims_a).lower()
        return b.lower() in combined or a.lower() in " ".join(claims_b).lower()

    def _get_source_type(self, url: str) -> str:
        """Get source type from URL."""
        if not url:
            return "web"
        url = url.lower()
        if "arxiv.org" in url:
            return "arxiv"
        elif "wikipedia.org" in url:
            return "wikipedia"
        elif "doi.org" in url:
            return "openalex"
        elif "pubmed" in url or "ncbi" in url:
            return "pubmed"
        elif "semanticscholar" in url:
            return "scholar"
        return "web"

    def get_nodes(self) -> List[Dict[str, Any]]:
        return [{"id": node, **data} for node, data in self.graph.nodes(data=True)]

    def get_edges(self) -> List[Dict[str, Any]]:
        return [{"source": u, "target": v, **data} for u, v, data in self.graph.edges(data=True)]

    def get_node_count(self) -> int:
        return self.graph.number_of_nodes()

    def get_edge_count(self) -> int:
        return self.graph.number_of_edges()

    def export_json(self, filepath: Path) -> None:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "session_id": self.session_id,
            "nodes": self.get_nodes(),
            "edges": self.get_edges(),
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Exported graph to {filepath}")

    @classmethod
    def import_json(cls, filepath: Path) -> "KnowledgeGraph":
        with open(filepath, "r") as f:
            data = json.load(f)
        kg = cls(session_id=data.get("session_id"))
        for node_data in data.get("nodes", []):
            node_id = node_data.pop("id")
            kg.graph.add_node(node_id, **node_data)
        for edge_data in data.get("edges", []):
            kg.graph.add_edge(edge_data.pop("source"), edge_data.pop("target"), **edge_data)
        return kg

    def to_vis_data(self) -> Dict[str, List]:
        nodes = []
        for node, data in self.graph.nodes(data=True):
            nodes.append({
                "id": node,
                "label": node,
                "title": data.get("description", ""),
                "sources": data.get("sources", []),
                "confidence": data.get("confidence", 0.5),
                "source_type": data.get("source_type", "web"),
                "size": 20 + (data.get("confidence", 0.5) * 30),
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
        self.graph.clear()
        self._entity_cache.clear()