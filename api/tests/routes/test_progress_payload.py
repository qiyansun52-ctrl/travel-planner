from __future__ import annotations

from datetime import UTC, datetime

from app.graph.state import ProgressEvent
from app.routes._shared import progress_payload


def progress_event(
    node: str,
    payload: dict[str, object],
    *,
    status: str = "completed",
) -> ProgressEvent:
    return ProgressEvent(
        node=node,
        status=status,
        payload=payload,
        created_at=datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
    )


def test_progress_payload_describes_planner_quality() -> None:
    event = progress_event(
        "planner",
        {"quality": {"day_count": 3, "segment_count": 15}},
    )

    payload = progress_payload(event)

    assert payload["status"] == "finish"
    assert payload["message"] == "已生成 3 天行程，包含 15 个安排"


def test_progress_payload_describes_validator_quality() -> None:
    event = progress_event(
        "validator",
        {"quality": {"issue_count": 2, "error_count": 1}},
    )

    payload = progress_payload(event)

    assert payload["message"] == "检查完成，发现 2 个问题，其中 1 个需要修正"


def test_progress_payload_falls_back_for_unknown_nodes() -> None:
    event = progress_event("custom", {}, status="started")

    payload = progress_payload(event)

    assert payload["status"] == "started"
    assert payload["message"] == "custom started"
