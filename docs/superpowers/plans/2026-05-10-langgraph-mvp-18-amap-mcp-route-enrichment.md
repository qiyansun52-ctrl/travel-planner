# AMap MCP Route Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Let the planning graph use AMap MCP-backed map tools through the existing provider registry so itineraries include real intra-city movement estimates without exposing raw MCP tool use directly to the LLM.

**Architecture:** Keep LLM output bounded to structured travel planning data. Add an optional AMap MCP adapter behind `TravelDataProviderRegistry`; graph nodes call the registry, the registry calls the provider, and the provider normalizes MCP tool results into `NormalizedPlace` and `NormalizedRoute`. Planner enrichment inserts route-aware `transit` segments only when coordinates and provider results are reliable, and falls back to the current deterministic itinerary when map calls fail.

**Tech Stack:** FastAPI backend, LangGraph graph nodes, Pydantic domain schemas, pytest/pytest-httpx, optional Python MCP SDK, AMap MCP server (`sugarforever/amap-mcp-server`), existing `TravelDataProviderRegistry`.

---

## Implementation Notes

- Completed through the Subagent-Driven flow: provider adapter, registry wiring, planner enrichment, smoke script, documentation, and review checkpoints.
- The final implementation intentionally tightens the original draft plan in a few places:
  - `run_planner_agent()` does not create a live default map registry unless explicitly opted in, keeping direct calls and unit tests deterministic.
  - `run_planner_node()` opts in only when `fixture_mode` is false.
  - API itinerary, itinerary streaming, stay override, and adjustment routes pass `E2E_FIXTURE_MODE` into graph workflows so fixture-mode tests do not call real map providers even when real map env vars exist.
  - Route segments are inserted only when the route duration fits the gap before the next scheduled segment.
  - Route enrichment catches provider/network/data failures but does not swallow programmer errors such as `TypeError`.

---

## Source Notes

- AMap MCP server repository: `https://github.com/sugarforever/amap-mcp-server`
- Useful MCP tools for this project: geocode, reverse geocode, POI search/detail, weather, route planning, and distance measurement.
- Product boundary decision: the app's LLM does not call raw AMap tools. The graph/provider layer calls map tools and validates results before they enter persisted session state.

---

## Current Backend Logic

Today the backend flow is:

1. `run_discovery_agent()` uses Tavily grounding and Gemini to create `DiscoveryOutput`.
2. Discovery then calls `TravelDataProviderRegistry.search_places()` to enrich card places.
3. `TravelDataProviderRegistry` chooses map providers by country: China destinations prefer `amap`, then fallback to Mapbox.
4. `run_planner_agent()` builds deterministic days and does not call `registry.route()` yet.
5. `validate_itinerary()` already understands `transit` segments and can flag `WASTEFUL_ROUTING`.

Plan18 keeps that architecture and adds route enrichment through the same registry boundary.

---

## File Structure

- Modify: `api/pyproject.toml`
  - Add optional MCP SDK dependency used by the streamable HTTP client.
- Create: `api/app/providers/map/amap_mcp.py`
  - Add `AMapMCPMapProvider`.
  - Add `StreamableHttpMCPToolClient`.
  - Normalize AMap MCP place and route tool results.
- Modify: `api/app/providers/registry.py`
  - Prefer `AMapMCPMapProvider` for provider id `amap` when `AMAP_MCP_URL` is configured.
  - Preserve existing `AMapMapProvider` REST behavior when MCP is not configured.
- Modify: `api/app/graph/nodes/planner.py`
  - Add optional `map_registry` parameter to `run_planner_agent()`.
  - Enrich day schedules with route-aware `transit` segments after deterministic segments are built.
  - Keep route failures non-blocking.
- Modify: `api/app/graph/workflow.py`
  - Thread fixture-mode opt-in to full and planner-only workflows.
- Modify: `api/app/routes/itinerary.py`
  - Pass `E2E_FIXTURE_MODE` into itinerary and streaming graph runs.
- Modify: `api/app/routes/adjustments.py` and adjustment workflow modules
  - Pass `E2E_FIXTURE_MODE` into planner-only adjustment reruns.
- Create: `api/scripts/smoke_amap_mcp.py`
  - Verify AMap MCP health, POI search, and route normalization without printing secrets.
- Modify: `api/tests/providers/test_amap_mcp.py`
  - Add provider-level tests with a fake MCP tool client.
- Modify: `api/tests/providers/test_registry.py`
  - Add registry wiring tests for `AMAP_MCP_URL` preference.
- Modify: `api/tests/graph/test_nodes.py`
  - Add planner route enrichment tests with fake route registry.
- Modify: `api/tests/graph/test_workflow.py` and `api/tests/routes/test_itinerary.py`
  - Add fixture-mode regressions that fail if configured map providers are created during fixture runs.
- Update: `docs/2026-05-10-real-mvp-work-summary.md`
  - Record Plan18 result and remaining provider caveats after implementation.

---

### Task 1: Add AMap MCP Provider Adapter Tests

**Files:**
- Create: `api/tests/providers/test_amap_mcp.py`

- [x] **Step 1: Create fake MCP client and place helper**

```python
from __future__ import annotations

import pytest

from app.models.schemas import Coordinate, NormalizedPlace
from app.providers.map.amap_mcp import AMapMCPMapProvider
from app.providers.types import (
    GeocodeRequest,
    PlaceSearchRequest,
    ProviderError,
    RouteRequest,
)


class FakeMCPToolClient:
    def __init__(self, results: dict[str, object]) -> None:
        self.results = results
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        self.calls.append((name, arguments))
        result = self.results.get(name)
        if isinstance(result, Exception):
            raise result
        return result


def _place(place_id: str, name: str, lat: float, lng: float) -> NormalizedPlace:
    return NormalizedPlace(
        id=place_id,
        name=name,
        coordinate=Coordinate(lat=lat, lng=lng),
        address=name,
        category="landmark",
        provider="amap",
    )
```

- [x] **Step 2: Add health tests**

```python
async def test_amap_mcp_health_requires_url_or_client() -> None:
    provider = AMapMCPMapProvider(mcp_url=None, tool_client=None)

    health = await provider.health()

    assert health.ok is False
    assert health.reason == "AMAP_MCP_URL is not configured"


async def test_amap_mcp_health_accepts_injected_client() -> None:
    provider = AMapMCPMapProvider(
        mcp_url=None,
        tool_client=FakeMCPToolClient({}),
    )

    health = await provider.health()

    assert health.ok is True
```

- [x] **Step 3: Add geocode normalization test**

```python
async def test_amap_mcp_geocode_normalizes_first_geocode() -> None:
    client = FakeMCPToolClient(
        {
            "maps_geo": {
                "status": "1",
                "return": [
                    {
                        "adcode": "310000",
                        "province": "上海市",
                        "city": "上海市",
                        "district": "黄浦区",
                        "location": "121.4737,31.2304",
                        "level": "兴趣点",
                    }
                ],
            }
        }
    )
    provider = AMapMCPMapProvider(tool_client=client)

    place = await provider.geocode(
        GeocodeRequest(query="人民广场", country_code="CN")
    )

    assert place.id == "amap:310000"
    assert place.name == "人民广场"
    assert place.coordinate is not None
    assert client.calls == [
        ("maps_geo", {"address": "人民广场"})
    ]
```

- [x] **Step 4: Add POI search normalization test**

```python
async def test_amap_mcp_search_places_normalizes_pois() -> None:
    client = FakeMCPToolClient(
        {
            "maps_text_search": {
                "status": "1",
                "return": [
                    {
                        "id": "B0FFG123",
                        "name": "东方明珠广播电视塔",
                        "address": "世纪大道1号",
                        "typecode": "110000",
                    }
                ],
            },
            "maps_search_detail": {
                "id": "B0FFG123",
                "name": "东方明珠广播电视塔",
                "address": "世纪大道1号",
                "type": "风景名胜",
                "location": "121.4998,31.2397",
            },
        }
    )
    provider = AMapMCPMapProvider(tool_client=client)

    places = await provider.search_places(
        PlaceSearchRequest(
            query="上海 东方明珠",
            country_code="CN",
            limit=3,
            category="sightseeing",
        )
    )

    assert [place.id for place in places] == ["amap:B0FFG123"]
    assert places[0].name == "东方明珠广播电视塔"
    assert client.calls[0] == (
        "maps_text_search",
        {"keywords": "上海 东方明珠"},
    )
    assert client.calls[1] == ("maps_search_detail", {"id": "B0FFG123"})
```

- [x] **Step 5: Add route normalization test**

```python
async def test_amap_mcp_route_maps_walking_duration_and_distance() -> None:
    client = FakeMCPToolClient(
        {
            "maps_direction_walking_by_coordinates": {
                "status": "1",
                "route": {
                    "paths": [
                        {
                            "duration": "900",
                            "distance": "1200",
                        }
                    ]
                },
            }
        }
    )
    provider = AMapMCPMapProvider(tool_client=client)

    route = await provider.route(
        RouteRequest(
            from_=_place("amap:start", "人民广场", 31.2304, 121.4737),
            to=_place("amap:end", "东方明珠", 31.2397, 121.4998),
            mode="walk",
        )
    )

    assert route.provider == "amap"
    assert route.mode == "walk"
    assert route.duration_minutes == 15
    assert route.distance_meters == 1200
    assert client.calls == [
        (
            "maps_direction_walking_by_coordinates",
            {
                "origin": "121.4737,31.2304",
                "destination": "121.4998,31.2397",
            },
        )
    ]
```

- [x] **Step 6: Add route failure tests**

```python
async def test_amap_mcp_route_rejects_missing_coordinates() -> None:
    provider = AMapMCPMapProvider(tool_client=FakeMCPToolClient({}))

    with pytest.raises(ProviderError) as error:
        await provider.route(
            RouteRequest(
                from_=NormalizedPlace(
                    id="amap:start",
                    name="Start",
                    coordinate=None,
                    address=None,
                    category=None,
                    provider="amap",
                ),
                to=_place("amap:end", "End", 31.2397, 121.4998),
                mode="walk",
            )
        )

    assert error.value.code == "invalid_normalized_payload"


async def test_amap_mcp_route_rejects_unsupported_mode() -> None:
    provider = AMapMCPMapProvider(tool_client=FakeMCPToolClient({}))

    with pytest.raises(ProviderError) as error:
        await provider.route(
            RouteRequest(
                from_=_place("amap:start", "Start", 31.2304, 121.4737),
                to=_place("amap:end", "End", 31.2397, 121.4998),
                mode="rail",
            )
        )

    assert error.value.code == "capability_unavailable"
```

- [x] **Step 7: Run tests and verify failure**

Run:

```bash
cd api && uv run pytest tests/providers/test_amap_mcp.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.providers.map.amap_mcp'`.

---

### Task 2: Implement AMap MCP Provider Adapter

**Files:**
- Modify: `api/pyproject.toml`
- Create: `api/app/providers/map/amap_mcp.py`
- Test: `api/tests/providers/test_amap_mcp.py`

- [x] **Step 1: Add Python MCP SDK dependency**

In `api/pyproject.toml`, add:

```toml
    "mcp>=1.14.0",
```

The dependency list should remain sorted by local convention only where the file already does so; do not reformat unrelated lines.

- [x] **Step 2: Create provider file with imports and protocol**

```python
"""AMap MCP map provider adapter."""
from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any, Protocol
from urllib.parse import quote

from pydantic import ValidationError

from app.models.schemas import Coordinate, NormalizedPlace, NormalizedRoute
from app.providers.map.coord import convert_gcj02_to_wgs84
from app.providers.types import (
    GeocodeRequest,
    PlaceSearchRequest,
    ProviderError,
    ProviderFailureCode,
    ProviderHealth,
    ReverseGeocodeRequest,
    RouteRequest,
)


class MCPToolClient(Protocol):
    async def call_tool(self, name: str, arguments: dict[str, object]) -> object: ...
```

- [x] **Step 3: Add streamable HTTP MCP client**

```python
class StreamableHttpMCPToolClient:
    def __init__(self, url: str) -> None:
        self._url = url

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        try:
            async with streamablehttp_client(self._url) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments=arguments)
        except (ConnectionError, TimeoutError, OSError) as exc:
            raise ProviderError(
                provider="amap",
                kind="map",
                code="network_failure",
                message=f"AMap MCP tool {name} failed",
                cause=exc,
            ) from exc

        return _extract_mcp_tool_payload(result)
```

- [x] **Step 4: Add provider class**

```python
class AMapMCPMapProvider:
    name = "amap"

    def __init__(
        self,
        *,
        mcp_url: str | None = None,
        tool_client: MCPToolClient | None = None,
    ) -> None:
        self._mcp_url = mcp_url
        self._tool_client = tool_client

    async def health(self) -> ProviderHealth:
        if self._tool_client is not None:
            return ProviderHealth(ok=True)
        if not self._mcp_url:
            return ProviderHealth(ok=False, reason="AMAP_MCP_URL is not configured")
        return ProviderHealth(ok=True)

    async def geocode(self, request: GeocodeRequest) -> NormalizedPlace:
        payload = await self._call_tool(
            "maps_geo",
            {"address": request.query},
        )
        geocodes = _tool_result_list(payload, "AMap MCP geocodes")
        first = geocodes[0] if geocodes else None
        if not isinstance(first, Mapping):
            raise self._provider_error("unknown_failure", "AMap MCP geocode returned no place")
        return normalize_amap_mcp_place(
            {
                "id": first.get("adcode"),
                "name": request.query,
                "formatted_address": first.get("formatted_address"),
                "category": first.get("level"),
                "location": first.get("location"),
            }
        )

    async def reverse_geocode(self, request: ReverseGeocodeRequest) -> NormalizedPlace:
        coordinate = request.coordinate
        payload = await self._call_tool(
            "maps_regeocode",
            {"location": f"{coordinate.lng},{coordinate.lat}"},
        )
        regeocode = _expect_mapping(_expect_mapping(payload).get("regeocode"))
        address = str(regeocode.get("formatted_address") or "AMap reverse geocode")
        return NormalizedPlace(
            id=f"amap:{quote(address, safe='')}",
            name=address,
            coordinate=coordinate,
            address=address,
            category="reverse_geocode",
            provider="amap",
        )

    async def search_places(self, request: PlaceSearchRequest) -> list[NormalizedPlace]:
        payload = await self._call_tool(
            "maps_text_search",
            {"keywords": request.query},
        )
        pois = _tool_result_list(payload, "AMap MCP pois")
        normalized: list[NormalizedPlace] = []
        for poi in pois:
            if not isinstance(poi, Mapping):
                raise self._invalid_payload_error("AMap MCP POI item is invalid")
            detail = await self._call_tool("maps_search_detail", {"id": poi["id"]})
            normalized.append(normalize_amap_mcp_place({**dict(poi), **detail}))
        return normalized

    async def route(self, request: RouteRequest) -> NormalizedRoute:
        tool_name = _route_tool_for_mode(request.mode)
        if request.from_.coordinate is None or request.to.coordinate is None:
            raise self._invalid_payload_error("AMap MCP route requires coordinates")
        payload = await self._call_tool(
            tool_name,
            {
                "origin": _coordinate_text(request.from_.coordinate),
                "destination": _coordinate_text(request.to.coordinate),
            },
        )
        duration_seconds, distance_meters = _extract_route_duration_and_distance(payload)
        try:
            return NormalizedRoute.model_validate(
                {
                    "from": request.from_,
                    "to": request.to,
                    "mode": request.mode,
                    "duration_minutes": round(duration_seconds / 60),
                    "distance_meters": distance_meters,
                    "cost_estimate": None,
                    "provider": "amap",
                }
            )
        except ValidationError as exc:
            raise self._invalid_payload_error("Invalid AMap MCP normalized route", exc) from exc

    async def _call_tool(self, name: str, arguments: dict[str, object]) -> object:
        client = self._tool_client
        if client is None:
            if not self._mcp_url:
                raise self._provider_error(
                    "auth_failure",
                    "AMAP_MCP_URL is not configured",
                )
            client = StreamableHttpMCPToolClient(self._mcp_url)
        return _extract_mcp_tool_payload(await client.call_tool(name, arguments))

    def _provider_error(
        self,
        code: ProviderFailureCode,
        message: str,
        cause: object | None = None,
    ) -> ProviderError:
        return ProviderError(
            provider=self.name,
            kind="map",
            code=code,
            message=message,
            cause=cause,
        )

    def _invalid_payload_error(
        self,
        message: str,
        cause: object | None = None,
    ) -> ProviderError:
        return self._provider_error("invalid_normalized_payload", message, cause)
```

- [x] **Step 5: Add normalization helpers**

```python
def normalize_amap_mcp_place(payload: dict[str, Any]) -> NormalizedPlace:
    coordinate = convert_gcj02_to_wgs84(_parse_location(payload.get("location")))
    stable_id = payload.get("id") or payload.get("adcode") or _create_stable_id(payload)
    try:
        return NormalizedPlace.model_validate(
            {
                "id": f"amap:{stable_id}",
                "name": (
                    payload.get("name")
                    or payload.get("formatted_address")
                    or payload.get("address")
                    or "AMap place"
                ),
                "coordinate": coordinate,
                "address": payload.get("formatted_address") or payload.get("address"),
                "category": payload.get("category") or payload.get("type"),
                "provider": "amap",
            }
        )
    except ValidationError as exc:
        raise ProviderError(
            provider="amap",
            kind="map",
            code="invalid_normalized_payload",
            message="Invalid AMap MCP normalized place payload",
            cause=exc,
        ) from exc


def _extract_mcp_tool_payload(result: object) -> object:
    if isinstance(result, Mapping):
        return result
    content = getattr(result, "content", None)
    if isinstance(content, list):
        for item in content:
            text = getattr(item, "text", None)
            if isinstance(text, str) and text.strip():
                try:
                    return json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ProviderError(
                        provider="amap",
                        kind="map",
                        code="invalid_normalized_payload",
                        message="AMap MCP tool returned non-JSON text",
                        cause=exc,
                    ) from exc
    raise ProviderError(
        provider="amap",
        kind="map",
        code="invalid_normalized_payload",
        message="AMap MCP tool returned unsupported payload",
    )


def _extract_route_duration_and_distance(payload: object) -> tuple[float, float]:
    route = _expect_mapping(_expect_mapping(payload).get("route"))
    candidates = route.get("paths") or route.get("transits") or []
    paths = _expect_list(candidates, "AMap MCP route paths")
    first = paths[0] if paths else None
    if not isinstance(first, Mapping):
        raise ProviderError(
            provider="amap",
            kind="map",
            code="unknown_failure",
            message="AMap MCP route returned no route",
        )
    duration = _number(first.get("duration"), "AMap MCP route duration")
    distance = _number(first.get("distance"), "AMap MCP route distance")
    return duration, distance


def _route_tool_for_mode(mode: str) -> str:
    if mode == "walk":
        return "maps_direction_walking_by_coordinates"
    if mode == "drive":
        return "maps_direction_driving_by_coordinates"
    if mode == "transit":
        return "maps_direction_transit_integrated_by_coordinates"
    raise ProviderError(
        provider="amap",
        kind="map",
        code="capability_unavailable",
        message=f"AMap MCP routing does not support {mode} routes in this adapter",
    )


def _coordinate_text(coordinate: Coordinate) -> str:
    return f"{coordinate.lng},{coordinate.lat}"


def _parse_location(location: object) -> Coordinate:
    try:
        if not isinstance(location, str):
            raise ValueError("location must be a string")
        lng_text, lat_text = location.split(",", 1)
        lng = float(lng_text)
        lat = float(lat_text)
        if not math.isfinite(lat) or not math.isfinite(lng):
            raise ValueError("coordinates must be finite")
    except ValueError as exc:
        raise ProviderError(
            provider="amap",
            kind="map",
            code="invalid_normalized_payload",
            message=f"Invalid AMap MCP location: {location}",
            cause=exc,
        ) from exc
    return Coordinate(lat=lat, lng=lng)


def _expect_mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProviderError(
            provider="amap",
            kind="map",
            code="invalid_normalized_payload",
            message="AMap MCP payload must be an object",
        )
    return value


def _expect_list(value: object, label: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ProviderError(
            provider="amap",
            kind="map",
            code="invalid_normalized_payload",
            message=f"{label} must be a list",
        )
    return value


def _number(value: object, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ProviderError(
            provider="amap",
            kind="map",
            code="invalid_normalized_payload",
            message=f"{label} must be numeric",
            cause=exc,
        ) from exc
    if not math.isfinite(number):
        raise ProviderError(
            provider="amap",
            kind="map",
            code="invalid_normalized_payload",
            message=f"{label} must be finite",
        )
    return number


def _create_stable_id(payload: dict[str, Any]) -> str:
    label = payload.get("name") or payload.get("formatted_address") or "place"
    return quote(f"{label}:{payload.get('location', '')}", safe="")
```

- [x] **Step 6: Run provider tests**

Run:

```bash
cd api && uv run pytest tests/providers/test_amap_mcp.py -q
```

Expected: PASS.

---

### Task 3: Wire AMap MCP Into Provider Registry

**Files:**
- Modify: `api/app/providers/registry.py`
- Modify: `api/tests/providers/test_registry.py`

- [x] **Step 1: Add failing registry test**

Append to `api/tests/providers/test_registry.py`:

```python
def test_default_registry_prefers_amap_mcp_when_url_configured() -> None:
    registry = create_default_provider_registry(
        env={
            "AMAP_MCP_URL": "http://127.0.0.1:8899/mcp",
            "AMAP_API_KEY": "rest-key",
            "MAPBOX_ACCESS_TOKEN": "mapbox-token",
        }
    )

    provider = registry._map_providers["amap"]  # noqa: SLF001

    assert provider.__class__.__name__ == "AMapMCPMapProvider"
```

- [x] **Step 2: Run test and verify failure**

Run:

```bash
cd api && uv run pytest tests/providers/test_registry.py::test_default_registry_prefers_amap_mcp_when_url_configured -q
```

Expected: FAIL because `create_default_provider_registry()` still always uses `AMapMapProvider`.

- [x] **Step 3: Import MCP provider and add factory helper**

In `api/app/providers/registry.py`:

```python
from app.providers.map.amap_mcp import AMapMCPMapProvider
```

Add helper near `create_default_provider_registry()`:

```python
def _create_default_amap_provider(source: Mapping[str, str]) -> MapProvider:
    mcp_url = source.get("AMAP_MCP_URL")
    if mcp_url:
        return AMapMCPMapProvider(mcp_url=mcp_url)
    return AMapMapProvider(api_key=source.get("AMAP_API_KEY"))
```

- [x] **Step 4: Use helper in default registry**

Change:

```python
"amap": AMapMapProvider(api_key=source.get("AMAP_API_KEY")),
```

to:

```python
"amap": _create_default_amap_provider(source),
```

- [x] **Step 5: Run registry tests**

Run:

```bash
cd api && uv run pytest tests/providers/test_registry.py -q
```

Expected: PASS.

---

### Task 4: Add Planner Route Enrichment Through Registry

**Files:**
- Modify: `api/app/graph/nodes/planner.py`
- Modify: `api/tests/graph/test_nodes.py`

- [x] **Step 1: Add fake route registry to graph tests**

In `api/tests/graph/test_nodes.py`, add imports:

```python
from app.models.schemas import NormalizedRoute
from app.providers.types import RouteRequest
```

Add fake registry near `FakeMapRegistry`:

```python
class FakeRouteRegistry:
    def __init__(self, duration_minutes: float = 18, distance_meters: float = 1400) -> None:
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
```

- [x] **Step 2: Add planner enrichment test**

```python
@pytest.mark.asyncio
async def test_run_planner_agent_adds_route_transit_segments_when_registry_available() -> None:
    registry = FakeRouteRegistry(duration_minutes=18, distance_meters=1400)

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
    assert "Estimated walk: 18 min, 1.4 km." in transit_segments[0].description
    assert registry.requests
    assert registry.requests[0][0] == "CN"
    assert registry.requests[0][1].mode == "walk"
```

- [x] **Step 3: Add graceful fallback test**

```python
class FailingRouteRegistry:
    async def route(self, country_code: str, request: RouteRequest) -> NormalizedRoute:
        raise RuntimeError("route unavailable")


@pytest.mark.asyncio
async def test_run_planner_agent_keeps_itinerary_when_route_enrichment_fails() -> None:
    itinerary = await run_planner_agent(
        fixtures.session(),
        fixtures.stay_recommendation(),
        fixtures.transport_recommendation(),
        map_registry=FailingRouteRegistry(),
    )

    assert all(
        segment.type != "transit"
        for day in itinerary.days
        for segment in day.segments
    )
```

- [x] **Step 4: Run tests and verify failure**

Run:

```bash
cd api && uv run pytest tests/graph/test_nodes.py::test_run_planner_agent_adds_route_transit_segments_when_registry_available tests/graph/test_nodes.py::test_run_planner_agent_keeps_itinerary_when_route_enrichment_fails -q
```

Expected: FAIL because `run_planner_agent()` does not accept `map_registry` yet.

- [x] **Step 5: Update planner signature and imports**

In `api/app/graph/nodes/planner.py`, add imports:

```python
from app.models.schemas import NormalizedRoute
from app.providers.registry import TravelDataProviderRegistry, create_default_provider_registry
from app.providers.types import RouteRequest
```

Change signature:

```python
async def run_planner_agent(
    session: PlanningSession,
    stay: StayRecommendation,
    transport: TransportRecommendation,
    validator_issues: list[ValidatorIssue] | None = None,
    *,
    map_registry: TravelDataProviderRegistry | None = None,
) -> Itinerary:
```

- [x] **Step 6: Enrich days after deterministic build**

Change:

```python
days = _build_days(session, cards, active_stay, validator_issues)
```

to:

```python
days = _build_days(session, cards, active_stay, validator_issues)
days = await _enrich_days_with_routes(days, session, map_registry)
```

- [x] **Step 7: Add enrichment helpers**

```python
async def _enrich_days_with_routes(
    days: list[ItineraryDay],
    session: PlanningSession,
    map_registry: TravelDataProviderRegistry | None,
    *,
    use_default_map_registry: bool = False,
) -> list[ItineraryDay]:
    registry = map_registry
    if registry is None and use_default_map_registry:
        registry = _default_route_registry()
    if registry is None:
        return days

    enriched_days: list[ItineraryDay] = []
    for day in days:
        enriched_days.append(
            await _enrich_day_with_routes(
                day,
                session.hard_constraints.destination_country_code,
                registry,
            )
        )
    return enriched_days


async def _enrich_day_with_routes(
    day: ItineraryDay,
    country_code: str,
    registry: TravelDataProviderRegistry,
) -> ItineraryDay:
    enriched: list[ItinerarySegment] = []
    previous_place: NormalizedPlace | None = None
    previous_end = "09:30"

    for segment in day.segments:
        if segment.place is not None and previous_place is not None:
            route = await _safe_route_between(country_code, registry, previous_place, segment.place)
            if route is not None:
                enriched.append(_route_segment(previous_end, route))
        enriched.append(segment)
        if segment.place is not None:
            previous_place = segment.place
            previous_end = segment.end_time
        else:
            previous_place = None

    return day.model_copy(update={"segments": enriched})


async def _safe_route_between(
    country_code: str,
    registry: TravelDataProviderRegistry,
    from_place: NormalizedPlace,
    to_place: NormalizedPlace,
) -> NormalizedRoute | None:
    if from_place.coordinate is None or to_place.coordinate is None:
        return None
    mode = _route_mode_for_places(from_place, to_place)
    try:
        return await registry.route(
            country_code,
            RouteRequest(from_=from_place, to=to_place, mode=mode),
        )
    except (ProviderRegistryError, ProviderError, TimeoutError, ConnectionError, ValueError):
        return None


def _route_mode_for_places(
    from_place: NormalizedPlace,
    to_place: NormalizedPlace,
) -> str:
    if from_place.coordinate is None or to_place.coordinate is None:
        return "drive"
    straight_line = _straight_line_distance_meters(
        from_place.coordinate.lat,
        from_place.coordinate.lng,
        to_place.coordinate.lat,
        to_place.coordinate.lng,
    )
    return "walk" if straight_line <= 1800 else "drive"


def _route_segment(start_time: str, route: NormalizedRoute) -> ItinerarySegment:
    minutes = max(5, int(round(route.duration_minutes)))
    distance_km = route.distance_meters / 1000
    return ItinerarySegment(
        type="transit",
        start_time=start_time,
        end_time=_add_minutes(start_time, minutes),
        place=None,
        card_ref=None,
        description=(
            f"Estimated {route.mode}: {int(round(route.duration_minutes))} min, "
            f"{distance_km:.1f} km."
        ),
        cost_estimate=None,
    )


def _straight_line_distance_meters(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> float:
    radius = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _add_minutes(value: str, minutes: int) -> str:
    hours, current_minutes = (int(part) for part in value.split(":"))
    total = min(23 * 60 + 59, hours * 60 + current_minutes + minutes)
    return f"{total // 60:02d}:{total % 60:02d}"


def _default_route_registry() -> TravelDataProviderRegistry | None:
    if not (
        os.environ.get("AMAP_MCP_URL")
        or os.environ.get("AMAP_API_KEY")
        or os.environ.get("MAPBOX_ACCESS_TOKEN")
    ):
        return None
    return create_default_provider_registry()
```

Also add `import os` at the top of `planner.py`.

- [x] **Step 8: Keep default registry opt-in and fixture-mode safe**

`run_planner_agent()` should remain deterministic by default and only use the default map registry when explicitly opted in. `run_planner_node()` should pass `use_default_map_registry=not parsed.fixture_mode`:

```python
itinerary = await run_planner_agent(
    parsed.session,
    stay,
    transport,
    parsed.validator_issues,
    use_default_map_registry=not parsed.fixture_mode,
)
```

Thread `fixture_mode` through workflow/API entry points so fixture-mode tests do not create real map providers when local map env vars are configured.

Do not thread raw MCP clients through LangGraph state. The provider registry remains the only map execution boundary.

- [x] **Step 9: Run planner tests**

Run:

```bash
cd api && uv run pytest tests/graph/test_nodes.py::test_run_planner_agent_adds_route_transit_segments_when_registry_available tests/graph/test_nodes.py::test_run_planner_agent_keeps_itinerary_when_route_enrichment_fails -q
```

Expected: PASS.

---

### Task 5: Add AMap MCP Smoke Script

**Files:**
- Create: `api/scripts/smoke_amap_mcp.py`

- [x] **Step 1: Create script**

```python
from __future__ import annotations

import asyncio
import os

from app.config import load_environment
from app.models.schemas import Coordinate, NormalizedPlace
from app.providers.map.amap_mcp import AMapMCPMapProvider
from app.providers.types import PlaceSearchRequest, RouteRequest


def _place(place_id: str, name: str, lat: float, lng: float) -> NormalizedPlace:
    return NormalizedPlace(
        id=place_id,
        name=name,
        coordinate=Coordinate(lat=lat, lng=lng),
        address=name,
        category="smoke",
        provider="amap",
    )


async def main() -> None:
    load_environment()
    provider = AMapMCPMapProvider(mcp_url=os.environ.get("AMAP_MCP_URL"))
    health = await provider.health()
    if not health.ok:
        raise SystemExit(f"amap_mcp_unhealthy {health.reason}")

    places = await provider.search_places(
        PlaceSearchRequest(query="上海 东方明珠", country_code="CN", limit=3)
    )
    if not places:
        raise SystemExit("amap_mcp_no_places")

    start = _place("amap:people-square", "人民广场", 31.2304, 121.4737)
    end = _place("amap:oriental-pearl", "东方明珠", 31.2397, 121.4998)
    route = await provider.route(RouteRequest(from_=start, to=end, mode="walk"))
    if route.duration_minutes <= 0 or route.distance_meters <= 0:
        raise SystemExit("amap_mcp_bad_route")

    print(
        "amap_mcp_smoke_ok",
        len(places),
        places[0].provider,
        route.provider,
        int(route.duration_minutes),
        int(route.distance_meters),
    )


if __name__ == "__main__":
    asyncio.run(main())
```

- [x] **Step 2: Run script without MCP URL**

Run:

```bash
cd api && uv run python scripts/smoke_amap_mcp.py
```

Expected: exits with `amap_mcp_unhealthy AMAP_MCP_URL is not configured`.

- [x] **Step 3: Run script with AMap MCP server**

After starting `sugarforever/amap-mcp-server` in streamable HTTP mode and setting `AMAP_MCP_URL`, run:

```bash
cd api && uv run python scripts/smoke_amap_mcp.py
```

Expected:

```text
amap_mcp_smoke_ok <place_count> amap amap <duration_minutes> <distance_meters>
```

The script must not print the AMap key or MCP URL.

---

### Task 6: Full Verification and Documentation

**Files:**
- Update: `docs/2026-05-10-real-mvp-work-summary.md`

- [x] **Step 1: Run provider tests**

```bash
cd api && uv run pytest tests/providers/test_amap_mcp.py tests/providers/test_registry.py -q
```

Expected: PASS.

- [x] **Step 2: Run graph tests**

```bash
cd api && uv run pytest tests/graph/test_nodes.py tests/graph/test_workflow.py -q
```

Expected: PASS.

- [x] **Step 3: Run full regression**

```bash
make regression
```

Expected: launch readiness, web typecheck/lint/unit/build, API pytest, API ruff, fixture smoke, and Playwright e2e all pass.

- [x] **Step 4: Update summary**

Add this note to `docs/2026-05-10-real-mvp-work-summary.md`:

```markdown
- Plan18 added a controlled AMap MCP map-provider path and route-duration enrichment. The planner now inserts route-aware transit segments when provider results are available, while preserving the deterministic itinerary when map calls fail.
```

- [x] **Step 5: Commit**

```bash
git add api/pyproject.toml api/app/providers/map/amap_mcp.py api/app/providers/registry.py api/app/graph/nodes/planner.py api/scripts/smoke_amap_mcp.py api/tests/providers/test_amap_mcp.py api/tests/providers/test_registry.py api/tests/graph/test_nodes.py docs/2026-05-10-real-mvp-work-summary.md docs/superpowers/plans/2026-05-10-langgraph-mvp-18-amap-mcp-route-enrichment.md
git commit -m "feat: add amap mcp route enrichment"
```
