"""
Wikipedia client — MediaWiki Action API (no API key).

Returns SourceSchema rows with extract text ready for the Extractor.
Never raises: logs and returns [] on failure.
"""

from __future__ import annotations

import logging
import uuid
from typing import List

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.schemas.common import SourceType
from src.schemas.source import SourceSchema

logger = logging.getLogger(__name__)

_API = "https://en.wikipedia.org/w/api.php"
_USER_AGENT = (
    "AutonomousResearchScientist/1.0 "
    "(educational research bot; contact=local)"
)
_TIMEOUT = 12.0


class WikipediaClient:
    """Search Wikipedia and fetch plain-text extracts."""

    def __init__(self, timeout: float = _TIMEOUT) -> None:
        self.timeout = timeout

    def search(self, query: str, max_results: int = 2) -> List[SourceSchema]:
        if not query or not query.strip():
            return []

        try:
            titles = self._search_titles(query.strip(), max_results)
            if not titles:
                return []
            sources = self._fetch_extracts(titles)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Wikipedia search failed for query=%r: %s", query, exc)
            return []

        logger.info("Wikipedia search: query=%r -> %d results", query, len(sources))
        return sources

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=6),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
        reraise=True,
    )
    def _search_titles(self, query: str, max_results: int) -> list[str]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": max_results,
            "format": "json",
            "utf8": 1,
        }
        with httpx.Client(timeout=self.timeout, headers={"User-Agent": _USER_AGENT}) as client:
            resp = client.get(_API, params=params)
            resp.raise_for_status()
            data = resp.json()
        hits = data.get("query", {}).get("search", []) or []
        return [h["title"] for h in hits if h.get("title")]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=6),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
        reraise=True,
    )
    def _fetch_extracts(self, titles: list[str]) -> list[SourceSchema]:
        params = {
            "action": "query",
            "prop": "extracts|info",
            "exintro": 1,
            "explaintext": 1,
            "inprop": "url",
            "titles": "|".join(titles),
            "format": "json",
            "utf8": 1,
        }
        with httpx.Client(timeout=self.timeout, headers={"User-Agent": _USER_AGENT}) as client:
            resp = client.get(_API, params=params)
            resp.raise_for_status()
            data = resp.json()

        pages = (data.get("query") or {}).get("pages") or {}
        sources: list[SourceSchema] = []
        # Preserve search-rank order when possible
        by_title = {
            (p.get("title") or ""): p
            for p in pages.values()
            if isinstance(p, dict) and "missing" not in p
        }
        for title in titles:
            page = by_title.get(title)
            if not page:
                continue
            extract = (page.get("extract") or "").strip()
            if not extract:
                continue
            url = page.get("fullurl") or (
                f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
            )
            sources.append(
                SourceSchema(
                    id=str(uuid.uuid4()),
                    source_type=SourceType.wikipedia,
                    title=title,
                    url=url,
                    content=extract,
                    quality_score=0.75,
                )
            )
        return sources


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for src in WikipediaClient().search("retrieval augmented generation", max_results=2):
        print(f"- {src.title} -> {src.url}")
        print(f"  {src.content[:140]}...")
