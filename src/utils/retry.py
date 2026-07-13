"""
Shared retry decorator — implements the plan's error-handling strategy
(section 2 / section 9): "Retry exponentiel + fallback + dégradation gracieuse".

3 attempts, exponential backoff. Used by every external API client (arXiv,
Brave Search, and later the LLM wrapper) so retry behavior is consistent
and defined in exactly one place.

Deliberately generic over exception types: each client passes in which
exceptions are worth retrying (e.g. timeouts, 5xx) vs which should fail fast
(e.g. a 401 bad API key — retrying that 3 times just wastes 7 seconds before
failing anyway).
"""

from typing import Type

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


def with_retry(*retryable_exceptions: Type[Exception]):
    """Decorator factory: 3 attempts, exponential backoff starting at 1s
    (1s, 2s, 4s), only retrying the given exception types.

    Usage:
        @with_retry(httpx.TimeoutException, httpx.ConnectError)
        async def call_api(...): ...
    """
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(retryable_exceptions),
        reraise=True,  # after 3 failed attempts, raise the real exception
    )
