# Task: BeautifulSoup Scraper (Khalil — Sprint 1, US-03)

## What this does
`src/clients/scraper.py` (`WebScraper` class) replaces Jina Reader with a
100% local, free, unlimited HTML fetcher + cleaner:
- Fetches a URL via `requests` (custom User-Agent, 15s timeout)
- Strips boilerplate tags (`script`, `style`, `nav`, `footer`, `header`,
  `aside`, `form`, `iframe`, ...)
- Prefers `<article>`/`<main>` content if present, otherwise falls back to `<body>`
- Returns a `Source` object (title, url, abstract = first 300 chars, full
  cleaned content capped at 20k chars to keep LLM prompts sane)
- Retries transient network errors 3x with exponential backoff (`tenacity`)
- Returns `None` (never raises) on failure — the caller decides what to do

## Files added
```
src/schemas/source.py     # shared Source dataclass (same one arXiv client uses)
src/clients/scraper.py    # the scraper itself
```

## Setup
```bash
pip install requests beautifulsoup4 lxml tenacity
```

## How to use it
```python
from src.clients.scraper import WebScraper

scraper = WebScraper()
source = scraper.fetch("https://example.com/some-article")

if source:
    print(source.title)
    print(source.content[:500])
else:
    print("Could not fetch/parse that page.")
```

## How to test it manually
```bash
python -m src.clients.scraper
```
Fetches a Wikipedia page on RAG and prints the title + first 400 chars.

## What YOU need to do next
1. Copy `src/clients/scraper.py` into your repo at that exact path.
2. Add to `requirements.txt`:
   ```
   requests==2.32.*
   beautifulsoup4==4.12.*
   lxml==5.*
   ```
3. Write unit tests (`tests/unit/test_scraper.py`):
   - feed it a canned HTML string via a mocked `requests.Session.get`
   - assert noise tags are stripped
   - assert `None` is returned for a non-HTML content-type
   - assert `None` is returned when the page is too short (< 100 chars)
4. **Rate/politeness note**: this scraper does not currently throttle
   between different domains. If Zeineb's Brave Search client returns many
   URLs on the same domain, add a small per-domain delay before Sprint 3
   to avoid being blocked.
5. **Sprint 2 hook**: the `Researcher` agent will call `scraper.fetch(url)`
   for each web result returned by Brave Search — no changes needed here.
6. Optional hardening (Sprint 4 polish): respect `robots.txt` via
   `urllib.robotparser` before fetching, if you want to be extra safe for
   the demo.

## Acceptance criteria (from the plan, US-03)
- [x] Local, zero-cost, zero external API — pure `requests` + `BeautifulSoup`
- [x] Timeout enforced (15s)
- [x] Graceful failure (returns `None`, doesn't raise / doesn't crash Streamlit)
- [x] Clean text output ready for the Extractor agent
