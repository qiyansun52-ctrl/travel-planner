"""Type B dependent recommendation adjustment routing."""

from __future__ import annotations

from app.graph.nodes.stay import run_stay_agent
from app.graph.nodes.transport import run_transport_agent
from app.graph.state import AdjustmentGraphResult
from app.graph.workflow import run_planner_only_workflow
from app.models.schemas import AdjustmentRequest, PlanningSession


async def run_type_b_adjustment(
    session: PlanningSession,
    classification: AdjustmentRequest,
) -> AdjustmentGraphResult:
    working = session

    if classification.target_scope == "stay":
        stay = await run_stay_agent(working.model_copy(update={"stay_recommendation": None}))
        working = working.model_copy(
            update={"stay_recommendation": stay.model_copy(update={"user_override_id": None})}
        )
    elif classification.target_scope == "transport":
        transport = await run_transport_agent(working)
        working = working.model_copy(update={"transport_recommendation": transport})

    result = await run_planner_only_workflow(
        working,
        reason=f"type_b_{classification.target_scope}_adjustment",
    )
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
