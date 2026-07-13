"""
Accueil — landing page for Autonomous Research Scientist.
"""

from __future__ import annotations

import streamlit as st

from app.components.theme import hero, inject_theme


def render_accueil_page() -> None:
    inject_theme()

    hero(
        brand="Autonomous Research Scientist",
        kicker="Your AI research partner",
        lead=(
            "Pose une question. Le système décompose, recherche, extrait, "
            "vérifie et synthétise — avec sources traçables, en streaming "
            "agent par agent."
        ),
        chips=[
            "Planner",
            "Researcher",
            "Extractor",
            "FactChecker",
            "Reasoning",
            "Teacher",
        ],
    )

    st.write("")
    left, right = st.columns([1.35, 1], gap="large")

    with left:
        st.markdown(
            """
<div class="ars-panel">
  <h3 class="ars-panel-title">Lancer une investigation</h3>
  <p class="ars-muted">
    Ouvre <strong>Recherche</strong> dans la navigation latérale, choisis ton niveau,
    puis lance le pipeline multi-agents.
  </p>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown(
            """
<div class="ars-panel">
  <h3 class="ars-panel-title">Ce que tu obtiens</h3>
  <p class="ars-muted">
    Sous-requêtes, sources arXiv / web, claims structurés, contradictions,
    puis une réponse adaptée à ton niveau.
  </p>
  <ul style="margin:0;padding-left:1.1rem;color:#243944;line-height:1.6;">
    <li>Progression visible à chaque étape</li>
    <li>Flux streamé agent par agent</li>
    <li>Citations et URLs vérifiables</li>
  </ul>
</div>
""",
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            """
<div class="ars-panel">
  <h3 class="ars-panel-title">Roadmap MVP</h3>
  <p class="ars-muted" style="margin-bottom:0.4rem;"><strong>Sprint 1</strong> — Sources brutes</p>
  <p class="ars-muted" style="margin-bottom:0.4rem;"><strong>Sprint 2</strong> — Agents + FAISS + UI</p>
  <p class="ars-muted" style="margin-bottom:0.4rem;"><strong>Sprint 3</strong> — Contradictions + graphe</p>
  <p class="ars-muted" style="margin:0;"><strong>Sprint 4</strong> — Finalisation &amp; démo</p>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown(
            """
<div class="ars-panel">
  <h3 class="ars-panel-title">Stack</h3>
  <p class="ars-muted" style="margin:0;line-height:1.7;">
    LangGraph · Groq · Streamlit<br/>
    FAISS · SQLite · NetworkX<br/>
    arXiv · Brave / DuckDuckGo
  </p>
</div>
""",
            unsafe_allow_html=True,
        )
