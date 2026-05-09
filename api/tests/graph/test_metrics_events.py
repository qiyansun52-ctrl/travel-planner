from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import app.metrics.events as metrics_events
from app.metrics import (
    append_metric_event,
    compute_metric_summary,
    default_metric_file_path,
    safe_append_metric_event,
)


async def test_writes_jsonl_events_and_computes_funnel_totals(tmp_path: Path) -> None:
    file_path = tmp_path / "events.jsonl"

    await append_metric_event(
        {
            "name": "step1_submitted",
            "session_id": "session-1",
            "payload": {"destination": "Tokyo"},
        },
        file_path=file_path,
    )
    await append_metric_event(
        {
            "name": "itinerary_finalized",
            "session_id": "session-1",
            "payload": {"days": 3},
        },
        file_path=file_path,
    )
    await append_metric_event(
        {
            "name": "step1_submitted",
            "session_id": "session-2",
            "payload": {},
        },
        file_path=file_path,
    )

    lines = file_path.read_text(encoding="utf-8").splitlines()
    summary = await compute_metric_summary(file_path=file_path)

    assert len(lines) == 3
    assert all(json.loads(line)["created_at"].endswith("Z") for line in lines)
    assert summary.event_counts["step1_submitted"] == 2
    assert summary.event_counts["itinerary_finalized"] == 1
    assert summary.sessions_submitted == 2
    assert summary.sessions_with_final_itinerary == 1


async def test_missing_file_summary_returns_zeros(tmp_path: Path) -> None:
    summary = await compute_metric_summary(file_path=tmp_path / "missing.jsonl")

    assert summary.event_counts == {}
    assert summary.sessions_submitted == 0
    assert summary.sessions_with_final_itinerary == 0
    assert summary.sessions_with_residual_validator_errors == 0


async def test_empty_file_and_blank_lines_summary_returns_zeros(tmp_path: Path) -> None:
    file_path = tmp_path / "events.jsonl"
    file_path.write_text("\n  \n", encoding="utf-8")

    summary = await compute_metric_summary(file_path=file_path)

    assert summary.event_counts == {}
    assert summary.sessions_submitted == 0
    assert summary.sessions_with_final_itinerary == 0
    assert summary.sessions_with_residual_validator_errors == 0


async def test_invalid_historical_rows_are_skipped_while_valid_rows_count(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "events.jsonl"
    valid_event = {
        "name": "validator_error_finalized",
        "session_id": "session-1",
        "payload": {},
        "created_at": "2026-05-09T00:00:00Z",
    }
    file_path.write_text(
        "\n".join(
            [
                "{not-json",
                json.dumps({"name": "step1_submitted", "payload": {}}),
                json.dumps(
                    {
                        "name": "unknown_event",
                        "session_id": "session-2",
                        "payload": {},
                    }
                ),
                json.dumps(valid_event),
            ]
        ),
        encoding="utf-8",
    )

    summary = await compute_metric_summary(file_path=file_path)

    assert summary.event_counts == {"validator_error_finalized": 1}
    assert summary.sessions_submitted == 0
    assert summary.sessions_with_final_itinerary == 0
    assert summary.sessions_with_residual_validator_errors == 1


async def test_append_metric_event_rejects_invalid_runtime_payload(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError):
        await append_metric_event(
            {
                "name": "unknown_event",
                "session_id": "session-1",
                "payload": {},
            },
            file_path=tmp_path / "events.jsonl",
        )


async def test_safe_append_metric_event_swallows_append_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_runtime_error(target: Path, line: str) -> None:
        raise RuntimeError("disk unavailable")

    monkeypatch.setattr(metrics_events, "_append_line", raise_runtime_error)

    await safe_append_metric_event(
        {
            "name": "step1_submitted",
            "session_id": "session-1",
            "payload": {},
        },
        file_path=Path("events.jsonl"),
    )


async def test_metric_event_helpers_accept_string_paths(tmp_path: Path) -> None:
    file_path = str(tmp_path / "events.jsonl")

    await append_metric_event(
        {
            "name": "step1_submitted",
            "session_id": "session-1",
            "payload": {},
        },
        file_path=file_path,
    )

    summary = await compute_metric_summary(file_path=file_path)

    assert summary.event_counts["step1_submitted"] == 1
    assert summary.sessions_submitted == 1


def test_default_metric_file_path_points_to_api_data_dir_without_env() -> None:
    path = default_metric_file_path({})

    assert path.name == "events.jsonl"
    assert path.parent.name == ".data"
    assert path.parent.parent.name == "api"


def test_default_metric_file_path_uses_env_override(tmp_path: Path) -> None:
    path = default_metric_file_path({"METRICS_DATA_DIR": str(tmp_path)})

    assert path == tmp_path / "events.jsonl"
