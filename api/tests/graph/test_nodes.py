"""Graph node behavior tests."""

from __future__ import annotations

import pytest

from app.graph.nodes.discovery import (
    compute_enrichment_status,
    run_discovery_agent,
    run_discovery_node,
)
from app.graph.nodes.planner import (
    active_stay_option,
    run_planner_agent,
    run_planner_node,
)
from app.graph.nodes.stay import run_stay_agent, run_stay_node
from app.graph.nodes.transport import run_transport_agent, run_transport_node
from app.graph.nodes.validator import run_validator_node
from app.graph.state import PlanState
from app.models.schemas import BudgetBand, DiscoveryOutput
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
async def test_run_discovery_node_returns_patch_and_progress() -> None:
    state = PlanState(session=fixtures.session(with_discovery=False), fixture_mode=True)

    patch = await run_discovery_node(state)

    assert patch["discovery_output"]
    cards = patch["discovery_output"]["cards"]
    assert patch["progress_events"][-1]["node"] == "discovery"
    assert patch["progress_events"][-1]["payload"]["card_count"] == len(cards)


@pytest.mark.asyncio
async def test_run_discovery_agent_uses_fixture_when_keys_missing(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    output = await run_discovery_agent(fixtures.session(), fixture_mode=False)

    assert len(output.cards) == 6
    assert output.source_notes[0].provider == "fixture"


@pytest.mark.asyncio
async def test_run_discovery_agent_live_path_calls_llm_and_normalizes(monkeypatch) -> None:
    recorded = {}
    card = fixtures.discovery_card().model_copy(
        update={
            "cost_signal": "high",
            "enrichment_status": "minimal",
            "image_url": "https://example.com/photo.jpg",
            "cost_estimate": fixtures.band(0, 0, "per_person"),
        }
    )
    llm_output = fixtures.discovery_output().model_copy(update={"cards": [card]})
    provider = object()

    async def fake_generate_structured(**kwargs):
        recorded.update(kwargs)
        return llm_output

    monkeypatch.setenv("LLM_PROVIDER_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.graph.nodes.discovery.generate_structured",
        fake_generate_structured,
    )

    output = await run_discovery_agent(
        fixtures.session(),
        llm_provider=provider,
        cost_logger=None,
    )

    assert recorded["schema"] is DiscoveryOutput
    assert recorded["label"] == "discovery_agent"
    assert recorded["provider"] is provider
    assert "travel discovery agent" in recorded["system"]
    assert "上海" in recorded["user"]
    assert output.cards[0].cost_signal == "free"
    assert output.cards[0].enrichment_status == "complete"


@pytest.mark.asyncio
async def test_run_stay_agent_uses_discovery_area_summaries() -> None:
    stay = await run_stay_agent(fixtures.session())

    assert stay.primary.id == "stay_primary"
    assert stay.primary.area.id == "area_central"
    assert stay.alternatives[0].id == "stay_alt_quiet"
    assert stay.alternatives[0].area.id == "area_french_concession"


@pytest.mark.asyncio
async def test_run_stay_agent_fallback_areas_and_override_preservation() -> None:
    existing = fixtures.stay_recommendation().model_copy(update={"user_override_id": "stay_alt_value"})
    session = fixtures.session(with_discovery=False).model_copy(
        update={"stay_recommendation": existing}
    )

    stay = await run_stay_agent(session)

    assert stay.primary.area.id == "area_central"
    assert stay.alternatives[0].area.id == "area_quiet"
    assert stay.user_override_id == "stay_alt_value"


@pytest.mark.asyncio
async def test_run_stay_node_returns_patch_and_progress() -> None:
    patch = await run_stay_node(PlanState(session=fixtures.session()))

    assert patch["stay_recommendation"]
    assert patch["progress_events"][-1]["node"] == "stay"
    assert patch["progress_events"][-1]["payload"]["primary_area"] == "area_central"


@pytest.mark.asyncio
async def test_run_transport_agent_respects_preferences() -> None:
    transport = await run_transport_agent(fixtures.session())

    assert transport.arrival.mode == "rail"
    assert transport.departure.mode == "rail"
    assert transport.intracity.primary_mode == "mixed"
    assert transport.intracity.daily_cost_band.low == 40
    assert transport.intracity.daily_cost_band.high == 120


@pytest.mark.asyncio
async def test_run_transport_agent_respects_flight_preference() -> None:
    session = fixtures.session()
    session = session.model_copy(
        update={
            "preferences": session.preferences.model_copy(
                update={"intercity_transport_preference": "flight"}
            )
        }
    )

    transport = await run_transport_agent(session)

    assert transport.arrival.mode == "flight"
    assert transport.departure.mode == "flight"


@pytest.mark.asyncio
async def test_run_transport_node_returns_patch_and_progress() -> None:
    patch = await run_transport_node(PlanState(session=fixtures.session()))

    assert patch["transport_recommendation"]
    assert patch["progress_events"][-1]["node"] == "transport"
    assert patch["progress_events"][-1]["payload"]["arrival_mode"] == "rail"


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


@pytest.mark.asyncio
async def test_run_planner_agent_falls_back_to_first_three_cards_when_none_selected() -> None:
    session = fixtures.session()
    discovery_state = session.discovery_state.model_copy(update={"selected_card_ids": []})
    session = session.model_copy(update={"discovery_state": discovery_state})

    itinerary = await run_planner_agent(
        session,
        fixtures.stay_recommendation(),
        fixtures.transport_recommendation(),
    )

    card_refs = [
        segment.card_ref
        for day in itinerary.days
        for segment in day.segments
        if segment.card_ref
    ]
    assert card_refs == ["disc_waterfront", "disc_museum", "disc_garden"]


@pytest.mark.asyncio
async def test_run_planner_agent_builds_required_segment_types() -> None:
    itinerary = await run_planner_agent(
        fixtures.session(),
        fixtures.stay_recommendation(),
        fixtures.transport_recommendation(),
    )

    segment_types = {segment.type for segment in itinerary.days[0].segments}
    assert {"hotel_checkin", "attraction", "food", "rest", "hotel_return"} <= segment_types


@pytest.mark.asyncio
async def test_run_planner_agent_adds_corrective_note_for_validator_context() -> None:
    itinerary = await run_planner_agent(
        fixtures.session(),
        fixtures.stay_recommendation(),
        fixtures.transport_recommendation(),
        [fixtures.validator_error()],
    )

    assert "Corrective pass used validator errors as planning context." in itinerary.days[0].notes


@pytest.mark.asyncio
async def test_run_planner_node_returns_patch_and_progress() -> None:
    state = PlanState(
        session=fixtures.session(),
        stay_recommendation=fixtures.stay_recommendation(),
        transport_recommendation=fixtures.transport_recommendation(),
    )

    patch = await run_planner_node(state)

    assert patch["itinerary"]
    assert patch["progress_events"][-1]["node"] == "planner"
    assert patch["progress_events"][-1]["payload"]["version"] == patch["itinerary"]["version"]


@pytest.mark.asyncio
async def test_run_planner_node_requires_stay_recommendation() -> None:
    state = PlanState(
        session=fixtures.session(),
        transport_recommendation=fixtures.transport_recommendation(),
    )

    with pytest.raises(ValueError, match="run_planner_node requires stay_recommendation"):
        await run_planner_node(state)


@pytest.mark.asyncio
async def test_run_planner_node_requires_transport_recommendation() -> None:
    state = PlanState(
        session=fixtures.session(),
        stay_recommendation=fixtures.stay_recommendation(),
    )

    with pytest.raises(ValueError, match="run_planner_node requires transport_recommendation"):
        await run_planner_node(state)


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
    assert patch["progress_events"][-1]["payload"]["error_count"] == len(
        [issue for issue in patch["validator_issues"] if issue["severity"] == "error"]
    )


@pytest.mark.asyncio
async def test_run_validator_node_requires_state_itinerary() -> None:
    session = fixtures.session().model_copy(update={"itinerary": fixtures.itinerary()})
    state = PlanState(session=session)

    with pytest.raises(ValueError, match="run_validator_node requires itinerary"):
        await run_validator_node(state)


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
