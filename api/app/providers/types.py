"""Provider contracts ported from web/src/server/providers/types.ts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from app.models.schemas import (
    BudgetBand,
    Coordinate,
    NormalizedPlace,
    NormalizedRoute,
    SourceNote,
)

ProviderId = Literal["amap", "mapbox", "baidu", "google", "tavily"]
MapProviderId = Literal["amap", "mapbox", "baidu", "google"]
ProviderKind = Literal["search", "map", "weather", "supplier"]
ProviderFailureCode = Literal[
    "timeout",
    "network_failure",
    "auth_failure",
    "unhealthy",
    "invalid_normalized_payload",
    "capability_unavailable",
    "unknown_failure",
]


class _StrictProviderModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


@dataclass(frozen=True)
class ProviderHealth:
    ok: bool
    reason: str | None = None


@dataclass(frozen=True)
class ProviderAttemptFailure:
    provider: ProviderId
    kind: ProviderKind
    operation: str
    code: ProviderFailureCode
    message: str


class ProviderError(Exception):
    """Structured provider failure used by adapters and registry."""

    def __init__(
        self,
        *,
        provider: ProviderId,
        kind: ProviderKind,
        code: ProviderFailureCode,
        message: str,
        cause: object | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.kind = kind
        self.code = code
        self.cause = cause


@dataclass(frozen=True)
class GeocodeRequest:
    query: str
    country_code: str | None = None
    bias: Coordinate | None = None


@dataclass(frozen=True)
class ReverseGeocodeRequest:
    coordinate: Coordinate


@dataclass(frozen=True)
class PlaceSearchRequest:
    query: str
    country_code: str | None = None
    bias: Coordinate | None = None
    limit: int | None = None
    category: str | None = None


@dataclass(frozen=True)
class RouteRequest:
    from_: NormalizedPlace
    to: NormalizedPlace
    mode: Literal["walk", "transit", "drive", "rail", "flight"]


@dataclass(frozen=True)
class SearchRequest:
    query: str
    country_code: str | None = None
    limit: int | None = None


class SearchResult(_StrictProviderModel):
    title: str
    url: str | None
    snippet: str
    source_note: SourceNote | None


@dataclass(frozen=True)
class WeatherRequest:
    place: NormalizedPlace
    start_date: str
    duration_days: int


class WeatherSummary(_StrictProviderModel):
    provider: MapProviderId
    place: NormalizedPlace
    summary: str
    daily_notes: list[str]
    source_note: SourceNote | None


@dataclass(frozen=True)
class SupplierRequest:
    destination: NormalizedPlace
    start_date: str
    duration_days: int
    currency: str


class SupplierReference(_StrictProviderModel):
    name: str
    category: Literal["hotel", "transport", "activity"]
    price_band: BudgetBand | None
    note: str
    source_note: SourceNote | None


class SearchProvider(Protocol):
    name: ProviderId

    async def health(self) -> ProviderHealth: ...

    async def search(self, request: SearchRequest) -> list[SearchResult]: ...


class MapProvider(Protocol):
    name: MapProviderId

    async def health(self) -> ProviderHealth: ...

    async def geocode(self, request: GeocodeRequest) -> NormalizedPlace: ...

    async def reverse_geocode(self, request: ReverseGeocodeRequest) -> NormalizedPlace: ...

    async def search_places(self, request: PlaceSearchRequest) -> list[NormalizedPlace]: ...

    async def route(self, request: RouteRequest) -> NormalizedRoute: ...


class WeatherProvider(Protocol):
    name: ProviderId

    async def health(self) -> ProviderHealth: ...

    async def get_weather_summary(self, request: WeatherRequest) -> WeatherSummary: ...


class SupplierProvider(Protocol):
    name: ProviderId

    async def health(self) -> ProviderHealth: ...

    async def get_sample_references(self, request: SupplierRequest) -> list[SupplierReference]: ...
