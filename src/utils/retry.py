from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")


def retry_call(
    fn: Callable[[], T],
    retries: int = 3,
    backoff_seconds: float = 2.0,
    backoff_multiplier: float = 2.0,
) -> T:
    last_exc = None
    delay = backoff_seconds

    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt == retries:
                break
            print(
                f"[WARN] retry_call attempt {attempt} failed: {exc} | "
                f"sleeping {delay} seconds before retry"
            )
            time.sleep(delay)
            delay *= backoff_multiplier

    raise last_exc