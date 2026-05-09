from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

import pytest

from app.models.schemas import NormalizedPlace
from app.providers.registry import (
    ProviderRegistryError,
    create_default_provider_registry,
    create_provider_registry,
    get_map_provider_order,
)
from app.providers.types import GeocodeRequest, ProviderHealth


def _place(provider: str, name: str = "Shanghai") -> NormalizedPlace:
    return NormalizedPlace(
        id=f"{provider}:shanghai",
        name=name,
        coordinate={"lat": 31.2304, "lng": 121.4737},
        address=name,
        category="city",
        provider=provider,
    )


@dataclass
class FixtureMapProvider:
    name: str
    geocode_handler: Callable[[GeocodeRequest], Awaitable[object]]
    ok: bool = True

    async def health(self) -> ProviderHealth:
        return ProviderHealth(ok=self.ok, reason=None if self.ok else "fixture unhealthy")

    async def geocode(self, request: GeocodeRequest) -> object:
        return await self.geocode_handler(request)

    async def reverse_geocode(self, request):
        return await self.geocode_handler(GeocodeRequest(query="reverse fixture"))

    async def search_places(self, request):
        return [await self.geocode_handler(GeocodeRequest(query="search fixture"))]

    async def route(self, request):
        raise RuntimeError("route fixture unused")


def test_provider_order_uses_country_code_only() -> None:
    assert get_map_provider_order("CN")[:2] == ["amap", "baidu"]
    assert get_map_provider_order("US")[:2] == ["mapbox", "google"]
    assert get_map_provider_order("cn")[:2] == ["mapbox", "google"]


async def test_routes_china_destinations_to_amap() -> None:
    registry = create_provider_registry(
        map_providers={
            "amap": FixtureMapProvider("amap", lambda request: _async_value(_place("amap"))),
            "mapbox": FixtureMapProvider("mapbox", lambda request: _async_value(_place("mapbox"))),
        }
    )

    place = await registry.geocode(GeocodeRequest(country_code="CN", query="Shanghai"))

    assert place.provider == "amap"


async def test_routes_international_destinations_to_mapbox_even_for_chinese_query() -> None:
    registry = create_provider_registry(
        map_providers={
            "amap": FixtureMapProvider("amap", lambda request: _async_value(_place("amap"))),
            "mapbox": FixtureMapProvider("mapbox", lambda request: _async_value(_place("mapbox"))),
        }
    )

    place = await registry.geocode(GeocodeRequest(country_code="US", query="北京"))

    assert place.provider == "mapbox"


async def test_falls_back_when_primary_times_out() -> None:
    async def never(_: GeocodeRequest) -> NormalizedPlace:
        await asyncio.sleep(10)
        return _place("amap")

    registry = create_provider_registry(
        operation_timeout_ms=1,
        map_providers={
            "amap": FixtureMapProvider("amap", never),
            "mapbox": FixtureMapProvider("mapbox", lambda request: _async_value(_place("mapbox"))),
        },
    )

    place = await registry.geocode(GeocodeRequest(country_code="CN", query="Shanghai"))

    assert place.provider == "mapbox"


async def test_falls_back_when_primary_returns_invalid_payload() -> None:
    registry = create_provider_registry(
        map_providers={
            "amap": FixtureMapProvider("amap", lambda request: _async_value({"coordinate": "31,121"})),
            "mapbox": FixtureMapProvider("mapbox", lambda request: _async_value(_place("mapbox"))),
        },
    )

    place = await registry.geocode(GeocodeRequest(country_code="CN", query="Shanghai"))

    assert place.provider == "mapbox"


async def test_returns_registry_error_when_fallback_also_fails() -> None:
    registry = create_provider_registry(
        map_providers={
            "amap": FixtureMapProvider("amap", lambda request: _async_value({"coordinate": "31,121"})),
            "mapbox": FixtureMapProvider("mapbox", lambda request: _async_value({"provider": "bad"})),
        },
    )

    with pytest.raises(ProviderRegistryError) as ei:
        await registry.geocode(GeocodeRequest(country_code="CN", query="Shanghai"))

    assert ei.value.code == "PROVIDER_FALLBACK_FAILED"
    assert [attempt.provider for attempt in ei.value.attempts] == ["amap", "mapbox"]
    assert ei.value.attempts[0].code == "invalid_normalized_payload"


async def test_default_registry_with_missing_env_gives_clear_provider_attempts() -> None:
    registry = create_default_provider_registry(env={})

    with pytest.raises(ProviderRegistryError) as ei:
        await registry.geocode(GeocodeRequest(country_code="CN", query="Shanghai"))

    assert ei.value.attempts
    assert "AMAP_API_KEY is not configured" in ei.value.attempts[0].message


async def test_registry_exposes_configured_non_map_providers() -> None:
    registry = create_default_provider_registry(env={"TAVILY_API_KEY": "tvly"})

    assert registry.search_provider is not None
    assert registry.weather_provider is not None
    assert registry.supplier_provider is not None


async def test_geocode_requires_country_code() -> None:
    registry = create_provider_registry(
        map_providers={"mapbox": FixtureMapProvider("mapbox", lambda request: _async_value(_place("mapbox")))}
    )

    with pytest.raises(ValueError, match="country_code is required"):
        await registry.geocode(GeocodeRequest(query="Shanghai"))


async def _async_value(value):
    return value
