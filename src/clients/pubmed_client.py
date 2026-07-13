"""
PubMed / NCBI E-utilities client — biomedical literature.

Free API (no key required for light use). Optional NCBI_API_KEY / NCBI_EMAIL
improve rate limits.
Never raises: logs and returns [] on failure.
"""

from __future__ import annotations

import logging
import os
import uuid
import xml.etree.ElementTree as ET
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

_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_TIMEOUT = 15.0


class PubMedClient:
    """Search PubMed and fetch title + abstract XML."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
        timeout: float = _TIMEOUT,
    ) -> None:
        self.api_key = (
            api_key if api_key is not None else os.getenv("NCBI_API_KEY") or ""
        ).strip()
        self.email = (
            email if email is not None else os.getenv("NCBI_EMAIL") or "research@local"
        ).strip()
        self.timeout = timeout

    def search(self, query: str, max_results: int = 2) -> List[SourceSchema]:
        if not query or not query.strip():
            return []

        try:
            ids = self._esearch(query.strip(), max_results)
            if not ids:
                return []
            sources = self._efetch(ids)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PubMed search failed for query=%r: %s", query, exc)
            return []

        logger.info("PubMed search: query=%r -> %d results", query, len(sources))
        return sources

    def _common_params(self) -> dict:
        params: dict = {"tool": "AutonomousResearchScientist", "email": self.email}
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
        reraise=True,
    )
    def _esearch(self, query: str, max_results: int) -> list[str]:
        params = {
            **self._common_params(),
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(_ESEARCH, params=params)
            resp.raise_for_status()
            data = resp.json()
        return list((data.get("esearchresult") or {}).get("idlist") or [])

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
        reraise=True,
    )
    def _efetch(self, ids: list[str]) -> list[SourceSchema]:
        params = {
            **self._common_params(),
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "xml",
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(_EFETCH, params=params)
            resp.raise_for_status()
            xml_text = resp.text

        root = ET.fromstring(xml_text)
        sources: list[SourceSchema] = []
        for article in root.findall(".//PubmedArticle"):
            src = self._article_to_source(article)
            if src:
                sources.append(src)
        return sources

    @staticmethod
    def _article_to_source(article: ET.Element) -> SourceSchema | None:
        medline = article.find("MedlineCitation")
        if medline is None:
            return None
        pmid_el = medline.find("PMID")
        pmid = (pmid_el.text or "").strip() if pmid_el is not None else ""
        if not pmid:
            return None

        article_el = medline.find("Article")
        if article_el is None:
            return None

        title_el = article_el.find("ArticleTitle")
        title = "".join(title_el.itertext()).strip() if title_el is not None else ""
        if not title:
            return None

        abstract_parts = [
            "".join(a.itertext()).strip()
            for a in article_el.findall("Abstract/AbstractText")
        ]
        abstract = " ".join(p for p in abstract_parts if p).strip()
        if not abstract:
            abstract = title

        year = None
        year_el = article_el.find("Journal/JournalIssue/PubDate/Year")
        if year_el is not None and year_el.text and year_el.text.isdigit():
            y = int(year_el.text)
            if 1900 <= y <= 2026:
                year = y

        return SourceSchema(
            id=str(uuid.uuid4()),
            source_type=SourceType.pubmed,
            title=title,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            published_year=year,
            content=abstract,
            quality_score=0.88,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for src in PubMedClient().search("large language model clinical", max_results=2):
        print(f"- {src.title} ({src.published_year}) -> {src.url}")
