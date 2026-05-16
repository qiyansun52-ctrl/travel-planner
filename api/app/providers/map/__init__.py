"""Map provider adapters."""

from app.providers.map.amap import AMapMapProvider, normalize_amap_place
from app.providers.map.coord import convert_gcj02_to_wgs84, is_outside_china
from app.providers.map.mapbox import MapboxMapProvider, normalize_mapbox_feature

__all__ = [
    "AMapMapProvider",
    "MapboxMapProvider",
    "convert_gcj02_to_wgs84",
    "is_outside_china",
    "normalize_amap_place",
    "normalize_mapbox_feature",
]
