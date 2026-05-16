from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.schemas import BudgetBand, NormalizedPlace, SourceNote
from app.providers.types import (
    ProviderError,
    ProviderHealth,
    SearchRequest,
    SearchResult,
    SupplierReference,
    WeatherRequest,
    WeatherSummary,
)


def test_provider_error_exposes_structured_fields() -> None:
    cause = RuntimeError("boom")
    err = ProviderError(
        provider="mapbox",
        kind="map",
        code="network_failure",
        message="Mapbox failed",
        cause=cause,
    )

    assert str(err) == "Mapbox failed"
    assert err.provider == "mapbox"
    assert err.kind == "map"
    assert err.code == "network_failure"
    assert err.cause is cause


def test_provider_health_defaults_to_ok_without_reason() -> None:
    assert ProviderHealth(ok=True).reason is None


def test_search_result_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SearchResult.model_validate({
            "title": "Guide",
            "url": "https://example.com",
            "snippet": "Useful",
            "source_note": None,
            "extra": "nope",
        })


def test_request_and_result_shapes_accept_expected_payloads() -> None:
    place = NormalizedPlace(
        id="mapbox:shanghai",
        name="Shanghai",
        coordinate={"lat": 31.2304, "lng": 121.4737},
        address="Shanghai",
        category="place",
        provider="mapbox",
    )
    band = BudgetBand(currency="CNY", low=100, high=300, confidence="medium", basis="per_trip")

    assert SearchRequest(query="Shanghai food", country_code="CN", limit=5).limit == 5
    assert WeatherRequest(place=place, start_date="2026-06-01", duration_days=3).duration_days == 3
    assert WeatherSummary(
        provider="google",
        place=place,
        summary="Warm",
        daily_notes=["Bring an umbrella"],
        source_note=SourceNote(provider="fixture", url=None, note="fixture"),
    ).summary == "Warm"
    assert SupplierReference(
        name="Sample hotel",
        category="hotel",
        price_band=band,
        note="Reference only",
        source_note=None,
    ).price_band == band
