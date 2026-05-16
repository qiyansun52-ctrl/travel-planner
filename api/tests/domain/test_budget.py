"""Mirror of web/src/domain/budget.test.ts."""
from __future__ import annotations

import pytest

from app.domain.budget import (
    DEFAULT_ATTRACTION_SHARE,
    calculate_daily_attraction_slot,
    classify_attraction_cost_signal,
    sum_budget_bands,
    to_per_trip_band,
)
from app.models.schemas import BudgetBand, BudgetBasis, HardConstraints


HARD_CONSTRAINTS = HardConstraints(
    departure_city="Beijing",
    destination_city="Shanghai",
    destination_country_code="CN",
    departure_date="2026-05-10",
    duration_days=2,
    traveler_count=2,
    total_budget=4000,
    currency="CNY",
)


def _band(high: float, basis: BudgetBasis = "per_person") -> BudgetBand:
    return BudgetBand(currency="CNY", low=high, high=high, confidence="medium", basis=basis)


def test_calculate_daily_attraction_slot_uses_default_share() -> None:
    assert DEFAULT_ATTRACTION_SHARE == 0.15
    assert calculate_daily_attraction_slot(4000, 2, 2) == 150


def test_classify_returns_unknown_when_cost_missing() -> None:
    assert classify_attraction_cost_signal(None, HARD_CONSTRAINTS) == "unknown"


def test_classify_free_when_zero() -> None:
    assert classify_attraction_cost_signal(_band(0), HARD_CONSTRAINTS) == "free"


def test_classify_low_at_or_below_30pct_of_slot() -> None:
    assert classify_attraction_cost_signal(_band(45), HARD_CONSTRAINTS) == "low"


def test_classify_medium_above_30pct_and_at_or_below_80pct() -> None:
    assert classify_attraction_cost_signal(_band(46), HARD_CONSTRAINTS) == "medium"
    assert classify_attraction_cost_signal(_band(120), HARD_CONSTRAINTS) == "medium"


def test_classify_high_above_80pct() -> None:
    assert classify_attraction_cost_signal(_band(121), HARD_CONSTRAINTS) == "high"


def test_classify_same_attraction_different_for_different_budgets() -> None:
    cheap = HARD_CONSTRAINTS.model_copy(update={"total_budget": 1000})
    pricey = HARD_CONSTRAINTS.model_copy(update={"total_budget": 8000})
    ticket = _band(80)

    assert classify_attraction_cost_signal(ticket, cheap) == "high"
    assert classify_attraction_cost_signal(ticket, pricey) == "low"


def test_to_per_trip_converts_per_person_with_traveler_count() -> None:
    band = to_per_trip_band(_band(100), traveler_count=3)
    assert band.low == 300
    assert band.high == 300
    assert band.basis == "per_trip"


def test_to_per_trip_rejects_per_person_without_traveler_count() -> None:
    with pytest.raises(ValueError, match="traveler_count"):
        to_per_trip_band(_band(100))


def test_to_per_trip_converts_per_room_per_night() -> None:
    band = to_per_trip_band(
        _band(400, "per_room_per_night"),
        room_count=2,
        duration_days=3,
    )
    assert band.low == 2400
    assert band.high == 2400
    assert band.basis == "per_trip"


def test_to_per_trip_rejects_per_room_per_night_without_room_count() -> None:
    with pytest.raises(ValueError, match="room_count"):
        to_per_trip_band(_band(400, "per_room_per_night"), duration_days=3)


def test_to_per_trip_converts_per_day_with_duration() -> None:
    band = to_per_trip_band(_band(50, "per_day"), duration_days=4)
    assert band.low == 200
    assert band.high == 200
    assert band.basis == "per_trip"


def test_sum_budget_bands_degrades_to_lowest_confidence() -> None:
    a = BudgetBand(currency="CNY", low=80, high=100, confidence="high", basis="per_trip")
    b = BudgetBand(currency="CNY", low=120, high=200, confidence="low", basis="per_trip")

    result = sum_budget_bands("CNY", [a, b])

    assert result.currency == "CNY"
    assert result.low == 200
    assert result.high == 300
    assert result.confidence == "low"
    assert result.basis == "per_trip"


def test_sum_budget_bands_rejects_mixed_basis() -> None:
    a = BudgetBand(currency="CNY", low=100, high=100, confidence="high", basis="per_trip")
    b = BudgetBand(currency="CNY", low=50, high=50, confidence="high", basis="per_person")

    with pytest.raises(ValueError, match="per_trip"):
        sum_budget_bands("CNY", [a, b])


def test_sum_budget_bands_rejects_currency_mismatch() -> None:
    a = BudgetBand(currency="CNY", low=100, high=100, confidence="high", basis="per_trip")
    b = BudgetBand(currency="USD", low=20, high=20, confidence="high", basis="per_trip")

    with pytest.raises(ValueError, match="CNY"):
        sum_budget_bands("CNY", [a, b])
