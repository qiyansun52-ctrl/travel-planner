"""AMap MCP map provider adapter."""
from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from typing import Any, Protocol

from pydantic import ValidationError

from app.models.schemas import NormalizedPlace, NormalizedRoute
from app.providers.map.amap import normalize_amap_place
from app.providers.types import (
    GeocodeRequest,
    PlaceSearchRequest,
    ProviderError,
    ProviderFailureCode,
    ProviderHealth,
    ReverseGeocodeRequest,
    RouteRequest,
)


class MCPToolClient(Protocol):
    async def call_tool(self, name: str, arguments: dict[str, object]) -> object: ...


class StreamableHttpMCPToolClient:
    def __init__(self, url: str) -> None:
        self._url = url

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client

            async with streamablehttp_client(self._url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await session.call_tool(name, arguments)
        except Exception as exc:
            raise _network_failure_error(name, exc) from exc


class AMapMCPMapProvider:
    name = "amap"

    def __init__(
        self,
        *,
        mcp_url: str | None = None,
        tool_client: MCPToolClient | None = None,
    ) -> None:
        self._mcp_url = mcp_url
        self._tool_client = tool_client

    async def health(self) -> ProviderHealth:
        if self._tool_client is None and not self._mcp_url:
            return ProviderHealth(ok=False, reason="AMAP_MCP_URL is not configured")
        return ProviderHealth(ok=True)

    async def geocode(self, request: GeocodeRequest) -> NormalizedPlace:
        payload = await self._call_tool(
            "maps_geo",
            {"address": request.query},
        )
        geocodes = _tool_result_list(payload, "AMap MCP geocodes")
        first = geocodes[0] if geocodes else None
        if first is None:
            raise self._provider_error(
                "unknown_failure", "AMap MCP geocode returned no place"
            )
        if not isinstance(first, dict):
            raise self._invalid_payload_error("AMap MCP geocode returned invalid place")

        return normalize_amap_place(
            {
                "id": first.get("id") or first.get("adcode"),
                "name": request.query,
                "formatted_address": _formatted_geocode_address(first),
                "address": first.get("address"),
                "category": first.get("level") or first.get("type"),
                "location": first.get("location"),
            }
        )

    async def reverse_geocode(
        self, request: ReverseGeocodeRequest
    ) -> NormalizedPlace:
        payload = await self._call_tool(
            "maps_regeocode",
            {"location": _format_lng_lat(request.coordinate)},
        )
        regeocode = _tool_result_mapping(payload, "AMap MCP reverse geocode payload")
        formatted_address = _formatted_reverse_geocode_address(regeocode)
        if not isinstance(formatted_address, str) or not formatted_address:
            raise self._invalid_payload_error(
                "AMap MCP reverse geocode address is invalid"
            )

        try:
            return NormalizedPlace.model_validate(
                {
                    "id": f"amap:reverse:{request.coordinate.lng},{request.coordinate.lat}",
                    "name": formatted_address,
                    "coordinate": request.coordinate,
                    "address": formatted_address,
                    "category": "reverse_geocode",
                    "provider": "amap",
                }
            )
        except ValidationError as exc:
            raise self._invalid_payload_error(
                "Invalid AMap MCP normalized reverse geocode payload", exc
            ) from exc

    async def search_places(
        self, request: PlaceSearchRequest
    ) -> list[NormalizedPlace]:
        payload = await self._call_tool(
            "maps_text_search",
            {"keywords": request.query},
        )
        pois = _tool_result_list(payload, "AMap MCP pois")
        normalized: list[NormalizedPlace] = []
        for poi in pois:
            if not isinstance(poi, dict):
                raise self._invalid_payload_error(
                    "AMap MCP search returned invalid place"
                )
            if request.limit is not None and len(normalized) >= request.limit:
                break
            detail = await self._search_detail(poi)
            if detail is None:
                continue
            normalized.append(normalize_amap_place(_merge_poi_detail(poi, detail)))
        return normalized

    async def route(self, request: RouteRequest) -> NormalizedRoute:
        tool_name = _to_amap_direction_tool(request.mode)
        if request.from_.coordinate is None or request.to.coordinate is None:
            raise self._invalid_payload_error("AMap MCP route requires coordinates")

        arguments = {
            "origin": _format_lng_lat(request.from_.coordinate),
            "destination": _format_lng_lat(request.to.coordinate),
        }
        if request.mode == "transit":
            arguments.update(_transit_city_arguments(request))

        payload = await self._call_tool(tool_name, arguments)
        route_payload = _first_route(payload)
        duration_seconds = _parse_number(
            route_payload.get("duration"), "AMap MCP route duration"
        )
        distance_meters = _parse_number(
            route_payload.get("distance"), "AMap MCP route distance"
        )

        try:
            return NormalizedRoute.model_validate(
                {
                    "from": request.from_,
                    "to": request.to,
                    "mode": request.mode,
                    "duration_minutes": round(duration_seconds / 60),
                    "distance_meters": distance_meters,
                    "cost_estimate": None,
                    "provider": "amap",
                }
            )
        except ValidationError as exc:
            raise self._invalid_payload_error(
                "Invalid AMap MCP normalized route payload", exc
            ) from exc

    async def _call_tool(
        self, name: str, arguments: dict[str, object]
    ) -> dict[str, Any]:
        client = self._tool_client
        if client is None:
            if not self._mcp_url:
                raise self._provider_error(
                    "auth_failure", "AMAP_MCP_URL is not configured"
                )
            client = StreamableHttpMCPToolClient(self._mcp_url)

        try:
            result = await client.call_tool(name, arguments)
        except ProviderError:
            raise
        except Exception as exc:
            raise _network_failure_error(name, exc) from exc
        payload = _extract_mcp_tool_payload(result)
        tool_error = payload.get("error")
        if isinstance(tool_error, str) and tool_error:
            raise self._provider_error(
                "unknown_failure",
                f"AMap MCP tool {name} returned error: {tool_error}",
            )
        return payload

    async def _search_detail(self, poi: dict[str, Any]) -> dict[str, Any] | None:
        poi_id = poi.get("id")
        if not isinstance(poi_id, str) or not poi_id:
            return None
        try:
            payload = await self._call_tool("maps_search_detail", {"id": poi_id})
        except ProviderError as exc:
            if exc.code == "unknown_failure":
                return None
            raise
        detail = _tool_result_mapping(
            payload,
            "AMap MCP POI detail",
            allow_direct=True,
        )
        if not detail.get("location"):
            return None
        return detail

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


def _extract_mcp_tool_payload(result: object) -> dict[str, Any]:
    if isinstance(result, Mapping):
        return dict(result)

    content = getattr(result, "content", None)
    if not isinstance(content, list):
        raise _invalid_payload_error("AMap MCP tool result content is invalid")

    for item in content:
        text = getattr(item, "text", None)
        if not isinstance(text, str) or not text.strip():
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise _invalid_payload_error(
                "AMap MCP tool result content is not JSON", exc
            ) from exc
        if not isinstance(payload, dict):
            raise _invalid_payload_error(
                "AMap MCP tool result JSON must be an object"
            )
        return payload

    raise _invalid_payload_error("AMap MCP tool result content is empty")


def _tool_result_list(payload: dict[str, Any], label: str) -> list[Any]:
    value = payload.get("return")
    if value is None:
        value = payload.get("geocodes")
    if value is None:
        value = payload.get("pois")
    if value is None:
        return []
    if not isinstance(value, list):
        raise _invalid_payload_error(f"{label} must be a list")
    return value


def _tool_result_mapping(
    payload: dict[str, Any],
    label: str,
    *,
    allow_direct: bool = False,
) -> dict[str, Any]:
    value = payload.get("return")
    if value is None:
        value = payload.get("regeocode")
    if value is None and allow_direct:
        value = payload
    if not isinstance(value, dict):
        raise _invalid_payload_error(f"{label} must be an object")
    return value


def _formatted_geocode_address(payload: dict[str, Any]) -> str | None:
    formatted = payload.get("formatted_address")
    if isinstance(formatted, str) and formatted:
        return formatted
    return _join_address_parts(
        payload.get("country"),
        payload.get("province"),
        payload.get("city"),
        payload.get("district"),
        payload.get("township"),
        payload.get("street"),
        payload.get("number"),
    )


def _formatted_reverse_geocode_address(payload: dict[str, Any]) -> str | None:
    formatted = payload.get("formatted_address")
    if isinstance(formatted, str) and formatted:
        return formatted
    return _join_address_parts(
        payload.get("province"),
        payload.get("city"),
        payload.get("district"),
        payload.get("township"),
    )


def _join_address_parts(*parts: object) -> str | None:
    normalized_parts: list[str] = []
    for part in parts:
        if not isinstance(part, str) or not part:
            continue
        if normalized_parts and normalized_parts[-1] == part:
            continue
        normalized_parts.append(part)
    address = "".join(normalized_parts)
    return address or None


def _merge_poi_detail(poi: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    merged = {**poi, **detail}
    if not merged.get("id"):
        merged["id"] = poi.get("id")
    if not merged.get("category"):
        merged["category"] = (
            detail.get("type")
            or detail.get("typecode")
            or poi.get("type")
            or poi.get("typecode")
        )
    if not merged.get("type"):
        merged["type"] = merged.get("category")
    if not merged.get("formatted_address"):
        merged["formatted_address"] = detail.get("address") or poi.get("address")
    return merged


def _first_route(payload: dict[str, Any]) -> dict[str, Any]:
    route = payload.get("route")
    if not isinstance(route, dict):
        raise _invalid_payload_error("AMap MCP route payload is invalid")

    paths = route.get("paths")
    if isinstance(paths, list) and paths:
        first = paths[0]
    else:
        transits = route.get("transits")
        if not isinstance(transits, list) or not transits:
            transits = payload.get("transits")
        if not isinstance(transits, list) or not transits:
            raise _invalid_payload_error("AMap MCP route returned no route")
        first = transits[0]

    if not isinstance(first, dict):
        raise _invalid_payload_error("AMap MCP route item is invalid")
    if "distance" not in first and route.get("distance") is not None:
        first = {**first, "distance": route.get("distance")}
    return first


def _parse_number(value: object, label: str) -> float:
    try:
        number = float(value) if isinstance(value, str) else value
        if not isinstance(number, (int, float)) or not math.isfinite(number):
            raise ValueError(f"{label} must be a finite number")
        return float(number)
    except (TypeError, ValueError) as exc:
        raise _invalid_payload_error(f"{label} is invalid", exc) from exc


def _format_lng_lat(coordinate: object) -> str:
    lat = getattr(coordinate, "lat", None)
    lng = getattr(coordinate, "lng", None)
    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        raise _invalid_payload_error("AMap MCP route coordinate is invalid")
    return f"{lng},{lat}"


def _to_amap_direction_tool(mode: str) -> str:
    if mode == "walk":
        return "maps_direction_walking_by_coordinates"
    if mode == "drive":
        return "maps_direction_driving_by_coordinates"
    if mode == "transit":
        return "maps_direction_transit_integrated_by_coordinates"
    raise ProviderError(
        provider="amap",
        kind="map",
        code="capability_unavailable",
        message=f"AMap MCP routing does not support {mode} routes in this adapter",
    )


def _transit_city_arguments(request: RouteRequest) -> dict[str, str]:
    city = _infer_amap_city(request.from_)
    cityd = _infer_amap_city(request.to)
    if city is None or cityd is None:
        raise _invalid_payload_error(
            "AMap MCP transit routing requires origin and destination city names"
        )
    return {"city": city, "cityd": cityd}


def _infer_amap_city(place: NormalizedPlace) -> str | None:
    searchable = " ".join(
        text
        for text in [place.address, place.name]
        if isinstance(text, str) and text
    )
    match = re.search(r"([\u4e00-\u9fff]{2,12}市)", searchable)
    if match:
        return match.group(1)
    for municipality in ("北京", "上海", "天津", "重庆"):
        if municipality in searchable:
            return f"{municipality}市"
    return None


def _invalid_payload_error(
    message: str, cause: object | None = None
) -> ProviderError:
    return ProviderError(
        provider="amap",
        kind="map",
        code="invalid_normalized_payload",
        message=message,
        cause=cause,
    )


def _network_failure_error(name: str, cause: object) -> ProviderError:
    return ProviderError(
        provider="amap",
        kind="map",
        code="network_failure",
        message=f"AMap MCP tool {name} failed",
        cause=cause,
    )
