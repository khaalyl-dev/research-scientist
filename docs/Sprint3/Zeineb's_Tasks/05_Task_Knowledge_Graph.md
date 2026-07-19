# Sprint 3 — Task 5: Knowledge Graph (NetworkX)

## Overview

### Objective

Implement a knowledge graph using **NetworkX** that builds a visual representation of relationships between entities extracted from claims, with support for export, import, and visualization-ready data formatting.

| Field | Value |
|-------|-------|
| **User Story** | US-09 |
| **Status** | Completed |

---

## Description

The **Knowledge Graph** module transforms extracted claims into a structured graph where entities become nodes and relationships between them become edges. This graph serves as the foundation for the interactive visualization in Streamlit and enables users to explore connections between concepts discovered during research.

---

## Key Responsibilities

### Entity Extraction

Identify unique entities from claims and create graph nodes.

### Relationship Discovery

Connect entities that appear in related contexts.

### Metadata Storage

Store confidence scores, source references, and descriptions on nodes.

### Persistence

Export graphs to JSON and import them from JSON.

### Visualization Preparation

Format graph data for Pyvis/vis.js rendering.

### Session Management

Track graphs by session ID.

---

## Why This Matters

The knowledge graph provides a visual summary of the research findings. Users can see which concepts are connected, how they relate, and which sources support each connection. This transforms raw claims into an explorable knowledge network.

---

## Pipeline Position

```text
Extractor (claims) → Knowledge Graph → Pyvis Visualization → Streamlit UI
```

---

# Implementation

## File Structure

| File | Description |
|------|-------------|
| `src/knowledge/graph.py` | Full Knowledge Graph implementation using NetworkX |
| `src/knowledge/__init__.py` | Package exports |
| `tests/unit/test_knowledge_graph.py` | Unit tests for the Knowledge Graph |

---

## Core Logic — `KnowledgeGraph` Class

The `KnowledgeGraph` class provides a clean interface for building and managing knowledge graphs.

| Method | Description |
|--------|-------------|
| `build_from_claims()` | Build graph from a list of claim dictionaries |
| `add_entity()` | Add a single entity node |
| `add_relationship()` | Add an edge between two entities |
| `export_json()` | Save graph to a JSON file |
| `import_json()` | Load graph from a JSON file |
| `to_vis_data()` | Convert graph to vis.js format |
| `get_nodes()` | Get all nodes with metadata |
| `get_edges()` | Get all edges with metadata |
| `clear()` | Clear the graph |

---

# Graph Structure

## Nodes

| Property | Description |
|----------|-------------|
| `id` | Entity name |
| `type` | Always `"entity"` |
| `description` | Claim text or description |
| `sources` | List of source IDs |
| `confidence` | Average confidence score |

---

## Edges

| Property | Description |
|----------|-------------|
| `source` | First entity |
| `target` | Second entity |
| `relationship` | Type of relationship (default: `"related"`) |
| `weight` | Relationship strength |

---

# Entity Relationship Detection

Entities are connected when:

- One entity name appears in the claims of another entity.
- Claims share significant word overlap.

This provides a basic but effective relationship discovery mechanism without requiring external NLP tools.

---

# JSON Export Format

```json
{
  "session_id": "session-uuid",
  "nodes": [
    {
      "id": "RAG",
      "type": "entity",
      "description": "RAG improves factuality",
      "sources": ["s1", "s2"],
      "confidence": 0.9
    }
  ],
  "edges": [
    {
      "source": "RAG",
      "target": "LLM",
      "relationship": "related",
      "weight": 0.5
    }
  ],
  "metadata": {
    "node_count": 5,
    "edge_count": 3
  }
}
```

---

# vis.js Format

The `to_vis_data()` method produces a format compatible with Pyvis.

```python
{
  "nodes": [
    {
      "id": "RAG",
      "label": "RAG",
      "title": "description",
      "size": 30
    }
  ],
  "edges": [
    {
      "from": "RAG",
      "to": "LLM",
      "label": "related"
    }
  ]
}
```

---

# Integration with Existing Components

## Dependencies

| Component | Role |
|-----------|------|
| `networkx` | Graph data structure and algorithms |
| `json` | Serialization for export/import |
| `uuid` | Session ID generation |

---

## Data Flow

```text
Claims from Extractor
    │
    ▼
KnowledgeGraph.build_from_claims()
    │
    ├── Create nodes for unique entities
    ├── Build edges between related entities
    └── Store metadata on nodes
    │
    ▼
Export to JSON (optional)
    │
    ▼
to_vis_data() for Pyvis
```

---

# Testing

## Unit Tests

File:

```
tests/unit/test_knowledge_graph.py
```

The test suite contains 10 unit tests covering all core functionality.

| Test | Purpose |
|------|---------|
| `test_build_from_claims` | Building graph from claims |
| `test_build_from_empty_claims` | Handling empty claims |
| `test_add_entity` | Adding a single entity |
| `test_add_relationship` | Adding a relationship |
| `test_get_nodes_and_edges` | Retrieving nodes and edges |
| `test_export_import_json` | Export and import roundtrip |
| `test_to_vis_data` | Converting to vis.js format |
| `test_clear_graph` | Clearing the graph |
| `test_node_count_and_edge_count` | Counting nodes and edges |
| `test_duplicate_entity_updates_sources` | Updating existing entity sources |

---

# Running the Tests

## Command

```bash
pytest tests/unit/test_knowledge_graph.py -v
```

---

## Expected Output

```text
collected 10 items

test_knowledge_graph.py::TestKnowledgeGraph::test_build_from_claims PASSED
test_knowledge_graph.py::TestKnowledgeGraph::test_build_from_empty_claims PASSED
test_knowledge_graph.py::TestKnowledgeGraph::test_add_entity PASSED
test_knowledge_graph.py::TestKnowledgeGraph::test_add_relationship PASSED
test_knowledge_graph.py::TestKnowledgeGraph::test_get_nodes_and_edges PASSED
test_knowledge_graph.py::TestKnowledgeGraph::test_export_import_json PASSED
test_knowledge_graph.py::TestKnowledgeGraph::test_to_vis_data PASSED
test_knowledge_graph.py::TestKnowledgeGraph::test_clear_graph PASSED
test_knowledge_graph.py::TestKnowledgeGraph::test_node_count_and_edge_count PASSED
test_knowledge_graph.py::TestKnowledgeGraph::test_duplicate_entity_updates_sources PASSED

===================== 10 passed in 0.5s ======================
```

---

# Files Modified and Created

| File | Action | Description |
|------|--------|-------------|
| `src/knowledge/graph.py` | Created | Full Knowledge Graph implementation |
| `src/knowledge/__init__.py` | Created | Package exports |
| `tests/unit/test_knowledge_graph.py` | Created | 10 unit tests |

---

# Handoff Notes for Khalil

## What is Ready

- `src/knowledge/graph.py` fully implemented Knowledge Graph
- `to_vis_data()` ready for Pyvis integration
- Export and import functionality for graph persistence via JSON
- 10 unit tests, all passing

---

## Important Notes

- The graph expects claims in the format: `{entity, claim, source_id, confidence}`.
- Edge detection is intentionally simple but effective for the MVP.
- The graph is session-scoped, with one graph per research session.
- Pyvis visualization consumes the output of `to_vis_data()`.

---

# Task Completion

## Delivered

- Full Knowledge Graph implementation with NetworkX
- Entity and relationship management
- JSON export and import
- vis.js format conversion
- Session ID tracking
- 10 unit tests, all passing

---

# Verification

```bash
pytest tests/unit/test_knowledge_graph.py -v
```

Expected result:

```text
10 tests passed
```

---

# Status

Completed
