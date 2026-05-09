from __future__ import annotations

import json
from pathlib import Path

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
    summary = compute_metric_summary(file_path=file_path)

    assert len(lines) == 3
    assert all(json.loads(line)["created_at"].endswith("Z") for line in lines)
    assert summary.event_counts["step1_submitted"] == 2
    assert summary.event_counts["itinerary_finalized"] == 1
    assert summary.sessions_submitted == 2
    assert summary.sessions_with_final_itinerary == 1


async def test_safe_append_metric_event_swallows_failure() -> None:
    await safe_append_metric_event(
        {
            "name": "step1_submitted",
            "session_id": "session-1",
            "payload": {},
        },
        file_path=Path("/dev/null/events.jsonl"),
    )


def test_default_metric_file_path_points_to_api_data_dir_without_env() -> None:
    path = default_metric_file_path({})

    assert path.name == "events.jsonl"
    assert path.parent.name == ".data"
    assert path.parent.parent.name == "api"


def test_default_metric_file_path_uses_env_override(tmp_path: Path) -> None:
    path = default_metric_file_path({"METRICS_DATA_DIR": str(tmp_path)})

    assert path == tmp_path / "events.jsonl"
