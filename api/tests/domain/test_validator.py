"""Mirror of web/src/domain/validator.test.ts."""
from __future__ import annotations

from app.domain.validator import OperatingWindow, ValidatorContext, validate_itinerary
from app.models.schemas import (
    BudgetBand,
    BudgetSummary,
    DiscoveryCard,
    Itinerary,
    ItineraryDay,
    ItinerarySegment,
)


def _band(amount: float = 0) -> BudgetBand:
    return BudgetBand(currency="CNY", low=amount, high=amount, confidence="high", basis="per_trip")


def _summary(total_high: float, user_budget: float) -> BudgetSummary:
    band = _band()
    total = BudgetBand(
        currency="CNY",
        low=total_high,
        high=total_high,
        confidence="high",
        basis="per_trip",
    )
    return BudgetSummary(
        currency="CNY",
        transport=band,
        stay=band,
        food=band,
        attractions=band,
        other=band,
        total=total,
        user_budget=user_budget,
        overrun_flag=total_high > user_budget,
    )


def _seg(
    *,
    type: str = "attraction",
    start: str = "09:00",
    end: str = "11:00",
    card_ref: str | None = None,
    description: str = "visit",
) -> ItinerarySegment:
    return ItinerarySegment(
        type=type,  # type: ignore[arg-type]
        start_time=start,
        end_time=end,
        place=None,
        card_ref=card_ref,
        description=description,
        cost_estimate=None,
    )


def _card(
    card_id: str,
    *,
    suggested_minutes: float = 60,
    reservation_hint: str | None = None,
) -> DiscoveryCard:
    return DiscoveryCard(
        id=card_id,
        name=f"card-{card_id}",
        reason="r",
        category="c",
        tags=[],
        suggested_duration_minutes=suggested_minutes,
        cost_signal="unknown",
        cost_estimate=None,
        image_url=None,
        reservation_hint=reservation_hint,
        place=None,
        enrichment_status="minimal",
    )


def _itinerary(
    days: list[ItineraryDay],
    *,
    total_high: float = 0,
    user_budget: float = 1000,
) -> Itinerary:
    return Itinerary(
        id="it-1",
        session_id="ses-1",
        days=days,
        budget=_summary(total_high, user_budget),
        validator_issues=[],
        version=1,
    )


def test_flags_budget_overrun_above_15pct() -> None:
    itinerary = _itinerary(days=[], total_high=1151, user_budget=1000)
    issues = validate_itinerary(itinerary, ValidatorContext(discovery_cards=[]))

    assert "BUDGET_OVERRUN" in [issue.code for issue in issues]


def test_does_not_flag_budget_overrun_at_or_below_15pct() -> None:
    itinerary = _itinerary(days=[], total_high=1150, user_budget=1000)
    issues = validate_itinerary(itinerary, ValidatorContext(discovery_cards=[]))

    assert all(issue.code != "BUDGET_OVERRUN" for issue in issues)


def test_flags_day_with_more_than_8_hours_active_attractions() -> None:
    day = ItineraryDay(
        day_index=1,
        date="2026-05-10",
        segments=[
            _seg(start="08:00", end="13:00", type="attraction"),
            _seg(start="14:00", end="18:00", type="attraction"),
        ],
        notes=[],
    )

    issues = validate_itinerary(_itinerary([day]), ValidatorContext(discovery_cards=[]))

    assert any(issue.code == "DAY_OVERLOADED" for issue in issues)


def test_flags_day_with_more_than_5_attraction_segments() -> None:
    segments = [
        _seg(start=f"{8 + index:02d}:00", end=f"{8 + index:02d}:30", type="attraction")
        for index in range(6)
    ]
    day = ItineraryDay(day_index=1, date="2026-05-10", segments=segments, notes=[])

    issues = validate_itinerary(_itinerary([day]), ValidatorContext(discovery_cards=[]))

    assert any(issue.code == "DAY_OVERLOADED" for issue in issues)


def test_flags_wasteful_routing_when_transit_exceeds_40pct_of_active() -> None:
    day = ItineraryDay(
        day_index=1,
        date="2026-05-10",
        segments=[
            _seg(start="09:00", end="10:00", type="attraction"),
            _seg(start="10:00", end="10:30", type="transit"),
            _seg(start="10:30", end="11:30", type="attraction"),
        ],
        notes=[],
    )
    issues = validate_itinerary(_itinerary([day]), ValidatorContext(discovery_cards=[]))
    assert all(issue.code != "WASTEFUL_ROUTING" for issue in issues)

    day_bad = ItineraryDay(
        day_index=1,
        date="2026-05-10",
        segments=[
            _seg(start="09:00", end="10:00", type="attraction"),
            _seg(start="10:00", end="11:00", type="transit"),
            _seg(start="11:00", end="12:00", type="attraction"),
        ],
        notes=[],
    )
    issues_bad = validate_itinerary(_itinerary([day_bad]), ValidatorContext(discovery_cards=[]))
    assert any(issue.code == "WASTEFUL_ROUTING" for issue in issues_bad)


def test_flags_timing_unrealistic_when_under_half_suggested_duration() -> None:
    card = _card("c1", suggested_minutes=120)
    day = ItineraryDay(
        day_index=1,
        date="2026-05-10",
        segments=[_seg(start="09:00", end="09:30", card_ref="c1")],
        notes=[],
    )

    issues = validate_itinerary(_itinerary([day]), ValidatorContext(discovery_cards=[card]))

    assert any(issue.code == "TIMING_UNREALISTIC" for issue in issues)


def test_flags_timing_unrealistic_outside_operating_window() -> None:
    card = _card("c1", suggested_minutes=60, reservation_hint="advance booking")
    day = ItineraryDay(
        day_index=1,
        date="2026-05-10",
        segments=[_seg(start="07:00", end="08:00", card_ref="c1")],
        notes=[],
    )
    context = ValidatorContext(
        discovery_cards=[card],
        operating_windows_by_card_id={"c1": OperatingWindow(open_time="09:00", close_time="17:00")},
    )

    issues = validate_itinerary(_itinerary([day]), context)

    assert any(issue.code == "TIMING_UNREALISTIC" for issue in issues)


def test_returns_empty_when_no_problems() -> None:
    card = _card("c1", suggested_minutes=60)
    day = ItineraryDay(
        day_index=1,
        date="2026-05-10",
        segments=[_seg(start="09:00", end="10:00", card_ref="c1")],
        notes=[],
    )

    issues = validate_itinerary(_itinerary([day]), ValidatorContext(discovery_cards=[card]))

    assert issues == []


def test_is_pure_and_does_not_mutate_input() -> None:
    itinerary = _itinerary(days=[], total_high=1160, user_budget=1000)
    before = itinerary.model_dump()

    first = validate_itinerary(itinerary, ValidatorContext(discovery_cards=[]))
    second = validate_itinerary(itinerary, ValidatorContext(discovery_cards=[]))

    assert second == first
    assert itinerary.model_dump() == before
