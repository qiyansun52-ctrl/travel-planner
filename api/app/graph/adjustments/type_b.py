"""Type B dependent recommendation adjustment routing."""

from __future__ import annotations

import re

from app.graph.nodes.stay import run_stay_agent
from app.graph.nodes.transport import run_transport_agent
from app.graph.state import AdjustmentGraphResult
from app.graph.workflow import run_planner_only_workflow
from app.models.schemas import AdjustmentRequest, PlanningSession, StayOption, StayRecommendation

QUIET_STAY_PATTERN = re.compile(r"安静|更静|清静|quiet|quieter|calm|calmer", re.IGNORECASE)


async def run_type_b_adjustment(
    session: PlanningSession,
    classification: AdjustmentRequest,
    *,
    fixture_mode: bool = False,
) -> AdjustmentGraphResult:
    working = session

    if classification.target_scope == "stay":
        stay = await run_stay_agent(working.model_copy(update={"stay_recommendation": None}))
        user_override_id = _select_stay_override(stay, classification)
        working = working.model_copy(
            update={
                "stay_recommendation": stay.model_copy(
                    update={"user_override_id": user_override_id}
                )
            }
        )
    elif classification.target_scope == "transport":
        transport = await run_transport_agent(working)
        working = working.model_copy(update={"transport_recommendation": transport})

    result = await run_planner_only_workflow(
        working,
        reason=f"type_b_{classification.target_scope}_adjustment",
        fixture_mode=fixture_mode,
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


def _select_stay_override(
    stay: StayRecommendation,
    classification: AdjustmentRequest,
) -> str | None:
    requested = " ".join(
        item
        for item in [classification.raw_text, classification.proposed_change]
        if item
    )
    if not QUIET_STAY_PATTERN.search(requested):
        return None

    quiet_option = next(
        (option for option in stay.alternatives if _matches_quiet_option(option)),
        None,
    )
    return quiet_option.id if quiet_option else None


def _matches_quiet_option(option: StayOption) -> bool:
    searchable = " ".join(
        [
            option.id,
            option.area.id,
            option.area.name,
            option.area.note,
            option.fit_reason,
            *option.area.vibe_tags,
        ]
    )
    return bool(QUIET_STAY_PATTERN.search(searchable))
