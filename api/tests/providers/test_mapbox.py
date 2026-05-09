from __future__ import annotations

import re

import pytest
from pytest_httpx import HTTPXMock

from app.models.schemas import NormalizedPlace
from app.providers.map.mapbox import MapboxMapProvider, normalize_mapbox_feature
from app.providers.types import (
    GeocodeRequest,
    PlaceSearchRequest,
    ProviderError,
    ReverseGeocodeRequest,
    RouteRequest,
)


async def test_health_reports_missing_token() -> None:
    provider = MapboxMapProvider(access_token=None)

    health = await provider.health()

    assert health.ok is False
    assert health.reason == "MAPBOX_ACCESS_TOKEN is not configured"


async def test_health_reports_configured_token() -> None:
    provider = MapboxMapProvider(access_token="token")

    health = await provider.health()

    assert health.ok is True
    assert health.reason is None


def test_normalize_mapbox_feature_accepts_missing_coordinate() -> None:
    place = normalize_mapbox_feature(
        {
            "id": "place.1",
            "text": "Shanghai",
            "place_name": "Shanghai, China",
            "geometry": {},
            "properties": {"feature_type": "place"},
        }
    )

    assert place.id == "mapbox:place.1"
    assert place.name == "Shanghai"
    assert place.coordinate is None
    assert place.provider == "mapbox"


def test_normalize_mapbox_feature_wraps_validation_errors() -> None:
    with pytest.raises(ProviderError) as error:
        normalize_mapbox_feature(
            {
                "id": "place.1",
                "text": ["Shanghai"],
                "geometry": {"coordinates": [121.4737, 31.2304]},
                "properties": {},
            }
        )

    assert error.value.code == "invalid_normalized_payload"


def test_normalize_mapbox_feature_rejects_invalid_geometry() -> None:
    with pytest.raises(ProviderError) as error:
        normalize_mapbox_feature(
            {
                "id": "place.1",
                "text": "Shanghai",
                "geometry": ["not-a-geometry"],
                "properties": {},
            }
        )

    assert error.value.code == "invalid_normalized_payload"


def test_normalize_mapbox_feature_rejects_invalid_coordinates() -> None:
    with pytest.raises(ProviderError) as error:
        normalize_mapbox_feature(
            {
                "id": "place.1",
                "text": "Shanghai",
                "geometry": {"coordinates": 121.4737},
                "properties": {},
            }
        )

    assert error.value.code == "invalid_normalized_payload"


async def test_geocode_returns_first_feature(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(
            r"https://api\.mapbox\.com/geocoding/v5/mapbox\.places/Shanghai\.json.*"
        ),
        json={
            "features": [
                {
                    "id": "place.1",
                    "text": "Shanghai",
                    "place_name": "Shanghai, China",
                    "geometry": {"coordinates": [121.4737, 31.2304]},
                    "properties": {"feature_type": "place"},
                }
            ]
        },
    )
    provider = MapboxMapProvider(access_token="token")

    place = await provider.geocode(GeocodeRequest(query="Shanghai", country_code="CN"))

    assert place.id == "mapbox:place.1"
    assert place.coordinate is not None
    assert place.coordinate.lat == 31.2304


async def test_geocode_maps_401_to_auth_failure(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(
            r"https://api\.mapbox\.com/geocoding/v5/mapbox\.places/Shanghai\.json.*"
        ),
        status_code=401,
    )
    provider = MapboxMapProvider(access_token="token")

    with pytest.raises(ProviderError) as error:
        await provider.geocode(GeocodeRequest(query="Shanghai", country_code="CN"))

    assert error.value.code == "auth_failure"


async def test_geocode_maps_redirect_to_network_failure(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(
            r"https://api\.mapbox\.com/geocoding/v5/mapbox\.places/Shanghai\.json.*"
        ),
        status_code=302,
        headers={"Location": "https://example.com/login"},
    )
    provider = MapboxMapProvider(access_token="token")

    with pytest.raises(ProviderError) as error:
        await provider.geocode(GeocodeRequest(query="Shanghai", country_code="CN"))

    assert error.value.code == "network_failure"


async def test_geocode_maps_malformed_json_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(
            r"https://api\.mapbox\.com/geocoding/v5/mapbox\.places/Shanghai\.json.*"
        ),
        content=b"{",
    )
    provider = MapboxMapProvider(access_token="token")

    with pytest.raises(ProviderError) as error:
        await provider.geocode(GeocodeRequest(query="Shanghai", country_code="CN"))

    assert error.value.code == "invalid_normalized_payload"


async def test_geocode_maps_non_dict_json_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(
            r"https://api\.mapbox\.com/geocoding/v5/mapbox\.places/Shanghai\.json.*"
        ),
        json=[],
    )
    provider = MapboxMapProvider(access_token="token")

    with pytest.raises(ProviderError) as error:
        await provider.geocode(GeocodeRequest(query="Shanghai", country_code="CN"))

    assert error.value.code == "invalid_normalized_payload"


async def test_geocode_maps_non_list_features_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(
            r"https://api\.mapbox\.com/geocoding/v5/mapbox\.places/Shanghai\.json.*"
        ),
        json={"features": {"id": "place.1"}},
    )
    provider = MapboxMapProvider(access_token="token")

    with pytest.raises(ProviderError) as error:
        await provider.geocode(GeocodeRequest(query="Shanghai", country_code="CN"))

    assert error.value.code == "invalid_normalized_payload"


async def test_geocode_maps_non_dict_first_feature_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(
            r"https://api\.mapbox\.com/geocoding/v5/mapbox\.places/Shanghai\.json.*"
        ),
        json={"features": ["not-a-place"]},
    )
    provider = MapboxMapProvider(access_token="token")

    with pytest.raises(ProviderError) as error:
        await provider.geocode(GeocodeRequest(query="Shanghai", country_code="CN"))

    assert error.value.code == "invalid_normalized_payload"


async def test_search_places_returns_all_features(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(
            r"https://api\.mapbox\.com/geocoding/v5/mapbox\.places/cafe\.json.*"
        ),
        json={
            "features": [
                {
                    "id": "poi.1",
                    "text": "Cafe A",
                    "geometry": {"coordinates": [1, 2]},
                    "properties": {},
                },
                {
                    "id": "poi.2",
                    "text": "Cafe B",
                    "geometry": {"coordinates": [3, 4]},
                    "properties": {},
                },
            ]
        },
    )
    provider = MapboxMapProvider(access_token="token")

    places = await provider.search_places(
        PlaceSearchRequest(query="cafe", country_code="US", limit=2)
    )

    assert [place.id for place in places] == ["mapbox:poi.1", "mapbox:poi.2"]


async def test_search_places_maps_non_dict_feature_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(
            r"https://api\.mapbox\.com/geocoding/v5/mapbox\.places/cafe\.json.*"
        ),
        json={"features": ["not-a-place"]},
    )
    provider = MapboxMapProvider(access_token="token")

    with pytest.raises(ProviderError) as error:
        await provider.search_places(PlaceSearchRequest(query="cafe", limit=1))

    assert error.value.code == "invalid_normalized_payload"


async def test_reverse_geocode_returns_first_feature(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(
            r"https://api\.mapbox\.com/geocoding/v5/mapbox\.places/"
            r"121\.4737,31\.2304\.json.*"
        ),
        json={
            "features": [
                {
                    "id": "address.1",
                    "text": "People's Square",
                    "place_name": "People's Square, Shanghai, China",
                    "geometry": {"coordinates": [121.4737, 31.2304]},
                    "properties": {"feature_type": "address"},
                }
            ]
        },
    )
    provider = MapboxMapProvider(access_token="token")

    place = await provider.reverse_geocode(
        ReverseGeocodeRequest(coordinate={"lat": 31.2304, "lng": 121.4737})
    )

    assert place.id == "mapbox:address.1"
    assert place.name == "People's Square"
    assert place.coordinate is not None
    assert place.coordinate.lat == 31.2304
    assert place.coordinate.lng == 121.4737


async def test_route_maps_duration_and_distance(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://api\.mapbox\.com/directions/v5/mapbox/walking/.*"),
        json={"routes": [{"duration": 900, "distance": 1200}]},
    )
    provider = MapboxMapProvider(access_token="token")
    start = _place("mapbox:start", 31.2304, 121.4737)
    end = _place("mapbox:end", 31.2310, 121.4800)

    route = await provider.route(RouteRequest(from_=start, to=end, mode="walk"))

    assert route.duration_minutes == 15
    assert route.distance_meters == 1200
    assert route.provider == "mapbox"


async def test_route_uses_driving_profile(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://api\.mapbox\.com/directions/v5/mapbox/driving/.*"),
        json={"routes": [{"duration": 60, "distance": 500}]},
    )
    provider = MapboxMapProvider(access_token="token")

    route = await provider.route(
        RouteRequest(
            from_=_place("mapbox:start", 31.2304, 121.4737),
            to=_place("mapbox:end", 31.2310, 121.4800),
            mode="drive",
        )
    )

    assert route.duration_minutes == 1
    assert route.distance_meters == 500


async def test_route_rejects_unsupported_mode() -> None:
    provider = MapboxMapProvider(access_token="token")

    with pytest.raises(ProviderError) as ei:
        await provider.route(
            RouteRequest(
                from_=_place("a", 1, 2),
                to=_place("b", 3, 4),
                mode="transit",
            )
        )
    assert ei.value.code == "capability_unavailable"


async def test_route_rejects_unsupported_mode_before_missing_token() -> None:
    provider = MapboxMapProvider(access_token=None)

    with pytest.raises(ProviderError) as error:
        await provider.route(
            RouteRequest(
                from_=_place("a", 1, 2),
                to=_place("b", 3, 4),
                mode="transit",
            )
        )

    assert error.value.code == "capability_unavailable"


async def test_route_maps_non_list_routes_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://api\.mapbox\.com/directions/v5/mapbox/walking/.*"),
        json={"routes": {"duration": 900, "distance": 1200}},
    )
    provider = MapboxMapProvider(access_token="token")

    with pytest.raises(ProviderError) as error:
        await provider.route(
            RouteRequest(
                from_=_place("mapbox:start", 31.2304, 121.4737),
                to=_place("mapbox:end", 31.2310, 121.4800),
                mode="walk",
            )
        )

    assert error.value.code == "invalid_normalized_payload"


@pytest.mark.parametrize("payload", [{"routes": []}, {}])
async def test_route_maps_no_routes_to_unknown_failure(
    httpx_mock: HTTPXMock,
    payload: dict[str, object],
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://api\.mapbox\.com/directions/v5/mapbox/walking/.*"),
        json=payload,
    )
    provider = MapboxMapProvider(access_token="token")

    with pytest.raises(ProviderError) as error:
        await provider.route(
            RouteRequest(
                from_=_place("mapbox:start", 31.2304, 121.4737),
                to=_place("mapbox:end", 31.2310, 121.4800),
                mode="walk",
            )
        )

    assert error.value.code == "unknown_failure"
    assert str(error.value) == "Mapbox route returned no route"


async def test_route_maps_missing_coordinates_to_invalid_payload() -> None:
    provider = MapboxMapProvider(access_token="token")
    start = NormalizedPlace(
        id="mapbox:start",
        name="start",
        coordinate=None,
        address=None,
        category=None,
        provider="mapbox",
    )

    with pytest.raises(ProviderError) as error:
        await provider.route(
            RouteRequest(
                from_=start,
                to=_place("mapbox:end", 31.2310, 121.4800),
                mode="walk",
            )
        )

    assert error.value.code == "invalid_normalized_payload"


async def test_route_maps_invalid_route_shape_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://api\.mapbox\.com/directions/v5/mapbox/walking/.*"),
        json={"routes": [{"duration": "soon", "distance": 1200}]},
    )
    provider = MapboxMapProvider(access_token="token")

    with pytest.raises(ProviderError) as error:
        await provider.route(
            RouteRequest(
                from_=_place("mapbox:start", 31.2304, 121.4737),
                to=_place("mapbox:end", 31.2310, 121.4800),
                mode="walk",
            )
        )

    assert error.value.code == "invalid_normalized_payload"


def _place(place_id: str, lat: float, lng: float) -> NormalizedPlace:
    return NormalizedPlace(
        id=place_id,
        name=place_id,
        coordinate={"lat": lat, "lng": lng},
        address=None,
        category=None,
        provider="mapbox",
    )
