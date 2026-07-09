"""
Shared test fixtures for unit tests.

`FakeDDGS` and `mock_response` are used across client tests to avoid ever
hitting real network during `pytest` runs — CI must be able to run these
with zero API keys and zero internet access.
"""

from unittest.mock import MagicMock

import pytest


class FakeDDGS:
    """Drop-in fake for the `ddgs.DDGS` class, injected via the
    `ddgs_class` parameter so we never monkey-patch the real library."""

    def __init__(self, fixed_results=None, raise_exc: Exception | None = None):
        self._fixed_results = fixed_results or []
        self._raise_exc = raise_exc

    def __call__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def text(self, query, max_results=5):
        if self._raise_exc:
            raise self._raise_exc
        return self._fixed_results[:max_results]


def make_mock_response(status_code: int, json_data: dict | None = None):
    """Build a fake httpx.Response-like object with just what our code reads:
    .status_code, .json(), .raise_for_status()."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data or {}
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture
def brave_success_response():
    return make_mock_response(
        200,
        {
            "web": {
                "results": [
                    {
                        "title": "Attention Is All You Need",
                        "url": "https://arxiv.org/abs/1706.03762",
                        "description": "The Transformer architecture paper.",
                        "age": "2017",
                    },
                    {
                        "title": "RAG blog post",
                        "url": "https://example.com/rag",
                        "description": "An overview of retrieval-augmented generation.",
                    },
                ]
            }
        },
    )
