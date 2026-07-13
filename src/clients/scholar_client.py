"""
Semantic Scholar client — academic paper search (Google-Scholar-like).

Uses the free Semantic Scholar Graph API. Optional API key via
SEMANTIC_SCHOLAR_API_KEY raises rate limits but is not required.

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

_ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "title,abstract,year,url,externalIds,authors,venue"
_USER_AGENT = "AutonomousResearchScientist/1.0"
_TIMEOUT = 15.0


class SemanticScholarClient:
    """Search Semantic Scholar for peer-reviewed / academic papers."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = _TIMEOUT,
    ) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("SEMANTIC_SCHOLAR_API_KEY") or "").strip()
        self.timeout = timeout

    def search(self, query: str, max_results: int = 2) -> List[SourceSchema]:
        if not query or not query.strip():
            return []

        try:
            papers = self._search_with_retry(query.strip(), max_results)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Semantic Scholar search failed for query=%r: %s", query, exc)
            return []

        sources = []
        for paper in papers:
            src = self._to_source(paper)
            if src:
                sources.append(src)

        logger.info(
            "Semantic Scholar search: query=%r -> %d results", query, len(sources)
        )
        return sources

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
        reraise=True,
    )
    def _search_with_retry(self, query: str, max_results: int) -> list[dict]:
        headers = {"User-Agent": _USER_AGENT}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        params = {
            "query": query,
            "limit": max_results,
            "fields": _FIELDS,
        }
        with httpx.Client(timeout=self.timeout, headers=headers) as client:
            resp = client.get(_ENDPOINT, params=params)
            if resp.status_code == 429:
                logger.warning("Semantic Scholar rate-limited (429)")
                return []
            resp.raise_for_status()
            data = resp.json()
        return list(data.get("data") or [])

    @staticmethod
    def _to_source(paper: dict) -> SourceSchema | None:
        title = (paper.get("title") or "").strip()
        abstract = (paper.get("abstract") or "").strip()
        if not title or not abstract:
            return None

        external = paper.get("externalIds") or {}
        arxiv_id = external.get("ArXiv")
        doi = external.get("DOI")
        paper_id = paper.get("paperId")

        if arxiv_id:
            url = f"https://arxiv.org/abs/{arxiv_id}"
        elif doi:
            url = f"https://doi.org/{doi}"
        elif paper.get("url"):
            url = str(paper["url"])
        elif paper_id:
            url = f"https://www.semanticscholar.org/paper/{paper_id}"
        else:
            return None

        authors = ", ".join(
            a.get("name", "") for a in (paper.get("authors") or []) if a.get("name")
        )
        venue = paper.get("venue") or ""
        header_bits = [b for b in (authors, venue) if b]
        header = " | ".join(header_bits)
        content = f"{header}\n\n{abstract}" if header else abstract

        year = paper.get("year")
        published_year = int(year) if isinstance(year, int) and 1900 <= year <= 2026 else None

        return SourceSchema(
            id=str(uuid.uuid4()),
            source_type=SourceType.scholar,
            title=title,
            url=url,
            published_year=published_year,
            content=content,
            quality_score=0.85,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for src in SemanticScholarClient().search("hallucination mitigation LLM", max_results=2):
        print(f"- {src.title} ({src.published_year}) -> {src.url}")
