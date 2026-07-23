"""
Streamlit entrypoint — navigation.

Run with:
    streamlit run app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env")

import streamlit as st

from app.views.accueil import render_accueil_page
from app.views.graphe import render_graphe_page
from app.views.recherche import render_recherche_page

st.set_page_config(
    page_title="Autonomous Research Scientist",
    layout="wide",
    initial_sidebar_state="expanded",
)

accueil = st.Page(render_accueil_page, title="Accueil")
recherche = st.Page(render_recherche_page, title="Recherche", default=True)
graphe = st.Page(render_graphe_page, title="Graphe")

pg = st.navigation([accueil, recherche, graphe])
pg.run()
