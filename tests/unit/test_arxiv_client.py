"""
Unit tests for src/clients/arxiv_client.py

These tests never touch the real network — the underlying `arxiv.Client`
is mocked out, so they run fast and deterministically in CI (no flakiness
from arXiv being slow/down, no risk of tripping their rate limit during
a build).

Run:
    pytest tests/unit/test_arxiv_client.py -v
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from src.clients.arxiv_client import ArxivClient
from src.schemas.common import SourceType
from src.schemas.source import SourceSchema


# --------------------------------------------------------------------- #
# Helpers — lightweight stand-ins for `arxiv.Result` objects.
# We only need the attributes ArxivClient._to_source() actually reads,
# so a SimpleNamespace is enough; no need to construct a real arxiv.Result.
# --------------------------------------------------------------------- #
def make_fake_result(
    title: str = "Attention Is All You Need",
    entry_id: str = "http://arxiv.org/abs/1706.03762v5",
    summary: str = "We propose a new simple network architecture, the Transformer.",
    author_names: list[str] | None = None,
    published: datetime | None = None,
) -> SimpleNamespace:
    author_names = author_names if author_names is not None else ["Ashish Vaswani", "Noam Shazeer"]
    return SimpleNamespace(
        title=title,
        entry_id=entry_id,
        summary=summary,
        authors=[SimpleNamespace(name=n) for n in author_names],
        published=published or datetime(2017, 6, 12),
    )


@pytest.fixture()
def client() -> ArxivClient:
    # min_interval=0 so tests don't actually wait on the throttle
    return ArxivClient(min_interval=0)


# --------------------------------------------------------------------- #
# search()
# --------------------------------------------------------------------- #
def test_search_returns_sources_on_success(client, mocker):
    fake_results = [make_fake_result(title="Paper A"), make_fake_result(title="Paper B")]
    mocker.patch.object(client._client, "results", return_value=fake_results)

    sources = client.search("transformers", max_results=2)

    assert len(sources) == 2
    assert all(isinstance(s, SourceSchema) for s in sources)
    assert {s.title for s in sources} == {"Paper A", "Paper B"}
    assert all(s.source_type == SourceType.arxiv for s in sources)


def test_search_empty_query_returns_empty_list_without_calling_api(client, mocker):
    spy = mocker.patch.object(client._client, "results")

    assert client.search("") == []
    assert client.search("   ") == []
    spy.assert_not_called()


def test_search_degrades_gracefully_on_api_failure(client, mocker):
    # Bypass tenacity's real retry/backoff sleeping by mocking the
    # retry-wrapped method directly — we're testing search()'s error
    # handling here, not tenacity's own retry mechanics.
    mocker.patch.object(client, "_search_with_retry", side_effect=RuntimeError("arXiv is down"))

    result = client.search("anything")

    assert result == []  # never raises, degrades to empty list


def test_search_respects_max_results(client, mocker):
    fake_results = [make_fake_result(title=f"Paper {i}") for i in range(3)]
    mocker.patch.object(client._client, "results", return_value=fake_results)

    sources = client.search("query", max_results=3)

    assert len(sources) == 3


# --------------------------------------------------------------------- #
# _to_source()
# --------------------------------------------------------------------- #
def test_to_source_folds_authors_into_content(client):
    fake = make_fake_result(author_names=["Alice", "Bob"], summary="Some abstract text.")

    source = client._to_source(fake)

    assert isinstance(source, SourceSchema)
    assert "Alice" in source.content
    assert "Bob" in source.content
    assert "Some abstract text." in source.content


def test_to_source_handles_missing_authors(client):
    fake = make_fake_result(author_names=[], summary="Solo abstract.")

    source = client._to_source(fake)

    assert "Authors:" not in source.content
    assert "Solo abstract." in source.content


def test_to_source_sets_published_year(client):
    fake = make_fake_result(published=datetime(2020, 1, 1))

    source = client._to_source(fake)

    assert source.published_year == 2020


def test_to_source_handles_missing_published_date(client):
    fake = make_fake_result(published=None)
    # SimpleNamespace default already sets a date in the helper, so
    # override explicitly to simulate arxiv returning no date at all.
    fake.published = None

    source = client._to_source(fake)

    assert source.published_year is None


def test_to_source_produces_valid_http_url(client):
    fake = make_fake_result(entry_id="http://arxiv.org/abs/1706.03762v5")

    source = client._to_source(fake)

    assert str(source.url).startswith("http://arxiv.org/abs/1706.03762")


# --------------------------------------------------------------------- #
# Throttle
# --------------------------------------------------------------------- #
def test_throttle_sleeps_when_called_too_soon(mocker):
    throttled_client = ArxivClient(min_interval=5.0)
    sleep_mock = mocker.patch("src.clients.arxiv_client.time.sleep")

    throttled_client._throttle()  # first call: no prior timestamp -> may or may not sleep
    sleep_mock.reset_mock()

    throttled_client._throttle()  # second call immediately after -> should sleep ~5s

    sleep_mock.assert_called_once()
    (slept_for,), _ = sleep_mock.call_args
    assert 0 < slept_for <= 5.0
