"""Planning workflow behavior tests."""

from __future__ import annotations

import pytest

from app.graph import workflow
from app.graph.nodes.discovery import run_discovery_node
from app.graph.nodes import planner as planner_node
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
async def test_full_workflow_fixture_mode_does_not_create_default_map_registry(
    monkeypatch,
) -> None:
    def fail_default_registry():
        raise AssertionError("default map registry should not be created")

    monkeypatch.setenv("AMAP_MCP_URL", "https://example.test/mcp")
    monkeypatch.setattr(
        planner_node,
        "create_default_provider_registry",
        fail_default_registry,
    )

    result = await workflow.run_full_planning_workflow(
        fixtures.session(),
        fixture_mode=True,
    )

    assert all(
        segment.type != "transit"
        for day in result.itinerary.days
        for segment in day.segments
    )


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
async def test_corrective_pass_sends_only_errors_to_planner(monkeypatch) -> None:
    planner_issue_contexts = []
    original_planner = workflow.run_planner_node
    error = fixtures.validator_error()
    warning = fixtures.validator_error().model_copy(
        update={
            "code": "long_walk",
            "severity": "warning",
            "message": "Day has a long walking segment.",
            "suggested_action": "Consider adding a rest stop.",
        }
    )

    async def recording_planner(state):
        parsed = validate_graph_state(state)
        planner_issue_contexts.append(parsed.validator_issues)
        return await original_planner(state)

    async def validator_with_mixed_issues(state):
        parsed = validate_graph_state(state)
        issues = [warning, error]
        itinerary = parsed.itinerary.model_copy(update={"validator_issues": issues})
        return {
            "validator_issues": [issue.model_dump(mode="json") for issue in issues],
            "itinerary": itinerary.model_dump(mode="json"),
            "progress_events": [
                {
                    "node": "validator",
                    "status": "completed",
                    "payload": {"issue_count": 2, "error_count": 1},
                    "created_at": parsed.session.updated_at.isoformat(),
                }
            ],
        }

    monkeypatch.setattr(workflow, "run_planner_node", recording_planner)
    monkeypatch.setattr(workflow, "run_validator_node", validator_with_mixed_issues)

    result = await workflow.run_full_planning_workflow(fixtures.session())

    assert planner_issue_contexts == [[], [error]]
    assert result.validator_issues == [warning, error]


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
    initial = PlanState(session=fixtures.session(with_discovery=False), fixture_mode=True)
    discovered = await run_discovery_node(initial)
    hydrated = validate_graph_state({**graph_input_from_state(initial), **discovered})

    result = await workflow.run_full_planning_workflow(hydrated.session)

    assert result.session_id == "session_test"
    assert result.itinerary.days[0].segments[1].card_ref == "disc_waterfront"
