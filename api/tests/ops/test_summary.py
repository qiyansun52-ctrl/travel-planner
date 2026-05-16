from __future__ import annotations

import json
from pathlib import Path

from app.ops.summary import build_ops_summary


async def test_build_ops_summary_counts_metrics_and_llm_costs(tmp_path: Path) -> None:
    metric_path = tmp_path / "events.jsonl"
    cost_path = tmp_path / "llm-cost.jsonl"

    metric_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "name": "step1_submitted",
                        "session_id": "session-1",
                        "payload": {},
                    }
                ),
                json.dumps(
                    {
                        "name": "itinerary_finalized",
                        "session_id": "session-1",
                        "payload": {},
                    }
                ),
                json.dumps(
                    {
                        "name": "step1_submitted",
                        "session_id": "session-2",
                        "payload": {},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    cost_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": "2026-05-10T00:00:00Z",
                        "label": "discover",
                        "prompt_tokens_estimate": 10,
                        "completion_tokens_estimate": 4,
                        "duration_ms": 25,
                        "success": True,
                        "failure": None,
                        "retry_count": 0,
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-05-10T00:00:01Z",
                        "label": "plan",
                        "prompt_tokens_estimate": 7,
                        "completion_tokens_estimate": 3,
                        "duration_ms": 80,
                        "success": False,
                        "failure": "redacted in summary",
                        "retry_count": 2,
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    summary = await build_ops_summary(metric_path=metric_path, cost_path=cost_path)

    assert summary["metrics"] == {
        "event_counts": {
            "itinerary_finalized": 1,
            "step1_submitted": 2,
        },
        "sessions_submitted": 2,
        "sessions_with_final_itinerary": 1,
        "sessions_with_residual_validator_errors": 0,
    }
    assert summary["llm"] == {
        "call_count": 2,
        "failure_count": 1,
        "total_tokens_estimate": 24,
        "retry_count": 2,
    }


async def test_build_ops_summary_returns_zeros_for_missing_files_and_invalid_cost_rows(
    tmp_path: Path,
) -> None:
    cost_path = tmp_path / "llm-cost.jsonl"
    cost_path.write_text(
        "\n".join(
            [
                "{not-json",
                json.dumps(["not", "an", "entry"]),
                "",
            ]
        ),
        encoding="utf-8",
    )

    summary = await build_ops_summary(
        metric_path=tmp_path / "missing-events.jsonl",
        cost_path=cost_path,
    )

    assert summary["metrics"] == {
        "event_counts": {},
        "sessions_submitted": 0,
        "sessions_with_final_itinerary": 0,
        "sessions_with_residual_validator_errors": 0,
    }
    assert summary["llm"] == {
        "call_count": 0,
        "failure_count": 0,
        "total_tokens_estimate": 0,
        "retry_count": 0,
    }
