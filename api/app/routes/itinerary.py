from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.graph.state import (
    PlanningGraphResult,
    PlanState,
    graph_input_from_state,
    validate_graph_state,
)
from app.graph.workflow import (
    create_planning_graph,
    run_full_planning_workflow,
    run_planner_only_workflow,
)
from app.models.schemas import PlanningSession, ValidatorIssue
from app.routes._shared import (
    ItineraryRequest,
    StayOverrideUpdate,
    persist_planning_result,
    progress_payload,
    repository,
    require_session,
    route_error,
    safe_metric,
    sse_frame,
)

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["itinerary"])


def _assert_itinerary_ready(session: PlanningSession) -> None:
    if session.discovery_state is None or session.preferences is None:
        raise HTTPException(
            status_code=409,
            detail="Discovery and preferences are required before itinerary generation",
        )


async def _run_planning(
    session: PlanningSession,
    reason: str | None,
) -> PlanningGraphResult:
    if reason and session.stay_recommendation and session.transport_recommendation:
        return await run_planner_only_workflow(session, reason=reason)
    return await run_full_planning_workflow(session)


@router.post("/itinerary", response_model=PlanningSession)
async def run_itinerary(session_id: str, body: ItineraryRequest) -> PlanningSession:
    repo = repository()
    session = await require_session(session_id, repo)
    _assert_itinerary_ready(session)
    try:
        result = await _run_planning(session, body.planner_only_reason)
        updated = await persist_planning_result(repo, session_id, result)
    except Exception as exc:
        raise route_error(exc) from exc

    await _log_itinerary_metrics(
        session_id,
        result.itinerary.version,
        result.validator_issues,
    )
    return updated


@router.patch("/stay-override", response_model=PlanningSession)
async def update_stay_override(
    session_id: str,
    body: StayOverrideUpdate,
) -> PlanningSession:
    repo = repository()
    try:
        with_override = await repo.update_stay_override(session_id, body.stay_option_id)
        result = await run_planner_only_workflow(with_override, reason="stay_override")
        updated = await persist_planning_result(repo, session_id, result)
    except Exception as exc:
        raise route_error(exc) from exc

    await safe_metric(
        {
            "name": "stay_override_set",
            "session_id": session_id,
            "payload": {"override_set": body.stay_option_id is not None},
        }
    )
    return updated


@router.get("/itinerary/stream")
async def stream_itinerary(session_id: str) -> StreamingResponse:
    return StreamingResponse(
        _stream_itinerary_events(session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


async def _stream_itinerary_events(session_id: str) -> AsyncIterator[str]:
    repo = repository()
    try:
        session = await require_session(session_id, repo)
        _assert_itinerary_ready(session)
        yield sse_frame(
            "progress",
            {
                "stage": "workflow",
                "status": "start",
                "message": "itinerary started",
            },
        )

        result: PlanningGraphResult | None = None
        async for item in _stream_planning_values(session):
            if isinstance(item, str):
                yield item
            else:
                result = item

        if result is None:
            raise RuntimeError("Planning stream ended without a result")

        updated = await persist_planning_result(repo, session_id, result)
        await _log_itinerary_metrics(
            session_id,
            result.itinerary.version,
            result.validator_issues,
        )
        yield sse_frame("complete", {"session": updated.model_dump(mode="json")})
    except Exception as exc:
        yield sse_frame(
            "error",
            {"stage": "workflow", "status": "error", "message": str(exc)},
        )


async def _stream_planning_values(
    session: PlanningSession,
) -> AsyncIterator[str | PlanningGraphResult]:
    graph = create_planning_graph()
    seen_progress = 0
    last_state = None
    async for value in graph.astream(
        graph_input_from_state(PlanState(session=session, mode="full_planning")),
        stream_mode="values",
    ):
        parsed = validate_graph_state(value)
        for event in parsed.progress_events[seen_progress:]:
            seen_progress += 1
            yield sse_frame("progress", progress_payload(event))
        last_state = value

    if last_state is None:
        raise RuntimeError("Planning graph produced no state")

    parsed = validate_graph_state(last_state)
    if parsed.stay_recommendation is None:
        raise RuntimeError("Planning graph finished without stay recommendation")
    if parsed.transport_recommendation is None:
        raise RuntimeError("Planning graph finished without transport recommendation")
    if parsed.itinerary is None:
        raise RuntimeError("Planning graph finished without itinerary")

    yield PlanningGraphResult(
        session_id=session.session_id,
        stay=parsed.stay_recommendation,
        transport=parsed.transport_recommendation,
        itinerary=parsed.itinerary.model_copy(
            update={"validator_issues": parsed.validator_issues}
        ),
        validator_issues=parsed.validator_issues,
        progress_events=parsed.progress_events,
    )


async def _log_itinerary_metrics(
    session_id: str,
    version: int,
    validator_issues: list[ValidatorIssue],
) -> None:
    await safe_metric(
        {
            "name": "itinerary_finalized",
            "session_id": session_id,
            "payload": {"version": version},
        }
    )
    residual_errors = [
        issue for issue in validator_issues if issue.severity == "error"
    ]
    if residual_errors:
        await safe_metric(
            {
                "name": "validator_error_finalized",
                "session_id": session_id,
                "payload": {"codes": [issue.code for issue in residual_errors]},
            }
        )
