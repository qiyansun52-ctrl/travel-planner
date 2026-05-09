from __future__ import annotations

from app.models.schemas import Coordinate
from app.providers.map.coord import convert_gcj02_to_wgs84, is_outside_china


def test_keeps_coordinates_outside_china_unchanged() -> None:
    coordinate = Coordinate(lat=40.7128, lng=-74.006)

    assert is_outside_china(coordinate) is True
    assert convert_gcj02_to_wgs84(coordinate) == coordinate


def test_converts_china_gcj02_coordinates_into_nearby_wgs84_coordinates() -> None:
    gcj02 = Coordinate(lat=31.2304, lng=121.4737)
    wgs84 = convert_gcj02_to_wgs84(gcj02)

    assert abs(wgs84.lat - gcj02.lat) > 0.001
    assert abs(wgs84.lng - gcj02.lng) > 0.001
    assert 31 < wgs84.lat < 32
    assert 121 < wgs84.lng < 122
