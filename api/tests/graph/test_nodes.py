"""Graph node behavior tests."""

from __future__ import annotations

import pytest

from app.graph.nodes.discovery import (
    budget_summary,
    compute_enrichment_status,
    run_discovery_agent,
    run_discovery_node,
)
from app.graph.nodes.planner import (
    _route_fits_gap,
    _route_segment,
    active_stay_option,
    run_planner_agent,
    run_planner_node,
)
from app.graph.nodes.stay import run_stay_agent, run_stay_node
from app.graph.nodes.transport import run_transport_agent, run_transport_node
from app.graph.nodes.validator import run_validator_node
from app.graph.state import (
    PlanState,
    append_progress,
    graph_input_from_state,
    validate_graph_state,
)
from app.models.schemas import (
    BudgetBand,
    Coordinate,
    DiscoveryOutput,
    NormalizedRoute,
    NormalizedPlace,
    SourceNote,
)
from app.providers.types import (
    ProviderError,
    PlaceSearchRequest,
    RouteRequest,
    SearchRequest,
    SearchResult,
)
from tests.graph import fixtures


class FakeSearchProvider:
    name = "tavily"

    def __init__(self, results_by_query: dict[str, list[SearchResult]]) -> None:
        self.results_by_query = results_by_query
        self.requests: list[SearchRequest] = []

    async def health(self):
        raise AssertionError("discovery grounding should call search directly")

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        self.requests.append(request)
        return self.results_by_query.get(request.query, [])


class FailingSearchProvider:
    name = "tavily"

    async def health(self):
        raise AssertionError("discovery grounding should call search directly")

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        raise ProviderError(
            provider="tavily",
            kind="search",
            code="network_failure",
            message=f"failed {request.query}",
        )


class FakeMapRegistry:
    def __init__(
        self,
        places_by_query: dict[str, list[NormalizedPlace]],
        *,
        fail: bool = False,
    ) -> None:
        self.places_by_query = places_by_query
        self.fail = fail
        self.requests: list[PlaceSearchRequest] = []

    async def search_places(self, request: PlaceSearchRequest) -> list[NormalizedPlace]:
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("map search failed")
        return self.places_by_query.get(request.query, [])


class FakeRouteRegistry:
    def __init__(
        self,
        duration_minutes: float = 18,
        distance_meters: float = 1400,
    ) -> None:
        self.duration_minutes = duration_minutes
        self.distance_meters = distance_meters
        self.requests: list[tuple[str, RouteRequest]] = []

    async def route(self, country_code: str, request: RouteRequest) -> NormalizedRoute:
        self.requests.append((country_code, request))
        return NormalizedRoute(
            from_=request.from_,
            to=request.to,
            mode=request.mode,
            duration_minutes=self.duration_minutes,
            distance_meters=self.distance_meters,
            cost_estimate=None,
            provider="amap",
        )


class FailingRouteRegistry:
    async def route(self, country_code: str, request: RouteRequest) -> NormalizedRoute:
        raise ConnectionError("route unavailable")


class BuggyRouteRegistry:
    async def route(self, country_code: str, request: RouteRequest) -> NormalizedRoute:
        raise TypeError("bad fake")


def search_result(title: str, url: str, snippet: str) -> SearchResult:
    return SearchResult(
        title=title,
        url=url,
        snippet=snippet,
        source_note=SourceNote(provider="tavily", url=url, note="Tavily search result"),
    )


def map_place(
    place_id: str = "amap:bund",
    name: str = "The Bund",
) -> NormalizedPlace:
    return NormalizedPlace(
        id=place_id,
        name=name,
        coordinate=Coordinate(lat=31.2403, lng=121.4906),
        address="Zhongshan East 1st Road",
        category="scenic_area",
        provider="amap",
    )


def test_compute_enrichment_status_classifies_enrichment_depth() -> None:
    complete = fixtures.discovery_card()
    assert compute_enrichment_status(complete) == "partial"

    complete = complete.model_copy(
        update={"image_url": "https://example.com/photo.jpg"}
    )
    assert compute_enrichment_status(complete) == "complete"

    minimal = complete.model_copy(update={"place": None})
    assert compute_enrichment_status(minimal) == "minimal"


@pytest.mark.asyncio
async def test_run_discovery_agent_fixture_returns_cards_budget_and_cost_signals() -> (
    None
):
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
    assert patch["session"]["discovery_state"]["payload"] == patch["discovery_output"]
    cards = patch["discovery_output"]["cards"]
    assert patch["progress_events"][-1]["node"] == "discovery"
    assert patch["progress_events"][-1]["payload"]["card_count"] == len(cards)
    assert patch["progress_events"][-1]["payload"]["agent"]["stage"] == "discovery"
    assert patch["progress_events"][-1]["payload"]["quality"]["min_cards_met"] is True


@pytest.mark.asyncio
async def test_run_discovery_node_session_patch_feeds_downstream_state() -> None:
    state = PlanState(session=fixtures.session(with_discovery=False), fixture_mode=True)
    raw = graph_input_from_state(state)

    patch = await run_discovery_node(state)
    restored = validate_graph_state({**raw, **patch})

    assert restored.session.discovery_state is not None
    assert restored.session.discovery_state.payload is not None
    assert len(restored.session.discovery_state.payload.cards) == len(
        patch["discovery_output"]["cards"]
    )


@pytest.mark.asyncio
async def test_run_discovery_agent_uses_fixture_when_keys_missing(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    output = await run_discovery_agent(fixtures.session(), fixture_mode=False)

    assert len(output.cards) == 6
    assert output.source_notes[0].provider == "fixture"


@pytest.mark.asyncio
async def test_run_discovery_agent_live_path_calls_llm_and_normalizes(
    monkeypatch,
) -> None:
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
    assert output.cards[0].image_url is None
    assert output.cards[0].enrichment_status == "partial"


@pytest.mark.asyncio
async def test_run_discovery_agent_adds_tavily_grounding_to_prompt_and_sources(
    monkeypatch,
) -> None:
    recorded = {}
    output_from_llm = fixtures.discovery_output().model_copy(
        update={
            "source_notes": [
                SourceNote(provider="gemini", url=None, note="Generated from prompt")
            ]
        }
    )
    provider = FakeSearchProvider(
        {
            "上海 必去景点 旅游体验 攻略 2025": [
                search_result(
                    "Shanghai waterfront guide",
                    "https://example.com/bund-guide",
                    "The Bund is a classic first-time visitor anchor.",
                )
            ],
            "上海 交通攻略 怎么去 市内出行 交通方式": [
                search_result(
                    "Shanghai metro guide",
                    "https://example.com/metro-guide",
                    "Metro is usually the easiest way to cross the city.",
                )
            ],
            "上海 美食推荐 必吃 餐厅 小吃 2025": [
                search_result(
                    "Shanghai food guide",
                    "https://example.com/food-guide",
                    "Xiaolongbao and shengjianbao are common local highlights.",
                )
            ],
        }
    )

    async def fake_generate_structured(**kwargs):
        recorded.update(kwargs)
        return output_from_llm

    monkeypatch.setenv("LLM_PROVIDER_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.graph.nodes.discovery.generate_structured",
        fake_generate_structured,
    )

    result = await run_discovery_agent(
        fixtures.session(),
        search_provider=provider,
    )

    assert len(provider.requests) == 3
    assert "Search grounding from Tavily" in recorded["user"]
    assert "Shanghai waterfront guide" in recorded["user"]
    assert "Shanghai metro guide" in recorded["user"]
    assert "Shanghai food guide" in recorded["user"]
    assert any(note.provider == "tavily" for note in result.source_notes)


@pytest.mark.asyncio
async def test_run_discovery_agent_continues_when_tavily_grounding_fails(
    monkeypatch,
) -> None:
    recorded = {}

    async def fake_generate_structured(**kwargs):
        recorded.update(kwargs)
        return fixtures.discovery_output()

    monkeypatch.setenv("LLM_PROVIDER_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.graph.nodes.discovery.generate_structured",
        fake_generate_structured,
    )

    result = await run_discovery_agent(
        fixtures.session(),
        search_provider=FailingSearchProvider(),
    )

    assert result.cards
    assert "Search grounding unavailable" in recorded["user"]


@pytest.mark.asyncio
async def test_run_discovery_agent_removes_placeholder_image_urls(monkeypatch) -> None:
    card = fixtures.discovery_card().model_copy(
        update={"image_url": "https://example.com/not-a-real-image.jpg"}
    )

    async def fake_generate_structured(**_: object):
        return fixtures.discovery_output().model_copy(update={"cards": [card]})

    monkeypatch.setenv("LLM_PROVIDER_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.graph.nodes.discovery.generate_structured",
        fake_generate_structured,
    )

    result = await run_discovery_agent(fixtures.session(), search_provider=None)

    assert result.cards[0].image_url is None
    assert result.cards[0].enrichment_status == "partial"


@pytest.mark.asyncio
async def test_run_discovery_agent_enriches_card_places_with_map_registry(
    monkeypatch,
) -> None:
    recorded = {}
    card = fixtures.discovery_card().model_copy(
        update={
            "name": "The Bund waterfront walk",
            "place": None,
            "image_url": None,
            "enrichment_status": "minimal",
        }
    )
    output_from_llm = fixtures.discovery_output().model_copy(update={"cards": [card]})
    registry = FakeMapRegistry({"上海 The Bund waterfront walk": [map_place()]})

    async def fake_generate_structured(**kwargs):
        recorded.update(kwargs)
        return output_from_llm

    monkeypatch.setenv("LLM_PROVIDER_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.graph.nodes.discovery.generate_structured",
        fake_generate_structured,
    )

    result = await run_discovery_agent(
        fixtures.session(),
        map_registry=registry,
        search_provider=None,
    )

    assert recorded["label"] == "discovery_agent"
    assert len(registry.requests) == 1
    assert registry.requests[0].query == "上海 The Bund waterfront walk"
    assert registry.requests[0].country_code == "CN"
    assert registry.requests[0].limit == 3
    assert registry.requests[0].category == "sightseeing"
    assert result.cards[0].place == map_place()
    assert result.cards[0].enrichment_status == "partial"


@pytest.mark.asyncio
async def test_run_discovery_agent_rejects_generic_map_place_match(
    monkeypatch,
) -> None:
    original_place = fixtures.place("model_oriental_pearl", "Oriental Pearl Tower")
    card = fixtures.discovery_card().model_copy(
        update={
            "name": "Oriental Pearl Tower",
            "place": original_place,
            "image_url": None,
            "enrichment_status": "partial",
        }
    )
    city_place = map_place("mapbox:shanghai", "Shanghai")
    output_from_llm = fixtures.discovery_output().model_copy(update={"cards": [card]})
    registry = FakeMapRegistry({"上海 Oriental Pearl Tower": [city_place]})

    async def fake_generate_structured(**_: object):
        return output_from_llm

    monkeypatch.setenv("LLM_PROVIDER_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.graph.nodes.discovery.generate_structured",
        fake_generate_structured,
    )

    result = await run_discovery_agent(
        fixtures.session(),
        map_registry=registry,
        search_provider=None,
    )

    assert result.cards[0].place == original_place


@pytest.mark.asyncio
async def test_run_discovery_agent_uses_later_matching_map_candidate(
    monkeypatch,
) -> None:
    card = fixtures.discovery_card().model_copy(
        update={
            "name": "Oriental Pearl Tower",
            "place": None,
            "image_url": None,
            "enrichment_status": "minimal",
        }
    )
    city_place = map_place("mapbox:shanghai", "Shanghai")
    tower_place = map_place("mapbox:oriental-pearl", "Oriental Pearl Tower")
    output_from_llm = fixtures.discovery_output().model_copy(update={"cards": [card]})
    registry = FakeMapRegistry({"上海 Oriental Pearl Tower": [city_place, tower_place]})

    async def fake_generate_structured(**_: object):
        return output_from_llm

    monkeypatch.setenv("LLM_PROVIDER_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.graph.nodes.discovery.generate_structured",
        fake_generate_structured,
    )

    result = await run_discovery_agent(
        fixtures.session(),
        map_registry=registry,
        search_provider=None,
    )

    assert result.cards[0].place == tower_place


@pytest.mark.asyncio
async def test_run_discovery_agent_keeps_existing_place_when_map_enrichment_fails(
    monkeypatch,
) -> None:
    card = fixtures.discovery_card().model_copy(
        update={"place": fixtures.place("model_place", "Model place")}
    )

    async def fake_generate_structured(**_: object):
        return fixtures.discovery_output().model_copy(update={"cards": [card]})

    monkeypatch.setenv("LLM_PROVIDER_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.graph.nodes.discovery.generate_structured",
        fake_generate_structured,
    )

    result = await run_discovery_agent(
        fixtures.session(),
        map_registry=FakeMapRegistry({}, fail=True),
        search_provider=None,
    )

    assert result.cards[0].place == fixtures.place("model_place", "Model place")
    assert result.cards[0].enrichment_status == "partial"


@pytest.mark.asyncio
async def test_run_stay_agent_uses_discovery_area_summaries() -> None:
    stay = await run_stay_agent(fixtures.session())

    assert stay.primary.id == "stay_primary"
    assert stay.primary.area.id == "area_central"
    assert stay.alternatives[0].id == "stay_alt_quiet"
    assert stay.alternatives[0].area.id == "area_french_concession"


@pytest.mark.asyncio
async def test_run_stay_agent_fallback_areas_and_override_preservation() -> None:
    existing = fixtures.stay_recommendation().model_copy(
        update={"user_override_id": "stay_alt_value"}
    )
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
    assert patch["progress_events"][-1]["payload"]["agent"]["stage"] == "stay"


@pytest.mark.asyncio
async def test_node_patch_returns_only_new_progress_event() -> None:
    state = append_progress(
        PlanState(session=fixtures.session()), "discovery", "completed"
    )

    patch = await run_stay_node(state)

    assert len(patch["progress_events"]) == 1
    assert patch["progress_events"][0]["node"] == "stay"


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
    assert patch["progress_events"][-1]["payload"]["agent"]["stage"] == "transport"


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
async def test_run_planner_agent_converts_budget_bands_to_per_trip() -> None:
    itinerary = await run_planner_agent(
        fixtures.session(),
        fixtures.stay_recommendation(),
        fixtures.transport_recommendation(),
    )

    assert itinerary.budget.transport.high == 480
    assert itinerary.budget.stay.high == 2100


@pytest.mark.asyncio
async def test_run_planner_agent_falls_back_to_first_three_cards_when_none_selected() -> (
    None
):
    session = fixtures.session()
    discovery_state = session.discovery_state.model_copy(
        update={"selected_card_ids": []}
    )
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
async def test_run_planner_agent_prefers_selected_cards() -> None:
    itinerary = await run_planner_agent(
        fixtures.session(),
        fixtures.stay_recommendation(),
        fixtures.transport_recommendation(),
    )

    card_refs = [
        segment.card_ref
        for day in itinerary.days
        for segment in day.segments
        if segment.card_ref
    ]
    assert set(card_refs) == {"disc_waterfront"}
    assert "disc_museum" not in card_refs
    assert "disc_garden" not in card_refs


@pytest.mark.asyncio
async def test_run_planner_agent_builds_required_segment_types() -> None:
    itinerary = await run_planner_agent(
        fixtures.session(),
        fixtures.stay_recommendation(),
        fixtures.transport_recommendation(),
    )

    segment_types = {segment.type for segment in itinerary.days[0].segments}
    assert {
        "hotel_checkin",
        "attraction",
        "food",
        "rest",
        "hotel_return",
    } <= segment_types


@pytest.mark.asyncio
async def test_run_planner_agent_does_not_use_default_registry_without_opt_in(
    monkeypatch,
) -> None:
    def fail_default_registry():
        raise AssertionError("default route registry should not be created")

    monkeypatch.setenv("AMAP_MCP_URL", "https://example.test/mcp")
    monkeypatch.setattr(
        "app.graph.nodes.planner.create_default_provider_registry",
        fail_default_registry,
    )

    itinerary = await run_planner_agent(
        fixtures.session(),
        fixtures.stay_recommendation(),
        fixtures.transport_recommendation(),
    )

    assert all(
        segment.type != "transit" for day in itinerary.days for segment in day.segments
    )


@pytest.mark.asyncio
async def test_run_planner_agent_adds_route_transit_segments_when_registry_available() -> (
    None
):
    registry = FakeRouteRegistry()

    itinerary = await run_planner_agent(
        fixtures.session(),
        fixtures.stay_recommendation(),
        fixtures.transport_recommendation(),
        map_registry=registry,
    )

    transit_segments = [
        segment
        for day in itinerary.days
        for segment in day.segments
        if segment.type == "transit"
    ]
    assert transit_segments
    assert transit_segments[0].description == "Estimated walk: 18 min, 1.4 km."
    assert registry.requests[0][0] == "CN"
    assert registry.requests[0][1].mode == "walk"


@pytest.mark.asyncio
async def test_run_planner_agent_skips_route_transit_when_duration_exceeds_gap() -> (
    None
):
    itinerary = await run_planner_agent(
        fixtures.session(),
        fixtures.stay_recommendation(),
        fixtures.transport_recommendation(),
        map_registry=FakeRouteRegistry(duration_minutes=45),
    )

    assert all(
        segment.type != "transit" for day in itinerary.days for segment in day.segments
    )


def test_route_gap_fit_accounts_for_minimum_rendered_duration() -> None:
    route = NormalizedRoute(
        from_=fixtures.place("origin"),
        to=fixtures.place("destination"),
        mode="walk",
        duration_minutes=4,
        distance_meters=200,
        cost_estimate=None,
        provider="amap",
    )

    assert _route_fits_gap(route, "09:30", "09:34") is False
    assert _route_fits_gap(route, "09:30", "09:35") is True
    assert _route_segment("09:30", route).end_time == "09:35"


@pytest.mark.asyncio
async def test_run_planner_agent_keeps_itinerary_when_route_enrichment_fails() -> None:
    itinerary = await run_planner_agent(
        fixtures.session(),
        fixtures.stay_recommendation(),
        fixtures.transport_recommendation(),
        map_registry=FailingRouteRegistry(),
    )

    assert all(
        segment.type != "transit" for day in itinerary.days for segment in day.segments
    )


@pytest.mark.asyncio
async def test_run_planner_agent_does_not_swallow_programmer_errors() -> None:
    with pytest.raises(TypeError, match="bad fake"):
        await run_planner_agent(
            fixtures.session(),
            fixtures.stay_recommendation(),
            fixtures.transport_recommendation(),
            map_registry=BuggyRouteRegistry(),
        )


@pytest.mark.asyncio
async def test_run_planner_agent_adds_corrective_note_for_validator_context() -> None:
    itinerary = await run_planner_agent(
        fixtures.session(),
        fixtures.stay_recommendation(),
        fixtures.transport_recommendation(),
        [fixtures.validator_error()],
    )

    assert (
        "Corrective pass used validator errors as planning context."
        in itinerary.days[0].notes
    )


@pytest.mark.asyncio
async def test_run_planner_agent_carries_reservation_hints_into_day_notes() -> None:
    session = fixtures.session()
    museum = fixtures.discovery_card(
        "disc_museum",
        "上海 museum afternoon",
    ).model_copy(update={"reservation_hint": "Reserve a timed entry before weekends."})
    discovery = fixtures.discovery_output().model_copy(update={"cards": [museum]})
    session = session.model_copy(
        update={
            "discovery_state": session.discovery_state.model_copy(
                update={"payload": discovery, "selected_card_ids": [museum.id]}
            )
        }
    )

    itinerary = await run_planner_agent(
        session,
        fixtures.stay_recommendation(),
        fixtures.transport_recommendation(),
    )

    assert (
        "Reservation check: 上海 museum afternoon - Reserve a timed entry before weekends."
        in itinerary.days[0].notes
    )


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
    assert (
        patch["progress_events"][-1]["payload"]["version"]
        == patch["itinerary"]["version"]
    )
    assert patch["progress_events"][-1]["payload"]["agent"]["stage"] == "planner"
    assert patch["progress_events"][-1]["payload"]["quality"]["day_count"] == 3


@pytest.mark.asyncio
async def test_run_planner_node_fixture_mode_does_not_use_default_registry(
    monkeypatch,
) -> None:
    def fail_default_registry():
        raise AssertionError("default route registry should not be created")

    monkeypatch.setenv("AMAP_MCP_URL", "https://example.test/mcp")
    monkeypatch.setattr(
        "app.graph.nodes.planner.create_default_provider_registry",
        fail_default_registry,
    )
    state = PlanState(
        session=fixtures.session(),
        fixture_mode=True,
        stay_recommendation=fixtures.stay_recommendation(),
        transport_recommendation=fixtures.transport_recommendation(),
    )

    patch = await run_planner_node(state)

    assert all(
        segment["type"] != "transit"
        for day in patch["itinerary"]["days"]
        for segment in day["segments"]
    )


@pytest.mark.asyncio
async def test_run_planner_node_requires_stay_recommendation() -> None:
    state = PlanState(
        session=fixtures.session(),
        transport_recommendation=fixtures.transport_recommendation(),
    )

    with pytest.raises(
        ValueError, match="run_planner_node requires stay_recommendation"
    ):
        await run_planner_node(state)


@pytest.mark.asyncio
async def test_run_planner_node_requires_transport_recommendation() -> None:
    state = PlanState(
        session=fixtures.session(),
        stay_recommendation=fixtures.stay_recommendation(),
    )

    with pytest.raises(
        ValueError, match="run_planner_node requires transport_recommendation"
    ):
        await run_planner_node(state)


def test_active_stay_option_uses_matching_user_override() -> None:
    stay = fixtures.stay_recommendation()
    alternative = stay.primary.model_copy(update={"id": "stay_alt_value"})
    stay = stay.model_copy(
        update={"alternatives": [alternative], "user_override_id": "stay_alt_value"}
    )

    assert active_stay_option(stay).id == "stay_alt_value"


@pytest.mark.asyncio
async def test_run_validator_node_attaches_issues_to_state_patch_and_itinerary() -> (
    None
):
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
    assert patch["progress_events"][-1]["payload"]["agent"]["stage"] == "validator"
    assert patch["progress_events"][-1]["payload"]["quality"]["issue_count"] == len(
        patch["validator_issues"]
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


def test_budget_summary_overrun_uses_validator_threshold() -> None:
    summary = budget_summary(
        "CNY",
        1000,
        transport=fixtures.band(100, 200),
        stay=fixtures.band(100, 500),
        food=fixtures.band(50, 150),
        attractions=fixtures.band(25, 150),
        other=fixtures.band(25, 150),
    )
    over_threshold = summary.model_copy(
        update={"total": summary.total.model_copy(update={"high": 1151})}
    )
    overrun_summary = budget_summary(
        "CNY",
        1000,
        transport=fixtures.band(100, 201),
        stay=fixtures.band(100, 500),
        food=fixtures.band(50, 150),
        attractions=fixtures.band(25, 150),
        other=fixtures.band(25, 150),
    )

    assert summary.total.high == 1150
    assert summary.overrun_flag is False
    assert over_threshold.total.high > summary.user_budget * 1.15
    assert overrun_summary.total.high == 1151
    assert overrun_summary.overrun_flag is True
