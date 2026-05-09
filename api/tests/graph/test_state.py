from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.graph.state import (
    PlanState,
    TypeCConfirmation,
    append_progress,
    graph_input_from_state,
    validate_graph_state,
)
from app.models.schemas import ValidatorIssue
from tests.graph.fixtures import session, validator_error


def test_plan_state_validates_session_and_defaults() -> None:
    state = PlanState(session=session())

    assert state.session.session_id == "session_test"
    assert state.mode == "full_planning"
    assert state.corrective_attempts == 0
    assert state.validator_issues == []
    assert state.progress_events == []


def test_graph_input_from_state_and_validate_graph_state_round_trip_json_dict() -> None:
    state = PlanState(session=session(), fixture_mode=True)

    raw = graph_input_from_state(state)
    restored = validate_graph_state(raw)

    assert isinstance(raw, dict)
    assert raw["session"]["created_at"] == "2026-05-09T12:00:00Z"
    assert restored == state


def test_validate_graph_state_accepts_plan_state_passthrough() -> None:
    state = PlanState(session=session())

    assert validate_graph_state(state) is state


def test_has_validator_errors_is_true_only_for_error_severity() -> None:
    warning = ValidatorIssue(
        code="long_walk",
        severity="warning",
        scope={"day": 1},
        message="This day has a long walking segment.",
        suggested_action=None,
    )

    assert PlanState(session=session(), validator_issues=[warning]).has_validator_errors is False
    assert PlanState(session=session(), validator_issues=[validator_error()]).has_validator_errors is True


def test_append_progress_returns_new_state_without_mutating_original() -> None:
    state = PlanState(session=session())

    updated = append_progress(state, "planner", "started", {"attempt": 1})

    assert state.progress_events == []
    assert len(updated.progress_events) == 1
    assert updated.progress_events[0].node == "planner"
    assert updated.progress_events[0].status == "started"
    assert updated.progress_events[0].payload == {"attempt": 1}
    assert updated.progress_events[0].created_at.tzinfo is not None


def test_type_c_confirmation_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TypeCConfirmation(
            detected_change="duration changed",
            rerun_stages=["itinerary"],
            discard_estimate="2 existing days affected",
            unexpected=True,
        )
