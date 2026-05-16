from __future__ import annotations

from app.models.schemas import Coordinate, NormalizedPlace, SourceNote


def fixture_provider_for_country(country_code: str) -> str:
    return "amap" if country_code == "CN" else "mapbox"


def fixture_place(id_suffix: str, name: str, provider: str) -> NormalizedPlace:
    offset = len(id_suffix) / 1000
    return NormalizedPlace(
        id=f"place_{id_suffix}",
        name=name,
        coordinate=Coordinate(lat=31.23 + offset, lng=121.47 + offset),
        address=name,
        category="poi",
        provider=provider,
    )


def fixture_source_note() -> SourceNote:
    return SourceNote(
        provider="fixture",
        url=None,
        note="Fixture-backed MVP discovery; live enrichment uses configured providers.",
    )
