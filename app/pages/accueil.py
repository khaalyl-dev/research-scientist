"""
Accueil — landing page for Autonomous Research Scientist.
"""

from __future__ import annotations

import streamlit as st


def render_accueil_page() -> None:
    st.title("Autonomous Research Scientist")
    st.caption("Your AI Research Partner — recherche multi-agents avec sources traçables.")

    st.markdown(
        """
Bienvenue. Utilise la page **Recherche** pour lancer le pipeline :

`Planner → Researcher → Extractor → FactChecker → Reasoning → Teacher`

Tu verras la **progression agent par agent** (US-07), les sous-requêtes du
Planner (US-02), puis un aperçu des sources, claims et de la réponse.
"""
    )

    st.info("➡️ Ouvre **Recherche** dans la barre latérale pour commencer.")

    with st.expander("Roadmap MVP", expanded=False):
        st.markdown(
            "- ✅ Sprint 1 — Sources brutes\n"
            "- ⏳ Sprint 2 — Agents + FAISS + UI Recherche\n"
            "- ⏳ Sprint 3 — Contradictions + Graphe\n"
            "- ⏳ Sprint 4 — Finalisation"
        )
