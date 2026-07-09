# Task: Streamlit Base UI (Khalil + Zeineb — Sprint 1, US-01)

## What this does
`app/main.py` is the Sprint-1 skeleton of the app. Per the plan's Sprint 1
objective: *"On peut lancer l'application Streamlit, entrer une requête,
et voir les sources brutes remontées depuis arXiv et Brave Search — sans
agents, juste le plumbing."*

It does **not** call any LangGraph agent yet (that's Sprint 2). It wires
the arXiv client and the scraper directly to a simple form so the whole
team has something demoable today.

Features included:
- Query text input + level selector (Débutant / Intermédiaire / Expert)
- "Rechercher" button with a loading spinner
- Calls `ArxivClient.search()` for arXiv results
- Calls `WebScraper.fetch()` on a couple of demo URLs (placeholder until
  Zeineb's Brave Search client lands in Sprint 2 — see note below)
- Displays results in two tabs: 📄 arXiv / 🌐 Web, each source in an
  expandable card showing title, URL, authors/year (arXiv), and
  abstract/extract
- Sidebar with a project title and a visible sprint roadmap
- Graceful empty/error states (no results, empty query)

## Files added
```
app/main.py
```
(depends on `src/clients/arxiv_client.py` and `src/clients/scraper.py`
 from the other two tasks — make sure those are in place first)

## Setup
```bash
pip install streamlit
```

## How to run it
```bash
streamlit run app/main.py
```
Opens at `http://localhost:8501`.

## What YOU need to do next
1. Copy `app/main.py` into your repo at that exact path.
2. Make sure `src/clients/arxiv_client.py`, `src/clients/scraper.py`, and
   `src/schemas/source.py` are already in place (see the other two READMEs) —
   this file imports them.
3. Confirm the repo root is on `PYTHONPATH` when running Streamlit. The
   file already does `sys.path.insert(0, ...)` for you, so
   `streamlit run app/main.py` should just work from the repo root.
4. **Replace the placeholder web sources**: right now `_DEMO_WEB_SOURCES`
   is a hardcoded list of 2 Wikipedia URLs so the "Web" tab isn't empty
   before Zeineb's Brave Search client exists. Once
   `src/clients/tavily_client.py` (Brave Search + DuckDuckGo fallback) is
   ready, replace that block with real search results:
   ```python
   from src.clients.tavily_client import BraveSearchClient
   web_results = BraveSearchClient().search(query, max_results=4)
   web_sources = [scraper.fetch(r.url) for r in web_results]
   web_sources = [s for s in web_sources if s]  # drop failed fetches
   ```
5. Add basic caching per US-12 groundwork: `@st.cache_resource` is already
   used for the clients (session/connection reuse); consider
   `@st.cache_data(ttl=1800)` around the actual search call once the
   in-memory TTL cache module (`src/cache/memory_cache.py`) exists.
6. Add `app/pages/` in Sprint 2+ per the project structure (section 8) —
   `01_search.py`, `02_results.py`, etc. For now everything lives in
   `main.py` on purpose, to keep Sprint 1 minimal.
7. Add to `requirements.txt`:
   ```
   streamlit==1.36.*
   ```

## Acceptance criteria (from the plan, US-01 + Sprint 1 deliverable)
- [x] `streamlit run app/main.py` starts without error
- [x] Text input + level selector + "Rechercher" button + spinner
- [x] Displays raw sources (title, URL, abstract) for a query
- [ ] Brave Search wired in (blocked on Zeineb's client — Sprint 2, see step 4 above)
