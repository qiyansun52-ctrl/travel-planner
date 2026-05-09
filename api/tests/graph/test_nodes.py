"""Graph node behavior tests."""

from __future__ import annotations

import pytest

from app.graph.nodes.discovery import compute_enrichment_status, run_discovery_agent
from app.graph.nodes.planner import active_stay_option, run_planner_agent
from app.graph.nodes.stay import run_stay_agent
from app.graph.nodes.transport import run_transport_agent
from app.graph.nodes.validator import run_validator_node
from app.graph.state import PlanState
from app.models.schemas import BudgetBand
from tests.graph import fixtures


def test_compute_enrichment_status_classifies_enrichment_depth() -> None:
    complete = fixtures.discovery_card()
    assert compute_enrichment_status(complete) == "partial"

    complete = complete.model_copy(update={"image_url": "https://example.com/photo.jpg"})
    assert compute_enrichment_status(complete) == "complete"

    minimal = complete.model_copy(update={"place": None})
    assert compute_enrichment_status(minimal) == "minimal"


@pytest.mark.asyncio
async def test_run_discovery_agent_fixture_returns_cards_budget_and_cost_signals() -> None:
    output = await run_discovery_agent(fixtures.session(), fixture_mode=True)

    assert len(output.cards) >= 3
    assert output.budget_estimate.currency == "CNY"
    assert {card.cost_signal for card in output.cards} <= {
        "free",
        "low",
        "medium",
        "high",
        "unknown",
    }
    assert output.cards[0].cost_signal == "free"


@pytest.mark.asyncio
async def test_run_stay_agent_uses_discovery_area_summaries() -> None:
    stay = await run_stay_agent(fixtures.session())

    assert stay.primary.id == "stay_primary"
    assert stay.primary.area.id == "area_central"
    assert stay.alternatives[0].id == "stay_alt_quiet"
    assert stay.alternatives[0].area.id == "area_french_concession"


@pytest.mark.asyncio
async def test_run_transport_agent_respects_preferences() -> None:
    transport = await run_transport_agent(fixtures.session())

    assert transport.arrival.mode == "rail"
    assert transport.departure.mode == "rail"
    assert transport.intracity.primary_mode == "mixed"
    assert transport.intracity.daily_cost_band.low == 40
    assert transport.intracity.daily_cost_band.high == 120


@pytest.mark.asyncio
async def test_run_planner_agent_increments_version_and_builds_days() -> None:
    session = fixtures.session()
    session = session.model_copy(update={"itinerary": fixtures.itinerary(version=2)})
    stay = fixtures.stay_recommendation()
    transport = fixtures.transport_recommendation()

    itinerary = await run_planner_agent(session, stay, transport)

    assert itinerary.version == 3
    assert len(itinerary.days) == session.hard_constraints.duration_days
    assert all(day.segments for day in itinerary.days)


def test_active_stay_option_uses_matching_user_override() -> None:
    stay = fixtures.stay_recommendation()
    alternative = stay.primary.model_copy(update={"id": "stay_alt_value"})
    stay = stay.model_copy(
        update={"alternatives": [alternative], "user_override_id": "stay_alt_value"}
    )

    assert active_stay_option(stay).id == "stay_alt_value"


@pytest.mark.asyncio
async def test_run_validator_node_attaches_issues_to_state_patch_and_itinerary() -> None:
    session = fixtures.session()
    itinerary = fixtures.itinerary(total_high=session.hard_constraints.total_budget * 2)
    state = PlanState(session=session, itinerary=itinerary)

    patch = await run_validator_node(state)

    assert patch["validator_issues"]
    assert patch["itinerary"]["validator_issues"] == patch["validator_issues"]
    assert patch["progress_events"][-1]["node"] == "validator"
    assert patch["progress_events"][-1]["payload"]["issue_count"] == len(
        patch["validator_issues"]
    )


def test_compute_enrichment_status_complete_requires_place_image_and_cost() -> None:
    card = fixtures.discovery_card().model_copy(
        update={
            "image_url": "https://example.com/photo.jpg",
            "cost_estimate": BudgetBand(
                currency="CNY",
                low=10,
                high=20,
                confidence="medium",
                basis="per_person",
            ),
        }
    )

    assert compute_enrichment_status(card) == "complete"
