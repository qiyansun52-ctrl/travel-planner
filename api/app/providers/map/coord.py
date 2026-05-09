"""Coordinate conversion helpers ported from coordinateConversion.ts."""
from __future__ import annotations

import math

from app.models.schemas import Coordinate

PI = math.pi
EARTH_RADIUS = 6378245.0
ECCENTRICITY_SQUARED = 0.00669342162296594323


def convert_gcj02_to_wgs84(coordinate: Coordinate) -> Coordinate:
    if is_outside_china(coordinate):
        return Coordinate(lat=coordinate.lat, lng=coordinate.lng)

    delta = _calculate_gcj_offset(coordinate)
    gcj_lat = coordinate.lat + delta.lat
    gcj_lng = coordinate.lng + delta.lng
    return Coordinate(
        lat=coordinate.lat * 2 - gcj_lat,
        lng=coordinate.lng * 2 - gcj_lng,
    )


def is_outside_china(coordinate: Coordinate) -> bool:
    return (
        coordinate.lng < 72.004
        or coordinate.lng > 137.8347
        or coordinate.lat < 0.8293
        or coordinate.lat > 55.8271
    )


def _calculate_gcj_offset(coordinate: Coordinate) -> Coordinate:
    d_lat = _transform_lat(coordinate.lng - 105.0, coordinate.lat - 35.0)
    d_lng = _transform_lng(coordinate.lng - 105.0, coordinate.lat - 35.0)
    rad_lat = (coordinate.lat / 180.0) * PI
    magic = math.sin(rad_lat)
    magic = 1 - ECCENTRICITY_SQUARED * magic * magic
    sqrt_magic = math.sqrt(magic)
    d_lat = (d_lat * 180.0) / (
        ((EARTH_RADIUS * (1 - ECCENTRICITY_SQUARED)) / (magic * sqrt_magic)) * PI
    )
    d_lng = (d_lng * 180.0) / (
        (EARTH_RADIUS / sqrt_magic) * math.cos(rad_lat) * PI
    )
    return Coordinate(lat=d_lat, lng=d_lng)


def _transform_lat(x: float, y: float) -> float:
    result = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y
    result += 0.2 * math.sqrt(abs(x))
    result += (
        (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0
    ) / 3.0
    result += (
        (20.0 * math.sin(y * PI) + 40.0 * math.sin((y / 3.0) * PI)) * 2.0
    ) / 3.0
    result += (
        (160.0 * math.sin((y / 12.0) * PI) + 320 * math.sin((y * PI) / 30.0))
        * 2.0
    ) / 3.0
    return result


def _transform_lng(x: float, y: float) -> float:
    result = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y
    result += 0.1 * math.sqrt(abs(x))
    result += (
        (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0
    ) / 3.0
    result += (
        (20.0 * math.sin(x * PI) + 40.0 * math.sin((x / 3.0) * PI)) * 2.0
    ) / 3.0
    result += (
        (150.0 * math.sin((x / 12.0) * PI) + 300.0 * math.sin((x / 30.0) * PI))
        * 2.0
    ) / 3.0
    return result
