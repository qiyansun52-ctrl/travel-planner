from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TypedDict

from app.llm.cost_logger import default_cost_log_path
from app.metrics.events import compute_metric_summary, default_metric_file_path

OpsSummaryPath = str | Path | None


class LLMSummary(TypedDict):
    call_count: int
    failure_count: int
    total_tokens_estimate: int
    retry_count: int


class OpsSummary(TypedDict):
    metrics: dict[str, object]
    llm: LLMSummary


async def build_ops_summary(
    metric_path: OpsSummaryPath = None,
    cost_path: OpsSummaryPath = None,
) -> OpsSummary:
    metric_target = _resolve_metric_path(metric_path)
    cost_target = _resolve_cost_path(cost_path)
    metric_summary = await compute_metric_summary(file_path=metric_target)
    llm_summary = await asyncio.to_thread(_compute_llm_summary, cost_target)

    return {
        "metrics": metric_summary.model_dump(),
        "llm": llm_summary,
    }


def _compute_llm_summary(file_path: Path) -> LLMSummary:
    summary: LLMSummary = {
        "call_count": 0,
        "failure_count": 0,
        "total_tokens_estimate": 0,
        "retry_count": 0,
    }

    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return summary

    for line in (raw_line.strip() for raw_line in lines):
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue

        prompt_tokens = _non_negative_int(record.get("prompt_tokens_estimate"))
        completion_tokens = _non_negative_int(record.get("completion_tokens_estimate"))
        retry_count = _non_negative_int(record.get("retry_count"))
        success = record.get("success")
        if (
            prompt_tokens is None
            or completion_tokens is None
            or retry_count is None
            or not isinstance(success, bool)
        ):
            continue

        summary["call_count"] += 1
        if not success:
            summary["failure_count"] += 1
        summary["total_tokens_estimate"] += prompt_tokens + completion_tokens
        summary["retry_count"] += retry_count

    return summary


def _non_negative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _resolve_metric_path(file_path: OpsSummaryPath) -> Path:
    if file_path is None:
        return default_metric_file_path()
    return Path(file_path)


def _resolve_cost_path(file_path: OpsSummaryPath) -> Path:
    if file_path is None:
        return default_cost_log_path()
    return Path(file_path)
