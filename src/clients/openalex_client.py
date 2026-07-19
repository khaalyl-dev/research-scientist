"""
OpenAlex client — open academic works index (papers, preprints, books).

Free polite-pool API. Optional OPENALEX_MAILTO improves rate limits.
Never raises: logs and returns [] on failure.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import List, Optional

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

_ENDPOINT = "https://api.openalex.org/works"
_TIMEOUT = 15.0


class OpenAlexClient:
    """Search OpenAlex for scholarly works."""

    def __init__(
        self,
        mailto: Optional[str] = None,
        timeout: float = _TIMEOUT,
    ) -> None:
        self.mailto = (
            mailto
            if mailto is not None
            else (os.getenv("OPENALEX_MAILTO") or "research-scientist@local")
        ).strip()
        self.timeout = timeout

    def search(self, query: str, max_results: int = 2) -> List[SourceSchema]:
        if not query or not query.strip():
            return []

        try:
            works = self._search_with_retry(query.strip(), max_results)
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAlex search failed for query=%r: %s", query, exc)
            return []

        sources = []
        for work in works:
            src = self._to_source(work)
            if src:
                sources.append(src)

        logger.info("OpenAlex search: query=%r -> %d results", query, len(sources))
        return sources

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
        reraise=True,
    )
    def _search_with_retry(self, query: str, max_results: int) -> list[dict]:
        headers = {
            "User-Agent": f"AutonomousResearchScientist/1.0 (mailto:{self.mailto})",
            "Accept": "application/json",
        }
        params = {
            "search": query,
            "per_page": max_results,
            "mailto": self.mailto,
        }
        with httpx.Client(timeout=self.timeout, headers=headers) as client:
            resp = client.get(_ENDPOINT, params=params)
            resp.raise_for_status()
            data = resp.json()
        return list(data.get("results") or [])

    @staticmethod
    def _to_source(work: dict) -> SourceSchema | None:
        title = (work.get("display_name") or work.get("title") or "").strip()
        if not title:
            return None

        abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))
        if not abstract:
            # OpenAlex sometimes omits abstracts — use title + venue as minimal content
            venue = ((work.get("primary_location") or {}).get("source") or {}).get(
                "display_name"
            ) or ""
            abstract = f"{title}. {venue}".strip()

        url = (
            (work.get("primary_location") or {}).get("landing_page_url")
            or work.get("id")
            or (
                work.get("doi") and
                f"https://doi.org/{str(work['doi']).replace('https://doi.org/', '')}"
            )        )
        if not url:
            return None
        url = str(url)

        year = work.get("publication_year")
        published_year = int(year) if isinstance(year, int) and 1900 <= year <= 2026 else None

        authors = ", ".join(
            (a.get("author") or {}).get("display_name", "")
            for a in (work.get("authorships") or [])[:8]
            if (a.get("author") or {}).get("display_name")
        )
        content = f"Authors: {authors}\n\n{abstract}" if authors else abstract

        return SourceSchema(
            id=str(uuid.uuid4()),
            source_type=SourceType.openalex,
            title=title,
            url=url,
            published_year=published_year,
            content=content,
            quality_score=0.8,
        )


def _reconstruct_abstract(inverted: dict | None) -> str:
    """OpenAlex stores abstracts as inverted index {token: [positions]}."""
    if not inverted or not isinstance(inverted, dict):
        return ""
    try:
        max_pos = max(pos for positions in inverted.values() for pos in positions)
        words = [""] * (max_pos + 1)
        for token, positions in inverted.items():
            for pos in positions:
                words[pos] = token
        return " ".join(w for w in words if w).strip()
    except Exception:  # noqa: BLE001
        return ""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for src in OpenAlexClient().search("retrieval augmented generation", max_results=2):
        print(f"- {src.title} ({src.published_year}) -> {src.url}")
