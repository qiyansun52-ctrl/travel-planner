"""Retry with exponential backoff -- async port of web/src/server/llm/retry.ts."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")

DEFAULT_MAX_RETRIES = 2
DEFAULT_BASE_DELAY_MS = 250
DEFAULT_MAX_DELAY_MS = 2_000

_TRANSIENT_UNIX_CODES = frozenset({
    "ECONNRESET",
    "ECONNREFUSED",
    "EHOSTUNREACH",
    "ENETUNREACH",
    "ETIMEDOUT",
    "EAI_AGAIN",
})


@dataclass(frozen=True)
class RetryOptions:
    max_retries: int = DEFAULT_MAX_RETRIES
    base_delay_ms: int = DEFAULT_BASE_DELAY_MS
    max_delay_ms: int = DEFAULT_MAX_DELAY_MS
    should_retry: Callable[[Exception], bool] | None = None


@dataclass(frozen=True)
class RetryResult(Generic[T]):
    value: T
    retry_count: int


class RetryExhaustedError(Exception):
    """Wraps the final cause after retries are exhausted."""

    def __init__(self, cause: Exception, retry_count: int) -> None:
        super().__init__(str(cause))
        self.cause = cause
        self.retry_count = retry_count


async def with_retry(
    operation: Callable[[], Awaitable[T]],
    options: RetryOptions | None = None,
) -> RetryResult[T]:
    opts = options or RetryOptions()
    should_retry = opts.should_retry or is_transient_network_error
    retry_count = 0

    while True:
        try:
            value = await operation()
            return RetryResult(value=value, retry_count=retry_count)
        except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
            raise
        except Exception as error:
            if retry_count >= opts.max_retries or not should_retry(error):
                raise RetryExhaustedError(error, retry_count) from error

            delay_ms = min(opts.base_delay_ms * (2 ** retry_count), opts.max_delay_ms)
            retry_count += 1
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)


def is_transient_network_error(error: Any) -> bool:
    if isinstance(error, asyncio.TimeoutError):
        return True
    if getattr(error, "transient", False):
        return True
    if getattr(error, "retryable", False):
        return True

    status = getattr(error, "status", None)
    if status in (408, 429):
        return True
    if isinstance(status, int) and status >= 500:
        return True

    code = getattr(error, "code", None)
    if isinstance(code, str) and code in _TRANSIENT_UNIX_CODES:
        return True
    return False
