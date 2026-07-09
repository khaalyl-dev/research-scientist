"""
Streamlit base UI — Task: "Streamlit base UI" (US-01, Sprint 1, Khalil+Zeineb)

Sprint 1 goal (per MVP_Plan_Final.pdf): "On peut lancer l'application
Streamlit, entrer une requete, et voir les sources brutes remontees
depuis arXiv et Brave Search - sans agents, juste le plumbing."

This file intentionally does NOT call any LangGraph agents yet — that's
Sprint 2. It wires the two Sprint-1 clients (arXiv + scraper) directly
to the UI so the team has an end-to-end, demoable skeleton today.

Run with:
    streamlit run app/main.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import streamlit as st

# Allow `from src...` imports when running via `streamlit run app/main.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.clients.arxiv_client import ArxivClient
from src.clients.scraper import WebScraper

# --------------------------------------------------------------------- #
# Page config
# --------------------------------------------------------------------- #
st.set_page_config(
    page_title="Autonomous Research Scientist",
    page_icon="🔬",
    layout="wide",
)

# Cached clients so we don't reinstantiate a requests.Session / arxiv.Client
# on every rerun (Streamlit reruns the whole script on each interaction).
@st.cache_resource
def get_arxiv_client() -> ArxivClient:
    return ArxivClient()


@st.cache_resource
def get_scraper() -> WebScraper:
    return WebScraper()


# A few safe, illustrative fallback URLs to scrape for the Sprint-1 demo
# until the Brave Search client (Zeineb, US-03) is wired in Sprint 2.
_DEMO_WEB_SOURCES = [
    "https://en.wikipedia.org/wiki/Retrieval-augmented_generation",
    "https://en.wikipedia.org/wiki/Large_language_model",
]


# --------------------------------------------------------------------- #
# Sidebar / navigation placeholder (pages/ get added in later sprints)
# --------------------------------------------------------------------- #
with st.sidebar:
    st.title("🔬 Research Scientist")
    st.caption("MVP — Sprint 1: plumbing only, no agents yet.")
    st.divider()
    st.markdown("**Roadmap**")
    st.markdown("- ✅ Sprint 1 — Sources brutes\n"
                "- ⏳ Sprint 2 — Agents + FAISS\n"
                "- ⏳ Sprint 3 — Contradictions + Graphe\n"
                "- ⏳ Sprint 4 — Finalisation")

# --------------------------------------------------------------------- #
# Main content
# --------------------------------------------------------------------- #
st.title("Autonomous Research Scientist")
st.caption("Your AI Research Partner — pose une question, obtiens des sources tracables.")

with st.form(key="query_form"):
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input(
            "Question de recherche",
            placeholder="e.g. What are the main approaches to hallucination mitigation in LLMs?",
        )
    with col2:
        level = st.selectbox("Niveau", ["Débutant", "Intermédiaire", "Expert"])

    max_results = st.slider("Nombre de résultats arXiv", min_value=2, max_value=10, value=5)
    submitted = st.form_submit_button("🔍 Rechercher", use_container_width=True)

if submitted:
    if not query.strip():
        st.warning("Merci d'entrer une question avant de lancer la recherche.")
    else:
        start = time.monotonic()
        with st.spinner("Recherche des sources en cours..."):
            arxiv_sources = get_arxiv_client().search(query, max_results=max_results)

            scraper = get_scraper()
            web_sources = []
            for url in _DEMO_WEB_SOURCES:
                src = scraper.fetch(url)
                if src:
                    web_sources.append(src)

        elapsed = time.monotonic() - start
        all_sources = arxiv_sources + web_sources

        if not all_sources:
            st.error(
                "Aucune source trouvée. Vérifie ta connexion internet, "
                "ou réessaie avec une autre requête."
            )
        else:
            st.success(f"{len(all_sources)} source(s) trouvée(s) en {elapsed:.1f}s "
                       f"(niveau sélectionné : {level})")

            tab_arxiv, tab_web = st.tabs(
                [f"📄 arXiv ({len(arxiv_sources)})", f"🌐 Web ({len(web_sources)})"]
            )

            with tab_arxiv:
                if not arxiv_sources:
                    st.info("Aucun résultat arXiv pour cette requête.")
                for src in arxiv_sources:
                    with st.expander(src.title):
                        st.markdown(f"**URL** : [{src.url}]({src.url})")
                        if src.published_year:
                            st.markdown(f"**Année** : {src.published_year}")
                        st.markdown("**Abstract**")
                        # SourceSchema has no separate `abstract` field — the
                        # arxiv client folds authors + summary into `content`.
                        preview = src.content[:600]
                        st.write(preview + ("..." if len(src.content) > 600 else ""))

            with tab_web:
                if not web_sources:
                    st.info("Aucune source web disponible.")
                for src in web_sources:
                    with st.expander(src.title):
                        st.markdown(f"**URL** : [{src.url}]({src.url})")
                        st.markdown("**Extrait**")
                        preview = src.content[:600]
                        st.write(preview + ("..." if len(src.content) > 600 else ""))
else:
    st.info("👆 Entre une question ci-dessus pour voir les sources brutes remontées "
            "par le client arXiv et le scraper BeautifulSoup.")