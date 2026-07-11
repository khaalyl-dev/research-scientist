"""
BeautifulSoup scraper — Task: "BeautifulSoup scraper" (US-03, Sprint 1)

Responsibilities (per MVP_Plan_Final.pdf, section 2 & 4):
  - Fetch a web page over HTTP (via `requests`)
  - Strip boilerplate (script, style, nav, footer, ads, etc.)
  - Return clean title + readable text, wrapped in the shared Source
    schema, ready for the Extractor agent
  - 100% local, zero external API cost — this replaces Jina Reader
  - Retry on transient failures, respect a timeout, degrade gracefully

Usage:
    from src.clients.scraper import WebScraper

    scraper = WebScraper()
    source = scraper.fetch("https://example.com/some-article")
    if source:
        print(source.title)
        print(source.content[:500])
"""

from __future__ import annotations

import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.schemas.common import SourceType
from src.schemas.source import SourceSchema
import uuid

logger = logging.getLogger(__name__)

# Tags that never contain "real" article content — strip them before
# extracting text so the LLM extractor isn't fed nav links, ads, etc.
_NOISE_TAGS = [
    "script",
    "style",
    "nav",
    "footer",
    "header",
    "aside",
    "form",
    "noscript",
    "iframe",
    "svg",
]

_DEFAULT_HEADERS = {
    # A real UA reduces the chance of being blocked by basic bot filters.
    "User-Agent": (
        "Mozilla/5.0 (compatible; AutonomousResearchScientist/1.0; "
        "+https://github.com/khaalyl-dev/research-scientist)"
    )
}

_REQUEST_TIMEOUT_SECONDS = 15
_MAX_CONTENT_CHARS = 20_000  # keep prompt sizes sane downstream


class WebScraper:
    """Local, free, unlimited HTML fetch + clean. No external API calls."""

    def __init__(
        self,
        timeout: int = _REQUEST_TIMEOUT_SECONDS,
        max_content_chars: int = _MAX_CONTENT_CHARS,
    ) -> None:
        self._timeout = timeout
        self._max_content_chars = max_content_chars
        self._session = requests.Session()
        self._session.headers.update(_DEFAULT_HEADERS)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def fetch(self, url: str) -> Optional[SourceSchema]:
        """
        Fetch and clean a single URL. Returns None on failure instead of
        raising, so one bad source never crashes the whole pipeline.
        """
        if not url or not url.startswith(("http://", "https://")):
            logger.warning("Skipping invalid URL: %r", url)
            return None

        try:
            html = self._get_with_retry(url)
        except Exception as exc:  # noqa: BLE001 - graceful degradation
            logger.warning("Scrape failed for %s: %s", url, exc)
            return None

        return self._parse(url, html)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(
            (requests.ConnectionError, requests.Timeout, requests.HTTPError)
        ),
        reraise=True,
    )
    def _get_with_retry(self, url: str) -> str:
        response = self._session.get(url, timeout=self._timeout)
        response.raise_for_status()
        # Basic guard: don't try to BeautifulSoup a PDF/binary payload.
        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type and "xml" not in content_type:
            raise ValueError(f"Unsupported content-type: {content_type!r}")
        return response.text

    def _parse(self, url: str, html: str) -> Optional[SourceSchema]:
        soup = BeautifulSoup(html, "lxml")

        for tag_name in _NOISE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        title = self._extract_title(soup)
        text = self._extract_text(soup)

        if not text or len(text) < 100:
            logger.info("Scraped page too short/empty, discarding: %s", url)
            return None

        return SourceSchema(
            id=str(uuid.uuid4()),  
            source_type=SourceType.web,
            title=title,
            url=url,
            content=text[: self._max_content_chars],
        )

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str:
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        return "Untitled page"

    @staticmethod
    def _extract_text(soup: BeautifulSoup) -> str:
        # Prefer <article> or <main> if present — usually the real content.
        container = soup.find("article") or soup.find("main") or soup.body or soup
        chunks = [
            chunk.get_text(" ", strip=True)
            for chunk in container.find_all(["p", "li", "h1", "h2", "h3"])
        ]
        text = "\n".join(c for c in chunks if c)
        return text.strip()


# ---------------------------------------------------------------------- #
# Manual smoke test: `python -m src.clients.scraper`
# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_scraper = WebScraper()
    demo_source = demo_scraper.fetch("https://en.wikipedia.org/wiki/Retrieval-augmented_generation")
    if demo_source:
        print(demo_source.title)
        print(demo_source.content[:400])
