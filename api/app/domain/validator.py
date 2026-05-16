"""Itinerary validator ported from web/src/domain/validator.ts."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models.schemas import DiscoveryCard, Itinerary, ItinerarySegment, ValidatorIssue


@dataclass(frozen=True)
class OperatingWindow:
    open_time: str
    close_time: str


@dataclass(frozen=True)
class ValidatorContext:
    discovery_cards: list[DiscoveryCard]
    operating_windows_by_card_id: dict[str, OperatingWindow] = field(default_factory=dict)


def validate_itinerary(itinerary: Itinerary, context: ValidatorContext) -> list[ValidatorIssue]:
    issues: list[ValidatorIssue] = []
    card_by_id = {card.id: card for card in context.discovery_cards}

    if itinerary.budget.total.high > itinerary.budget.user_budget * 1.15:
        issues.append(
            ValidatorIssue(
                code="BUDGET_OVERRUN",
                severity="error",
                scope={"type": "trip"},
                message=(
                    f"Estimated total {itinerary.budget.total.high} "
                    "exceeds the user budget by more than 15%."
                ),
                suggested_action=(
                    "Reduce optional costs or ask the user before changing stay or transport "
                    "assumptions."
                ),
            )
        )

    for day in itinerary.days:
        attraction_segments = [segment for segment in day.segments if segment.type == "attraction"]
        active_minutes = sum(_segment_duration_minutes(segment) for segment in attraction_segments)

        if active_minutes > 8 * 60 or len(attraction_segments) > 5:
            issues.append(
                ValidatorIssue(
                    code="DAY_OVERLOADED",
                    severity="warning",
                    scope={"type": "day", "day_index": day.day_index},
                    message=f"Day {day.day_index} may feel too dense.",
                    suggested_action="Move one stop into flexible time or another day.",
                )
            )

        movement_minutes = sum(
            _segment_duration_minutes(segment)
            for segment in day.segments
            if segment.type == "transit"
        )
        if active_minutes > 0 and movement_minutes > active_minutes * 0.4:
            issues.append(
                ValidatorIssue(
                    code="WASTEFUL_ROUTING",
                    severity="warning",
                    scope={"type": "day", "day_index": day.day_index},
                    message=f"Day {day.day_index} spends a large share of active time in transit.",
                    suggested_action="Group nearby stops or consider a different stay area.",
                )
            )

        for segment_index, segment in enumerate(day.segments):
            if segment.type != "attraction" or not segment.card_ref:
                continue
            card = card_by_id.get(segment.card_ref)
            if card is None:
                continue

            duration = _segment_duration_minutes(segment)
            if duration < card.suggested_duration_minutes * 0.5:
                issues.append(
                    ValidatorIssue(
                        code="TIMING_UNREALISTIC",
                        severity="error",
                        scope={
                            "type": "segment",
                            "day_index": day.day_index,
                            "segment_index": segment_index,
                            "card_ref": segment.card_ref,
                        },
                        message=(
                            f"{card.name} is scheduled for less than half its suggested visit "
                            "duration."
                        ),
                        suggested_action="Lengthen the visit or remove the stop.",
                    )
                )

            window = context.operating_windows_by_card_id.get(segment.card_ref)
            if card.reservation_hint and window and _outside_window(segment, window):
                issues.append(
                    ValidatorIssue(
                        code="TIMING_UNREALISTIC",
                        severity="error",
                        scope={
                            "type": "segment",
                            "day_index": day.day_index,
                            "segment_index": segment_index,
                            "card_ref": segment.card_ref,
                        },
                        message=f"{card.name} is placed outside its known operating window.",
                        suggested_action=(
                            f"Schedule it between {window.open_time} and {window.close_time}."
                        ),
                    )
                )

    return issues


def _outside_window(segment: ItinerarySegment, window: OperatingWindow) -> bool:
    return (
        _time_to_minutes(segment.start_time) < _time_to_minutes(window.open_time)
        or _time_to_minutes(segment.end_time) > _time_to_minutes(window.close_time)
    )


def _segment_duration_minutes(segment: ItinerarySegment) -> int:
    return max(0, _time_to_minutes(segment.end_time) - _time_to_minutes(segment.start_time))


def _time_to_minutes(value: str) -> int:
    hours, minutes = (int(part) for part in value.split(":"))
    return hours * 60 + minutes
