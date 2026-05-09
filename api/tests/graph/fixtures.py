"""Reusable graph-domain test fixtures."""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.schemas import (
    AreaSummary,
    BudgetBand,
    BudgetSummary,
    Coordinate,
    DiscoveryCard,
    DiscoveryOutput,
    DiscoveryState,
    FoodSummary,
    HardConstraints,
    IntracityStrategy,
    Itinerary,
    ItineraryDay,
    ItinerarySegment,
    NormalizedPlace,
    PlanningSession,
    Preference,
    SourceNote,
    StayOption,
    StayRecommendation,
    TransportLeg,
    TransportRecommendation,
    ValidatorIssue,
)


def band(low: float = 100, high: float = 200, basis: str = "per_trip") -> BudgetBand:
    return BudgetBand(currency="CNY", low=low, high=high, confidence="medium", basis=basis)


def budget_summary(user_budget: float = 6000, total_high: float = 1000) -> BudgetSummary:
    return BudgetSummary(
        currency="CNY",
        transport=band(100, 200),
        stay=band(300, 500),
        food=band(100, 150),
        attractions=band(50, 100),
        other=band(25, 50),
        total=band(total_high / 2, total_high),
        user_budget=user_budget,
        overrun_flag=total_high > user_budget,
    )


def hard_constraints(total_budget: float = 6000) -> HardConstraints:
    return HardConstraints(
        departure_city="杭州",
        destination_city="上海",
        destination_country_code="CN",
        departure_date="2026-06-01",
        duration_days=3,
        traveler_count=2,
        total_budget=total_budget,
        currency="CNY",
    )


def preferences() -> Preference:
    return Preference(
        area_vibe="walkable central neighborhoods",
        quiet_vs_lively="balanced",
        stay_type="hotel",
        willing_to_change_hotels=False,
        intercity_transport_preference="rail",
        early_departure_tolerance="medium",
        transfer_tolerance="medium",
        pay_more_to_save_time=True,
    )


def area(area_id: str = "area_central", name: str = "上海 central core") -> AreaSummary:
    return AreaSummary(
        id=area_id,
        name=name,
        vibe_tags=["central", "walkable"],
        note="Convenient base for first-time visitors.",
        center=Coordinate(lat=31.2304, lng=121.4737),
    )


def place(place_id: str = "place_waterfront", name: str = "上海 waterfront") -> NormalizedPlace:
    return NormalizedPlace(
        id=place_id,
        name=name,
        coordinate=Coordinate(lat=31.2397, lng=121.4998),
        address="Zhongshan East 1st Road",
        category="waterfront",
        provider="amap",
    )


def discovery_card(
    card_id: str = "disc_waterfront",
    name: str = "上海 waterfront walk",
) -> DiscoveryCard:
    return DiscoveryCard(
        id=card_id,
        name=name,
        reason="Classic skyline views with an easy walking route.",
        category="sightseeing",
        tags=["views", "walk"],
        suggested_duration_minutes=90,
        cost_signal="free",
        cost_estimate=band(0, 0),
        image_url=None,
        reservation_hint=None,
        place=place(),
        enrichment_status="complete",
    )


def discovery_output() -> DiscoveryOutput:
    return DiscoveryOutput(
        cards=[
            discovery_card(),
            discovery_card("disc_museum", "上海 museum afternoon"),
            discovery_card("disc_garden", "上海 garden stroll"),
        ],
        food_summaries=[
            FoodSummary(
                id="food_noodles",
                name="Local noodles",
                category="casual",
                description="Simple lunch option near central attractions.",
                image_url=None,
            )
        ],
        area_summaries=[
            area(),
            area("area_french_concession", "上海 French Concession"),
        ],
        budget_estimate=budget_summary(),
        source_notes=[
            SourceNote(
                provider="fixture",
                url=None,
                note="Fixture source note for graph tests.",
            )
        ],
    )


def session(
    with_discovery: bool = True,
    with_preferences: bool = True,
) -> PlanningSession:
    now = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)
    return PlanningSession(
        session_id="session_test",
        hard_constraints=hard_constraints(),
        discovery_state=DiscoveryState(
            payload=discovery_output() if with_discovery else None,
            selected_card_ids=["disc_waterfront"],
        )
        if with_discovery
        else None,
        preferences=preferences() if with_preferences else None,
        stay_recommendation=None,
        transport_recommendation=None,
        itinerary=None,
        conversation_history=[],
        validator_issues=[],
        parent_session_id=None,
        snapshot_label=None,
        status="active",
        created_at=now,
        updated_at=now,
    )


def stay_recommendation() -> StayRecommendation:
    selected_area = area()
    hotel_place = place("place_hotel", "上海 central hotel")
    option = StayOption(
        id="stay_central",
        area=selected_area,
        fit_reason="Keeps transit simple and most activities nearby.",
        price_band=band(400, 700, "per_room_per_night"),
        sample_hotels=[
            {
                "name": "Central Sample Hotel",
                "style": "midrange",
                "price_band": band(400, 700, "per_room_per_night"),
                "place": hotel_place,
            }
        ],
    )
    return StayRecommendation(primary=option, alternatives=[], user_override_id=None)


def transport_recommendation() -> TransportRecommendation:
    return TransportRecommendation(
        arrival=TransportLeg(
            mode="rail",
            duration_minutes=60,
            cost_band=band(80, 120, "per_person"),
            note="Fast train into the city.",
        ),
        departure=TransportLeg(
            mode="rail",
            duration_minutes=60,
            cost_band=band(80, 120, "per_person"),
            note="Return by rail.",
        ),
        intracity=IntracityStrategy(
            primary_mode="transit",
            daily_cost_band=band(20, 40, "per_day"),
            note="Metro plus walking covers the core route.",
        ),
        tradeoffs=["Rail balances time and budget."],
    )


def itinerary(version: int = 1, total_high: float = 1000) -> Itinerary:
    return Itinerary(
        id=f"itinerary_v{version}",
        session_id="session_test",
        days=[
            ItineraryDay(
                day_index=1,
                date="2026-06-01",
                segments=[
                    ItinerarySegment(
                        type="attraction",
                        start_time="10:00",
                        end_time="11:30",
                        place=place(),
                        card_ref="disc_waterfront",
                        description="Walk the waterfront.",
                        cost_estimate=band(0, 0),
                    )
                ],
                notes=["Keep the afternoon flexible."],
            )
        ],
        budget=budget_summary(total_high=total_high),
        validator_issues=[],
        version=version,
    )


def validator_error() -> ValidatorIssue:
    return ValidatorIssue(
        code="budget_overrun",
        severity="error",
        scope={"field": "budget"},
        message="Trip exceeds the requested budget.",
        suggested_action="Reduce hotel or attraction costs.",
    )
