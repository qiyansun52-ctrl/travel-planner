"""Stay recommendation graph node."""

from __future__ import annotations

from app.graph.agent_contracts import agent_progress_payload
from app.graph.nodes.discovery import band
from app.graph.state import GraphState, PlanState, append_progress, validate_graph_state
from app.models.schemas import (
    AreaSummary,
    Coordinate,
    PlanningSession,
    StayOption,
    StayRecommendation,
)


async def run_stay_agent(session: PlanningSession) -> StayRecommendation:
    city = session.hard_constraints.destination_city
    currency = session.hard_constraints.currency
    areas = (
        session.discovery_state.payload.area_summaries
        if session.discovery_state and session.discovery_state.payload
        else []
    )
    primary_area = (
        areas[0] if areas else _fallback_area("area_central", f"{city} central core")
    )
    alternative_area = (
        areas[1]
        if len(areas) > 1
        else _fallback_area("area_quiet", f"{city} quieter edge", quiet=True)
    )

    return StayRecommendation(
        primary=_option(
            "stay_primary",
            primary_area,
            currency,
            "Best balance of transit access and recovery time.",
        ),
        alternatives=[
            _option(
                "stay_alt_quiet",
                alternative_area,
                currency,
                "Better if quiet evenings matter more than transfer time.",
            ),
            _option(
                "stay_alt_value",
                primary_area,
                currency,
                "Value-first backup near the same transit spine.",
            ),
        ],
        user_override_id=(
            session.stay_recommendation.user_override_id
            if session.stay_recommendation
            else None
        ),
    )


async def run_stay_node(state: PlanState) -> GraphState:
    parsed = validate_graph_state(state)
    stay = await run_stay_agent(parsed.session)
    updated = append_progress(
        parsed.model_copy(update={"stay_recommendation": stay}),
        "stay",
        "completed",
        agent_progress_payload(
            "stay",
            primary_area=stay.primary.area.id,
            alternative_count=len(stay.alternatives),
            sample_hotel_count=sum(
                len(option.sample_hotels)
                for option in [
                    stay.primary,
                    *stay.alternatives,
                ]
            ),
            quality={
                "has_primary": True,
                "has_alternatives": bool(stay.alternatives),
                "has_user_override": stay.user_override_id is not None,
            },
        ),
    )
    new_event = updated.progress_events[-1]
    return GraphState(
        stay_recommendation=stay.model_dump(mode="json"),
        progress_events=[new_event.model_dump(mode="json")],
    )


def _option(id_: str, area: AreaSummary, currency: str, fit_reason: str) -> StayOption:
    return StayOption(
        id=id_,
        area=area,
        fit_reason=fit_reason,
        price_band=band(currency, 1200, 2200, "per_trip"),
        sample_hotels=[],
    )


def _fallback_area(id_: str, name: str, *, quiet: bool = False) -> AreaSummary:
    return AreaSummary(
        id=id_,
        name=name,
        vibe_tags=["calm", "local"] if quiet else ["central", "walkable"],
        note=(
            "Softer evenings with longer transfer tradeoffs."
            if quiet
            else "Balanced base for first-time planning."
        ),
        center=Coordinate(
            lat=31.21 if quiet else 31.23, lng=121.43 if quiet else 121.47
        ),
    )
