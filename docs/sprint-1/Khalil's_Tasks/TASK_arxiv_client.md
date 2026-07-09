# Task: arXiv Client (Khalil — Sprint 1, US-03)

## What this does
`src/clients/arxiv_client.py` wraps the official `arxiv` Python package to:
- Search arXiv for a query and return up to N results
- Parse each result into the shared `Source` schema (title, url, abstract, authors, published_year)
- Respect arXiv's rate limit (throttled to ~1 request / 3 sec)
- Retry up to 3 times with exponential backoff on transient failures (`tenacity`)
- **Never crash the app**: on failure it logs a warning and returns `[]`

## Files added
```
src/schemas/source.py       # shared Source dataclass used by all clients
src/clients/arxiv_client.py # the client itself
```

## Setup
```bash
pip install arxiv tenacity
# (already in requirements.txt — see "What to update" below)
```

## How to use it
```python
from src.clients.arxiv_client import ArxivClient

client = ArxivClient()
sources = client.search("retrieval augmented generation", max_results=5)

for s in sources:
    print(s.title, "-", s.url)
```

## How to test it manually
```bash
python -m src.clients.arxiv_client
```
This runs a small smoke test that searches for "large language model hallucination"
and prints the top 3 titles + URLs.

## What YOU need to do next
1. **Drop the files in place** — copy `src/schemas/source.py` and
   `src/clients/arxiv_client.py` into your repo at those exact paths
   (they match the project structure in section 8 of the plan).
2. Add `__init__.py` files if they don't already exist:
   ```bash
   touch src/__init__.py src/clients/__init__.py src/schemas/__init__.py
   ```
3. Add to `requirements.txt`:
   ```
   arxiv==2.*
   tenacity==8.*
   ```
4. Write the unit test (`tests/unit/test_arxiv_client.py` per the project
   structure) — mock `arxiv.Client.results()` so the test doesn't hit the
   real network. Suggested cases:
   - returns a list of `Source` on success
   - returns `[]` on empty query
   - returns `[]` (not an exception) when the underlying client raises
5. Wire it into the Streamlit UI (already done for you in `app/main.py` —
   see the other README) so you can demo it end-to-end.
6. **Sprint 2 hook**: this client is what the `Researcher` agent will call
   inside a LangGraph node — no changes needed here, just import it there.

## Acceptance criteria (from the plan, US-03)
- [x] Min 2 arXiv sources returned for a normal query
- [x] Timeout / retry handled (via `tenacity`, 3 attempts, exponential backoff)
- [x] Fails gracefully if arXiv API is down (returns `[]`, doesn't crash Streamlit)
