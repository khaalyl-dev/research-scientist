# Sprint 3 — Task 6: Pyvis Visualization

## Overview

### Objective
Implement an interactive knowledge graph visualization using **Pyvis** that displays entities and their relationships in the Streamlit interface, allowing users to explore connections between concepts discovered during research.

| Field | Value |
|--------|-------|
| **User Story** | US-09 |
| **Status** | Completed |
| **Description** | The Pyvis Visualization module transforms the NetworkX knowledge graph into an interactive HTML visualization that can be embedded directly in Streamlit. Users can drag, zoom, click, and explore the graph to better understand relationships between entities discovered during the research process. |

---

# Key Responsibilities

- **Graph rendering** – Convert the NetworkX graph into an interactive Pyvis visualization.
- **Node styling** – Color-code nodes according to confidence level (green, amber, red).
- **Physics configuration** – Enable or disable physics simulation for layout control.
- **Streamlit integration** – Embed the generated HTML using `st.components.v1.html`.
- **Empty state handling** – Display a user-friendly message when no graph is available.
- **Metadata display** – Show confidence scores and source information on node hover.

---

# Why This Matters

The knowledge graph provides an intuitive visual summary of research findings, making it easier than reading raw claims.

Users can:

- Identify central concepts.
- Explore relationships between entities.
- Understand supporting evidence through metadata.
- Interactively navigate the research results.

This transforms abstract claims into an explorable knowledge network.

---

# Pipeline Position

```text
Extractor
      │
      ▼
Knowledge Graph
      │
      ▼
Pyvis Visualization
      │
      ▼
Streamlit UI
```

---

# Implementation

## File Structure

| File | Description |
|------|-------------|
| `src/knowledge/visualizer.py` | Pyvis rendering helper with interactive graph generation |
| `app/views/graphe.py` | Streamlit page for graph visualization |
| `src/knowledge/__init__.py` | Package exports |
| `tests/unit/test_visualizer.py` | Unit tests for the visualizer |

---

# Core Logic

## `KnowledgeGraphVisualizer`

The `KnowledgeGraphVisualizer` class converts a `KnowledgeGraph` into an interactive Pyvis visualization.

| Method | Description |
|---------|-------------|
| `render()` | Generates the HTML visualization for Streamlit embedding |
| `_get_color()` | Returns the node color based on confidence score |
| `_empty_graph_html()` | Generates the HTML displayed when no graph exists |

---

# Node Styling

| Confidence | Color | Hex |
|------------|-------|-----|
| High (≥ 0.8) | Green | `#22c55e` |
| Medium (≥ 0.5) | Amber | `#f59e0b` |
| Low (< 0.5) | Red | `#ef4444` |

Additional styling:

- Node size scales with confidence.
- Larger nodes represent higher confidence.
- Hover tooltips display metadata such as confidence and source information.

---

# Graph Configuration

| Feature | Default | Description |
|---------|----------|-------------|
| Physics | Enabled | Allows nodes to settle into a natural layout |
| Height | 600px | Visualization height |
| Width | 100% | Full-width responsive graph |
| Directed | False | Displays an undirected graph |

---

# Streamlit Integration

## Graphe Page (`app/views/graphe.py`)

The **Graphe** page provides the user interface for graph visualization.

### Workflow

1. Check for an existing session in `st.session_state`.
2. Retrieve `last_session_id`.
3. Load the graph from:

```text
data/graphs/{session_id}.json
```

4. Import the graph using:

```python
KnowledgeGraph.import_json()
```

5. Render the visualization with:

```python
render_kg_html()
```

6. Embed the HTML using:

```python
st.components.v1.html()
```

7. Display graph statistics:

- Number of nodes
- Number of edges

8. Provide an export option for graph data.

---

# Empty State

When no graph is available, the page displays a friendly message guiding users to perform a search in the **Recherche** page before accessing the graph visualization.

---

# Convenience Function

```python
render_kg_html(
    kg,
    height="700px",
    physics=True
)
```

This helper function wraps the visualizer and provides a simple interface for rendering a `KnowledgeGraph`.

---

# Integration with Existing Components

## Dependencies

| Component | Role |
|-----------|------|
| Pyvis | Interactive graph rendering |
| NetworkX | Graph data structure |
| KnowledgeGraph | Graph data source |
| Streamlit | User interface |

---

# Data Flow

```text
KnowledgeGraph (from Reasoning)
            │
            ▼
KnowledgeGraphVisualizer.render()
            │
            ├── Create Pyvis Network
            ├── Add styled nodes
            ├── Add labeled edges
            └── Generate HTML
            │
            ▼
st.components.v1.html(html)
            │
            ▼
Interactive Knowledge Graph
```

---

# Testing

## Unit Tests

**File**

```text
tests/unit/test_visualizer.py
```

### Test Coverage

| Test | Purpose |
|------|---------|
| `test_initialization` | Verify visualizer initialization |
| `test_render_empty_graph` | Ensure empty graphs are handled correctly |
| `test_render_with_nodes` | Verify graph rendering with populated nodes |
| `test_render_with_physics_disabled` | Validate rendering with physics disabled |
| `test_get_color_by_confidence` | Verify confidence-to-color mapping |
| `test_render_kg_html_convenience` | Test the helper rendering function |
| `test_render_handles_large_graph` | Verify rendering of large graphs |
| `test_empty_graph_html_structure` | Validate empty-state HTML structure |

---

## Running the Tests

```bash
pytest tests/unit/test_visualizer.py -v
```

### Expected Output

```text
collected 8 items

test_visualizer.py::TestKnowledgeGraphVisualizer::test_initialization PASSED
test_visualizer.py::TestKnowledgeGraphVisualizer::test_render_empty_graph PASSED
test_visualizer.py::TestKnowledgeGraphVisualizer::test_render_with_nodes PASSED
test_visualizer.py::TestKnowledgeGraphVisualizer::test_render_with_physics_disabled PASSED
test_visualizer.py::TestKnowledgeGraphVisualizer::test_get_color_by_confidence PASSED
test_visualizer.py::TestKnowledgeGraphVisualizer::test_render_kg_html_convenience PASSED
test_visualizer.py::TestKnowledgeGraphVisualizer::test_render_handles_large_graph PASSED
test_visualizer.py::TestKnowledgeGraphVisualizer::test_empty_graph_html_structure PASSED

===================== 8 passed in 0.5s ======================
```

---

# Files Created and Modified

| File | Action | Description |
|------|--------|-------------|
| `src/knowledge/visualizer.py` | Created | Pyvis visualization implementation |
| `src/knowledge/__init__.py` | Modified | Added visualizer exports |
| `app/views/graphe.py` | Created | Streamlit graph visualization page |
| `tests/unit/test_visualizer.py` | Created | Comprehensive unit tests |

---

# Handoff Notes

## What Is Ready

- Complete Pyvis visualizer implementation.
- Streamlit **Graphe** page.
- `render_kg_html()` convenience function.
- Eight passing unit tests.

---

## Integration Points

| Component | Usage |
|-----------|-------|
| `render_kg_html(kg)` | Render a `KnowledgeGraph` to interactive HTML |
| `KnowledgeGraphVisualizer` | Customizable visualization class |
| `st.components.v1.html()` | Embed visualization into Streamlit |

---

## Important Notes

- The visualizer requires a valid `KnowledgeGraph` instance.
- Graphs are loaded from:

```text
data/graphs/{session_id}.json
```

- The page retrieves the current session using:

```python
st.session_state["last_session_id"]
```

- Physics simulation can be disabled to improve rendering performance for large graphs.

---

# Task Completion

## Delivered

- Interactive Pyvis-based knowledge graph visualization.
- Confidence-based node color coding.
- Configurable physics and layout options.
- Empty state handling.
- Streamlit integration using `st.components.v1.html`.
- Graph metadata displayed on hover.
- Eight comprehensive unit tests.

---

# Verification

```bash
pytest tests/unit/test_visualizer.py -v
# 8 tests passed
```

```bash
streamlit run app/main.py
```

Verification steps:

1. Navigate to **Recherche**.
2. Execute a research query.
3. Open the **Graphe** page.
4. Verify that the interactive knowledge graph is displayed.

---

# Status

**Completed**
