"""Retry logic for transient failures."""

import logging
import time
from functools import wraps
from typing import Callable, TypeVar

T = TypeVar("T")


def retry_on_transient_error(
    max_retries: int, delay_seconds: int, logger: logging.Logger
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to retry on transient errors (connection timeout, HTTP 429, etc.).
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_str = str(e).lower()

                    # Check if error is likely transient
                    transient_indicators = [
                        "timeout",
                        "connection reset",
                        "connection refused",
                        "temporary",
                        "temporarily unavailable",
                        "429",
                        "too many requests",
                    ]
                    is_transient = any(indicator in error_str for indicator in transient_indicators)

                    if not is_transient or attempt >= max_retries:
                        raise

                    logger.warning(
                        f"Transient error (attempt {attempt}/{max_retries}): {e}. "
                        f"Retrying in {delay_seconds}s..."
                    )
                    time.sleep(delay_seconds)

            # Should not reach here, but raise if all retries exhausted
            if last_exception:
                raise last_exception

        return wrapper

    return decorator
