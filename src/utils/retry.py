"""
Retry utilities with exponential backoff.

Provides a decorator for retrying functions that may fail transiently.
"""

import time
import logging
from functools import wraps
from typing import Callable, Type, Tuple

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including first)
        backoff_factor: Base wait time (doubles each retry)
        exceptions: Tuple of exception types to retry on

    Example:
        @retry_with_backoff(max_attempts=3)
        def call_api():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"All {max_attempts} attempts failed: {e}")
                        raise
                    wait_time = backoff_factor * (2 ** (attempt - 1))
                    logger.warning(
                        f"Attempt {attempt} failed: {e}. "
                        f"Retrying in {wait_time:.2f}s..."
                    )
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator