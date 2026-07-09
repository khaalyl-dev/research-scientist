# Task: Unit Tests + GitHub Actions CI

## What this delivers
- `tests/unit/test_arxiv_client.py` — 10 tests for `ArxivClient`
- `tests/unit/test_scraper.py` — 12 tests for `WebScraper`
- `conftest.py` — makes `from src... import ...` work no matter where `pytest` is run from
- `.github/workflows/ci.yml` — runs `ruff`, `black --check`, and `pytest` on every push/PR to `main`

All 22 tests pass in well under a second because **everything is mocked** —
no real HTTP calls to arXiv or the web are made. This matters for CI: it
means the pipeline is fast, deterministic, and never fails because arXiv
was briefly slow or a website changed.

## Where to put these files
Copy them into your repo at these **exact** paths (matches the structure
in section 8 of the MVP plan):

```
research-scientist/
├── conftest.py                          # <-- repo root, NOT inside tests/
├── .github/
│   └── workflows/
│       └── ci.yml
└── tests/
    ├── unit/
    │   ├── test_arxiv_client.py
    │   └── test_scraper.py
    └── fixtures/                        # already exists per plan, unused by these tests
```

> `conftest.py` goes at the **repo root** (next to `requirements.txt`), not
> inside `tests/`. Pytest auto-discovers root-level `conftest.py` files and
> uses them to set up `sys.path` before any test file imports `src...`.

## Setup
```bash
pip install pytest pytest-mock
```
(these are also installed automatically by the CI workflow — add them to
`requirements.txt` or a separate `requirements-dev.txt` if you keep one)

## How to run the tests locally
```bash
# from the repo root
pytest tests/unit/ -v
```
Expected output: `22 passed`.

If you get `ModuleNotFoundError: No module named 'src'`, it means
`conftest.py` isn't at the repo root — double check its location.

## What's covered

**`test_arxiv_client.py`**
- Successful search returns a list of valid `SourceSchema` objects
- Empty/whitespace-only query short-circuits without calling the API
- API failures degrade gracefully to `[]` instead of raising (no crash)
- `max_results` is respected
- Authors are correctly folded into `content` (and omitted cleanly when there are none)
- `published_year` is set correctly, or `None` when arXiv gives no date
- The resulting `url` is a valid, parseable `HttpUrl`
- The rate-limit throttle actually sleeps when called twice in quick succession

**`test_scraper.py`**
- Successful fetch returns a valid `SourceSchema` with clean title + content
- Noise tags (`<script>`, `<nav>`, `<footer>`, `<style>`) are stripped from content
- `<article>` content is preferred over unrelated sidebar/body text
- Invalid URLs (not starting with `http`) are rejected **without** making a network call
- Non-HTML content types (e.g. a PDF) are rejected
- Pages with too little text (< 100 chars) are discarded
- HTTP errors (404, etc.) return `None` instead of raising
- Persistent connection errors return `None` after retries are exhausted
- A transient error that resolves on retry (2 failures then success) still returns a valid result
- Title extraction fallback chain: `<title>` → `<h1>` → `"Untitled page"`
- Content is correctly capped at `max_content_chars`
