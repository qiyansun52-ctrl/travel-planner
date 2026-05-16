"""Mirror of withRetry behavior in web/src/server/llm/retry.ts."""
from __future__ import annotations

import asyncio

import pytest

from app.llm.retry import (
    RetryExhaustedError,
    RetryOptions,
    is_transient_network_error,
    with_retry,
)


class _Transient(Exception):
    transient = True


class _PermanentHTTP(Exception):
    status = 400


class _TransientHTTP(Exception):
    status = 503


# ---------- with_retry: success path ----------

async def test_returns_value_with_zero_retries_on_first_success() -> None:
    async def op() -> int:
        return 42

    result = await with_retry(op, RetryOptions(base_delay_ms=0))
    assert result.value == 42
    assert result.retry_count == 0


async def test_retries_then_succeeds_and_reports_retry_count() -> None:
    calls = {"n": 0}

    async def op() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise _Transient("flaky")
        return "ok"

    result = await with_retry(op, RetryOptions(max_retries=3, base_delay_ms=0))
    assert result.value == "ok"
    assert result.retry_count == 2
    assert calls["n"] == 3


# ---------- with_retry: exhaustion ----------

async def test_raises_retry_exhausted_with_cause_after_max() -> None:
    async def op() -> None:
        raise _Transient("always")

    with pytest.raises(RetryExhaustedError) as ei:
        await with_retry(op, RetryOptions(max_retries=2, base_delay_ms=0))
    assert ei.value.retry_count == 2
    assert isinstance(ei.value.cause, _Transient)


async def test_does_not_retry_when_should_retry_returns_false() -> None:
    calls = {"n": 0}

    async def op() -> None:
        calls["n"] += 1
        raise _PermanentHTTP("hard fail")

    with pytest.raises(RetryExhaustedError):
        await with_retry(op, RetryOptions(max_retries=5, base_delay_ms=0))
    assert calls["n"] == 1  # never retried


async def test_reraises_cancelled_error_without_retry_wrapping() -> None:
    async def op() -> None:
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await with_retry(op, RetryOptions(base_delay_ms=0))


async def test_reraises_keyboard_interrupt_without_retry_wrapping() -> None:
    async def op() -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        await with_retry(op, RetryOptions(base_delay_ms=0))


# ---------- is_transient_network_error ----------

def test_is_transient_for_network_typeerror() -> None:
    # Python's analogue: any explicit transient-marked exception
    assert is_transient_network_error(_Transient()) is True


def test_is_transient_for_5xx_and_429_and_408() -> None:
    e1 = _TransientHTTP("503")
    assert is_transient_network_error(e1) is True
    e408 = type("E", (Exception,), {"status": 408})()
    assert is_transient_network_error(e408) is True
    e429 = type("E", (Exception,), {"status": 429})()
    assert is_transient_network_error(e429) is True


def test_is_not_transient_for_4xx_other_than_408_429() -> None:
    assert is_transient_network_error(_PermanentHTTP()) is False


def test_is_transient_for_unix_network_codes() -> None:
    e = type("E", (Exception,), {"code": "ECONNRESET"})()
    assert is_transient_network_error(e) is True
