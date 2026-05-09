"""LLM client facade -- async port of web/src/server/llm/client.ts.

Public entry point: `generate_structured(...)`. All node code in Plan 5
must call this and never bypass to GeminiLLMProvider directly.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Mapping, Protocol, TypeVar

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
    async def generate(self, *, system: str, user: str, timeout_ms: int) -> str: ...


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
    started = time.perf_counter()
    completion = ""
    retry_count = 0
    success = False
    failure: str | None = None

    try:
        async def _call() -> str:
            return await _with_timeout(
                chosen_provider.generate(system=system, user=user, timeout_ms=timeout_ms),
                timeout_ms=timeout_ms,
            )

        result = await with_retry(_call, retry)
        completion = result.value
        retry_count = result.retry_count

        parsed = _parse_llm_json(completion)
        try:
            validated = schema.model_validate(parsed)
        except ValidationError as ve:
            raise LLMJsonParseError("LLM JSON failed schema validation", cause=ve) from ve

        success = True
        return validated
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
            system=system,
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

    async def generate(self, *, system: str, user: str, timeout_ms: int) -> str:
        # Lazy import keeps unit tests free of SDK imports unless explicitly used.
        from google import genai
        from google.genai import errors as genai_errors
        from google.genai import types as genai_types

        client = genai.Client(api_key=self._api_key)
        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
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


async def _safe_log(logger: LLMCostLogger, entry: LLMCostLogEntry) -> None:
    try:
        await logger(entry)
    except Exception:  # noqa: BLE001
        return
