"""Agent contract and quality-report tests."""

from __future__ import annotations

import json

from app.graph.agent_contracts import (
    AGENT_CONTRACTS,
    agent_progress_payload,
    discovery_quality_report,
    itinerary_quality_report,
    validator_quality_report,
)
from tests.graph import fixtures


def test_agent_contracts_cover_planning_stages() -> None:
    assert set(AGENT_CONTRACTS) == {
        "discovery",
        "stay",
        "transport",
        "planner",
        "validator",
    }
    assert AGENT_CONTRACTS["discovery"].handoff_to == ("stay", "transport", "planner")
    assert AGENT_CONTRACTS["validator"].handoff_to == ("planner", "user")


def test_agent_progress_payload_is_json_serializable_and_keeps_metrics() -> None:
    payload = agent_progress_payload(
        "planner",
        version=2,
        quality={"day_count": 3, "budget_overrun_flag": False},
    )

    assert payload["version"] == 2
    assert payload["agent"]["stage"] == "planner"
    assert payload["agent"]["contract_version"] == "2026-05-13"
    assert payload["agent"]["handoff_to"] == ["validator"]
    json.dumps(payload)


def test_discovery_quality_report_counts_grounding_and_enrichment() -> None:
    report = discovery_quality_report(fixtures.discovery_output())

    assert report == {
        "card_count": 3,
        "source_note_count": 1,
        "complete_card_count": 3,
        "partial_card_count": 0,
        "minimal_card_count": 0,
        "cards_with_place_count": 3,
        "cards_with_cost_estimate_count": 3,
        "reservation_hint_count": 0,
        "min_cards_met": True,
        "has_grounding": True,
    }


def test_itinerary_quality_report_counts_segments_and_reservation_notes() -> None:
    itinerary = fixtures.itinerary().model_copy(
        update={
            "days": [
                fixtures.itinerary()
                .days[0]
                .model_copy(
                    update={
                        "notes": [
                            "Keep the afternoon flexible.",
                            "Reservation check: 上海 museum afternoon - Reserve ahead.",
                        ]
                    }
                )
            ]
        }
    )

    report = itinerary_quality_report(itinerary, expected_day_count=1)

    assert report["day_count"] == 1
    assert report["expected_day_count"] == 1
    assert report["day_count_matches_duration"] is True
    assert report["segment_count"] == 1
    assert report["attraction_segment_count"] == 1
    assert report["mapped_attraction_segment_count"] == 1
    assert report["reservation_note_count"] == 1


def test_validator_quality_report_counts_severity_and_codes() -> None:
    warning = fixtures.validator_error().model_copy(
        update={"severity": "warning", "code": "dense_day"}
    )
    error = fixtures.validator_error()

    report = validator_quality_report([warning, error])

    assert report == {
        "issue_count": 2,
        "error_count": 1,
        "warning_count": 1,
        "issue_codes": ["dense_day", "budget_overrun"],
    }
