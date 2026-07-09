"""
Unit tests for src/clients/scraper.py

`requests.Session.get` is mocked throughout — no real HTTP calls are made,
so these tests are fast, deterministic, and safe to run in CI (no risk of
hitting a real site, being rate-limited, or failing due to flaky internet).

Run:
    pytest tests/unit/test_scraper.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from src.clients.scraper import WebScraper
from src.schemas.common import SourceType
from src.schemas.source import SourceSchema


LONG_PARAGRAPH = "This is a long article paragraph. " * 10  # > 100 chars


def make_response(
    text: str = "",
    status_code: int = 200,
    content_type: str = "text/html; charset=utf-8",
) -> MagicMock:
    response = MagicMock()
    response.text = text
    response.status_code = status_code
    response.headers = {"Content-Type": content_type}
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"{status_code} error")
    else:
        response.raise_for_status.return_value = None
    return response


@pytest.fixture()
def scraper() -> WebScraper:
    return WebScraper()


@pytest.fixture(autouse=True)
def no_real_sleep(mocker):
    # tenacity's retry backoff calls time.sleep — patch it globally so
    # retry tests run instantly instead of actually waiting seconds.
    mocker.patch("time.sleep")


# --------------------------------------------------------------------- #
# fetch() — happy path
# --------------------------------------------------------------------- #
def test_fetch_returns_source_on_success(scraper, mocker):
    html = f"<html><head><title>My Article</title></head><body><article><p>{LONG_PARAGRAPH}</p></article></body></html>"
    mocker.patch.object(scraper._session, "get", return_value=make_response(html))

    source = scraper.fetch("https://example.com/article")

    assert isinstance(source, SourceSchema)
    assert source.title == "My Article"
    assert source.source_type == SourceType.web
    assert "long article paragraph" in source.content


def test_fetch_strips_noise_tags(scraper, mocker):
    html = (
        "<html><head><title>Clean Me</title>"
        "<style>.x{color:red}</style></head>"
        "<body>"
        "<nav>Home | About | Contact</nav>"
        f"<article><p>{LONG_PARAGRAPH}</p></article>"
        "<script>trackEvent('pageview');</script>"
        "<footer>Copyright 2026</footer>"
        "</body></html>"
    )
    mocker.patch.object(scraper._session, "get", return_value=make_response(html))

    source = scraper.fetch("https://example.com/article")

    assert source is not None
    assert "trackEvent" not in source.content
    assert "Home | About | Contact" not in source.content
    assert "Copyright 2026" not in source.content
    assert "long article paragraph" in source.content


def test_fetch_prefers_article_tag_over_full_body(scraper, mocker):
    html = (
        "<html><head><title>T</title></head><body>"
        "<div>Sidebar junk that should be ignored because article exists</div>"
        f"<article><p>{LONG_PARAGRAPH}</p></article>"
        "</body></html>"
    )
    mocker.patch.object(scraper._session, "get", return_value=make_response(html))

    source = scraper.fetch("https://example.com/article")

    assert source is not None
    assert "Sidebar junk" not in source.content


# --------------------------------------------------------------------- #
# fetch() — rejection / graceful-failure paths
# --------------------------------------------------------------------- #
def test_fetch_rejects_invalid_url_without_network_call(scraper, mocker):
    spy = mocker.patch.object(scraper._session, "get")

    assert scraper.fetch("not-a-url") is None
    assert scraper.fetch("") is None
    spy.assert_not_called()


def test_fetch_returns_none_for_non_html_content_type(scraper, mocker):
    mocker.patch.object(
        scraper._session,
        "get",
        return_value=make_response("%PDF-1.4 ...", content_type="application/pdf"),
    )

    assert scraper.fetch("https://example.com/file.pdf") is None


def test_fetch_returns_none_when_content_too_short(scraper, mocker):
    html = "<html><head><title>Empty</title></head><body><p>Too short.</p></body></html>"
    mocker.patch.object(scraper._session, "get", return_value=make_response(html))

    assert scraper.fetch("https://example.com/empty") is None


def test_fetch_returns_none_on_http_error(scraper, mocker):
    mocker.patch.object(scraper._session, "get", return_value=make_response("", status_code=404))

    assert scraper.fetch("https://example.com/missing") is None


def test_fetch_returns_none_after_persistent_connection_errors(scraper, mocker):
    mocker.patch.object(
        scraper._session, "get", side_effect=requests.ConnectionError("network unreachable")
    )

    assert scraper.fetch("https://example.com/unreachable") is None


def test_fetch_retries_then_succeeds_after_transient_error(scraper, mocker):
    html = f"<html><head><title>Recovered</title></head><body><p>{LONG_PARAGRAPH}</p></body></html>"
    get_mock = mocker.patch.object(
        scraper._session,
        "get",
        side_effect=[
            requests.ConnectionError("flaky network"),
            requests.ConnectionError("flaky network"),
            make_response(html),
        ],
    )

    source = scraper.fetch("https://example.com/flaky")

    assert source is not None
    assert source.title == "Recovered"
    assert get_mock.call_count == 3


# --------------------------------------------------------------------- #
# Title extraction fallback chain
# --------------------------------------------------------------------- #
def test_title_falls_back_to_h1_when_no_title_tag(scraper, mocker):
    html = f"<html><body><h1>Fallback Heading</h1><p>{LONG_PARAGRAPH}</p></body></html>"
    mocker.patch.object(scraper._session, "get", return_value=make_response(html))

    source = scraper.fetch("https://example.com/no-title")

    assert source.title == "Fallback Heading"


def test_title_falls_back_to_untitled_when_nothing_found(scraper, mocker):
    html = f"<html><body><p>{LONG_PARAGRAPH}</p></body></html>"
    mocker.patch.object(scraper._session, "get", return_value=make_response(html))

    source = scraper.fetch("https://example.com/no-title-no-h1")

    assert source.title == "Untitled page"


# --------------------------------------------------------------------- #
# Content is capped to avoid huge downstream LLM prompts
# --------------------------------------------------------------------- #
def test_content_is_capped_at_max_length():
    small_cap_scraper = WebScraper(max_content_chars=50)
    html = f"<html><head><title>T</title></head><body><p>{LONG_PARAGRAPH}</p></body></html>"

    import unittest.mock as mock

    with mock.patch.object(small_cap_scraper._session, "get", return_value=make_response(html)):
        source = small_cap_scraper.fetch("https://example.com/long")

    assert source is not None
    assert len(source.content) <= 50