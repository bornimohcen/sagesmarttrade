from __future__ import annotations

import time
from typing import Any, Callable, Iterable, Tuple, Type, TypeVar


T = TypeVar("T")


def retry(
    max_attempts: int = 3,
    backoff_seconds: float = 2.0,
    retry_exceptions: Iterable[Type[BaseException]] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Simple retry decorator with linear backoff.

    Intended for wrapping external API calls (e.g. HTTP requests).
    """
    if max_attempts <= 0:
        raise ValueError("max_attempts must be positive")

    exc_tuple: Tuple[Type[BaseException], ...]
    if retry_exceptions is None:
        exc_tuple = (Exception,)
    else:
        exc_tuple = tuple(retry_exceptions)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exc_tuple:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    # Linear backoff: n * backoff_seconds
                    sleep_for = backoff_seconds * attempt
                    time.sleep(sleep_for)

        return wrapper

    return decorator

