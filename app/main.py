"""
Streamlit entrypoint — navigation (Sprint 2).

Run with:
    streamlit run app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

# Repo root on sys.path so `from app...` and `from src...` both work
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Load .env before any agent/LLM import side effects
load_dotenv(_ROOT / ".env")

import streamlit as st

from app.views.accueil import render_accueil_page
from app.views.recherche import render_recherche_page

st.set_page_config(
    page_title="Autonomous Research Scientist",
    layout="wide",
    initial_sidebar_state="expanded",
)

accueil = st.Page(render_accueil_page, title="Accueil")
recherche = st.Page(render_recherche_page, title="Recherche", default=True)

pg = st.navigation([accueil, recherche])
pg.run()
