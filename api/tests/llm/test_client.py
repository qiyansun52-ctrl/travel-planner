"""Mirror of web/src/server/llm/client.test.ts.

Uses an in-memory FakeProvider so no real Gemini call is made.
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from types import ModuleType, SimpleNamespace
from typing import Awaitable, Callable

import pytest
from pydantic import BaseModel, ConfigDict, Field

from app.llm.client import (
    GeminiLLMProvider,
    LLMConfigurationError,
    LLMJsonParseError,
    LLMNetworkError,
    LLMTimeoutError,
    generate_structured,
)
from app.llm.cost_logger import LLMCostLogEntry
from app.llm.retry import RetryOptions


class _Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str


class _PositiveOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: int = Field(gt=0)


# ---------- helpers ----------

@dataclass
class FakeProvider:
    """Provider stub with scripted responses or behaviour callable."""

    handler: Callable[..., Awaitable[str]]
    calls: list[dict] = field(default_factory=list)

    async def generate(
        self,
        *,
        system: str,
        user: str,
        timeout_ms: int,
        schema: type[BaseModel] | None = None,
    ) -> str:
        self.calls.append({
            "system": system,
            "user": user,
            "timeout_ms": timeout_ms,
            "schema": schema,
        })
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

    provider = FakeProvider(handler=ok)
    result = await generate_structured(
        system="You return JSON.",
        user="Say hello.",
        schema=_Output,
        label="unit.success",
        provider=provider,
        cost_logger=_capturing_logger(entries),
        retry=RetryOptions(base_delay_ms=0),
    )

    assert result == _Output(message="hello")
    assert provider.calls[0]["system"].startswith("You return JSON.")
    assert "JSON Schema" in provider.calls[0]["system"]
    assert '"message"' in provider.calls[0]["system"]
    assert provider.calls[0]["schema"] is _Output
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


async def test_retries_schema_validation_failure_then_succeeds() -> None:
    entries: list[LLMCostLogEntry] = []
    state = {"calls": 0}

    async def flaky_json(**_: object) -> str:
        state["calls"] += 1
        if state["calls"] == 1:
            return '{"wrong":"shape"}'
        return '{"message":"recovered"}'

    result = await generate_structured(
        system="s",
        user="u",
        schema=_Output,
        label="unit.schema_retry",
        provider=FakeProvider(handler=flaky_json),
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


# ---------- Gemini provider ----------

async def test_gemini_generate_returns_json_and_closes_async_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed = {"value": False}
    calls: list[dict[str, object]] = []

    class FakeAPIError(Exception):
        pass

    class FakeModels:
        async def generate_content(self, **kwargs: object) -> SimpleNamespace:
            calls.append(kwargs)
            return SimpleNamespace(text='{"message":"from gemini"}')

    class FakeAio:
        def __init__(self) -> None:
            self.models = FakeModels()

        async def aclose(self) -> None:
            closed["value"] = True

    class FakeClient:
        def __init__(self, *, api_key: str) -> None:
            self.api_key = api_key
            self.aio = FakeAio()

    def fake_generate_content_config(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(**kwargs)

    google_module = ModuleType("google")
    genai_module = ModuleType("google.genai")
    errors_module = ModuleType("google.genai.errors")
    types_module = ModuleType("google.genai.types")

    genai_module.Client = FakeClient
    errors_module.APIError = FakeAPIError
    types_module.GenerateContentConfig = fake_generate_content_config
    genai_module.errors = errors_module
    genai_module.types = types_module
    google_module.genai = genai_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.errors", errors_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", types_module)

    provider = GeminiLLMProvider(api_key="test-key", model="test-model")
    result = await provider.generate(
        system="sys",
        user="usr",
        timeout_ms=1000,
        schema=_Output,
    )

    assert result == '{"message":"from gemini"}'
    assert len(calls) == 1
    assert calls[0]["model"] == "test-model"
    assert calls[0]["contents"] == "usr"
    config = calls[0]["config"]
    assert config.system_instruction == "sys"
    assert config.response_mime_type == "application/json"
    assert config.response_schema["properties"]["message"]["type"] == "string"
    assert "additionalProperties" not in str(config.response_schema)
    assert closed["value"] is True


async def test_gemini_generate_sanitizes_pydantic_schema_for_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    class FakeAPIError(Exception):
        pass

    class FakeModels:
        async def generate_content(self, **kwargs: object) -> SimpleNamespace:
            calls.append(kwargs)
            return SimpleNamespace(text='{"count":1}')

    class FakeAio:
        def __init__(self) -> None:
            self.models = FakeModels()

        async def aclose(self) -> None:
            return None

    class FakeClient:
        def __init__(self, *, api_key: str) -> None:
            self.api_key = api_key
            self.aio = FakeAio()

    def fake_generate_content_config(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(**kwargs)

    google_module = ModuleType("google")
    genai_module = ModuleType("google.genai")
    errors_module = ModuleType("google.genai.errors")
    types_module = ModuleType("google.genai.types")

    genai_module.Client = FakeClient
    errors_module.APIError = FakeAPIError
    types_module.GenerateContentConfig = fake_generate_content_config
    genai_module.errors = errors_module
    genai_module.types = types_module
    google_module.genai = genai_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.errors", errors_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", types_module)

    provider = GeminiLLMProvider(api_key="test-key", model="test-model")
    await provider.generate(
        system="sys",
        user="usr",
        timeout_ms=1000,
        schema=_PositiveOutput,
    )

    response_schema = calls[0]["config"].response_schema
    assert "exclusiveMinimum" not in str(response_schema)
    assert "additionalProperties" not in str(response_schema)
    assert response_schema["properties"]["count"]["minimum"] == 0


async def test_gemini_generate_preserves_api_error_when_close_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAPIError(Exception):
        def __init__(self, message: str, *, code: int) -> None:
            super().__init__(message)
            self.code = code

    class FakeModels:
        async def generate_content(self, **_: object) -> SimpleNamespace:
            raise FakeAPIError("provider unavailable", code=500)

    class FakeAio:
        def __init__(self) -> None:
            self.models = FakeModels()

        async def aclose(self) -> None:
            raise RuntimeError("close failed")

    class FakeClient:
        def __init__(self, *, api_key: str) -> None:
            self.api_key = api_key
            self.aio = FakeAio()

    def fake_generate_content_config(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(**kwargs)

    google_module = ModuleType("google")
    genai_module = ModuleType("google.genai")
    errors_module = ModuleType("google.genai.errors")
    types_module = ModuleType("google.genai.types")

    genai_module.Client = FakeClient
    errors_module.APIError = FakeAPIError
    types_module.GenerateContentConfig = fake_generate_content_config
    genai_module.errors = errors_module
    genai_module.types = types_module
    google_module.genai = genai_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.errors", errors_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", types_module)

    provider = GeminiLLMProvider(api_key="test-key", model="test-model")
    with pytest.raises(LLMNetworkError) as exc_info:
        await provider.generate(system="sys", user="usr", timeout_ms=1000)

    assert exc_info.value.status == 500
    assert str(exc_info.value) == "provider unavailable"
