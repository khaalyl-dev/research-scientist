"""
Page Graphe — visualise Zeineb's NetworkX KnowledgeGraph via pyvis.

Does not modify src/knowledge/graph.py — only consumes build_from_claims /
to_vis_data / import_json.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from app.components.theme import inject_theme
from app.components.session_store import load_pipeline_result
from src.knowledge.graph import KnowledgeGraph

_GRAPH_DIR = Path(__file__).resolve().parents[2] / "data" / "graphs"


def _load_kg_for_session(session_id: str | None, claims: list | None) -> KnowledgeGraph | None:
    if session_id:
        json_path = _GRAPH_DIR / f"{session_id}.json"
        if json_path.is_file():
            try:
                return KnowledgeGraph.import_json(json_path)
            except Exception:
                pass
    if claims:
        kg = KnowledgeGraph(session_id=session_id or "ui")
        claim_dicts = [
            c if isinstance(c, dict) else (c.model_dump() if hasattr(c, "model_dump") else {})
            for c in claims
        ]
        kg.build_from_claims(claim_dicts)
        return kg
    return None


def _render_pyvis(kg: KnowledgeGraph) -> None:
    """Build an interactive pyvis HTML from to_vis_data()."""
    try:
        from pyvis.network import Network
    except ImportError:
        st.warning("Le package `pyvis` n’est pas installé. Lance `pip install pyvis`.")
        vis = kg.to_vis_data()
        st.json(vis)
        return

    vis = kg.to_vis_data()
    net = Network(height="520px", width="100%", bgcolor="#ffffff", font_color="#111827")
    net.barnes_hut()

    for node in vis.get("nodes") or []:
        net.add_node(
            node["id"],
            label=node.get("label") or node["id"],
            title=node.get("title") or "",
            size=node.get("size") or 25,
        )
    for edge in vis.get("edges") or []:
        net.add_edge(
            edge["from"],
            edge["to"],
            title=edge.get("label") or "related",
            value=edge.get("weight") or 0.5,
        )

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        path = tmp.name
    net.save_graph(path)
    html = Path(path).read_text(encoding="utf-8")
    components.html(html, height=540, scrolling=True)


def render_graphe_page() -> None:
    inject_theme()
    st.markdown(
        """
<div class="ars-hero">
  <div class="ars-kicker">US-09 · NetworkX + pyvis</div>
  <h1 class="ars-brand">Graphe de connaissances</h1>
  <p class="ars-lead">
    Visualisation des entités et relations extraites des claims
    (backend Zeineb — page consommatrice).
  </p>
</div>
""",
        unsafe_allow_html=True,
    )

    session_id = st.session_state.get("last_session_id")
    claims = st.session_state.get("last_claims") or []

    # Fallback: recover from full Recherche snapshot if keys were lost
    if (not session_id or not claims) and (saved := load_pipeline_result(st)):
        state = saved.get("state") or {}
        session_id = session_id or state.get("session_id")
        claims = claims or state.get("claims") or []
        if session_id:
            st.session_state["last_session_id"] = session_id
        st.session_state["last_claims"] = claims
        st.caption(f"Session : `{str(session_id)[:8]}…`" if session_id else "")

    if not session_id and not claims:
        st.info(
            "Lance d’abord une recherche sur la page Recherche — "
            "le graphe de la dernière session apparaîtra ici."
        )
        return

    kg = _load_kg_for_session(session_id, claims)
    if kg is None or kg.graph.number_of_nodes() == 0:
        st.warning("Aucun nœud dans le graphe pour cette session.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Entités", kg.graph.number_of_nodes())
    c2.metric("Relations", kg.graph.number_of_edges())
    c3.metric("Claims", len(claims))

    st.markdown("##### Vue interactive")
    _render_pyvis(kg)

    with st.expander("Données vis.js (to_vis_data)", expanded=False):
        st.json(kg.to_vis_data())
