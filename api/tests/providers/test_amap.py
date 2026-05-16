from __future__ import annotations

import re

import pytest
from pytest_httpx import HTTPXMock

from app.providers.map.amap import AMapMapProvider, normalize_amap_place
from app.providers.types import GeocodeRequest, PlaceSearchRequest, ProviderError


async def test_health_reports_missing_key() -> None:
    provider = AMapMapProvider(api_key=None)

    health = await provider.health()

    assert health.ok is False
    assert health.reason == "AMAP_API_KEY is not configured"


def test_normalize_amap_place_converts_gcj02_to_wgs84() -> None:
    place = normalize_amap_place(
        {
            "id": "B0FFG123",
            "name": "人民广场",
            "address": "上海市黄浦区",
            "category": "landmark",
            "location": "121.4737,31.2304",
        }
    )

    assert place.provider == "amap"
    assert place.id == "amap:B0FFG123"
    assert place.coordinate is not None
    assert place.coordinate.lat != 31.2304
    assert place.coordinate.lng != 121.4737


def test_normalize_amap_place_requires_location() -> None:
    with pytest.raises(ProviderError) as error:
        normalize_amap_place({"id": "x", "name": "No location"})

    assert error.value.provider == "amap"
    assert error.value.kind == "map"
    assert error.value.code == "invalid_normalized_payload"


def test_normalize_amap_place_wraps_validation_errors() -> None:
    with pytest.raises(ProviderError) as error:
        normalize_amap_place(
            {
                "id": "x",
                "name": ["Invalid name"],
                "location": "121.4737,31.2304",
            }
        )

    assert error.value.code == "invalid_normalized_payload"


async def test_geocode_normalizes_first_result(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://restapi\.amap\.com/v3/geocode/geo.*"),
        json={
            "status": "1",
            "geocodes": [
                {
                    "adcode": "310000",
                    "formatted_address": "上海市",
                    "location": "121.4737,31.2304",
                    "level": "city",
                }
            ],
        },
    )
    provider = AMapMapProvider(api_key="key")

    place = await provider.geocode(GeocodeRequest(query="上海", country_code="CN"))

    assert place.id == "amap:310000"
    assert place.name == "上海"
    assert place.address == "上海市"
    assert place.category == "city"


async def test_geocode_maps_redirect_to_network_failure(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://restapi\.amap\.com/v3/geocode/geo.*"),
        status_code=302,
        headers={"Location": "https://example.com/login"},
    )
    provider = AMapMapProvider(api_key="key")

    with pytest.raises(ProviderError) as error:
        await provider.geocode(GeocodeRequest(query="上海", country_code="CN"))

    assert error.value.code == "network_failure"


async def test_geocode_maps_401_to_auth_failure(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://restapi\.amap\.com/v3/geocode/geo.*"),
        status_code=401,
    )
    provider = AMapMapProvider(api_key="key")

    with pytest.raises(ProviderError) as error:
        await provider.geocode(GeocodeRequest(query="上海", country_code="CN"))

    assert error.value.code == "auth_failure"


async def test_geocode_maps_amap_status_failure_to_unknown_failure(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://restapi\.amap\.com/v3/geocode/geo.*"),
        json={"status": "0", "info": "INVALID_USER_KEY"},
    )
    provider = AMapMapProvider(api_key="key")

    with pytest.raises(ProviderError) as error:
        await provider.geocode(GeocodeRequest(query="上海", country_code="CN"))

    assert error.value.code == "unknown_failure"


async def test_geocode_maps_malformed_json_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://restapi\.amap\.com/v3/geocode/geo.*"),
        content=b"{",
    )
    provider = AMapMapProvider(api_key="key")

    with pytest.raises(ProviderError) as error:
        await provider.geocode(GeocodeRequest(query="上海", country_code="CN"))

    assert error.value.code == "invalid_normalized_payload"


async def test_geocode_maps_non_dict_json_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://restapi\.amap\.com/v3/geocode/geo.*"),
        json=[],
    )
    provider = AMapMapProvider(api_key="key")

    with pytest.raises(ProviderError) as error:
        await provider.geocode(GeocodeRequest(query="上海", country_code="CN"))

    assert error.value.code == "invalid_normalized_payload"


async def test_geocode_maps_non_list_geocodes_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://restapi\.amap\.com/v3/geocode/geo.*"),
        json={"status": "1", "geocodes": {"location": "121.4737,31.2304"}},
    )
    provider = AMapMapProvider(api_key="key")

    with pytest.raises(ProviderError) as error:
        await provider.geocode(GeocodeRequest(query="上海", country_code="CN"))

    assert error.value.code == "invalid_normalized_payload"


async def test_geocode_maps_non_dict_first_geocode_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://restapi\.amap\.com/v3/geocode/geo.*"),
        json={"status": "1", "geocodes": ["not-a-place"]},
    )
    provider = AMapMapProvider(api_key="key")

    with pytest.raises(ProviderError) as error:
        await provider.geocode(GeocodeRequest(query="上海", country_code="CN"))

    assert error.value.code == "invalid_normalized_payload"


async def test_search_places_normalizes_pois(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://restapi\.amap\.com/v3/place/text.*"),
        json={
            "status": "1",
            "pois": [
                {
                    "id": "B0FFG123",
                    "name": "人民广场",
                    "formatted_address": "上海市黄浦区",
                    "type": "landmark",
                    "location": "121.4737,31.2304",
                }
            ],
        },
    )
    provider = AMapMapProvider(api_key="key")

    places = await provider.search_places(
        PlaceSearchRequest(query="人民广场", country_code="CN", limit=1)
    )

    assert [p.id for p in places] == ["amap:B0FFG123"]


async def test_search_places_maps_non_list_pois_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://restapi\.amap\.com/v3/place/text.*"),
        json={"status": "1", "pois": {"id": "B0FFG123"}},
    )
    provider = AMapMapProvider(api_key="key")

    with pytest.raises(ProviderError) as error:
        await provider.search_places(
            PlaceSearchRequest(query="人民广场", country_code="CN", limit=1)
        )

    assert error.value.code == "invalid_normalized_payload"


async def test_search_places_maps_non_dict_poi_to_invalid_payload(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://restapi\.amap\.com/v3/place/text.*"),
        json={"status": "1", "pois": ["not-a-place"]},
    )
    provider = AMapMapProvider(api_key="key")

    with pytest.raises(ProviderError) as error:
        await provider.search_places(
            PlaceSearchRequest(query="人民广场", country_code="CN", limit=1)
        )

    assert error.value.code == "invalid_normalized_payload"


async def test_reverse_and_route_are_explicitly_unavailable() -> None:
    provider = AMapMapProvider(api_key="key")

    with pytest.raises(ProviderError) as reverse:
        await provider.reverse_geocode(None)  # type: ignore[arg-type]
    assert reverse.value.code == "capability_unavailable"

    with pytest.raises(ProviderError) as route:
        await provider.route(None)  # type: ignore[arg-type]
    assert route.value.code == "capability_unavailable"
