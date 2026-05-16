# Mapbox Place Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent real map provider results from replacing discovery card places when the returned place is obviously a generic or mismatched location.

**Architecture:** Keep map access inside the provider registry, but add a discovery-layer acceptance gate before a provider result is attached to a card. The gate requests a small candidate set, chooses the first coordinate-bearing candidate that resembles the card name, and preserves the LLM/model place when no reliable match exists.

**Tech Stack:** FastAPI backend, Pydantic domain schemas, pytest async tests, Mapbox/AMap map providers through `TravelDataProviderRegistry`.

---

## Root Cause Notes

Real Mapbox smoke after configuring `MAPBOX_ACCESS_TOKEN` showed:

- Direct route with fixed Shanghai coordinates returned real non-zero routes, so Mapbox auth and directions are working.
- `search_places()` and `geocode()` for China landmarks like Oriental Pearl and The Bund returned city-level `Shanghai` results.
- Current discovery enrichment requests only `limit=1` and blindly assigns `places[0]`, so one generic provider result can overwrite a more honest model place or create false precision.

The fix should address the source of the bad behavior: discovery should not accept a provider result unless it is plausibly the requested card place.

---

## File Structure

- Modify: `api/app/graph/nodes/discovery.py`
  - Increase map search limit from 1 to 3.
  - Add `_best_place_match()` and small text matching helpers.
  - Preserve the original card when no provider candidate passes the acceptance gate.
- Modify: `api/tests/graph/test_nodes.py`
  - Update the existing enrichment test to expect `limit=3`.
  - Add a regression test for rejecting generic city-level results.
  - Add a regression test for choosing a later matching candidate after a bad first candidate.
- Update: `docs/2026-05-10-real-mvp-work-summary.md`
  - Record the Mapbox verification outcome and the remaining China POI caveat.

---

### Task 1: Add Regression Tests

**Files:**
- Modify: `api/tests/graph/test_nodes.py`

- [x] **Step 1: Update existing enrichment expectation**

Change the assertion in `test_run_discovery_agent_enriches_card_places_with_map_registry`:

```python
assert registry.requests[0].limit == 3
```

- [x] **Step 2: Add test rejecting generic provider result**

```python
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
```

- [x] **Step 3: Add test selecting later matching candidate**

```python
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
```

- [x] **Step 4: Run tests and verify failure**

Run:

```bash
cd api && uv run pytest tests/graph/test_nodes.py::test_run_discovery_agent_enriches_card_places_with_map_registry tests/graph/test_nodes.py::test_run_discovery_agent_rejects_generic_map_place_match tests/graph/test_nodes.py::test_run_discovery_agent_uses_later_matching_map_candidate -q
```

Expected before implementation: FAIL because discovery still requests one result and blindly accepts the generic first result.

---

### Task 2: Add Discovery Place Acceptance Gate

**Files:**
- Modify: `api/app/graph/nodes/discovery.py`

- [x] **Step 1: Request multiple map candidates**

Change `_safe_enrich_card_place()`:

```python
request = PlaceSearchRequest(
    query=_place_search_query(card, session),
    country_code=session.hard_constraints.destination_country_code,
    limit=3,
    category=card.category,
)
```

- [x] **Step 2: Select only acceptable matches**

```python
match = _best_place_match(card, session, places)
if match is None:
    return card
return card.model_copy(update={"place": match})
```

- [x] **Step 3: Add helper functions**

```python
def _best_place_match(
    card: DiscoveryCard,
    session: PlanningSession,
    places: list[NormalizedPlace],
) -> NormalizedPlace | None:
    for place in places:
        if _is_acceptable_place_match(card, session, place):
            return place
    return None
```

The acceptance helper should require coordinates, reject candidates whose name is only the destination city, and accept substring/token overlap between the card name and the candidate name/address/category.

- [x] **Step 4: Run focused tests**

Run:

```bash
cd api && uv run pytest tests/graph/test_nodes.py::test_run_discovery_agent_enriches_card_places_with_map_registry tests/graph/test_nodes.py::test_run_discovery_agent_rejects_generic_map_place_match tests/graph/test_nodes.py::test_run_discovery_agent_uses_later_matching_map_candidate -q
```

Expected: PASS.

---

### Task 3: Verify Product Regression

**Files:**
- Update: `docs/2026-05-10-real-mvp-work-summary.md`

- [x] **Step 1: Run graph tests**

```bash
cd api && uv run pytest tests/graph/test_nodes.py -q
```

Expected: PASS.

- [x] **Step 2: Run full regression**

```bash
make regression
```

Expected: API, web unit, and Playwright suites pass.

- [x] **Step 3: Record summary**

Add a short note to the work summary:

```markdown
- Mapbox is configured and live route smoke passed. Discovery now rejects generic city-level map matches, so bad POI coverage does not create false precision.
```
