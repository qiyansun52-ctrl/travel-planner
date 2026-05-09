"""AMap map provider adapter."""
from __future__ import annotations

import math
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from app.models.schemas import Coordinate, NormalizedPlace, NormalizedRoute
from app.providers.map.coord import convert_gcj02_to_wgs84
from app.providers.types import (
    GeocodeRequest,
    PlaceSearchRequest,
    ProviderError,
    ProviderFailureCode,
    ProviderHealth,
    ReverseGeocodeRequest,
    RouteRequest,
)

AMAP_BASE_URL = "https://restapi.amap.com"


class AMapMapProvider:
    name = "amap"

    def __init__(
        self, *, api_key: str | None = None, base_url: str = AMAP_BASE_URL
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def health(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(ok=False, reason="AMAP_API_KEY is not configured")
        return ProviderHealth(ok=True)

    async def geocode(self, request: GeocodeRequest) -> NormalizedPlace:
        api_key = self._require_api_key()
        body = await self._fetch_json(
            "/v3/geocode/geo",
            {"key": api_key, "address": request.query},
            "geocode",
        )
        if body.get("status") != "1":
            raise self._provider_error(
                "unknown_failure", body.get("info") or "AMap geocode failed"
            )

        geocodes = body.get("geocodes", [])
        if "geocodes" in body and not isinstance(geocodes, list):
            raise self._invalid_payload_error("AMap geocode payload geocodes is invalid")

        first = (geocodes or [None])[0]
        if first is not None and not isinstance(first, dict):
            raise self._invalid_payload_error("AMap geocode payload place is invalid")
        if not first or not first.get("location"):
            raise self._provider_error("unknown_failure", "AMap geocode returned no place")

        return normalize_amap_place(
            {
                "id": first.get("adcode"),
                "name": request.query,
                "formatted_address": first.get("formatted_address"),
                "category": first.get("level"),
                "location": first["location"],
            }
        )

    async def reverse_geocode(
        self, request: ReverseGeocodeRequest
    ) -> NormalizedPlace:
        raise self._provider_error(
            "capability_unavailable", "AMap reverse geocoding is not wired yet"
        )

    async def search_places(
        self, request: PlaceSearchRequest
    ) -> list[NormalizedPlace]:
        api_key = self._require_api_key()
        body = await self._fetch_json(
            "/v3/place/text",
            {
                "key": api_key,
                "keywords": request.query,
                "offset": str(request.limit or 10),
            },
            "searchPlaces",
        )
        if body.get("status") != "1":
            raise self._provider_error(
                "unknown_failure", body.get("info") or "AMap place search failed"
            )

        pois = body.get("pois", [])
        if "pois" in body and not isinstance(pois, list):
            raise self._invalid_payload_error("AMap place search payload pois is invalid")
        for poi in pois:
            if not isinstance(poi, dict):
                raise self._invalid_payload_error(
                    "AMap place search payload place is invalid"
                )

        return [normalize_amap_place(poi) for poi in pois]

    async def route(self, request: RouteRequest) -> NormalizedRoute:
        raise self._provider_error(
            "capability_unavailable", "AMap routing is not wired yet"
        )

    async def _fetch_json(
        self, path: str, params: dict[str, str], operation: str
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self._base_url}{path}", params=params)
        except httpx.HTTPError as exc:
            raise self._provider_error(
                "network_failure", f"AMap {operation} network failure", exc
            ) from exc

        if response.status_code in (401, 403):
            raise self._provider_error("auth_failure", f"AMap {operation} auth failure")
        if not response.is_success:
            raise self._provider_error(
                "network_failure", f"AMap {operation} HTTP {response.status_code}"
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise self._invalid_payload_error(
                f"AMap {operation} returned malformed JSON", exc
            ) from exc

        if not isinstance(body, dict):
            raise self._invalid_payload_error(
                f"AMap {operation} returned non-object JSON"
            )
        return body

    def _require_api_key(self) -> str:
        if not self._api_key:
            raise self._provider_error("auth_failure", "AMAP_API_KEY is not configured")
        return self._api_key

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


def normalize_amap_place(payload: dict[str, Any]) -> NormalizedPlace:
    coordinate = convert_gcj02_to_wgs84(_parse_amap_location(payload.get("location")))
    stable_id = payload.get("id") or _create_stable_amap_id(payload)

    try:
        return NormalizedPlace.model_validate(
            {
                "id": f"amap:{stable_id}",
                "name": (
                    payload.get("name")
                    or payload.get("formatted_address")
                    or payload.get("address")
                    or "AMap place"
                ),
                "coordinate": coordinate,
                "address": payload.get("formatted_address") or payload.get("address"),
                "category": payload.get("category") or payload.get("type"),
                "provider": "amap",
            }
        )
    except ValidationError as exc:
        raise ProviderError(
            provider="amap",
            kind="map",
            code="invalid_normalized_payload",
            message="Invalid AMap normalized place payload",
            cause=exc,
        ) from exc


def _parse_amap_location(location: object) -> Coordinate:
    try:
        if not isinstance(location, str):
            raise ValueError("location must be a string")
        lng_text, lat_text = location.split(",", 1)
        lng = float(lng_text)
        lat = float(lat_text)
        if not math.isfinite(lat) or not math.isfinite(lng):
            raise ValueError("location coordinates must be finite")
    except ValueError as exc:
        raise ProviderError(
            provider="amap",
            kind="map",
            code="invalid_normalized_payload",
            message=f"Invalid AMap location: {location}",
            cause=exc,
        ) from exc
    return Coordinate(lat=lat, lng=lng)


def _create_stable_amap_id(payload: dict[str, Any]) -> str:
    label = payload.get("name") or payload.get("formatted_address") or "place"
    return quote(f"{label}:{payload.get('location', '')}", safe="")
