"""Validate Pydantic schemas mirror Zod behavior in web/src/domain/schemas.ts."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    BudgetBand,
    Coordinate,
    HardConstraints,
    Itinerary,
    NormalizedPlace,
    PlanningSession,
    Preference,
    ValidatorIssue,
)


def test_coordinate_accepts_valid_lat_lng() -> None:
    Coordinate(lat=39.9, lng=116.4)


def test_coordinate_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Coordinate(lat=39.9, lng=116.4, alt=10)  # type: ignore[call-arg]


def test_budget_band_requires_high_ge_low() -> None:
    with pytest.raises(ValidationError) as exc_info:
        BudgetBand(currency="CNY", low=200, high=100, confidence="high", basis="per_trip")
    assert "high" in str(exc_info.value)


def test_budget_band_currency_must_be_3_chars() -> None:
    with pytest.raises(ValidationError):
        BudgetBand(currency="CN", low=100, high=200, confidence="high", basis="per_trip")


def test_budget_band_negative_amounts_rejected() -> None:
    with pytest.raises(ValidationError):
        BudgetBand(currency="CNY", low=-1, high=100, confidence="high", basis="per_trip")


def test_normalized_place_allows_null_coordinate() -> None:
    place = NormalizedPlace(
        id="poi-1",
        name="Tiananmen",
        coordinate=None,
        address=None,
        category=None,
        provider="amap",
    )
    assert place.coordinate is None


def test_normalized_place_rejects_unknown_provider() -> None:
    with pytest.raises(ValidationError):
        NormalizedPlace(
            id="poi-1",
            name="x",
            coordinate=None,
            address=None,
            category=None,
            provider="yahoo",  # type: ignore[arg-type]
        )


def test_hard_constraints_country_code_pattern() -> None:
    with pytest.raises(ValidationError):
        HardConstraints(
            departure_city="Beijing",
            destination_city="Shanghai",
            destination_country_code="cn",
            departure_date="2026-05-10",
            duration_days=2,
            traveler_count=2,
            total_budget=4000,
            currency="CNY",
        )


def test_hard_constraints_date_format() -> None:
    with pytest.raises(ValidationError):
        HardConstraints(
            departure_city="Beijing",
            destination_city="Shanghai",
            destination_country_code="CN",
            departure_date="May 10, 2026",
            duration_days=2,
            traveler_count=2,
            total_budget=4000,
            currency="CNY",
        )


def test_preference_enum_values() -> None:
    Preference(
        area_vibe="historic",
        quiet_vs_lively="balanced",
        stay_type="hotel",
        willing_to_change_hotels=False,
        intercity_transport_preference="rail",
        early_departure_tolerance="medium",
        transfer_tolerance="medium",
        pay_more_to_save_time=False,
    )

    with pytest.raises(ValidationError):
        Preference(
            area_vibe="historic",
            quiet_vs_lively="ultra-loud",  # type: ignore[arg-type]
            stay_type="hotel",
            willing_to_change_hotels=False,
            intercity_transport_preference="rail",
            early_departure_tolerance="medium",
            transfer_tolerance="medium",
            pay_more_to_save_time=False,
        )


def test_validator_issue_scope_is_open_dict() -> None:
    issue = ValidatorIssue(
        code="BUDGET_OVERRUN",
        severity="error",
        scope={"type": "trip"},
        message="too high",
        suggested_action=None,
    )
    assert issue.scope == {"type": "trip"}


def _minimal_itinerary_dict() -> dict:
    band = {
        "currency": "CNY",
        "low": 0,
        "high": 0,
        "confidence": "high",
        "basis": "per_trip",
    }
    return {
        "id": "it-1",
        "session_id": "ses-1",
        "days": [],
        "budget": {
            "currency": "CNY",
            "transport": band,
            "stay": band,
            "food": band,
            "attractions": band,
            "other": band,
            "total": band,
            "user_budget": 0,
            "overrun_flag": False,
        },
        "validator_issues": [],
        "version": 1,
    }


def test_itinerary_roundtrip() -> None:
    payload = _minimal_itinerary_dict()
    obj = Itinerary.model_validate(payload)
    assert obj.model_dump() == payload


def test_planning_session_accepts_iso_datetime() -> None:
    session = PlanningSession.model_validate(
        {
            "session_id": "ses-1",
            "hard_constraints": {
                "departure_city": "Beijing",
                "destination_city": "Shanghai",
                "destination_country_code": "CN",
                "departure_date": "2026-05-10",
                "duration_days": 2,
                "traveler_count": 2,
                "total_budget": 4000,
                "currency": "CNY",
            },
            "discovery_state": None,
            "preferences": None,
            "stay_recommendation": None,
            "transport_recommendation": None,
            "itinerary": None,
            "conversation_history": [],
            "validator_issues": [],
            "parent_session_id": None,
            "snapshot_label": None,
            "status": "active",
            "created_at": "2026-05-09T12:00:00Z",
            "updated_at": "2026-05-09T12:00:00Z",
        }
    )
    assert session.session_id == "ses-1"
