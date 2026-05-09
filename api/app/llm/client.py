"""LLM client facade -- async port of web/src/server/llm/client.ts.

Public entry point: `generate_structured(...)`. All node code in Plan 5
must call this and never bypass to GeminiLLMProvider directly.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import time
from typing import Mapping, Protocol, TypeVar, cast

from pydantic import BaseModel, ValidationError

from app.llm.cost_logger import (
    LLMCostLogEntry,
    LLMCostLogger,
    create_cost_log_entry,
    log_cost,
)
from app.llm.json_repair import JsonRepairError, parse_json_with_repair
from app.llm.retry import (
    RetryExhaustedError,
    RetryOptions,
    is_transient_network_error,
    with_retry,
)

DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

M = TypeVar("M", bound=BaseModel)


# ---------- Errors ----------

class LLMConfigurationError(Exception):
    """API key missing or model misconfigured."""


class LLMAuthError(Exception):
    """401/403 from provider -- not retryable."""


class LLMNetworkError(Exception):
    """Transient network or provider error -- retryable."""

    transient = True
    retryable = True

    def __init__(self, message: str, *, status: int | None = None, cause: object | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.cause = cause


class LLMProviderError(Exception):
    """Non-retryable HTTP error returned by the provider."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class LLMTimeoutError(Exception):
    def __init__(self, timeout_ms: int) -> None:
        super().__init__(f"LLM call timed out after {timeout_ms}ms")
        self.timeout_ms = timeout_ms


class LLMJsonParseError(Exception):
    def __init__(self, message: str, *, cause: object) -> None:
        super().__init__(message)
        self.cause = cause


# ---------- Provider Protocol ----------

class LLMProvider(Protocol):
    async def generate(
        self,
        *,
        system: str,
        user: str,
        timeout_ms: int,
        schema: type[BaseModel] | None = None,
    ) -> str: ...


# ---------- Public facade ----------

async def generate_structured(
    *,
    system: str,
    user: str,
    schema: type[M],
    label: str,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    provider: LLMProvider | None = None,
    cost_logger: LLMCostLogger | None = None,
    retry: RetryOptions | None = None,
) -> M:
    chosen_provider = provider or create_default_provider()
    effective_system = _system_with_schema(system, schema)
    started = time.perf_counter()
    completion = ""
    retry_count = 0
    success = False
    failure: str | None = None

    try:
        async def _call() -> M:
            nonlocal completion

            completion = await _with_timeout(
                chosen_provider.generate(
                    system=effective_system,
                    user=user,
                    timeout_ms=timeout_ms,
                    schema=schema,
                ),
                timeout_ms=timeout_ms,
            )
            parsed = _parse_llm_json(completion)
            try:
                return schema.model_validate(parsed)
            except ValidationError as ve:
                raise LLMJsonParseError("LLM JSON failed schema validation", cause=ve) from ve

        result = await with_retry(_call, _structured_retry_options(retry))
        retry_count = result.retry_count
        success = True
        return result.value
    except RetryExhaustedError as exhausted:
        retry_count = exhausted.retry_count
        failure = str(exhausted.cause)
        raise exhausted.cause  # noqa: B904 -- surface original cause to caller
    except Exception as e:
        failure = str(e)
        raise
    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)
        entry = create_cost_log_entry(
            label=label,
            system=effective_system,
            user=user,
            completion=completion,
            duration_ms=duration_ms,
            success=success,
            failure=failure,
            retry_count=retry_count,
        )
        await _safe_log(cost_logger or log_cost, entry)


# ---------- Default provider ----------

def create_default_provider(env: Mapping[str, str] | None = None) -> LLMProvider:
    env = env if env is not None else os.environ
    api_key = read_api_key(env)
    model = env.get("LLM_PROVIDER_MODEL") or env.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    return GeminiLLMProvider(api_key=api_key, model=model)


def read_api_key(env: Mapping[str, str] | None = None) -> str:
    env = env if env is not None else os.environ
    api_key = env.get("LLM_PROVIDER_API_KEY") or env.get("GEMINI_API_KEY")
    if not api_key:
        raise LLMConfigurationError("LLM_PROVIDER_API_KEY is not configured")
    return api_key


# ---------- GeminiLLMProvider ----------

class GeminiLLMProvider:
    def __init__(self, *, api_key: str, model: str = DEFAULT_GEMINI_MODEL) -> None:
        self._api_key = api_key
        self._model = model

    async def generate(
        self,
        *,
        system: str,
        user: str,
        timeout_ms: int,
        schema: type[BaseModel] | None = None,
    ) -> str:
        # Lazy import keeps unit tests free of SDK imports unless explicitly used.
        from google import genai
        from google.genai import errors as genai_errors
        from google.genai import types as genai_types

        client = genai.Client(api_key=self._api_key)
        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=_provider_response_schema(schema) if schema else None,
        )
        try:
            response = await client.aio.models.generate_content(
                model=self._model,
                contents=user,
                config=config,
            )
        except genai_errors.APIError as api_err:
            status = getattr(api_err, "code", None)
            if status in (401, 403):
                raise LLMAuthError(str(api_err)) from api_err
            if status in (408, 429) or (isinstance(status, int) and status >= 500):
                raise LLMNetworkError(str(api_err), status=status, cause=api_err) from api_err
            raise LLMProviderError(str(api_err), status=status) from api_err
        except (asyncio.CancelledError, LLMTimeoutError):
            raise
        except Exception as e:
            raise LLMNetworkError("LLM provider network failure", cause=e) from e
        finally:
            with contextlib.suppress(Exception):
                await client.aio.aclose()

        text = (response.text or "").strip()
        if not text:
            raise LLMProviderError("LLM provider returned no text")
        return text


# ---------- helpers ----------

async def _with_timeout(awaitable, *, timeout_ms: int):
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_ms / 1000)
    except asyncio.TimeoutError as e:
        raise LLMTimeoutError(timeout_ms) from e


def _parse_llm_json(raw: str) -> object:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as initial:
        try:
            return parse_json_with_repair(raw)
        except (JsonRepairError, json.JSONDecodeError) as repair:
            raise LLMJsonParseError(
                "LLM returned invalid JSON",
                cause={"initial": str(initial), "repair": str(repair)},
            ) from repair


def _system_with_schema(system: str, schema: type[BaseModel]) -> str:
    schema_json = json.dumps(
        schema.model_json_schema(),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        f"{system.strip()}\n\n"
        "Return only one JSON value that validates against this JSON Schema. "
        "Do not include markdown, prose, comments, or keys not allowed by the schema.\n"
        f"{schema_json}"
    )


def _provider_response_schema(schema: type[BaseModel]) -> dict[str, object]:
    return cast(dict[str, object], _sanitize_provider_schema(schema.model_json_schema()))


def _sanitize_provider_schema(value: object) -> object:
    if isinstance(value, dict):
        sanitized: dict[str, object] = {}
        for key, item in value.items():
            if key == "exclusiveMinimum":
                sanitized.setdefault("minimum", _sanitize_provider_schema(item))
                continue
            if key == "exclusiveMaximum":
                sanitized.setdefault("maximum", _sanitize_provider_schema(item))
                continue
            if key in {"$schema", "additionalProperties", "additional_properties", "examples"}:
                continue
            sanitized[key] = _sanitize_provider_schema(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_provider_schema(item) for item in value]
    return value


def _structured_retry_options(retry: RetryOptions | None) -> RetryOptions:
    if retry is None:
        return RetryOptions(should_retry=_should_retry_structured_generation)
    if retry.should_retry is not None:
        return retry
    return RetryOptions(
        max_retries=retry.max_retries,
        base_delay_ms=retry.base_delay_ms,
        max_delay_ms=retry.max_delay_ms,
        should_retry=_should_retry_structured_generation,
    )


def _should_retry_structured_generation(error: Exception) -> bool:
    if isinstance(error, LLMJsonParseError):
        return True
    return is_transient_network_error(error)


async def _safe_log(logger: LLMCostLogger, entry: LLMCostLogEntry) -> None:
    try:
        await logger(entry)
    except Exception:  # noqa: BLE001
        return
