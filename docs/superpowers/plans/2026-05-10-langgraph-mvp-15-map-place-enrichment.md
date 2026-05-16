# Map Place Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make real discovery cards use AMap/Mapbox-backed place resolution when map provider keys are configured, while preserving deterministic fixture mode and graceful fallback when maps are unavailable.

**Architecture:** Keep provider adapters and registry as the single map access layer. The discovery agent still asks Gemini for card ideas, then performs a bounded `search_places` lookup per card through the map registry, replacing model-invented or missing `card.place` values only when a real normalized provider result is available.

**Tech Stack:** FastAPI backend, Pydantic v2 models, existing provider registry, AMap/Mapbox adapters, pytest, existing `make regression` gate.

---

## File Map

- Modify `api/app/graph/nodes/discovery.py`: add optional map registry injection, default map registry creation, safe place search, card place replacement, and enrichment-status recomputation.
- Modify `api/tests/graph/test_nodes.py`: add fake map registry tests for successful place enrichment and graceful fallback.
- Modify `docs/2026-05-10-real-mvp-work-summary.md`: update agent/product status after Plan15 verification.
- Create this plan at `docs/superpowers/plans/2026-05-10-langgraph-mvp-15-map-place-enrichment.md`.

---

### Task 1: Add Failing Map Enrichment Tests

**Files:**
- Modify: `api/tests/graph/test_nodes.py`

- [x] **Step 1: Add imports for map enrichment fixtures**

Add these imports near the current provider imports:

```python
from app.models.schemas import Coordinate, NormalizedPlace
from app.providers.types import PlaceSearchRequest
```

- [x] **Step 2: Add fake map registry helpers**

Add these helpers near the existing fake providers:

```python
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


def map_place(
    place_id: str = "amap:bund",
    name: str = "The Bund",
    *,
    provider: str = "amap",
) -> NormalizedPlace:
    return NormalizedPlace(
        id=place_id,
        name=name,
        coordinate=Coordinate(lat=31.2403, lng=121.4906),
        address="Zhongshan East 1st Road",
        category="scenic_area",
        provider=provider,
    )
```

- [x] **Step 3: Add test that map enrichment replaces missing/model places**

Add this test near the discovery-agent tests:

```python
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
    registry = FakeMapRegistry(
        {"上海 The Bund waterfront walk": [map_place()]}
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
        map_registry=registry,
        search_provider=None,
    )

    assert recorded["label"] == "discovery_agent"
    assert len(registry.requests) == 1
    assert registry.requests[0].query == "上海 The Bund waterfront walk"
    assert registry.requests[0].country_code == "CN"
    assert registry.requests[0].limit == 1
    assert registry.requests[0].category == "sightseeing"
    assert result.cards[0].place == map_place()
    assert result.cards[0].enrichment_status == "partial"
```

- [x] **Step 4: Add test that map failures keep the LLM place and continue**

Add this test:

```python
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
```

- [x] **Step 5: Run tests to verify failure**

Run:

```bash
cd api
uv run pytest tests/graph/test_nodes.py::test_run_discovery_agent_enriches_card_places_with_map_registry tests/graph/test_nodes.py::test_run_discovery_agent_keeps_existing_place_when_map_enrichment_fails -q
```

Expected: FAIL because `run_discovery_agent` does not accept `map_registry` and does not enrich places yet.

---

### Task 2: Implement Map Place Enrichment

**Files:**
- Modify: `api/app/graph/nodes/discovery.py`

- [x] **Step 1: Add imports**

Add these imports near the provider imports:

```python
from app.providers.registry import TravelDataProviderRegistry, create_default_provider_registry
from app.providers.types import PlaceSearchRequest
```

- [x] **Step 2: Add optional `map_registry` parameter**

Change the `run_discovery_agent` signature:

```python
async def run_discovery_agent(
    session: PlanningSession,
    *,
    fixture_mode: bool = False,
    llm_provider: LLMProvider | None = None,
    search_provider: SearchProvider | None = None,
    map_registry: TravelDataProviderRegistry | None = None,
    cost_logger: LLMCostLogger | None = None,
) -> DiscoveryOutput:
```

- [x] **Step 3: Enrich cards before normalization**

Replace the current returned card normalization with:

```python
    enriched_cards = await _enrich_card_places(output.cards, session, map_registry)
    return output.model_copy(
        update={
            "cards": [_normalize_discovery_card(card, session) for card in enriched_cards],
            "source_notes": _merge_source_notes(
                _source_notes_from_search_results(search_results),
                output.source_notes,
            ),
        }
    )
```

- [x] **Step 4: Add map enrichment helpers**

Add these helpers below the search-grounding helpers:

```python
async def _enrich_card_places(
    cards: list[DiscoveryCard],
    session: PlanningSession,
    map_registry: TravelDataProviderRegistry | None,
) -> list[DiscoveryCard]:
    registry = map_registry or _default_map_registry()
    if registry is None:
        return cards

    enriched = await asyncio.gather(
        *[_safe_enrich_card_place(card, session, registry) for card in cards],
        return_exceptions=False,
    )
    return enriched


async def _safe_enrich_card_place(
    card: DiscoveryCard,
    session: PlanningSession,
    registry: TravelDataProviderRegistry,
) -> DiscoveryCard:
    query = _place_search_query(card, session)
    request = PlaceSearchRequest(
        query=query,
        country_code=session.hard_constraints.destination_country_code,
        limit=1,
        category=card.category,
    )
    try:
        places = await registry.search_places(request)
    except Exception:
        return card
    if not places:
        return card
    return card.model_copy(update={"place": places[0]})


def _place_search_query(card: DiscoveryCard, session: PlanningSession) -> str:
    return f"{session.hard_constraints.destination_city} {card.name}".strip()


def _default_map_registry() -> TravelDataProviderRegistry | None:
    if not _has_map_provider_key():
        return None
    return create_default_provider_registry()


def _has_map_provider_key() -> bool:
    return bool(os.environ.get("AMAP_API_KEY") or os.environ.get("MAPBOX_ACCESS_TOKEN"))
```

- [x] **Step 5: Run task tests**

Run:

```bash
cd api
uv run pytest tests/graph/test_nodes.py::test_run_discovery_agent_enriches_card_places_with_map_registry tests/graph/test_nodes.py::test_run_discovery_agent_keeps_existing_place_when_map_enrichment_fails -q
```

Expected: PASS.

---

### Task 3: Verify, Document, and Commit

**Files:**
- Modify: `docs/2026-05-10-real-mvp-work-summary.md`
- Modify: `docs/superpowers/plans/2026-05-10-langgraph-mvp-15-map-place-enrichment.md`

- [x] **Step 1: Run targeted graph/provider tests**

Run:

```bash
cd api
uv run pytest tests/graph/test_nodes.py tests/providers/test_registry.py tests/providers/test_amap.py tests/providers/test_mapbox.py -q
```

Expected: PASS.

- [x] **Step 2: Run full regression**

Run:

```bash
make regression
```

Expected: all gates pass.

- [x] **Step 3: Update summary document**

Update `docs/2026-05-10-real-mvp-work-summary.md` so the agent status says:

```markdown
- Map place enrichment：Plan15 已接入 discovery 主流程；有 AMap/Mapbox key 时会用 provider registry 为 discovery cards 解析真实 `NormalizedPlace`，失败时保留 LLM place 并继续。
```

Update next plans so AMap/Mapbox provider validation is no longer listed as untouched; the next recommended plan becomes route-duration enrichment or production readiness.

- [x] **Step 4: Run final guards**

Run:

```bash
git diff --check
rg -n 'AI''zaSy|tvly''-' --glob '!api/.env' --glob '!web/.env.local' --glob '!node_modules' --glob '!.git'
```

Expected: `git diff --check` exits 0 and secret grep returns no matches.

- [x] **Step 5: Commit**

Run:

```bash
git add api/app/graph/nodes/discovery.py api/tests/graph/test_nodes.py docs/2026-05-10-real-mvp-work-summary.md docs/superpowers/plans/2026-05-10-langgraph-mvp-15-map-place-enrichment.md
git commit -m "feat: enrich discovery places with map providers"
```

---

## Self-Review

- Spec coverage: The plan wires real map provider resolution into discovery cards, keeps fixture mode deterministic, and keeps graceful fallback when maps are missing or failing.
- Placeholder scan: No TBD/TODO placeholders are present.
- Type consistency: The plan uses existing `TravelDataProviderRegistry`, `PlaceSearchRequest`, `NormalizedPlace`, and `DiscoveryCard` types.
