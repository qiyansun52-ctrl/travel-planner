from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.graph.state import AdjustmentGraphResult, PlanningGraphResult, ProgressEvent
from app.metrics import MetricEventPayload, safe_append_metric_event
from app.models.schemas import (
    AdjustmentRequest,
    PlanningSession,
    Preference,
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


async def require_session(
    session_id: str,
    repo: SessionRepository | None = None,
) -> PlanningSession:
    loaded = await (repo or repository()).get(session_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return loaded


def route_error(error: Exception) -> HTTPException:
    if isinstance(error, SessionNotFoundError):
        return HTTPException(status_code=404, detail="Session not found")
    if isinstance(error, ArchivedSessionMutationError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, SessionStoreError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, SessionRepositoryError):
        return HTTPException(status_code=500, detail=str(error))
    return HTTPException(status_code=502, detail=str(error))


def fixture_mode_enabled() -> bool:
    return os.environ.get("E2E_FIXTURE_MODE") == "1"


async def safe_metric(event: MetricEventPayload) -> None:
    await safe_append_metric_event(event)


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
        "message": f"{event.node} {event.status}",
        "payload": event.payload,
    }


async def iter_progress_frames(
    progress_events: list[ProgressEvent],
) -> AsyncIterator[str]:
    for event in progress_events:
        yield sse_frame("progress", progress_payload(event))
