"""Deterministic planner graph node."""

from __future__ import annotations

from datetime import date, timedelta

from app.graph.nodes.discovery import band, budget_summary
from app.graph.state import GraphState, PlanState, append_progress, validate_graph_state
from app.models.schemas import (
    DiscoveryCard,
    Itinerary,
    ItineraryDay,
    ItinerarySegment,
    NormalizedPlace,
    PlanningSession,
    StayOption,
    StayRecommendation,
    TransportRecommendation,
    ValidatorIssue,
)


async def run_planner_agent(
    session: PlanningSession,
    stay: StayRecommendation,
    transport: TransportRecommendation,
    validator_issues: list[ValidatorIssue] | None = None,
) -> Itinerary:
    cards = _selected_cards(session)
    active_stay = active_stay_option(stay)
    days = _build_days(session, cards, active_stay, validator_issues)
    currency = session.hard_constraints.currency
    transport_high = transport.arrival.cost_band.high + transport.departure.cost_band.high
    stay_high = active_stay.price_band.high
    version = (session.itinerary.version if session.itinerary else 0) + 1

    return Itinerary(
        id=session.itinerary.id if session.itinerary else "itinerary_mvp",
        session_id=session.session_id,
        days=days,
        budget=budget_summary(
            currency,
            session.hard_constraints.total_budget,
            transport=band(currency, transport_high * 0.75, transport_high, "per_trip"),
            stay=band(currency, stay_high * 0.75, stay_high, "per_trip"),
            food=band(currency, 600, 1100, "per_trip"),
            attractions=band(currency, 200, 700, "per_trip"),
            other=band(currency, 150, 400, "per_trip", "low"),
        ),
        validator_issues=[],
        version=version,
    )


def active_stay_option(stay: StayRecommendation) -> StayOption:
    options = [stay.primary, *stay.alternatives]
    return next(
        (option for option in options if option.id == stay.user_override_id),
        stay.primary,
    )


async def run_planner_node(state: PlanState) -> GraphState:
    parsed = validate_graph_state(state)
    stay = parsed.stay_recommendation or parsed.session.stay_recommendation
    transport = parsed.transport_recommendation or parsed.session.transport_recommendation
    if stay is None:
        raise ValueError("run_planner_node requires stay_recommendation")
    if transport is None:
        raise ValueError("run_planner_node requires transport_recommendation")

    itinerary = await run_planner_agent(parsed.session, stay, transport, parsed.validator_issues)
    updated = append_progress(
        parsed.model_copy(update={"itinerary": itinerary}),
        "planner",
        "completed",
        {"version": itinerary.version},
    )
    return GraphState(
        itinerary=itinerary.model_dump(mode="json"),
        progress_events=[event.model_dump(mode="json") for event in updated.progress_events],
    )


def _selected_cards(session: PlanningSession) -> list[DiscoveryCard]:
    payload = session.discovery_state.payload if session.discovery_state else None
    if payload is None:
        return []
    ids = set(session.discovery_state.selected_card_ids)
    selected = [card for card in payload.cards if card.id in ids]
    return selected if selected else payload.cards[:3]


def _build_days(
    session: PlanningSession,
    selected: list[DiscoveryCard],
    stay: StayOption,
    validator_issues: list[ValidatorIssue] | None,
) -> list[ItineraryDay]:
    days: list[ItineraryDay] = []
    duration = session.hard_constraints.duration_days
    relaxed = len(selected) <= duration
    cursor = 0

    for day_index in range(1, duration + 1):
        first = _card_at(selected, cursor)
        second = _card_at(selected, cursor + 1)
        cursor += 1 if relaxed else 2
        segments = [
            _hotel_segment("09:00", "09:30", stay, "Start from the active stay area.")
        ]
        if first:
            segments.append(_card_segment(first, "10:00", "12:00" if relaxed else "11:45"))
        segments.append(
            ItinerarySegment(
                type="food",
                start_time="12:15",
                end_time="13:30",
                place=None,
                card_ref=None,
                description=(
                    "Keep lunch flexible near the morning area instead of locking a "
                    "specific restaurant."
                ),
                cost_estimate=band(session.hard_constraints.currency, 80, 180, "per_party"),
            )
        )
        if second and not relaxed:
            segments.append(_card_segment(second, "14:00", "16:00"))
        else:
            segments.append(
                ItinerarySegment(
                    type="rest",
                    start_time="14:00",
                    end_time="16:00",
                    place=None,
                    card_ref=None,
                    description="Flexible rest or low-confidence optional discovery slot.",
                    cost_estimate=None,
                )
            )
        segments.append(
            ItinerarySegment(
                type="hotel_return",
                start_time="18:00",
                end_time="18:30",
                place=None,
                card_ref=None,
                description="Return before dinner so the evening can stay light.",
                cost_estimate=band(session.hard_constraints.currency, 20, 80, "per_party"),
            )
        )
        note = (
            "Few selections detected, so the plan preserves flexible time."
            if relaxed
            else "Dense selections were prioritized by route and fit."
        )
        notes = [note]
        if validator_issues:
            notes.append("Corrective pass used validator errors as planning context.")
        days.append(
            ItineraryDay(
                day_index=day_index,
                date=_add_days(session.hard_constraints.departure_date, day_index - 1),
                segments=segments,
                notes=notes,
            )
        )

    return days


def _card_at(cards: list[DiscoveryCard], index: int) -> DiscoveryCard | None:
    if not cards:
        return None
    return cards[index % len(cards)]


def _hotel_segment(
    start_time: str,
    end_time: str,
    stay: StayOption,
    description: str,
) -> ItinerarySegment:
    return ItinerarySegment(
        type="hotel_checkin",
        start_time=start_time,
        end_time=end_time,
        place=NormalizedPlace(
            id=stay.area.id,
            name=stay.area.name,
            coordinate=stay.area.center,
            address=stay.area.name,
            category="stay_area",
            provider="mapbox",
        ),
        card_ref=None,
        description=description,
        cost_estimate=None,
    )


def _card_segment(card: DiscoveryCard, start_time: str, end_time: str) -> ItinerarySegment:
    return ItinerarySegment(
        type="attraction",
        start_time=start_time,
        end_time=end_time,
        place=card.place,
        card_ref=card.id,
        description=card.reason,
        cost_estimate=card.cost_estimate,
    )


def _add_days(value: str, offset: int) -> str:
    parsed = date.fromisoformat(value)
    return (parsed + timedelta(days=offset)).isoformat()
