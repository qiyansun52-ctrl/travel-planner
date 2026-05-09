"""Adjustment graph behavior tests."""

from __future__ import annotations

import pytest

from app.graph.adjustments import run_adjustment_workflow
from app.graph.adjustments.type_c import run_type_c_adjustment
from app.graph.nodes.adjustment_classifier import classify_adjustment
from tests.graph import fixtures


def planned_session():
    return fixtures.session().model_copy(
        update={
            "stay_recommendation": fixtures.stay_recommendation(),
            "transport_recommendation": fixtures.transport_recommendation(),
            "itinerary": fixtures.itinerary(),
        }
    )


def test_classify_light_itinerary_adjustment_targets_day() -> None:
    classification = classify_adjustment("Update the itinerary for day two.")

    assert classification.type == "A"
    assert classification.confidence >= 0.55
    assert classification.target_scope == "day"


def test_classify_second_afternoon_easier_unknown_under_ts_parity() -> None:
    classification = classify_adjustment("Make the second afternoon easier.")

    assert classification.type == "unknown"
    assert classification.confidence < 0.55
    assert classification.target_scope == "none"


def test_classify_stay_adjustment_targets_stay() -> None:
    classification = classify_adjustment("酒店换到更安静的区域")

    assert classification.type == "B"
    assert classification.target_scope == "stay"


def test_classify_budget_adjustment_targets_budget() -> None:
    classification = classify_adjustment("预算改成 3000")

    assert classification.type == "C"
    assert classification.target_scope == "budget"


def test_classify_short_confirmation_is_unknown() -> None:
    classification = classify_adjustment("ok")

    assert classification.type == "unknown"
    assert classification.confidence < 0.55


@pytest.mark.asyncio
async def test_type_a_workflow_updates_itinerary() -> None:
    result = await run_adjustment_workflow(
        planned_session(),
        message="Update the itinerary for day two.",
    )

    assert result.classification.type == "A"
    assert result.itinerary is not None
    assert result.message == "Itinerary updated."


@pytest.mark.asyncio
async def test_type_b_stay_workflow_reruns_stay_and_clears_override() -> None:
    session = planned_session()
    session = session.model_copy(
        update={
            "stay_recommendation": session.stay_recommendation.model_copy(
                update={"user_override_id": "stay_central"}
            )
        }
    )

    result = await run_adjustment_workflow(session, message="酒店换到更安静的区域")

    assert result.classification.type == "B"
    assert result.classification.target_scope == "stay"
    assert result.stay is not None
    assert result.stay.user_override_id is None
    assert result.stay.primary.id == "stay_primary"
    assert result.itinerary is not None


@pytest.mark.asyncio
async def test_type_b_transport_workflow_reruns_transport() -> None:
    result = await run_adjustment_workflow(
        planned_session(),
        message="Change the transport to train.",
    )

    assert result.classification.type == "B"
    assert result.classification.target_scope == "transport"
    assert result.transport is not None
    assert result.transport.arrival.duration_minutes == 300
    assert result.itinerary is not None


@pytest.mark.asyncio
async def test_low_confidence_returns_clarification_without_itinerary() -> None:
    result = await run_adjustment_workflow(planned_session(), message="ok")

    assert result.message == (
        "Can you clarify whether this changes the itinerary, stay, transport, or core "
        "trip constraints?"
    )
    assert result.itinerary is None


@pytest.mark.asyncio
async def test_type_c_without_action_returns_confirmation_without_reset_or_fork() -> None:
    result = await run_adjustment_workflow(planned_session(), message="预算改成 3000")

    assert result.message == "This changes core trip constraints."
    assert result.confirmation is not None
    assert result.confirmation.detected_change == "预算改成 3000"
    assert result.confirmation.rerun_stages == ["discovery", "preferences", "itinerary"]
    assert (
        result.confirmation.discard_estimate
        == "Most downstream planning state will be refreshed."
    )
    assert result.reset_to_step is None
    assert result.fork_requested is False
    assert result.itinerary is None


@pytest.mark.asyncio
async def test_type_c_action_replan_requests_discovery_reset() -> None:
    result = await run_adjustment_workflow(
        planned_session(),
        message="预算改成 3000",
        type_c_action="replan",
    )

    assert result.reset_to_step == "discovery"
    assert result.message == "Session reset to discovery."


@pytest.mark.asyncio
async def test_type_c_action_save_and_start_new_requests_fork() -> None:
    result = await run_adjustment_workflow(
        planned_session(),
        message="预算改成 3000",
        type_c_action="save_and_start_new",
    )

    assert result.fork_requested is True
    assert result.message == "New session requested."


@pytest.mark.asyncio
async def test_type_c_action_cancel_returns_cancelled_message() -> None:
    result = await run_adjustment_workflow(
        planned_session(),
        message="预算改成 3000",
        type_c_action="cancel",
    )

    assert result.message == "Root change cancelled."


@pytest.mark.asyncio
async def test_type_c_invalid_action_is_rejected_without_reset() -> None:
    classification = classify_adjustment("预算改成 3000")

    with pytest.raises(ValueError, match="Unknown Type C action"):
        await run_type_c_adjustment(
            planned_session(),
            classification,
            action="restart",  # type: ignore[arg-type]
        )
