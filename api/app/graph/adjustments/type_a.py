"""Type A itinerary-only adjustment routing."""

from __future__ import annotations

from app.graph.state import AdjustmentGraphResult
from app.graph.workflow import run_planner_only_workflow
from app.models.schemas import AdjustmentRequest, PlanningSession


async def run_type_a_adjustment(
    session: PlanningSession,
    classification: AdjustmentRequest,
) -> AdjustmentGraphResult:
    result = await run_planner_only_workflow(session, reason="type_a_adjustment")
    return AdjustmentGraphResult(
        session_id=result.session_id,
        classification=classification,
        message="Itinerary updated.",
        stay=result.stay,
        transport=result.transport,
        itinerary=result.itinerary,
        validator_issues=result.validator_issues,
        progress_events=result.progress_events,
    )
