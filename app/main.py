"""
Streamlit entrypoint — navigation (Sprint 2).

Run with:
    streamlit run app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Repo root on sys.path so `from app...` and `from src...` both work
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.pages.accueil import render_accueil_page
from app.pages.recherche import render_recherche_page

st.set_page_config(
    page_title="Autonomous Research Scientist",
    page_icon="🔬",
    layout="wide",
)

accueil = st.Page(render_accueil_page, title="Accueil", icon="🏠")
recherche = st.Page(render_recherche_page, title="Recherche", icon="🔍", default=True)

pg = st.navigation([accueil, recherche])
pg.run()
