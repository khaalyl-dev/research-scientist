"""
Unit tests for src/clients/brave_client.py.

Zero real network calls — httpx is mocked, and DuckDuckGo is replaced via
the injectable `ddgs_class` parameter (see FakeDDGS in conftest.py). This
means the suite runs identically with or without a real BRAVE_API_KEY, and
in CI with no internet access at all.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from pydantic import ValidationError

from src.clients.brave_client import (
    BraveAPIError,
    BraveAuthError,
    BraveQuotaExceededError,
    BraveSearchClient,
    WebSearchResult,
    web_search,
)
from tests.unit.conftest import FakeDDGS, make_mock_response


# ---------------------------------------------------------------------------
# BraveSearchClient.search() — direct tests of the Brave call itself
# ---------------------------------------------------------------------------

class TestBraveSearchClient:
    async def test_search_success_parses_results(self, brave_success_response):
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=brave_success_response)):
            client = BraveSearchClient(api_key="fake-key")
            results = await client.search("transformers", count=5)

        assert len(results) == 2
        assert results[0].title == "Attention Is All You Need"
        assert str(results[0].url) == "https://arxiv.org/abs/1706.03762"
        assert results[0].published_date == "2017"
        assert results[0].engine == "brave"

    async def test_search_respects_count_limit(self, brave_success_response):
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=brave_success_response)):
            client = BraveSearchClient(api_key="fake-key")
            results = await client.search("transformers", count=1)

        assert len(results) == 1

    async def test_search_skips_malformed_result_without_crashing(self):
        response = make_mock_response(
            200,
            {"web": {"results": [{"title": "missing url field"}]}},
        )
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
            client = BraveSearchClient(api_key="fake-key")
            results = await client.search("query", count=5)

        assert results == []  # malformed entry skipped, no exception raised

    async def test_search_401_raises_auth_error(self):
        response = make_mock_response(401)
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
            client = BraveSearchClient(api_key="bad-key")
            with pytest.raises(BraveAuthError):
                await client.search("query")

    async def test_search_429_raises_quota_error(self):
        response = make_mock_response(429)
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
            client = BraveSearchClient(api_key="fake-key")
            with pytest.raises(BraveQuotaExceededError):
                await client.search("query")

    async def test_search_no_api_key_raises_auth_error(self):
        client = BraveSearchClient(api_key=None)
        with pytest.raises(BraveAuthError):
            await client.search("query")

    async def test_search_5xx_raises_brave_api_error(self):
        response = make_mock_response(503)
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
            client = BraveSearchClient(api_key="fake-key")
            with pytest.raises(BraveAPIError):
                await client.search("query")

    async def test_search_retries_on_timeout_then_succeeds(self, brave_success_response):
        # First call times out, second succeeds — proves the tenacity retry
        # decorator actually kicks in rather than failing on the first error.
        mock_get = AsyncMock(side_effect=[httpx.TimeoutException("timed out"), brave_success_response])
        with patch("httpx.AsyncClient.get", new=mock_get):
            client = BraveSearchClient(api_key="fake-key")
            results = await client.search("query")

        assert len(results) == 2
        assert mock_get.call_count == 2

    async def test_search_gives_up_after_3_timeouts(self):
        mock_get = AsyncMock(side_effect=httpx.TimeoutException("always times out"))
        with patch("httpx.AsyncClient.get", new=mock_get):
            client = BraveSearchClient(api_key="fake-key")
            with pytest.raises(httpx.TimeoutException):
                await client.search("query")

        assert mock_get.call_count == 3  # stop_after_attempt(3)


# ---------------------------------------------------------------------------
# web_search() — the public entry point, including fallback behavior
# ---------------------------------------------------------------------------

class TestWebSearchFallback:
    async def test_uses_brave_when_successful_no_fallback(self, brave_success_response):
        never_called_ddgs = FakeDDGS(raise_exc=AssertionError("DuckDuckGo should not be called"))
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=brave_success_response)), \
             patch("os.getenv", return_value="fake-key"):
            results = await web_search("query", ddgs_class=never_called_ddgs)

        assert all(r.engine == "brave" for r in results)

    async def test_falls_back_on_quota_exceeded(self):
        response = make_mock_response(429)
        fake_ddgs = FakeDDGS([{"title": "DDG result", "href": "https://example.com", "body": "text"}])
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)), \
             patch("os.getenv", return_value="fake-key"):
            results = await web_search("query", ddgs_class=fake_ddgs)

        assert len(results) == 1
        assert results[0].engine == "duckduckgo"

    async def test_falls_back_on_missing_api_key(self):
        fake_ddgs = FakeDDGS([{"title": "DDG only", "href": "https://example.org", "body": "text"}])
        with patch.dict("os.environ", {}, clear=True):
            results = await web_search("query", ddgs_class=fake_ddgs)

        assert len(results) == 1
        assert results[0].engine == "duckduckgo"

    async def test_falls_back_on_empty_brave_results(self):
        response = make_mock_response(200, {"web": {"results": []}})
        fake_ddgs = FakeDDGS([{"title": "DDG fallback", "href": "https://example.net", "body": "text"}])
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)), \
             patch("os.getenv", return_value="fake-key"):
            results = await web_search("query", ddgs_class=fake_ddgs)

        assert len(results) == 1
        assert results[0].engine == "duckduckgo"

    async def test_falls_back_after_repeated_timeouts(self):
        mock_get = AsyncMock(side_effect=httpx.TimeoutException("down"))
        fake_ddgs = FakeDDGS([{"title": "DDG after timeout", "href": "https://x.com", "body": "text"}])
        with patch("httpx.AsyncClient.get", new=mock_get), \
             patch("os.getenv", return_value="fake-key"):
            results = await web_search("query", ddgs_class=fake_ddgs)

        assert len(results) == 1
        assert results[0].engine == "duckduckgo"

    async def test_skips_malformed_duckduckgo_result_without_crashing(self):
        response = make_mock_response(429)
        # missing "href" -> WebSearchResult will fail URL validation, should be skipped not crash
        fake_ddgs = FakeDDGS([{"title": "no url here", "body": "text"}])
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)), \
             patch("os.getenv", return_value="fake-key"):
            results = await web_search("query", ddgs_class=fake_ddgs)

        assert results == []


# ---------------------------------------------------------------------------
# WebSearchResult schema validation
# ---------------------------------------------------------------------------

class TestWebSearchResultSchema:
    def test_rejects_invalid_url(self):
        with pytest.raises(ValidationError):
            WebSearchResult(title="t", url="not-a-valid-url", engine="brave")

    def test_accepts_valid_minimal_result(self):
        result = WebSearchResult(title="t", url="https://example.com", engine="brave")
        assert result.description == ""
        assert result.published_date is None
