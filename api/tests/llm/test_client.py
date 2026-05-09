"""Mirror of web/src/server/llm/client.test.ts.

Uses an in-memory FakeProvider so no real Gemini call is made.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable

import pytest
from pydantic import BaseModel, ConfigDict

from app.llm.client import (
    LLMConfigurationError,
    LLMJsonParseError,
    LLMTimeoutError,
    generate_structured,
)
from app.llm.cost_logger import LLMCostLogEntry
from app.llm.retry import RetryOptions


class _Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str


# ---------- helpers ----------

@dataclass
class FakeProvider:
    """Provider stub with scripted responses or behaviour callable."""

    handler: Callable[..., Awaitable[str]]
    calls: list[dict] = field(default_factory=list)

    async def generate(self, *, system: str, user: str, timeout_ms: int) -> str:
        self.calls.append({"system": system, "user": user, "timeout_ms": timeout_ms})
        return await self.handler(system=system, user=user, timeout_ms=timeout_ms)


def _capturing_logger(sink: list[LLMCostLogEntry]):
    async def _log(entry: LLMCostLogEntry) -> None:
        sink.append(entry)
    return _log


# ---------- success path ----------

async def test_returns_validated_pydantic_model_and_logs_cost() -> None:
    entries: list[LLMCostLogEntry] = []

    async def ok(**_: object) -> str:
        return '{"message":"hello"}'

    result = await generate_structured(
        system="You return JSON.",
        user="Say hello.",
        schema=_Output,
        label="unit.success",
        provider=FakeProvider(handler=ok),
        cost_logger=_capturing_logger(entries),
        retry=RetryOptions(base_delay_ms=0),
    )

    assert result == _Output(message="hello")
    assert len(entries) == 1
    assert entries[0].label == "unit.success"
    assert entries[0].success is True
    assert entries[0].retry_count == 0
    assert entries[0].prompt_tokens_estimate > 0
    assert entries[0].completion_tokens_estimate > 0


# ---------- json repair path ----------

async def test_repairs_malformed_json_before_schema_validation() -> None:
    async def messy(**_: object) -> str:
        return 'Sure:\n{"message":"hello",}\n'

    result = await generate_structured(
        system="s", user="u", schema=_Output, label="unit.repair",
        provider=FakeProvider(handler=messy),
        cost_logger=_capturing_logger([]),
        retry=RetryOptions(base_delay_ms=0),
    )
    assert result.message == "hello"


async def test_raises_llm_json_parse_error_when_unrecoverable() -> None:
    async def bad(**_: object) -> str:
        return "this is not json at all"

    with pytest.raises(LLMJsonParseError):
        await generate_structured(
            system="s", user="u", schema=_Output, label="unit.parse_fail",
            provider=FakeProvider(handler=bad),
            cost_logger=_capturing_logger([]),
            retry=RetryOptions(base_delay_ms=0),
        )


# ---------- retry path ----------

async def test_retries_transient_then_succeeds_and_records_retry_count() -> None:
    entries: list[LLMCostLogEntry] = []
    state = {"calls": 0}

    async def flaky(**_: object) -> str:
        state["calls"] += 1
        if state["calls"] == 1:
            err = ConnectionError("flaky")
            err.transient = True  # type: ignore[attr-defined]
            raise err
        return '{"message":"recovered"}'

    result = await generate_structured(
        system="s", user="u", schema=_Output, label="unit.retry",
        provider=FakeProvider(handler=flaky),
        cost_logger=_capturing_logger(entries),
        retry=RetryOptions(base_delay_ms=0),
    )
    assert result.message == "recovered"
    assert state["calls"] == 2
    assert entries[0].success is True
    assert entries[0].retry_count == 1


# ---------- timeout path ----------

async def test_enforces_configured_timeout() -> None:
    async def hang(**_: object) -> str:
        await asyncio.sleep(10)
        return ""

    with pytest.raises(LLMTimeoutError):
        await generate_structured(
            system="s", user="u", schema=_Output, label="unit.timeout",
            provider=FakeProvider(handler=hang),
            cost_logger=_capturing_logger([]),
            retry=RetryOptions(base_delay_ms=0, max_retries=0),
            timeout_ms=20,
        )


# ---------- cost logger isolation ----------

async def test_does_not_fail_when_cost_logger_raises() -> None:
    async def ok(**_: object) -> str:
        return '{"message":"hello"}'

    async def bad_logger(_entry: LLMCostLogEntry) -> None:
        raise RuntimeError("disk full")

    result = await generate_structured(
        system="s", user="u", schema=_Output, label="unit.logging_failure",
        provider=FakeProvider(handler=ok),
        cost_logger=bad_logger,
        retry=RetryOptions(base_delay_ms=0),
    )
    assert result.message == "hello"


# ---------- failure logging ----------

async def test_logs_failure_when_retries_exhausted() -> None:
    entries: list[LLMCostLogEntry] = []

    async def always_fail(**_: object) -> str:
        err = ConnectionError("always")
        err.transient = True  # type: ignore[attr-defined]
        raise err

    with pytest.raises(ConnectionError):
        await generate_structured(
            system="s", user="u", schema=_Output, label="unit.exhaust",
            provider=FakeProvider(handler=always_fail),
            cost_logger=_capturing_logger(entries),
            retry=RetryOptions(base_delay_ms=0, max_retries=1),
        )

    assert len(entries) == 1
    assert entries[0].success is False
    assert entries[0].failure is not None
    assert entries[0].retry_count == 1


# ---------- default provider config error ----------

async def test_default_provider_raises_config_error_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER_API_KEY", raising=False)

    from app.llm.client import create_default_provider

    with pytest.raises(LLMConfigurationError):
        create_default_provider(env={})
