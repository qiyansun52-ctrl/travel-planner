from __future__ import annotations

import pytest

from app.models.schemas import NormalizedPlace
from app.providers.supplier import create_unavailable_supplier_provider
from app.providers.types import ProviderError, SupplierRequest, WeatherRequest
from app.providers.weather import create_unavailable_weather_provider


def _place() -> NormalizedPlace:
    return NormalizedPlace(
        id="mapbox:shanghai",
        name="Shanghai",
        coordinate={"lat": 31.2304, "lng": 121.4737},
        address="Shanghai",
        category="city",
        provider="mapbox",
    )


async def test_unavailable_weather_provider_health_and_error() -> None:
    provider = create_unavailable_weather_provider()

    health = await provider.health()
    assert health.ok is False
    assert health.reason == "Weather provider is not configured"

    with pytest.raises(ProviderError) as ei:
        await provider.get_weather_summary(
            WeatherRequest(place=_place(), start_date="2026-06-01", duration_days=3)
        )
    assert ei.value.kind == "weather"
    assert ei.value.code == "capability_unavailable"


async def test_unavailable_supplier_provider_health_and_error() -> None:
    provider = create_unavailable_supplier_provider()

    health = await provider.health()
    assert health.ok is False
    assert health.reason == "Supplier provider is not configured"

    with pytest.raises(ProviderError) as ei:
        await provider.get_sample_references(
            SupplierRequest(destination=_place(), start_date="2026-06-01", duration_days=3, currency="CNY")
        )
    assert ei.value.kind == "supplier"
    assert ei.value.code == "capability_unavailable"
