"""LLM cost logger -- async append to the local metrics directory.

Estimates tokens by character count (matches web/src/server/llm/costLogger.ts).
Failures are swallowed: cost logging must never affect the user-facing LLM call.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

DEFAULT_COST_LOG_FILENAME = "llm-cost.jsonl"
DEFAULT_DATA_DIR = Path(".data")


@dataclass(frozen=True)
class LLMCostLogEntry:
    timestamp: str
    label: str
    prompt_tokens_estimate: int
    completion_tokens_estimate: int
    duration_ms: int
    success: bool
    failure: str | None
    retry_count: int


LLMCostLogger = Callable[[LLMCostLogEntry], Awaitable[None]]


def estimate_token_count(text: str) -> int:
    trimmed = text.strip()
    if not trimmed:
        return 0
    return max(1, math.ceil(len(trimmed) / 4))


def create_cost_log_entry(
    *,
    label: str,
    system: str,
    user: str,
    completion: str,
    duration_ms: int,
    success: bool,
    failure: str | None,
    retry_count: int,
) -> LLMCostLogEntry:
    return LLMCostLogEntry(
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        label=label,
        prompt_tokens_estimate=estimate_token_count(f"{system}\n\n{user}"),
        completion_tokens_estimate=estimate_token_count(completion),
        duration_ms=duration_ms,
        success=success,
        failure=failure,
        retry_count=retry_count,
    )


def default_cost_log_path() -> Path:
    override = os.environ.get("LLM_COST_LOG_PATH")
    if override:
        return Path(override)
    metrics_dir = os.environ.get("METRICS_DATA_DIR")
    if metrics_dir:
        return Path(metrics_dir) / DEFAULT_COST_LOG_FILENAME
    return DEFAULT_DATA_DIR / DEFAULT_COST_LOG_FILENAME


async def log_cost(
    entry: LLMCostLogEntry,
    *,
    file_path: Path | None = None,
) -> None:
    target = file_path or default_cost_log_path()
    payload = json.dumps(asdict(entry), ensure_ascii=False) + "\n"
    try:
        await asyncio.to_thread(_append_sync, target, payload)
    except Exception:  # noqa: BLE001 -- cost logging must never raise
        return


def _append_sync(target: Path, payload: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(payload)
