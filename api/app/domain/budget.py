"""Budget calculation helpers ported from web/src/domain/budget.ts."""
from __future__ import annotations

from collections.abc import Iterable

from app.models.schemas import BudgetBand, Confidence, CostSignal, HardConstraints

DEFAULT_ATTRACTION_SHARE = 0.15


def calculate_daily_attraction_slot(
    total_budget: float,
    duration_days: int,
    traveler_count: int,
    attraction_share: float = DEFAULT_ATTRACTION_SHARE,
) -> float:
    return (total_budget * attraction_share) / (duration_days * traveler_count)


def classify_attraction_cost_signal(
    cost_estimate: BudgetBand | None,
    hard_constraints: HardConstraints,
    attraction_share: float = DEFAULT_ATTRACTION_SHARE,
) -> CostSignal:
    if cost_estimate is None:
        return "unknown"

    per_person = _estimate_per_person_cost(cost_estimate, hard_constraints.traveler_count)
    if per_person is None:
        return "unknown"
    if per_person == 0:
        return "free"

    daily_slot = calculate_daily_attraction_slot(
        hard_constraints.total_budget,
        hard_constraints.duration_days,
        hard_constraints.traveler_count,
        attraction_share,
    )
    if per_person <= daily_slot * 0.3:
        return "low"
    if per_person <= daily_slot * 0.8:
        return "medium"
    return "high"


def to_per_trip_band(
    band: BudgetBand,
    *,
    traveler_count: int | None = None,
    duration_days: int | None = None,
    room_count: int | None = None,
) -> BudgetBand:
    match band.basis:
        case "per_trip":
            return band.model_copy()
        case "per_party":
            return band.model_copy(update={"basis": "per_trip"})
        case "per_person":
            multiplier = _require_positive("traveler_count", traveler_count)
            return _multiply_band(band, multiplier)
        case "per_day":
            multiplier = _require_positive("duration_days", duration_days)
            return _multiply_band(band, multiplier)
        case "per_room_per_night":
            rooms = _require_positive("room_count", room_count)
            days = _require_positive("duration_days", duration_days)
            return _multiply_band(band, rooms * days)


def sum_budget_bands(currency: str, bands: Iterable[BudgetBand]) -> BudgetBand:
    band_list = list(bands)
    for band in band_list:
        if band.currency != currency:
            raise ValueError(f"Expected all budget bands to use {currency}")
        if band.basis != "per_trip":
            raise ValueError("sum_budget_bands expects all inputs to have per_trip basis")

    return BudgetBand(
        currency=currency,
        low=sum(band.low for band in band_list),
        high=sum(band.high for band in band_list),
        confidence=_lowest_confidence([band.confidence for band in band_list]),
        basis="per_trip",
    )


def _estimate_per_person_cost(band: BudgetBand, traveler_count: int) -> float | None:
    match band.basis:
        case "per_person":
            return band.high
        case "per_party" | "per_trip":
            return band.high / traveler_count
        case "per_day" | "per_room_per_night":
            return None


def _multiply_band(band: BudgetBand, multiplier: float) -> BudgetBand:
    return band.model_copy(
        update={
            "low": band.low * multiplier,
            "high": band.high * multiplier,
            "basis": "per_trip",
        }
    )


def _require_positive(name: str, value: int | None) -> int:
    if value is None or value <= 0:
        raise ValueError(f"Budget conversion requires {name}")
    return value


def _lowest_confidence(values: list[Confidence]) -> Confidence:
    if "low" in values:
        return "low"
    if "medium" in values:
        return "medium"
    return "high"
