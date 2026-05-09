"""Planning workflow behavior tests."""

from __future__ import annotations

import pytest

from app.graph import workflow
from app.graph.nodes.discovery import run_discovery_node
from app.graph.state import PlanState, graph_input_from_state, validate_graph_state
from tests.graph import fixtures


@pytest.mark.asyncio
async def test_full_workflow_happy_path_finalizes_without_corrective_pass() -> None:
    result = await workflow.run_full_planning_workflow(fixtures.session())

    assert result.session_id == "session_test"
    assert result.stay.primary.id == "stay_primary"
    assert result.transport.arrival.mode == "rail"
    assert result.itinerary.version == 1
    assert result.validator_issues == result.itinerary.validator_issues
    assert [event.node for event in result.progress_events] == [
        "stay",
        "transport",
        "planner",
        "validator",
    ]


@pytest.mark.asyncio
async def test_planner_only_workflow_requires_existing_stay_and_transport() -> None:
    with pytest.raises(ValueError, match="requires existing stay and transport"):
        await workflow.run_planner_only_workflow(fixtures.session(), reason="user adjustment")


@pytest.mark.asyncio
async def test_corrective_pass_runs_once_for_error_severity(monkeypatch) -> None:
    planner_calls = 0
    original_planner = workflow.run_planner_node
    issue = fixtures.validator_error()

    async def counting_planner(state):
        nonlocal planner_calls
        planner_calls += 1
        return await original_planner(state)

    async def validator_with_error(state):
        parsed = validate_graph_state(state)
        itinerary = parsed.itinerary.model_copy(update={"validator_issues": [issue]})
        return {
            "validator_issues": [issue.model_dump(mode="json")],
            "itinerary": itinerary.model_dump(mode="json"),
            "progress_events": [
                {
                    "node": "validator",
                    "status": "completed",
                    "payload": {"issue_count": 1, "error_count": 1},
                    "created_at": parsed.session.updated_at.isoformat(),
                }
            ],
        }

    monkeypatch.setattr(workflow, "run_planner_node", counting_planner)
    monkeypatch.setattr(workflow, "run_validator_node", validator_with_error)

    result = await workflow.run_full_planning_workflow(fixtures.session())

    assert planner_calls == 2
    assert result.validator_issues == [issue]
    assert result.itinerary.validator_issues == [issue]


@pytest.mark.asyncio
async def test_warning_only_validation_does_not_rerun_planner(monkeypatch) -> None:
    planner_calls = 0
    original_planner = workflow.run_planner_node
    issue = fixtures.validator_error().model_copy(update={"severity": "warning"})

    async def counting_planner(state):
        nonlocal planner_calls
        planner_calls += 1
        return await original_planner(state)

    async def validator_with_warning(state):
        parsed = validate_graph_state(state)
        itinerary = parsed.itinerary.model_copy(update={"validator_issues": [issue]})
        return {
            "validator_issues": [issue.model_dump(mode="json")],
            "itinerary": itinerary.model_dump(mode="json"),
            "progress_events": [
                {
                    "node": "validator",
                    "status": "completed",
                    "payload": {"issue_count": 1, "error_count": 0},
                    "created_at": parsed.session.updated_at.isoformat(),
                }
            ],
        }

    monkeypatch.setattr(workflow, "run_planner_node", counting_planner)
    monkeypatch.setattr(workflow, "run_validator_node", validator_with_warning)

    result = await workflow.run_full_planning_workflow(fixtures.session())

    assert planner_calls == 1
    assert result.validator_issues == [issue]


@pytest.mark.asyncio
async def test_full_workflow_uses_session_hydrated_by_separate_discovery_node() -> None:
    initial = PlanState(session=fixtures.session(with_discovery=False))
    discovered = await run_discovery_node(initial)
    hydrated = validate_graph_state({**graph_input_from_state(initial), **discovered})

    result = await workflow.run_full_planning_workflow(hydrated.session)

    assert result.session_id == "session_test"
    assert result.itinerary.days[0].segments[1].card_ref == "disc_waterfront"
