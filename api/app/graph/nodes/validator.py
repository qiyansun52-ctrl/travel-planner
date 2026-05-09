"""Validator graph node."""

from __future__ import annotations

from app.domain.validator import ValidatorContext, validate_itinerary
from app.graph.state import GraphState, PlanState, append_progress, validate_graph_state


async def run_validator_node(state: PlanState) -> GraphState:
    parsed = validate_graph_state(state)
    if parsed.itinerary is None:
        raise ValueError("run_validator_node requires itinerary")

    itinerary = parsed.itinerary
    payload = (
        parsed.session.discovery_state.payload
        if parsed.session.discovery_state and parsed.session.discovery_state.payload
        else None
    )
    issues = validate_itinerary(
        itinerary,
        ValidatorContext(discovery_cards=payload.cards if payload else []),
    )
    itinerary_with_issues = itinerary.model_copy(update={"validator_issues": issues})
    updated = append_progress(
        parsed.model_copy(
            update={
                "validator_issues": issues,
                "itinerary": itinerary_with_issues,
            }
        ),
        "validator",
        "completed",
        {
            "issue_count": len(issues),
            "error_count": sum(issue.severity == "error" for issue in issues),
        },
    )
    new_event = updated.progress_events[-1]
    return GraphState(
        validator_issues=[issue.model_dump(mode="json") for issue in issues],
        itinerary=itinerary_with_issues.model_dump(mode="json"),
        progress_events=[new_event.model_dump(mode="json")],
    )
