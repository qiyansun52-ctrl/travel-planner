from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.graph.state import AdjustmentGraphResult, PlanningGraphResult, ProgressEvent
from app.metrics import MetricEventPayload, safe_append_metric_event
from app.models.schemas import (
    AdjustmentRequest,
    PlanningSession,
    Preference,
)
from app.ops.operation_budget import (
    OperationBudgetExceeded,
    OperationName,
    SessionOperationBudget,
)
from app.persistence import (
    ArchivedSessionMutationError,
    SessionNotFoundError,
    SessionRepository,
    SessionRepositoryError,
    SessionStoreError,
)
from app.persistence.file_session_repository import get_default_session_repository


class _RouteModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SelectionUpdate(_RouteModel):
    selected_card_ids: list[str]


class PreferenceUpdate(_RouteModel):
    preferences: Preference


class ItineraryRequest(_RouteModel):
    planner_only_reason: str | None = None


class StayOverrideUpdate(_RouteModel):
    stay_option_id: str | None = None


class AdjustmentInput(_RouteModel):
    message: str = Field(min_length=1)
    type_c_action: Literal["replan", "save_and_start_new", "cancel"] | None = None


class AdjustmentResponse(_RouteModel):
    session: PlanningSession
    classification: AdjustmentRequest
    message: str
    confirmation: object | None = None


def repository() -> SessionRepository:
    return get_default_session_repository()


def _budget_limits() -> dict[OperationName, int]:
    settings = get_settings()
    return {
        "discovery": settings.max_discovery_runs_per_session,
        "itinerary": settings.max_itinerary_runs_per_session,
        "adjustment": settings.max_adjustments_per_session,
    }


_OPERATION_BUDGET: SessionOperationBudget | None = None


def _operation_budget() -> SessionOperationBudget:
    global _OPERATION_BUDGET
    if _OPERATION_BUDGET is None:
        _OPERATION_BUDGET = SessionOperationBudget(default_limits=_budget_limits())
    return _OPERATION_BUDGET


async def require_session(
    session_id: str,
    repo: SessionRepository | None = None,
) -> PlanningSession:
    loaded = await (repo or repository()).get(session_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return loaded


def route_error(error: Exception) -> HTTPException:
    if isinstance(error, OperationBudgetExceeded):
        return HTTPException(status_code=429, detail=str(error))
    if isinstance(error, SessionNotFoundError):
        return HTTPException(status_code=404, detail="Session not found")
    if isinstance(error, ArchivedSessionMutationError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, SessionStoreError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, SessionRepositoryError):
        return HTTPException(status_code=500, detail=str(error))
    return HTTPException(status_code=502, detail=str(error))


async def safe_metric(event: MetricEventPayload) -> None:
    await safe_append_metric_event(event)


async def guard_expensive_operation(
    session_id: str,
    operation: OperationName,
) -> None:
    _operation_budget().consume(session_id, operation)
    await safe_metric(
        {
            "name": "operation_budget_consumed",
            "session_id": session_id,
            "payload": {"operation": operation},
        }
    )


async def persist_planning_result(
    repo: SessionRepository,
    session_id: str,
    result: PlanningGraphResult,
) -> PlanningSession:
    await repo.update_stay_recommendation(session_id, result.stay)
    await repo.update_transport_recommendation(session_id, result.transport)
    return await repo.write_itinerary(
        session_id,
        result.itinerary,
        result.validator_issues,
    )


async def persist_adjustment_result(
    repo: SessionRepository,
    session: PlanningSession,
    result: AdjustmentGraphResult,
) -> PlanningSession:
    if result.reset_to_step == "discovery":
        return await repo.reset_to_step(
            session.session_id,
            "discovery",
            session.hard_constraints,
        )
    if result.fork_requested:
        return await repo.archive_and_fork(
            session.session_id,
            "Before root constraint change",
            session.hard_constraints,
        )
    if result.stay is not None:
        await repo.update_stay_recommendation(session.session_id, result.stay)
    if result.transport is not None:
        await repo.update_transport_recommendation(session.session_id, result.transport)
    if result.itinerary is not None:
        return await repo.write_itinerary(
            session.session_id,
            result.itinerary,
            result.validator_issues,
        )
    return (await repo.get(session.session_id)) or session


def conversation_turn_id() -> str:
    return f"turn_{uuid4()}"


def sse_frame(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def progress_payload(event: ProgressEvent) -> dict[str, object]:
    status = "finish" if event.status == "completed" else event.status
    return {
        "stage": event.node,
        "status": status,
        "message": _progress_message(event),
        "payload": event.payload,
    }


def _progress_message(event: ProgressEvent) -> str:
    if event.status != "completed":
        return f"{event.node} {event.status}"

    quality = event.payload.get("quality", {})
    if not isinstance(quality, dict):
        quality = {}

    if event.node == "discovery":
        card_count = _quality_int(quality, "card_count")
        source_note_count = _quality_int(quality, "source_note_count")
        if card_count is not None and source_note_count is not None:
            return (
                f"已生成 {card_count} 张发现卡片，保留 {source_note_count} 条来源线索"
            )
        return "已完成发现卡片整理"

    if event.node == "stay":
        return "已选出住宿区域和备选方案"

    if event.node == "transport":
        return "已分析抵达、返程和市内交通方案"

    if event.node == "planner":
        day_count = _quality_int(quality, "day_count")
        segment_count = _quality_int(quality, "segment_count")
        if day_count is not None and segment_count is not None:
            return f"已生成 {day_count} 天行程，包含 {segment_count} 个安排"
        return "已生成每日行程"

    if event.node == "validator":
        issue_count = _quality_int(quality, "issue_count")
        error_count = _quality_int(quality, "error_count")
        if issue_count == 0:
            return "检查完成，预算和节奏没有发现阻断问题"
        if issue_count is not None and error_count is not None:
            return f"检查完成，发现 {issue_count} 个问题，其中 {error_count} 个需要修正"
        return "已完成预算与节奏检查"

    return f"{event.node} {event.status}"


def _quality_int(quality: dict[object, object], key: str) -> int | None:
    value = quality.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


async def iter_progress_frames(
    progress_events: list[ProgressEvent],
) -> AsyncIterator[str]:
    for event in progress_events:
        yield sse_frame("progress", progress_payload(event))
