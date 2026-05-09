"""Mapbox map provider adapter."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from app.models.schemas import NormalizedPlace, NormalizedRoute
from app.providers.types import (
    GeocodeRequest,
    PlaceSearchRequest,
    ProviderError,
    ProviderFailureCode,
    ProviderHealth,
    ReverseGeocodeRequest,
    RouteRequest,
)

MAPBOX_BASE_URL = "https://api.mapbox.com"


class MapboxMapProvider:
    name = "mapbox"

    def __init__(
        self, *, access_token: str | None = None, base_url: str = MAPBOX_BASE_URL
    ) -> None:
        self._access_token = access_token
        self._base_url = base_url.rstrip("/")

    async def health(self) -> ProviderHealth:
        if not self._access_token:
            return ProviderHealth(
                ok=False, reason="MAPBOX_ACCESS_TOKEN is not configured"
            )
        return ProviderHealth(ok=True)

    async def geocode(self, request: GeocodeRequest) -> NormalizedPlace:
        features = await self._fetch_forward_geocode(
            request, request.country_code, 1
        )
        first = features[0] if features else None
        if first is None:
            raise self._provider_error(
                "unknown_failure", "Mapbox geocode returned no place"
            )
        if not isinstance(first, dict):
            raise self._invalid_payload_error(
                "Mapbox geocode returned invalid feature"
            )
        return normalize_mapbox_feature(first)

    async def reverse_geocode(
        self, request: ReverseGeocodeRequest
    ) -> NormalizedPlace:
        token = self._require_access_token()
        lat, lng = _coordinate_lat_lng(request.coordinate)
        path = (
            "/geocoding/v5/mapbox.places/"
            f"{lng},{lat}.json"
        )
        body = await self._fetch_json(
            path, {"access_token": token, "limit": "1"}, "reverseGeocode"
        )
        features = _expect_list(body.get("features"), "Mapbox reverse geocode features")
        first = features[0] if features else None
        if first is None:
            raise self._provider_error(
                "unknown_failure", "Mapbox reverse geocode returned no place"
            )
        if not isinstance(first, dict):
            raise self._invalid_payload_error(
                "Mapbox reverse geocode returned invalid feature"
            )
        return normalize_mapbox_feature(first)

    async def search_places(
        self, request: PlaceSearchRequest
    ) -> list[NormalizedPlace]:
        features = await self._fetch_forward_geocode(
            request, request.country_code, request.limit or 10
        )
        normalized: list[NormalizedPlace] = []
        for feature in features:
            if not isinstance(feature, dict):
                raise self._invalid_payload_error(
                    "Mapbox search returned invalid feature"
                )
            normalized.append(normalize_mapbox_feature(feature))
        return normalized

    async def route(self, request: RouteRequest) -> NormalizedRoute:
        profile = _to_mapbox_directions_profile(request.mode)
        token = self._require_access_token()
        if request.from_.coordinate is None or request.to.coordinate is None:
            raise self._invalid_payload_error("Mapbox route requires coordinates")

        coordinates = (
            f"{request.from_.coordinate.lng},{request.from_.coordinate.lat};"
            f"{request.to.coordinate.lng},{request.to.coordinate.lat}"
        )
        body = await self._fetch_json(
            f"/directions/v5/mapbox/{profile}/{coordinates}",
            {"access_token": token, "overview": "false"},
            "route",
        )
        routes = _expect_list(body.get("routes"), "Mapbox routes")
        if not routes:
            raise self._provider_error(
                "unknown_failure", "Mapbox route returned no route"
            )
        first = routes[0]
        if (
            not isinstance(first, dict)
            or not isinstance(first.get("duration"), (int, float))
            or not isinstance(first.get("distance"), (int, float))
        ):
            raise self._invalid_payload_error("Mapbox route returned invalid route")

        try:
            return NormalizedRoute.model_validate(
                {
                    "from": request.from_,
                    "to": request.to,
                    "mode": request.mode,
                    "duration_minutes": round(first["duration"] / 60),
                    "distance_meters": first["distance"],
                    "cost_estimate": None,
                    "provider": "mapbox",
                }
            )
        except ValidationError as exc:
            raise self._invalid_payload_error(
                "Invalid Mapbox normalized route payload", exc
            ) from exc

    async def _fetch_forward_geocode(
        self,
        request: GeocodeRequest | PlaceSearchRequest,
        country_code: str | None,
        limit: int,
    ) -> list[Any]:
        token = self._require_access_token()
        params = {
            "access_token": token,
            "limit": str(limit),
        }
        if country_code:
            params["country"] = country_code
        if request.bias:
            params["proximity"] = f"{request.bias.lng},{request.bias.lat}"

        body = await self._fetch_json(
            f"/geocoding/v5/mapbox.places/{quote(request.query, safe='')}.json",
            params,
            "geocode",
        )
        return _expect_list(body.get("features"), "Mapbox features")

    async def _fetch_json(
        self, path: str, params: dict[str, str], operation: str
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self._base_url}{path}", params=params)
        except httpx.HTTPError as exc:
            raise self._provider_error(
                "network_failure", f"Mapbox {operation} network failure", exc
            ) from exc

        if response.status_code in (401, 403):
            raise self._provider_error(
                "auth_failure", f"Mapbox {operation} auth failure"
            )
        if not response.is_success:
            raise self._provider_error(
                "network_failure", f"Mapbox {operation} HTTP {response.status_code}"
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise self._invalid_payload_error(
                f"Mapbox {operation} returned malformed JSON", exc
            ) from exc

        if not isinstance(body, dict):
            raise self._invalid_payload_error(
                f"Mapbox {operation} returned non-object JSON"
            )
        return body

    def _require_access_token(self) -> str:
        if not self._access_token:
            raise self._provider_error(
                "auth_failure", "MAPBOX_ACCESS_TOKEN is not configured"
            )
        return self._access_token

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
        self, message: str, cause: object | None = None
    ) -> ProviderError:
        return self._provider_error(
            "invalid_normalized_payload",
            message,
            cause,
        )


def normalize_mapbox_feature(feature: dict[str, Any]) -> NormalizedPlace:
    geometry = feature.get("geometry") or {}
    if not isinstance(geometry, dict):
        raise ProviderError(
            provider="mapbox",
            kind="map",
            code="invalid_normalized_payload",
            message="Invalid Mapbox feature geometry",
        )
    coordinates = geometry.get("coordinates") or []
    if not isinstance(coordinates, list):
        raise ProviderError(
            provider="mapbox",
            kind="map",
            code="invalid_normalized_payload",
            message="Invalid Mapbox feature coordinates",
        )
    lng = coordinates[0] if len(coordinates) >= 1 else None
    lat = coordinates[1] if len(coordinates) >= 2 else None
    properties = feature.get("properties") or {}
    if not isinstance(properties, dict):
        raise ProviderError(
            provider="mapbox",
            kind="map",
            code="invalid_normalized_payload",
            message="Invalid Mapbox feature properties",
        )

    name = properties.get("name") or feature.get("text") or feature.get("place_name")
    coordinate = (
        {"lat": lat, "lng": lng}
        if isinstance(lat, (int, float)) and isinstance(lng, (int, float))
        else None
    )
    fallback_id = quote(f"{name or 'place'}:{lng},{lat}", safe="")

    try:
        return NormalizedPlace.model_validate(
            {
                "id": f"mapbox:{feature.get('id') or fallback_id}",
                "name": name,
                "coordinate": coordinate,
                "address": properties.get("full_address") or feature.get("place_name"),
                "category": properties.get("feature_type") or feature.get("type"),
                "provider": "mapbox",
            }
        )
    except ValidationError as exc:
        raise ProviderError(
            provider="mapbox",
            kind="map",
            code="invalid_normalized_payload",
            message="Invalid Mapbox normalized place payload",
            cause=exc,
        ) from exc


def _expect_list(value: object, label: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ProviderError(
            provider="mapbox",
            kind="map",
            code="invalid_normalized_payload",
            message=f"{label} must be a list",
        )
    return value


def _coordinate_lat_lng(coordinate: object) -> tuple[float, float]:
    if isinstance(coordinate, dict):
        lat = coordinate.get("lat")
        lng = coordinate.get("lng")
    else:
        lat = getattr(coordinate, "lat", None)
        lng = getattr(coordinate, "lng", None)

    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        raise ProviderError(
            provider="mapbox",
            kind="map",
            code="invalid_normalized_payload",
            message="Invalid Mapbox reverse geocode coordinate",
        )
    return lat, lng


def _to_mapbox_directions_profile(mode: str) -> str:
    if mode == "walk":
        return "walking"
    if mode == "drive":
        return "driving"
    raise ProviderError(
        provider="mapbox",
        kind="map",
        code="capability_unavailable",
        message=f"Mapbox routing does not support {mode} routes in this adapter",
    )
