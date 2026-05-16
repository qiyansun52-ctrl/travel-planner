from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Mapping, NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, Field, ValidationError

MetricFilePath = str | Path | None
MetricEventName = Literal[
    "step1_submitted",
    "discovery_arrived",
    "discovery_enrichment_summary",
    "attraction_selected",
    "preferences_completed",
    "itinerary_finalized",
    "validator_error_finalized",
    "adjustment_classified",
    "type_c_action_taken",
    "provider_fallback_used",
    "stay_override_set",
    "operation_budget_consumed",
]


class MetricEventPayload(TypedDict):
    name: MetricEventName
    session_id: str
    payload: dict[str, object]
    created_at: NotRequired[str]


class MetricEventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: MetricEventName
    session_id: str
    payload: dict[str, object] = Field(default_factory=dict)
    created_at: str | None = None


class MetricSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_counts: dict[MetricEventName, int] = Field(default_factory=dict)
    sessions_submitted: int = 0
    sessions_with_final_itinerary: int = 0
    sessions_with_residual_validator_errors: int = 0


def default_metric_file_path(env: Mapping[str, str] | None = None) -> Path:
    source = env if env is not None else os.environ
    data_dir = source.get("METRICS_DATA_DIR")
    if data_dir:
        return Path(data_dir) / "events.jsonl"
    return Path(__file__).resolve().parents[2] / ".data" / "events.jsonl"


async def append_metric_event(
    event: MetricEventPayload,
    file_path: MetricFilePath = None,
) -> None:
    record = MetricEventRecord.model_validate(dict(event))
    target = _metric_file_path(file_path)
    line = json.dumps(_event_with_timestamp(record), ensure_ascii=False) + "\n"
    await asyncio.to_thread(_append_line, target, line)


async def safe_append_metric_event(
    event: MetricEventPayload,
    file_path: MetricFilePath = None,
) -> None:
    try:
        await append_metric_event(event, file_path=file_path)
    except Exception:  # noqa: BLE001 -- metrics must never block the planning flow.
        return


async def compute_metric_summary(file_path: MetricFilePath = None) -> MetricSummary:
    event_counts: dict[MetricEventName, int] = {}
    submitted: set[str] = set()
    finalized: set[str] = set()
    residual_errors: set[str] = set()

    events = await asyncio.to_thread(_read_metric_events, _metric_file_path(file_path))
    for event in events:
        name = event.name
        session_id = event.session_id

        event_counts[name] = event_counts.get(name, 0) + 1
        if name == "step1_submitted":
            submitted.add(session_id)
        if name == "itinerary_finalized":
            finalized.add(session_id)
        if name == "validator_error_finalized":
            residual_errors.add(session_id)

    return MetricSummary(
        event_counts=event_counts,
        sessions_submitted=len(submitted),
        sessions_with_final_itinerary=len(finalized),
        sessions_with_residual_validator_errors=len(residual_errors),
    )


def _event_with_timestamp(event: MetricEventRecord) -> dict[str, object]:
    record = event.model_copy(update={"created_at": event.created_at or _utc_timestamp()})
    return record.model_dump()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _metric_file_path(file_path: MetricFilePath) -> Path:
    if file_path is None:
        return default_metric_file_path()
    return Path(file_path)


def _append_line(target: Path, line: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(line)


def _read_metric_events(file_path: Path) -> list[MetricEventRecord]:
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []

    events: list[MetricEventRecord] = []
    for line in (raw_line.strip() for raw_line in lines):
        if not line:
            continue
        try:
            events.append(MetricEventRecord.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValidationError):
            continue

    return events
