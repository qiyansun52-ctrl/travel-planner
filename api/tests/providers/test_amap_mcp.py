from __future__ import annotations

from typing import Any

import pytest

from app.models.schemas import Coordinate, NormalizedPlace
from app.providers.map.amap_mcp import AMapMCPMapProvider
from app.providers.types import (
    GeocodeRequest,
    PlaceSearchRequest,
    ProviderError,
    ReverseGeocodeRequest,
    RouteRequest,
)


class FakeMCPToolClient:
    def __init__(
        self,
        results: dict[str, object] | None = None,
        errors: dict[str, Exception] | None = None,
    ) -> None:
        self.results = results or {}
        self.errors = errors or {}
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        self.calls.append((name, arguments))
        if name in self.errors:
            raise self.errors[name]
        return self.results[name]


async def test_health_reports_missing_url_and_client() -> None:
    provider = AMapMCPMapProvider(mcp_url=None)

    health = await provider.health()

    assert health.ok is False
    assert health.reason == "AMAP_MCP_URL is not configured"


async def test_health_accepts_injected_tool_client() -> None:
    provider = AMapMCPMapProvider(tool_client=FakeMCPToolClient())

    health = await provider.health()

    assert health.ok is True
    assert health.reason is None


async def test_geocode_calls_maps_geo_and_normalizes_first_geocode() -> None:
    client = FakeMCPToolClient(
        {
            "maps_geo": {
                "return": [
                    {
                        "adcode": "310000",
                        "country": "中国",
                        "province": "上海市",
                        "city": "上海市",
                        "district": "黄浦区",
                        "location": "121.4737,31.2304",
                        "level": "city",
                    }
                ]
            }
        }
    )
    provider = AMapMCPMapProvider(tool_client=client)

    place = await provider.geocode(GeocodeRequest(query="上海", country_code="CN"))

    assert client.calls == [
        ("maps_geo", {"address": "上海"}),
    ]
    assert place.provider == "amap"
    assert place.id == "amap:310000"
    assert place.name == "上海"
    assert place.address == "中国上海市黄浦区"
    assert place.category == "city"
    assert place.coordinate is not None
    assert place.coordinate.lat != 31.2304
    assert place.coordinate.lng != 121.4737


async def test_search_places_calls_text_search_and_normalizes_pois() -> None:
    client = FakeMCPToolClient(
        {
            "maps_text_search": {
                "return": [
                    {
                        "id": "B0FFG123",
                        "name": "人民广场",
                        "address": "上海市黄浦区",
                        "typecode": "110000",
                    }
                ]
            },
            "maps_search_detail": {
                "id": "B0FFG123",
                "name": "人民广场",
                "address": "上海市黄浦区人民大道",
                "type": "landmark",
                "typecode": "110000",
                "location": "121.4737,31.2304",
            },
        }
    )
    provider = AMapMCPMapProvider(tool_client=client)

    places = await provider.search_places(
        PlaceSearchRequest(query="人民广场", country_code="CN", limit=5)
    )

    assert client.calls == [
        ("maps_text_search", {"keywords": "人民广场"}),
        ("maps_search_detail", {"id": "B0FFG123"}),
    ]
    assert len(places) == 1
    assert places[0].provider == "amap"
    assert places[0].id == "amap:B0FFG123"
    assert places[0].category == "landmark"


async def test_reverse_geocode_calls_regeocode_and_normalizes_place() -> None:
    client = FakeMCPToolClient(
        {
            "maps_regeocode": {
                "return": {
                    "province": "上海市",
                    "city": "上海市",
                    "district": "黄浦区",
                }
            }
        }
    )
    provider = AMapMCPMapProvider(tool_client=client)
    coordinate = Coordinate(lat=31.2304, lng=121.4737)

    place = await provider.reverse_geocode(ReverseGeocodeRequest(coordinate=coordinate))

    assert client.calls == [
        ("maps_regeocode", {"location": "121.4737,31.2304"}),
    ]
    assert place.provider == "amap"
    assert place.coordinate == coordinate
    assert place.name == "上海市黄浦区"
    assert place.address == "上海市黄浦区"
    assert place.category == "reverse_geocode"


async def test_injected_client_runtime_error_maps_to_network_failure() -> None:
    cause = RuntimeError("boom")
    provider = AMapMCPMapProvider(
        tool_client=FakeMCPToolClient(errors={"maps_geo": cause})
    )

    with pytest.raises(ProviderError) as error:
        await provider.geocode(GeocodeRequest(query="上海"))

    assert error.value.provider == "amap"
    assert error.value.kind == "map"
    assert error.value.code == "network_failure"
    assert error.value.cause is cause
    assert str(error.value) == "AMap MCP tool maps_geo failed"


async def test_route_walk_calls_direction_tool_and_normalizes_route() -> None:
    client = FakeMCPToolClient(
        {
            "maps_direction_walking_by_coordinates": {
                "route": {
                    "paths": [
                        {
                            "duration": "900",
                            "distance": "1200",
                        }
                    ]
                }
            }
        }
    )
    provider = AMapMCPMapProvider(tool_client=client)
    origin = _place("origin", lat=31.2304, lng=121.4737)
    destination = _place("destination", lat=31.2244, lng=121.4692)

    route = await provider.route(
        RouteRequest(from_=origin, to=destination, mode="walk")
    )

    assert client.calls == [
        (
            "maps_direction_walking_by_coordinates",
            {
                "origin": "121.4737,31.2304",
                "destination": "121.4692,31.2244",
            },
        ),
    ]
    assert route.provider == "amap"
    assert route.from_ == origin
    assert route.to == destination
    assert route.mode == "walk"
    assert route.duration_minutes == 15
    assert route.distance_meters == 1200


async def test_route_drive_and_transit_use_coordinate_tools() -> None:
    client = FakeMCPToolClient(
        {
            "maps_direction_driving_by_coordinates": {
                "route": {"paths": [{"duration": "60", "distance": "1000"}]}
            },
            "maps_direction_transit_integrated_by_coordinates": {
                "route": {"transits": [{"duration": "120", "distance": "3000"}]}
            },
        }
    )
    provider = AMapMCPMapProvider(tool_client=client)
    origin = _place("origin", lat=31.2304, lng=121.4737)
    destination = _place("destination", lat=31.2244, lng=121.4692)

    await provider.route(RouteRequest(from_=origin, to=destination, mode="drive"))
    await provider.route(RouteRequest(from_=origin, to=destination, mode="transit"))

    assert [call[0] for call in client.calls] == [
        "maps_direction_driving_by_coordinates",
        "maps_direction_transit_integrated_by_coordinates",
    ]
    assert client.calls[1][1] == {
        "origin": "121.4737,31.2304",
        "destination": "121.4692,31.2244",
        "city": "上海市",
        "cityd": "上海市",
    }


async def test_route_transit_requires_inferable_city_names() -> None:
    provider = AMapMCPMapProvider(tool_client=FakeMCPToolClient())

    with pytest.raises(ProviderError) as error:
        await provider.route(
            RouteRequest(
                from_=_place("origin", lat=31.2304, lng=121.4737, address=None),
                to=_place("destination", lat=31.2244, lng=121.4692, address=None),
                mode="transit",
            )
        )

    assert error.value.code == "invalid_normalized_payload"


async def test_route_rejects_missing_coordinates() -> None:
    provider = AMapMCPMapProvider(tool_client=FakeMCPToolClient())

    with pytest.raises(ProviderError) as error:
        await provider.route(
            RouteRequest(
                from_=_place("origin", coordinate=None),
                to=_place("destination", lat=31.2244, lng=121.4692),
                mode="walk",
            )
        )

    assert error.value.provider == "amap"
    assert error.value.kind == "map"
    assert error.value.code == "invalid_normalized_payload"


async def test_route_rejects_unsupported_mode() -> None:
    provider = AMapMCPMapProvider(tool_client=FakeMCPToolClient())

    with pytest.raises(ProviderError) as error:
        await provider.route(
            RouteRequest(
                from_=_place("origin", lat=31.2304, lng=121.4737),
                to=_place("destination", lat=31.2244, lng=121.4692),
                mode="rail",
            )
        )

    assert error.value.provider == "amap"
    assert error.value.kind == "map"
    assert error.value.code == "capability_unavailable"


def _place(
    name: str,
    *,
    lat: float | None = None,
    lng: float | None = None,
    coordinate: Any = ...,
    address: str | None = "上海市黄浦区",
) -> NormalizedPlace:
    if coordinate is ...:
        coordinate = {"lat": lat, "lng": lng}
    return NormalizedPlace.model_validate(
        {
            "id": f"test:{name}",
            "name": name,
            "coordinate": coordinate,
            "address": address,
            "category": None,
            "provider": "amap",
        }
    )
