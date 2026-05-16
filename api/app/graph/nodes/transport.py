"""Transport recommendation graph node."""

from __future__ import annotations

from app.graph.agent_contracts import agent_progress_payload
from app.graph.nodes.discovery import band
from app.graph.state import GraphState, PlanState, append_progress, validate_graph_state
from app.models.schemas import (
    IntracityStrategy,
    PlanningSession,
    TransportLeg,
    TransportRecommendation,
)


async def run_transport_agent(session: PlanningSession) -> TransportRecommendation:
    currency = session.hard_constraints.currency
    preferred = (
        session.preferences.intercity_transport_preference
        if session.preferences
        else "flexible"
    )
    mode = "flight" if preferred == "flight" else "rail"
    is_flight = mode == "flight"

    return TransportRecommendation(
        arrival=TransportLeg(
            mode=mode,
            duration_minutes=160 if is_flight else 300,
            cost_band=band(
                currency,
                900 if is_flight else 500,
                1600 if is_flight else 900,
                "per_trip",
            ),
            note=(
                "Faster arrival with airport transfer padding."
                if is_flight
                else "Lower-friction rail arrival near the city core."
            ),
        ),
        departure=TransportLeg(
            mode=mode,
            duration_minutes=160 if is_flight else 300,
            cost_band=band(
                currency,
                900 if is_flight else 500,
                1600 if is_flight else 900,
                "per_trip",
            ),
            note="Mirror the arrival mode unless live fares strongly disagree.",
        ),
        intracity=IntracityStrategy(
            primary_mode="mixed",
            daily_cost_band=band(currency, 40, 120, "per_day"),
            note="Use transit for cross-city hops and taxi only for late returns.",
        ),
        tradeoffs=[
            (
                "Flight saves time but adds airport transfer uncertainty."
                if is_flight
                else "Rail keeps the trip simpler but can consume more door-to-door time."
            )
        ],
    )


async def run_transport_node(state: PlanState) -> GraphState:
    parsed = validate_graph_state(state)
    transport = await run_transport_agent(parsed.session)
    updated = append_progress(
        parsed.model_copy(update={"transport_recommendation": transport}),
        "transport",
        "completed",
        agent_progress_payload(
            "transport",
            arrival_mode=transport.arrival.mode,
            departure_mode=transport.departure.mode,
            intracity_mode=transport.intracity.primary_mode,
            quality={
                "has_arrival_cost_band": transport.arrival.cost_band is not None,
                "has_departure_cost_band": transport.departure.cost_band is not None,
                "tradeoff_count": len(transport.tradeoffs),
            },
        ),
    )
    new_event = updated.progress_events[-1]
    return GraphState(
        transport_recommendation=transport.model_dump(mode="json"),
        progress_events=[new_event.model_dump(mode="json")],
    )
