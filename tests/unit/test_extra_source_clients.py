"""
Unit tests for new source clients (mocked HTTP — no live network).
"""

from __future__ import annotations

import json

import httpx

from src.clients.openalex_client import OpenAlexClient, _reconstruct_abstract
from src.clients.pubmed_client import PubMedClient
from src.clients.scholar_client import SemanticScholarClient
from src.clients.wikipedia_client import WikipediaClient
from src.schemas.common import SourceType


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200, text: str | None = None):
        self._payload = payload
        self.status_code = status_code
        self.text = text if text is not None else (
            payload if isinstance(payload, str) else json.dumps(payload)
        )

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("GET", "https://example.com"),
                response=httpx.Response(self.status_code),
            )

    def json(self):
        if isinstance(self._payload, str):
            return json.loads(self._payload)
        return self._payload


class _FakeClient:
    def __init__(self, responses: list):
        self._responses = list(responses)
        self.calls: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None, **kwargs):
        self.calls.append((url, params))
        if not self._responses:
            raise AssertionError(f"Unexpected HTTP GET {url}")
        return self._responses.pop(0)


def test_wikipedia_client_builds_sources(monkeypatch):
    search_resp = _FakeResponse(
        {"query": {"search": [{"title": "Retrieval-augmented generation"}]}}
    )
    extract_resp = _FakeResponse(
        {
            "query": {
                "pages": {
                    "1": {
                        "title": "Retrieval-augmented generation",
                        "extract": "RAG combines retrieval with generation.",
                        "fullurl": "https://en.wikipedia.org/wiki/Retrieval-augmented_generation",
                    }
                }
            }
        }
    )
    fake = _FakeClient([search_resp, extract_resp])
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: fake)

    sources = WikipediaClient().search("RAG", max_results=1)
    assert len(sources) == 1
    assert sources[0].source_type == SourceType.wikipedia
    assert "RAG combines" in sources[0].content


def test_scholar_client_builds_sources(monkeypatch):
    resp = _FakeResponse(
        {
            "data": [
                {
                    "paperId": "abc",
                    "title": "Mitigating Hallucinations",
                    "abstract": "We study hallucination mitigation.",
                    "year": 2024,
                    "url": "https://www.semanticscholar.org/paper/abc",
                    "authors": [{"name": "Ada"}],
                    "externalIds": {},
                }
            ]
        }
    )
    fake = _FakeClient([resp])
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: fake)

    sources = SemanticScholarClient(api_key="").search("hallucination", max_results=1)
    assert len(sources) == 1
    assert sources[0].source_type == SourceType.scholar
    assert sources[0].published_year == 2024


def test_openalex_reconstruct_and_search(monkeypatch):
    inverted = {"Hello": [0], "world": [1]}
    assert _reconstruct_abstract(inverted) == "Hello world"

    resp = _FakeResponse(
        {
            "results": [
                {
                    "display_name": "Open work",
                    "id": "https://openalex.org/W1",
                    "publication_year": 2023,
                    "abstract_inverted_index": {"Open": [0], "abstract": [1]},
                    "authorships": [{"author": {"display_name": "Bob"}}],
                    "primary_location": {"landing_page_url": "https://example.com/paper"},
                }
            ]
        }
    )
    fake = _FakeClient([resp])
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: fake)

    sources = OpenAlexClient(mailto="t@example.com").search("open", max_results=1)
    assert len(sources) == 1
    assert sources[0].source_type == SourceType.openalex
    assert "Open abstract" in sources[0].content


def test_pubmed_client_parses_xml(monkeypatch):
    search_resp = _FakeResponse({"esearchresult": {"idlist": ["999"]}})
    xml = """
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>999</PMID>
          <Article>
            <ArticleTitle>Clinical LLMs</ArticleTitle>
            <Abstract><AbstractText>Useful abstract here.</AbstractText></Abstract>
            <Journal><JournalIssue><PubDate><Year>2022</Year></PubDate></JournalIssue></Journal>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>
    """
    fetch_resp = _FakeResponse(xml, text=xml)
    fake = _FakeClient([search_resp, fetch_resp])
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: fake)

    sources = PubMedClient(api_key="", email="t@example.com").search("LLM", max_results=1)
    assert len(sources) == 1
    assert sources[0].source_type == SourceType.pubmed
    assert sources[0].url.endswith("/999/")
    assert sources[0].published_year == 2022


def test_clients_return_empty_on_blank_query():
    assert WikipediaClient().search("  ") == []
    assert SemanticScholarClient(api_key="").search("") == []
    assert OpenAlexClient().search("") == []
    assert PubMedClient().search("") == []
