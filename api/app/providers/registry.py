"""Provider registry and map fallback orchestration."""
from __future__ import annotations

import asyncio
import contextlib
import os
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import TypeAdapter, ValidationError

from app.domain.geography import is_china_destination
from app.models.schemas import NormalizedPlace, NormalizedRoute
from app.providers.map.amap import AMapMapProvider
from app.providers.map.amap_mcp import AMapMCPMapProvider
from app.providers.map.mapbox import MapboxMapProvider
from app.providers.search.tavily import TavilySearchProvider
from app.providers.supplier import create_unavailable_supplier_provider
from app.providers.types import (
    GeocodeRequest,
    MapProvider,
    MapProviderId,
    PlaceSearchRequest,
    ProviderAttemptFailure,
    ProviderError,
    ProviderFailureCode,
    ProviderHealth,
    ProviderId,
    ProviderKind,
    ReverseGeocodeRequest,
    RouteRequest,
    SearchProvider,
    SupplierProvider,
    WeatherProvider,
)
from app.providers.weather import create_unavailable_weather_provider

T = TypeVar("T")
DEFAULT_OPERATION_TIMEOUT_MS = 8_000
_NORMALIZED_PLACE_LIST = TypeAdapter(list[NormalizedPlace])


@dataclass(frozen=True)
class ProviderRegistryConfig:
    map_providers: Mapping[MapProviderId, MapProvider]
    search_provider: SearchProvider | None = None
    weather_provider: WeatherProvider | None = None
    supplier_provider: SupplierProvider | None = None
    operation_timeout_ms: int = DEFAULT_OPERATION_TIMEOUT_MS


class ProviderRegistryError(Exception):
    code = "PROVIDER_FALLBACK_FAILED"

    def __init__(self, operation: str, attempts: list[ProviderAttemptFailure]) -> None:
        super().__init__(f"All configured providers failed for {operation}")
        self.operation = operation
        self.attempts = attempts


class TravelDataProviderRegistry:
    def __init__(self, config: ProviderRegistryConfig) -> None:
        self._map_providers = dict(config.map_providers)
        self.search_provider = config.search_provider
        self.weather_provider = config.weather_provider
        self.supplier_provider = config.supplier_provider
        self._operation_timeout_ms = config.operation_timeout_ms

    async def geocode(self, request: GeocodeRequest) -> NormalizedPlace:
        if not request.country_code:
            raise ValueError("country_code is required for registry geocode")
        return await self._run_map_operation(
            country_code=request.country_code,
            operation="geocode",
            execute=lambda provider: provider.geocode(request),
            validate=NormalizedPlace.model_validate,
        )

    async def reverse_geocode(
        self, country_code: str, request: ReverseGeocodeRequest
    ) -> NormalizedPlace:
        return await self._run_map_operation(
            country_code=country_code,
            operation="reverse_geocode",
            execute=lambda provider: provider.reverse_geocode(request),
            validate=NormalizedPlace.model_validate,
        )

    async def search_places(
        self, request: PlaceSearchRequest
    ) -> list[NormalizedPlace]:
        if not request.country_code:
            raise ValueError("country_code is required for registry search_places")
        return await self._run_map_operation(
            country_code=request.country_code,
            operation="search_places",
            execute=lambda provider: provider.search_places(request),
            validate=_NORMALIZED_PLACE_LIST.validate_python,
        )

    async def route(
        self, country_code: str, request: RouteRequest
    ) -> NormalizedRoute:
        return await self._run_map_operation(
            country_code=country_code,
            operation="route",
            execute=lambda provider: provider.route(request),
            validate=NormalizedRoute.model_validate,
        )

    async def _run_map_operation(
        self,
        *,
        country_code: str,
        operation: str,
        execute: Callable[[MapProvider], Awaitable[Any]],
        validate: Callable[[Any], T],
    ) -> T:
        attempts: list[ProviderAttemptFailure] = []

        for provider in self._get_map_provider_run_list(country_code):
            health = await self._check_health(provider, operation)
            if not health.ok:
                attempts.append(
                    ProviderAttemptFailure(
                        provider=provider.name,
                        kind="map",
                        operation=operation,
                        code="unhealthy",
                        message=health.reason or f"{provider.name} is unhealthy",
                    )
                )
                continue

            try:
                raw = await self._with_timeout(
                    lambda: execute(provider),
                    provider.name,
                    "map",
                    operation,
                )
                return validate(raw)
            except (
                ConnectionError,
                ProviderError,
                TimeoutError,
                ValidationError,
            ) as exc:
                attempts.append(to_attempt_failure(provider.name, "map", operation, exc))

        raise ProviderRegistryError(operation, attempts)

    def _get_map_provider_run_list(self, country_code: str) -> list[MapProvider]:
        provider_order = get_map_provider_order(country_code)
        primary_id, *fallback_ids = provider_order
        providers: list[MapProvider] = []

        primary = self._map_providers.get(primary_id)
        if primary:
            providers.append(primary)

        fallback = next(
            (
                self._map_providers[provider_id]
                for provider_id in fallback_ids
                if provider_id in self._map_providers
            ),
            None,
        )
        if fallback:
            providers.append(fallback)

        if not providers and self._map_providers:
            providers.append(next(iter(self._map_providers.values())))

        return providers

    async def _check_health(
        self, provider: MapProvider, operation: str
    ) -> ProviderHealth:
        try:
            return await self._with_timeout(
                provider.health,
                provider.name,
                "map",
                f"{operation}:health",
            )
        except (
            ConnectionError,
            ProviderError,
            TimeoutError,
            ValidationError,
        ) as exc:
            failure = to_attempt_failure(
                provider.name,
                "map",
                f"{operation}:health",
                exc,
            )
            return ProviderHealth(ok=False, reason=failure.message)

    async def _with_timeout(
        self,
        operation: Callable[[], Awaitable[T]],
        provider: ProviderId,
        kind: ProviderKind,
        operation_name: str,
    ) -> T:
        task = asyncio.create_task(operation())
        try:
            return await asyncio.wait_for(
                task,
                timeout=self._operation_timeout_ms / 1000,
            )
        except asyncio.TimeoutError as exc:
            if task.done() and not task.cancelled():
                return task.result()
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            raise ProviderError(
                provider=provider,
                kind=kind,
                code="timeout",
                message=(
                    f"{provider} {operation_name} timed out after "
                    f"{self._operation_timeout_ms}ms"
                ),
                cause=exc,
            ) from exc
        except asyncio.CancelledError:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            raise


def create_provider_registry(
    *,
    map_providers: Mapping[MapProviderId, MapProvider],
    search_provider: SearchProvider | None = None,
    weather_provider: WeatherProvider | None = None,
    supplier_provider: SupplierProvider | None = None,
    operation_timeout_ms: int = DEFAULT_OPERATION_TIMEOUT_MS,
) -> TravelDataProviderRegistry:
    return TravelDataProviderRegistry(
        ProviderRegistryConfig(
            map_providers=map_providers,
            search_provider=search_provider,
            weather_provider=weather_provider,
            supplier_provider=supplier_provider,
            operation_timeout_ms=operation_timeout_ms,
        )
    )


def create_default_provider_registry(
    env: Mapping[str, str] | None = None,
) -> TravelDataProviderRegistry:
    source = env if env is not None else os.environ
    return create_provider_registry(
        map_providers={
            "amap": _create_default_amap_provider(source),
            "mapbox": MapboxMapProvider(
                access_token=source.get("MAPBOX_ACCESS_TOKEN")
            ),
        },
        search_provider=TavilySearchProvider(api_key=source.get("TAVILY_API_KEY")),
        weather_provider=create_unavailable_weather_provider(),
        supplier_provider=create_unavailable_supplier_provider(),
    )


def _create_default_amap_provider(source: Mapping[str, str]) -> MapProvider:
    mcp_url = source.get("AMAP_MCP_URL")
    if mcp_url:
        return AMapMCPMapProvider(mcp_url=mcp_url)
    return AMapMapProvider(api_key=source.get("AMAP_API_KEY"))


def get_map_provider_order(country_code: str) -> list[MapProviderId]:
    if is_china_destination(country_code):
        return ["amap", "baidu", "mapbox", "google"]
    return ["mapbox", "google", "amap", "baidu"]


def to_attempt_failure(
    provider: ProviderId,
    kind: ProviderKind,
    operation: str,
    error: Exception,
) -> ProviderAttemptFailure:
    if isinstance(error, ProviderError):
        return ProviderAttemptFailure(
            provider=provider,
            kind=kind,
            operation=operation,
            code=error.code,
            message=str(error),
        )

    if isinstance(error, ValidationError):
        return ProviderAttemptFailure(
            provider=provider,
            kind=kind,
            operation=operation,
            code="invalid_normalized_payload",
            message=str(error),
        )

    return ProviderAttemptFailure(
        provider=provider,
        kind=kind,
        operation=operation,
        code=infer_provider_failure_code(error),
        message=str(error),
    )


def infer_provider_failure_code(error: Exception) -> ProviderFailureCode:
    if isinstance(error, (ConnectionError, TimeoutError)):
        return "network_failure"
    return "unknown_failure"
