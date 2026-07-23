"""
Pyvis visualizer for the Knowledge Graph — Enhanced Edition.

Generates an interactive, beautiful HTML visualization of the knowledge graph
with advanced styling, physics tuning, and interactivity.
"""

import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional

from pyvis.network import Network

from src.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeGraphVisualizer:
    """
    Enhanced Pyvis visualizer for knowledge graphs with advanced styling.
    """

    def __init__(self, kg):
        """Initialize the visualizer with a KnowledgeGraph."""
        self.kg = kg
        self.net = None

    def render(
        self,
        height: str = "700px",
        width: str = "100%",
        physics: bool = True,
        directed: bool = False,
        notebook: bool = False,
        stabilization_iterations: int = 200,
    ) -> str:
        """
        Render the knowledge graph as an interactive HTML string.

        Args:
            height: Height of the visualization
            width: Width of the visualization
            physics: Enable physics simulation
            directed: Use directed graph
            notebook: Pyvis notebook mode
            stabilization_iterations: Physics stabilization iterations

        Returns:
            HTML string for embedding in Streamlit
        """
        if self.kg.get_node_count() == 0:
            return self._empty_graph_html()

        self.net = Network(
            height=height,
            width=width,
            directed=directed,
            notebook=notebook,
            bgcolor="#ffffff",
            font_color="#1f2937",
        )

        # Configure advanced physics
        self._configure_physics(physics, stabilization_iterations)

        # Add nodes with enhanced styling
        self._add_enhanced_nodes()

        # Add edges with styling
        self._add_enhanced_edges()

        # Enable interactivity
        self._configure_interactivity()

        # Save and return HTML
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
            self.net.save_graph(f.name)
            html_path = Path(f.name)

        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        html_path.unlink()

        # Inject enhanced CSS
        html_content = self._inject_css(html_content)

        return html_content

    def _configure_physics(self, enabled: bool, iterations: int) -> None:
        """Configure physics with optimal settings."""
        physics_options = f"""
        var options = {{
            "physics": {{
                "enabled": {str(enabled).lower()},
                "stabilization": {{
                    "enabled": {str(enabled).lower()},
                    "iterations": {iterations},
                    "updateInterval": 50
                }},
                "repulsion": {{
                    "nodeDistance": 250,
                    "centralGravity": 0.3,
                    "springLength": 200,
                    "springConstant": 0.05,
                    "damping": 0.09
                }},
                "solver": "repulsion"
            }},
            "layout": {{
                "hierarchical": {{
                    "enabled": false
                }}
            }}
        }}
        """
        self.net.set_options(physics_options)

    def _add_enhanced_nodes(self) -> None:
        """Add nodes with advanced styling."""
        source_colors = {
            "arxiv": "#3b82f6",      # Blue
            "wikipedia": "#22c55e",  # Green
            "openalex": "#f59e0b",   # Amber
            "scholar": "#8b5cf6",    # Purple
            "pubmed": "#ef4444",     # Red
            "web": "#6b7280",        # Gray
            "default": "#6366f1",    # Indigo
        }

        # Calculate confidence stats for scaling
        nodes_data = self.kg.get_nodes()
        confidences = [node.get("confidence", 0.5) for node in nodes_data]
        max_conf = max(confidences) if confidences else 1.0
        min_conf = min(confidences) if confidences else 0.0
        conf_range = max_conf - min_conf or 0.5

        for node_data in nodes_data:
            node_id = node_data.get("id", "")
            description = node_data.get("title", node_data.get("description", ""))
            sources = node_data.get("sources", [])
            confidence = node_data.get("confidence", 0.5)

            # ✅ READ SOURCE_TYPE FROM NODE DATA
            source_type = node_data.get("source_type", "web")
            if source_type not in source_colors:
                source_type = "default"

            # Get color based on source type
            base_color = source_colors.get(source_type, source_colors["default"])

            # Size: larger for higher confidence
            normalized_conf = (confidence - min_conf) / conf_range if conf_range > 0 else 0.5
            size = 15 + (normalized_conf * 50)

            # Border: darker for higher confidence
            border_width = 2 + (normalized_conf * 3)

            # Build title with metadata
            title_parts = [
                f"<b>{node_id}</b>",
                f"<br><i>{description[:150]}</i>" if description else "",
                f"<br><br><b>Confidence:</b> {confidence:.2f}",
                f"<br><b>Sources:</b> {len(sources)}",
                f"<br><b>Type:</b> {source_type}",
            ]
            if sources:
                src_preview = ", ".join([str(s)[:30] for s in sources[:3]])
                if len(sources) > 3:
                    src_preview += f"... (+{len(sources)-3} more)"
                title_parts.append(f"<br><b>Sources:</b> {src_preview}")

            title = "".join(title_parts)

            self.net.add_node(
                node_id,
                label=node_id,
                title=title,
                color={
                    "background": base_color,
                    "border": self._darken_color(base_color, 0.7),
                    "highlight": {"background": "#fbbf24", "border": "#f59e0b"},
                },
                borderWidth=border_width,
                borderWidthSelected=5,
                size=size,
                font={"size": 14, "face": "sans-serif", "color": "#1f2937"},
                shape="dot",
                shadow={
                    "enabled": True,
                    "color": "rgba(0,0,0,0.2)",
                    "size": 5,
                    "x": 3,
                    "y": 3,
                },
                sources=len(sources),
                confidence=confidence,
                source_type=source_type,
            )

    def _add_enhanced_edges(self) -> None:
        """Add edges with styling based on relationship strength."""
        for edge in self.kg.get_edges():
            source = edge.get("source", "")
            target = edge.get("target", "")
            relationship = edge.get("relationship", "related")
            weight = edge.get("weight", 0.5)

            # Edge width based on weight
            width = 1 + (weight * 3)

            # Edge color based on weight
            if weight >= 0.7:
                color = "#22c55e"  # Green for strong
            elif weight >= 0.4:
                color = "#f59e0b"  # Amber for medium
            else:
                color = "#6b7280"  # Gray for weak

            self.net.add_edge(
                source,
                target,
                label=relationship,
                title=f"{relationship}<br>Weight: {weight:.2f}",
                color=color,
                width=width,
                length=150 + (1 - weight) * 100,
                font={"size": 11, "face": "sans-serif", "color": "#4b5563"},
                smooth={
                    "enabled": True,
                    "type": "dynamic",
                    "roundness": 0.5,
                },
                arrows={"to": {"enabled": False}},
            )

    def _configure_interactivity(self) -> None:
        """Enable interactivity features."""
        interactivity_options = """
        var options = {
            "interaction": {
                "hover": true,
                "tooltipDelay": 200,
                "zoomView": true,
                "dragView": true,
                "dragNodes": true,
                "selectable": true,
                "multiselect": false,
                "navigationButtons": true,
                "keyboard": {
                    "enabled": true
                }
            },
            "manipulation": {
                "enabled": false
            }
        }
        """
        self.net.set_options(interactivity_options)

    def _darken_color(self, hex_color: str, factor: float) -> str:
        """Darken a hex color by a factor."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            r = int(r * factor)
            g = int(g * factor)
            b = int(b * factor)
            return f"#{r:02x}{g:02x}{b:02x}"
        return hex_color

    def _inject_css(self, html: str) -> str:
        """Inject enhanced CSS into the HTML."""
        css = """
        <style>
            .vis-network {
                border-radius: 12px;
                box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
            }
            .vis-network .vis-tooltip {
                background-color: #ffffff !important;
                border: 1px solid #e5e7eb !important;
                border-radius: 8px !important;
                padding: 12px 16px !important;
                box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1) !important;
                font-family: system-ui, sans-serif !important;
                font-size: 13px !important;
                color: #1f2937 !important;
                max-width: 300px !important;
            }
            .vis-network .vis-tooltip b {
                color: #111827 !important;
                font-size: 14px !important;
            }
            .vis-network .vis-navigation {
                background: rgba(255,255,255,0.9) !important;
                border-radius: 8px !important;
                border: 1px solid #e5e7eb !important;
            }
            .vis-network .vis-navigation button {
                background: #f9fafb !important;
                border: none !important;
                border-radius: 4px !important;
                padding: 6px !important;
            }
            .vis-network .vis-navigation button:hover {
                background: #e5e7eb !important;
            }
            .vis-network .vis-legend {
                background: rgba(255,255,255,0.95) !important;
                border: 1px solid #e5e7eb !important;
                border-radius: 8px !important;
                padding: 12px 16px !important;
            }
        </style>
        """
        if "</head>" in html:
            html = html.replace("</head>", f"{css}</head>")
        return html

    def _empty_graph_html(self) -> str:
        """Return HTML for empty graph state."""
        return """
        <div style="
            text-align: center;
            padding: 80px 20px;
            color: #6b7280;
            font-family: system-ui, sans-serif;
            border: 2px dashed #d1d5db;
            border-radius: 16px;
            background: linear-gradient(135deg, #fafafa 0%, #f3f4f6 100%);
        ">
            <div style="font-size: 64px; margin-bottom: 20px; opacity: 0.5;">🕸️</div>
            <h3 style="margin: 0 0 8px; color: #374151; font-weight: 600;">No Graph Available</h3>
            <p style="margin: 0; font-size: 15px; max-width: 400px; margin: 8px auto;">
                Run a search in <strong style="color: #6366f1;">Recherche</strong> first, then return here to see the knowledge graph.
            </p>
            <p style="margin: 8px 0 0; font-size: 13px; color: #9ca3af;">
                The graph will show entities and their relationships from your research.
            </p>
        </div>
        """

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the graph."""
        return {
            "nodes": self.kg.get_node_count(),
            "edges": self.kg.get_edge_count(),
            "source_types": self._get_source_type_distribution(),
            "avg_confidence": self._get_avg_confidence(),
        }

    def _get_source_type_distribution(self) -> Dict[str, int]:
        """Get distribution of source types."""
        counts = {}
        for node in self.kg.get_nodes():
            source_type = node.get("source_type", "unknown")
            counts[source_type] = counts.get(source_type, 0) + 1
        return counts

    def _get_avg_confidence(self) -> float:
        """Get average confidence of nodes."""
        nodes = self.kg.get_nodes()
        if not nodes:
            return 0.0
        confidences = [n.get("confidence", 0.5) for n in nodes]
        return sum(confidences) / len(confidences)


def render_kg_html(
    kg,
    height: str = "700px",
    width: str = "100%",
    physics: bool = True,
    stabilization_iterations: int = 200,
) -> str:
    """
    Convenience function to render a KnowledgeGraph to HTML.

    Args:
        kg: KnowledgeGraph instance
        height: Height of the visualization
        width: Width of the visualization
        physics: Enable physics simulation
        stabilization_iterations: Physics stabilization iterations

    Returns:
        HTML string for embedding in Streamlit
    """
    visualizer = KnowledgeGraphVisualizer(kg)
    return visualizer.render(
        height=height,
        width=width,
        physics=physics,
        stabilization_iterations=stabilization_iterations,
    )


def render_graph_stats(kg) -> Dict[str, Any]:
    """
    Get statistics for the graph.

    Args:
        kg: KnowledgeGraph instance

    Returns:
        Dictionary with statistics
    """
    visualizer = KnowledgeGraphVisualizer(kg)
    return visualizer.get_stats()