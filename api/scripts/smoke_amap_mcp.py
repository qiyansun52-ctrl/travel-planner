"""Smoke test: real AMap MCP map provider calls.

Usage:
    cd api && uv run python scripts/smoke_amap_mcp.py

Requires AMAP_MCP_URL in env and a running AMap MCP server.
This is NOT run in pytest -- it hits the real map provider.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _place(
    *,
    place_id: str,
    name: str,
    lat: float,
    lng: float,
    address: str,
):
    from app.models.schemas import Coordinate, NormalizedPlace

    return NormalizedPlace(
        id=place_id,
        name=name,
        coordinate=Coordinate(lat=lat, lng=lng),
        address=address,
        category="smoke",
        provider="amap",
    )


async def main() -> int:
    from app.config import load_environment
    from app.providers.map.amap_mcp import AMapMCPMapProvider
    from app.providers.types import PlaceSearchRequest, RouteRequest

    load_environment()
    provider = AMapMCPMapProvider(mcp_url=os.environ.get("AMAP_MCP_URL"))
    health = await provider.health()
    if not health.ok:
        raise SystemExit(f"amap_mcp_unhealthy {health.reason}")

    places = await provider.search_places(
        PlaceSearchRequest(
            query="上海 东方明珠",
            country_code="CN",
            limit=3,
        )
    )
    people_square = _place(
        place_id="smoke_people_square",
        name="人民广场",
        lat=31.2304,
        lng=121.4737,
        address="上海市黄浦区人民广场",
    )
    oriental_pearl = _place(
        place_id="smoke_oriental_pearl",
        name="东方明珠",
        lat=31.2397,
        lng=121.4998,
        address="上海市浦东新区世纪大道1号",
    )
    route = await provider.route(
        RouteRequest(
            from_=people_square,
            to=oriental_pearl,
            mode="walk",
        )
    )

    print(
        "amap_mcp_smoke_ok",
        len(places),
        places[0].provider if places else "none",
        route.provider,
        route.duration_minutes,
        route.distance_meters,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
