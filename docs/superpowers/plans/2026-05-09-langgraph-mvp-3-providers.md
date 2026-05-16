# LangGraph MVP — Plan 3: Provider Adapters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `web/src/server/providers/` 的 provider 抽象、map fallback registry、AMap/Mapbox adapter、GCJ02 坐标转换、Tavily search adapter、weather/supplier unavailable fallback 移植到 Python `api/app/providers/`,给 Plan 5 LangGraph 节点提供统一的外部数据入口。

**Architecture:** Provider 层只负责 I/O、外部 payload 解析、错误归一化和 Pydantic schema 校验;agent/graph 不直接知道 AMap、Mapbox、Tavily 的 HTTP 细节。Map provider 按国家码选择主备链路:中国优先 AMap,非中国优先 Mapbox;失败时记录结构化 attempt 并 fallback。Search 用 Tavily 作为真实实现,weather/supplier 在 MVP 先提供明确的 unavailable provider,避免 Plan 5 写死空值。

**Tech Stack:** Python 3.12, Pydantic v2, httpx, pytest, pytest-asyncio, pytest-httpx, ruff。**不新增依赖**。

---

## Scope

**In scope:**
- 新增 `api/app/providers/` 包和契约类型。
- 新增 Tavily search provider,并保留旧 `api/app/services/tavily.py` 兼容 shim,确保 Plan 6 前旧 route/test 不断。
- 新增 AMap / Mapbox map providers,包含 WGS84 坐标归一化。
- 新增 provider registry,实现 map 主备选择、health 检查、timeout、schema validation、attempt 记录。
- 新增 weather / supplier unavailable providers,返回明确 health reason 和 `capability_unavailable` 错误。

**Out of scope:**
- 不接 LangGraph 节点,Plan 5 再接。
- 不改 FastAPI routes,Plan 6 再统一迁移。
- 不删除 `api/app/routes/{discover,plan}.py`。
- 不删除旧 `api/app/services/gemini.py`。
- 不做真实 weather / hotel / ticket supplier API。

**Important compatibility decision:**
- 路线图里写了删除 `api/app/services/tavily.py`,但当前 `api/app/routes/discover.py` 和 `api/tests/test_tavily_query_builder.py` 仍依赖它。本计划把它改成薄 shim,真实实现移到 `api/app/providers/search/tavily.py`;Plan 6 删除旧 route 时再删除 shim。

---

## File Structure

**Create:**
- `api/app/providers/__init__.py` — providers 包入口,导出 registry、types、默认创建函数。
- `api/app/providers/types.py` — Protocol / request dataclass / result Pydantic models / ProviderError。
- `api/app/providers/registry.py` — `TravelDataProviderRegistry`, map fallback, default env wiring。
- `api/app/providers/search/__init__.py`
- `api/app/providers/search/tavily.py` — Tavily `SearchProvider` 实现和 discovery 三查询 builder。
- `api/app/providers/map/__init__.py`
- `api/app/providers/map/coord.py` — GCJ02 → WGS84,等价于 TS `coordinateConversion.ts`。
- `api/app/providers/map/amap.py` — AMap geocode / place search / normalization。
- `api/app/providers/map/mapbox.py` — Mapbox geocode / reverse geocode / place search / walking+driving route。
- `api/app/providers/supplier.py` — unavailable supplier provider。
- `api/app/providers/weather.py` — unavailable weather provider。
- `api/tests/providers/__init__.py`
- `api/tests/providers/test_types.py`
- `api/tests/providers/test_unavailable.py`
- `api/tests/providers/test_coord.py`
- `api/tests/providers/test_amap.py`
- `api/tests/providers/test_mapbox.py`
- `api/tests/providers/test_tavily.py`
- `api/tests/providers/test_registry.py`

**Modify:**
- `api/app/services/tavily.py` — 改成旧接口兼容 shim,内部调用 `app.providers.search.tavily`。
- `api/tests/test_tavily_query_builder.py` — 可以保持不变;它会继续通过 shim 访问 `build_search_queries`。

**Untouched (Plan 6 再动):**
- `api/app/routes/discover.py`
- `api/app/routes/plan.py`
- `api/app/services/gemini.py`

**Reference (read-only — TS 源文件,不改):**
- `web/src/server/providers/types.ts`
- `web/src/server/providers/registry.ts`
- `web/src/server/providers/registry.test.ts`
- `web/src/server/providers/map/{amap,mapbox,coordinateConversion}.ts`
- `web/src/server/providers/map/coordinateConversion.test.ts`
- `web/src/server/providers/search/index.ts`
- `web/src/server/providers/supplier/index.ts`
- `web/src/server/providers/weather/index.ts`

---

## Task 0 — Setup

**Files:**
- Create: `api/app/providers/__init__.py`
- Create: `api/app/providers/map/__init__.py`
- Create: `api/app/providers/search/__init__.py`
- Create: `api/tests/providers/__init__.py`

- [ ] **Step 0.1: 创建空目录占位**

```bash
mkdir -p api/app/providers/map api/app/providers/search api/tests/providers
touch api/app/providers/__init__.py api/app/providers/map/__init__.py api/app/providers/search/__init__.py api/tests/providers/__init__.py
```

- [ ] **Step 0.2: 跑当前后端基线**

Run: `cd api && uv run pytest -v`

Expected: 当前 97 个测试全 PASS。

- [ ] **Step 0.3: 提交**

```bash
git add api/app/providers/__init__.py api/app/providers/map/__init__.py api/app/providers/search/__init__.py api/tests/providers/__init__.py
git commit -m "chore(api): scaffold providers package"
```

---

## Task 1 — `types.py` Provider Contracts

**Files:**
- Create: `api/app/providers/types.py`
- Create: `api/tests/providers/test_types.py`

**Reference:** `web/src/server/providers/types.ts`

**Design notes:**
- `NormalizedPlace.provider` 仍使用 `app.models.schemas.Provider` 的四个 map provider id:`amap | mapbox | baidu | google`。
- `ProviderAttemptFailure.provider` 需要记录 search provider,所以 Python provider attempt id 额外允许 `tavily`。这只用于内部错误记录,不会进入 `NormalizedPlace.provider`。

- [ ] **Step 1.1: 写测试**

写到 `api/tests/providers/test_types.py`:

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.schemas import BudgetBand, NormalizedPlace, SourceNote
from app.providers.types import (
    ProviderError,
    ProviderHealth,
    SearchRequest,
    SearchResult,
    SupplierReference,
    WeatherRequest,
    WeatherSummary,
)


def test_provider_error_exposes_structured_fields() -> None:
    cause = RuntimeError("boom")
    err = ProviderError(
        provider="mapbox",
        kind="map",
        code="network_failure",
        message="Mapbox failed",
        cause=cause,
    )

    assert str(err) == "Mapbox failed"
    assert err.provider == "mapbox"
    assert err.kind == "map"
    assert err.code == "network_failure"
    assert err.cause is cause


def test_provider_health_defaults_to_ok_without_reason() -> None:
    assert ProviderHealth(ok=True).reason is None


def test_search_result_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SearchResult.model_validate({
            "title": "Guide",
            "url": "https://example.com",
            "snippet": "Useful",
            "source_note": None,
            "extra": "nope",
        })


def test_request_and_result_shapes_accept_expected_payloads() -> None:
    place = NormalizedPlace(
        id="mapbox:shanghai",
        name="Shanghai",
        coordinate={"lat": 31.2304, "lng": 121.4737},
        address="Shanghai",
        category="place",
        provider="mapbox",
    )
    band = BudgetBand(currency="CNY", low=100, high=300, confidence="medium", basis="per_trip")

    assert SearchRequest(query="Shanghai food", country_code="CN", limit=5).limit == 5
    assert WeatherRequest(place=place, start_date="2026-06-01", duration_days=3).duration_days == 3
    assert WeatherSummary(
        provider="google",
        place=place,
        summary="Warm",
        daily_notes=["Bring an umbrella"],
        source_note=SourceNote(provider="fixture", url=None, note="fixture"),
    ).summary == "Warm"
    assert SupplierReference(
        name="Sample hotel",
        category="hotel",
        price_band=band,
        note="Reference only",
        source_note=None,
    ).price_band == band
```

- [ ] **Step 1.2: 跑测试,确认失败**

Run: `cd api && uv run pytest tests/providers/test_types.py -v`

Expected: `ModuleNotFoundError: No module named 'app.providers.types'`。

- [ ] **Step 1.3: 实现 `types.py`**

写到 `api/app/providers/types.py`:

```python
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
```

- [ ] **Step 1.4: 跑测试,确认通过**

Run: `cd api && uv run pytest tests/providers/test_types.py -v`

Expected: 4 PASS。

- [ ] **Step 1.5: 提交**

```bash
git add api/app/providers/types.py api/tests/providers/test_types.py
git commit -m "feat(api): add provider contract types"
```

---

## Task 2 — Unavailable Weather / Supplier Providers

**Files:**
- Create: `api/app/providers/weather.py`
- Create: `api/app/providers/supplier.py`
- Create: `api/tests/providers/test_unavailable.py`

**Reference:** `web/src/server/providers/{weather,supplier}/index.ts`

- [ ] **Step 2.1: 写测试**

写到 `api/tests/providers/test_unavailable.py`:

```python
from __future__ import annotations

import pytest

from app.models.schemas import NormalizedPlace
from app.providers.supplier import create_unavailable_supplier_provider
from app.providers.types import ProviderError, SupplierRequest, WeatherRequest
from app.providers.weather import create_unavailable_weather_provider


def _place() -> NormalizedPlace:
    return NormalizedPlace(
        id="mapbox:shanghai",
        name="Shanghai",
        coordinate={"lat": 31.2304, "lng": 121.4737},
        address="Shanghai",
        category="city",
        provider="mapbox",
    )


async def test_unavailable_weather_provider_health_and_error() -> None:
    provider = create_unavailable_weather_provider()

    health = await provider.health()
    assert health.ok is False
    assert health.reason == "Weather provider is not configured"

    with pytest.raises(ProviderError) as ei:
        await provider.get_weather_summary(
            WeatherRequest(place=_place(), start_date="2026-06-01", duration_days=3)
        )
    assert ei.value.kind == "weather"
    assert ei.value.code == "capability_unavailable"


async def test_unavailable_supplier_provider_health_and_error() -> None:
    provider = create_unavailable_supplier_provider()

    health = await provider.health()
    assert health.ok is False
    assert health.reason == "Supplier provider is not configured"

    with pytest.raises(ProviderError) as ei:
        await provider.get_sample_references(
            SupplierRequest(destination=_place(), start_date="2026-06-01", duration_days=3, currency="CNY")
        )
    assert ei.value.kind == "supplier"
    assert ei.value.code == "capability_unavailable"
```

- [ ] **Step 2.2: 跑测试,确认失败**

Run: `cd api && uv run pytest tests/providers/test_unavailable.py -v`

Expected: `ModuleNotFoundError`。

- [ ] **Step 2.3: 实现 `weather.py`**

写到 `api/app/providers/weather.py`:

```python
"""Weather provider fallback for MVP."""
from __future__ import annotations

from app.providers.types import ProviderError, ProviderHealth, WeatherRequest, WeatherSummary


class UnavailableWeatherProvider:
    name = "google"

    async def health(self) -> ProviderHealth:
        return ProviderHealth(ok=False, reason="Weather provider is not configured")

    async def get_weather_summary(self, request: WeatherRequest) -> WeatherSummary:
        raise ProviderError(
            provider=self.name,
            kind="weather",
            code="capability_unavailable",
            message="Weather provider is not configured",
        )


def create_unavailable_weather_provider() -> UnavailableWeatherProvider:
    return UnavailableWeatherProvider()
```

- [ ] **Step 2.4: 实现 `supplier.py`**

写到 `api/app/providers/supplier.py`:

```python
"""Supplier provider fallback for MVP."""
from __future__ import annotations

from app.providers.types import ProviderError, ProviderHealth, SupplierReference, SupplierRequest


class UnavailableSupplierProvider:
    name = "google"

    async def health(self) -> ProviderHealth:
        return ProviderHealth(ok=False, reason="Supplier provider is not configured")

    async def get_sample_references(self, request: SupplierRequest) -> list[SupplierReference]:
        raise ProviderError(
            provider=self.name,
            kind="supplier",
            code="capability_unavailable",
            message="Supplier provider is not configured",
        )


def create_unavailable_supplier_provider() -> UnavailableSupplierProvider:
    return UnavailableSupplierProvider()
```

- [ ] **Step 2.5: 跑测试,确认通过**

Run: `cd api && uv run pytest tests/providers/test_unavailable.py -v`

Expected: 2 PASS。

- [ ] **Step 2.6: 提交**

```bash
git add api/app/providers/weather.py api/app/providers/supplier.py api/tests/providers/test_unavailable.py
git commit -m "feat(api): add unavailable weather and supplier providers"
```

---

## Task 3 — `map/coord.py` GCJ02 → WGS84

**Files:**
- Create: `api/app/providers/map/coord.py`
- Create: `api/tests/providers/test_coord.py`

**Reference:** `web/src/server/providers/map/coordinateConversion.ts`

- [ ] **Step 3.1: 写测试**

写到 `api/tests/providers/test_coord.py`:

```python
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
```

- [ ] **Step 3.2: 跑测试,确认失败**

Run: `cd api && uv run pytest tests/providers/test_coord.py -v`

Expected: `ModuleNotFoundError`。

- [ ] **Step 3.3: 实现 `coord.py`**

写到 `api/app/providers/map/coord.py`:

```python
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
    d_lat = (d_lat * 180.0) / (((EARTH_RADIUS * (1 - ECCENTRICITY_SQUARED)) / (magic * sqrt_magic)) * PI)
    d_lng = (d_lng * 180.0) / ((EARTH_RADIUS / sqrt_magic) * math.cos(rad_lat) * PI)
    return Coordinate(lat=d_lat, lng=d_lng)


def _transform_lat(x: float, y: float) -> float:
    result = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y
    result += 0.2 * math.sqrt(abs(x))
    result += ((20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0) / 3.0
    result += ((20.0 * math.sin(y * PI) + 40.0 * math.sin((y / 3.0) * PI)) * 2.0) / 3.0
    result += ((160.0 * math.sin((y / 12.0) * PI) + 320 * math.sin((y * PI) / 30.0)) * 2.0) / 3.0
    return result


def _transform_lng(x: float, y: float) -> float:
    result = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y
    result += 0.1 * math.sqrt(abs(x))
    result += ((20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0) / 3.0
    result += ((20.0 * math.sin(x * PI) + 40.0 * math.sin((x / 3.0) * PI)) * 2.0) / 3.0
    result += ((150.0 * math.sin((x / 12.0) * PI) + 300.0 * math.sin((x / 30.0) * PI)) * 2.0) / 3.0
    return result
```

- [ ] **Step 3.4: 跑测试,确认通过**

Run: `cd api && uv run pytest tests/providers/test_coord.py -v`

Expected: 2 PASS。

- [ ] **Step 3.5: 提交**

```bash
git add api/app/providers/map/coord.py api/tests/providers/test_coord.py
git commit -m "feat(api): add gcj02 to wgs84 coordinate conversion"
```

---

## Task 4 — `map/amap.py`

**Files:**
- Create: `api/app/providers/map/amap.py`
- Create: `api/tests/providers/test_amap.py`

**Reference:** `web/src/server/providers/map/amap.ts`

- [ ] **Step 4.1: 写测试**

写到 `api/tests/providers/test_amap.py`:

```python
from __future__ import annotations

import re

import pytest
from pytest_httpx import HTTPXMock

from app.providers.map.amap import AMapMapProvider, normalize_amap_place
from app.providers.types import GeocodeRequest, PlaceSearchRequest, ProviderError


async def test_health_reports_missing_key() -> None:
    provider = AMapMapProvider(api_key=None)

    health = await provider.health()

    assert health.ok is False
    assert health.reason == "AMAP_API_KEY is not configured"


def test_normalize_amap_place_converts_gcj02_to_wgs84() -> None:
    place = normalize_amap_place({
        "id": "B0FFG123",
        "name": "人民广场",
        "address": "上海市黄浦区",
        "category": "landmark",
        "location": "121.4737,31.2304",
    })

    assert place.provider == "amap"
    assert place.id == "amap:B0FFG123"
    assert place.coordinate is not None
    assert place.coordinate.lat != 31.2304
    assert place.coordinate.lng != 121.4737


async def test_geocode_normalizes_first_result(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://restapi\.amap\.com/v3/geocode/geo.*"),
        json={
            "status": "1",
            "geocodes": [{
                "adcode": "310000",
                "formatted_address": "上海市",
                "location": "121.4737,31.2304",
                "level": "city",
            }],
        },
    )
    provider = AMapMapProvider(api_key="key")

    place = await provider.geocode(GeocodeRequest(query="上海", country_code="CN"))

    assert place.id == "amap:310000"
    assert place.name == "上海"
    assert place.address == "上海市"
    assert place.category == "city"


async def test_search_places_normalizes_pois(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://restapi\.amap\.com/v3/place/text.*"),
        json={
            "status": "1",
            "pois": [{
                "id": "B0FFG123",
                "name": "人民广场",
                "formatted_address": "上海市黄浦区",
                "type": "landmark",
                "location": "121.4737,31.2304",
            }],
        },
    )
    provider = AMapMapProvider(api_key="key")

    places = await provider.search_places(PlaceSearchRequest(query="人民广场", country_code="CN", limit=1))

    assert [p.id for p in places] == ["amap:B0FFG123"]


async def test_reverse_and_route_are_explicitly_unavailable() -> None:
    provider = AMapMapProvider(api_key="key")

    with pytest.raises(ProviderError) as reverse:
        await provider.reverse_geocode(None)  # type: ignore[arg-type]
    assert reverse.value.code == "capability_unavailable"

    with pytest.raises(ProviderError) as route:
        await provider.route(None)  # type: ignore[arg-type]
    assert route.value.code == "capability_unavailable"
```

- [ ] **Step 4.2: 跑测试,确认失败**

Run: `cd api && uv run pytest tests/providers/test_amap.py -v`

Expected: `ModuleNotFoundError`。

- [ ] **Step 4.3: 实现 `amap.py`**

实现要求:
- `AMapMapProvider.name == "amap"`。
- `health()` 在缺 `api_key` 时返回 `ProviderHealth(ok=False, reason="AMAP_API_KEY is not configured")`。
- `geocode()` 调 `https://restapi.amap.com/v3/geocode/geo`,params:`key`,`address`。
- `search_places()` 调 `https://restapi.amap.com/v3/place/text`,params:`key`,`keywords`,`offset`。
- HTTP 401/403 映射 `auth_failure`;非 2xx 映射 `network_failure`;AMap `status != "1"` 映射 `unknown_failure`。
- `normalize_amap_place()` 解析 `"lng,lat"` 并用 `convert_gcj02_to_wgs84()` 后生成 `NormalizedPlace`。
- `reverse_geocode()` 和 `route()` 明确抛 `ProviderError(code="capability_unavailable")`。

关键实现骨架:

```python
"""AMap map provider adapter."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from app.models.schemas import Coordinate, NormalizedPlace
from app.providers.map.coord import convert_gcj02_to_wgs84
from app.providers.types import (
    GeocodeRequest,
    PlaceSearchRequest,
    ProviderError,
    ProviderHealth,
    ReverseGeocodeRequest,
    RouteRequest,
)

AMAP_BASE_URL = "https://restapi.amap.com"


class AMapMapProvider:
    name = "amap"

    def __init__(self, *, api_key: str | None = None, base_url: str = AMAP_BASE_URL) -> None:
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
            raise self._provider_error("unknown_failure", body.get("info") or "AMap geocode failed")
        first = (body.get("geocodes") or [None])[0]
        if not first or not first.get("location"):
            raise self._provider_error("unknown_failure", "AMap geocode returned no place")
        return normalize_amap_place({
            "id": first.get("adcode"),
            "name": request.query,
            "formatted_address": first.get("formatted_address"),
            "category": first.get("level"),
            "location": first["location"],
        })

    async def reverse_geocode(self, request: ReverseGeocodeRequest) -> NormalizedPlace:
        raise self._provider_error("capability_unavailable", "AMap reverse geocoding is not wired yet")

    async def search_places(self, request: PlaceSearchRequest) -> list[NormalizedPlace]:
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
            raise self._provider_error("unknown_failure", body.get("info") or "AMap place search failed")
        return [normalize_amap_place(poi) for poi in body.get("pois", [])]

    async def route(self, request: RouteRequest):
        raise self._provider_error("capability_unavailable", "AMap routing is not wired yet")

    async def _fetch_json(self, path: str, params: dict[str, str], operation: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self._base_url}{path}", params=params)
        except httpx.HTTPError as exc:
            raise self._provider_error("network_failure", f"AMap {operation} network failure", exc) from exc
        if response.status_code in (401, 403):
            raise self._provider_error("auth_failure", f"AMap {operation} auth failure")
        if response.status_code >= 400:
            raise self._provider_error("network_failure", f"AMap {operation} HTTP {response.status_code}")
        return response.json()

    def _require_api_key(self) -> str:
        if not self._api_key:
            raise self._provider_error("auth_failure", "AMAP_API_KEY is not configured")
        return self._api_key

    def _provider_error(self, code, message: str, cause: object | None = None) -> ProviderError:
        return ProviderError(provider=self.name, kind="map", code=code, message=message, cause=cause)


def normalize_amap_place(payload: dict[str, Any]) -> NormalizedPlace:
    coordinate = convert_gcj02_to_wgs84(_parse_amap_location(str(payload["location"])))
    stable_id = payload.get("id") or _create_stable_amap_id(payload)
    return NormalizedPlace.model_validate({
        "id": f"amap:{stable_id}",
        "name": payload.get("name") or payload.get("formatted_address") or payload.get("address") or "AMap place",
        "coordinate": coordinate,
        "address": payload.get("formatted_address") or payload.get("address"),
        "category": payload.get("category") or payload.get("type"),
        "provider": "amap",
    })


def _parse_amap_location(location: str) -> Coordinate:
    try:
        lng_text, lat_text = location.split(",", 1)
        lng = float(lng_text)
        lat = float(lat_text)
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
```

- [ ] **Step 4.4: 跑测试,确认通过**

Run: `cd api && uv run pytest tests/providers/test_amap.py -v`

Expected: 5 PASS。

- [ ] **Step 4.5: 提交**

```bash
git add api/app/providers/map/amap.py api/tests/providers/test_amap.py
git commit -m "feat(api): add amap map provider adapter"
```

---

## Task 5 — `map/mapbox.py`

**Files:**
- Create: `api/app/providers/map/mapbox.py`
- Create: `api/tests/providers/test_mapbox.py`

**Reference:** `web/src/server/providers/map/mapbox.ts`

- [ ] **Step 5.1: 写测试**

写到 `api/tests/providers/test_mapbox.py`:

```python
from __future__ import annotations

import re

import pytest
from pytest_httpx import HTTPXMock

from app.models.schemas import NormalizedPlace
from app.providers.map.mapbox import MapboxMapProvider, normalize_mapbox_feature
from app.providers.types import GeocodeRequest, PlaceSearchRequest, ProviderError, RouteRequest


async def test_health_reports_missing_token() -> None:
    provider = MapboxMapProvider(access_token=None)

    health = await provider.health()

    assert health.ok is False
    assert health.reason == "MAPBOX_ACCESS_TOKEN is not configured"


def test_normalize_mapbox_feature_accepts_missing_coordinate() -> None:
    place = normalize_mapbox_feature({
        "id": "place.1",
        "text": "Shanghai",
        "place_name": "Shanghai, China",
        "geometry": {},
        "properties": {"feature_type": "place"},
    })

    assert place.id == "mapbox:place.1"
    assert place.name == "Shanghai"
    assert place.coordinate is None
    assert place.provider == "mapbox"


async def test_geocode_returns_first_feature(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://api\.mapbox\.com/geocoding/v5/mapbox\.places/Shanghai\.json.*"),
        json={
            "features": [{
                "id": "place.1",
                "text": "Shanghai",
                "place_name": "Shanghai, China",
                "geometry": {"coordinates": [121.4737, 31.2304]},
                "properties": {"feature_type": "place"},
            }]
        },
    )
    provider = MapboxMapProvider(access_token="token")

    place = await provider.geocode(GeocodeRequest(query="Shanghai", country_code="CN"))

    assert place.id == "mapbox:place.1"
    assert place.coordinate is not None
    assert place.coordinate.lat == 31.2304


async def test_search_places_returns_all_features(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://api\.mapbox\.com/geocoding/v5/mapbox\.places/cafe\.json.*"),
        json={
            "features": [
                {"id": "poi.1", "text": "Cafe A", "geometry": {"coordinates": [1, 2]}, "properties": {}},
                {"id": "poi.2", "text": "Cafe B", "geometry": {"coordinates": [3, 4]}, "properties": {}},
            ]
        },
    )
    provider = MapboxMapProvider(access_token="token")

    places = await provider.search_places(PlaceSearchRequest(query="cafe", country_code="US", limit=2))

    assert [place.id for place in places] == ["mapbox:poi.1", "mapbox:poi.2"]


async def test_route_maps_duration_and_distance(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"https://api\.mapbox\.com/directions/v5/mapbox/walking/.*"),
        json={"routes": [{"duration": 900, "distance": 1200}]},
    )
    provider = MapboxMapProvider(access_token="token")
    start = _place("mapbox:start", 31.2304, 121.4737)
    end = _place("mapbox:end", 31.2310, 121.4800)

    route = await provider.route(RouteRequest(from_=start, to=end, mode="walk"))

    assert route.duration_minutes == 15
    assert route.distance_meters == 1200
    assert route.provider == "mapbox"


async def test_route_rejects_unsupported_mode() -> None:
    provider = MapboxMapProvider(access_token="token")

    with pytest.raises(ProviderError) as ei:
        await provider.route(RouteRequest(from_=_place("a", 1, 2), to=_place("b", 3, 4), mode="transit"))
    assert ei.value.code == "capability_unavailable"


def _place(place_id: str, lat: float, lng: float) -> NormalizedPlace:
    return NormalizedPlace(
        id=place_id,
        name=place_id,
        coordinate={"lat": lat, "lng": lng},
        address=None,
        category=None,
        provider="mapbox",
    )
```

- [ ] **Step 5.2: 跑测试,确认失败**

Run: `cd api && uv run pytest tests/providers/test_mapbox.py -v`

Expected: `ModuleNotFoundError`。

- [ ] **Step 5.3: 实现 `mapbox.py`**

实现要求:
- `MapboxMapProvider.name == "mapbox"`。
- `health()` 在缺 token 时返回明确 reason。
- forward geocode URL:`https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json`。
- reverse geocode URL:`https://api.mapbox.com/geocoding/v5/mapbox.places/{lng},{lat}.json`。
- route URL:`https://api.mapbox.com/directions/v5/mapbox/{walking|driving}/{lng1},{lat1};{lng2},{lat2}`。
- `walk -> walking`, `drive -> driving`;其他 mode 抛 `capability_unavailable`。
- response 401/403 映射 auth,其他 4xx/5xx 映射 network。
- `NormalizedRoute` 用 alias `"from"` 填入起点。

关键实现骨架:

```python
"""Mapbox map provider adapter."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from app.models.schemas import NormalizedPlace, NormalizedRoute
from app.providers.types import (
    GeocodeRequest,
    PlaceSearchRequest,
    ProviderError,
    ProviderHealth,
    ReverseGeocodeRequest,
    RouteRequest,
)

MAPBOX_BASE_URL = "https://api.mapbox.com"


class MapboxMapProvider:
    name = "mapbox"

    def __init__(self, *, access_token: str | None = None, base_url: str = MAPBOX_BASE_URL) -> None:
        self._access_token = access_token
        self._base_url = base_url.rstrip("/")

    async def health(self) -> ProviderHealth:
        if not self._access_token:
            return ProviderHealth(ok=False, reason="MAPBOX_ACCESS_TOKEN is not configured")
        return ProviderHealth(ok=True)

    async def geocode(self, request: GeocodeRequest) -> NormalizedPlace:
        features = await self._fetch_forward_geocode(request, request.country_code, 1)
        first = features[0] if features else None
        if not first:
            raise self._provider_error("unknown_failure", "Mapbox geocode returned no place")
        return normalize_mapbox_feature(first)

    async def reverse_geocode(self, request: ReverseGeocodeRequest) -> NormalizedPlace:
        token = self._require_access_token()
        path = f"/geocoding/v5/mapbox.places/{request.coordinate.lng},{request.coordinate.lat}.json"
        body = await self._fetch_json(path, {"access_token": token, "limit": "1"}, "reverseGeocode")
        features = body.get("features") or []
        if not features:
            raise self._provider_error("unknown_failure", "Mapbox reverse geocode returned no place")
        return normalize_mapbox_feature(features[0])

    async def search_places(self, request: PlaceSearchRequest) -> list[NormalizedPlace]:
        features = await self._fetch_forward_geocode(request, request.country_code, request.limit or 10)
        return [normalize_mapbox_feature(feature) for feature in features]

    async def route(self, request: RouteRequest) -> NormalizedRoute:
        token = self._require_access_token()
        if request.from_.coordinate is None or request.to.coordinate is None:
            raise self._provider_error("invalid_normalized_payload", "Mapbox route requires coordinates")
        profile = _to_mapbox_directions_profile(request.mode)
        coordinates = (
            f"{request.from_.coordinate.lng},{request.from_.coordinate.lat};"
            f"{request.to.coordinate.lng},{request.to.coordinate.lat}"
        )
        body = await self._fetch_json(
            f"/directions/v5/mapbox/{profile}/{coordinates}",
            {"access_token": token, "overview": "false"},
            "route",
        )
        first = (body.get("routes") or [None])[0]
        if not first or not isinstance(first.get("duration"), (int, float)) or not isinstance(first.get("distance"), (int, float)):
            raise self._provider_error("unknown_failure", "Mapbox route returned no route")
        return NormalizedRoute.model_validate({
            "from": request.from_,
            "to": request.to,
            "mode": request.mode,
            "duration_minutes": round(first["duration"] / 60),
            "distance_meters": first["distance"],
            "cost_estimate": None,
            "provider": "mapbox",
        })

    async def _fetch_forward_geocode(self, request: GeocodeRequest | PlaceSearchRequest, country_code: str | None, limit: int) -> list[dict[str, Any]]:
        token = self._require_access_token()
        body = await self._fetch_json(
            f"/geocoding/v5/mapbox.places/{quote(request.query, safe='')}.json",
            {
                "access_token": token,
                "limit": str(limit),
                **({"country": country_code} if country_code else {}),
                **({"proximity": f"{request.bias.lng},{request.bias.lat}"} if request.bias else {}),
            },
            "geocode",
        )
        return body.get("features") or []

    async def _fetch_json(self, path: str, params: dict[str, str], operation: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self._base_url}{path}", params=params)
        except httpx.HTTPError as exc:
            raise self._provider_error("network_failure", f"Mapbox {operation} network failure", exc) from exc
        if response.status_code in (401, 403):
            raise self._provider_error("auth_failure", f"Mapbox {operation} auth failure")
        if response.status_code >= 400:
            raise self._provider_error("network_failure", f"Mapbox {operation} HTTP {response.status_code}")
        return response.json()

    def _require_access_token(self) -> str:
        if not self._access_token:
            raise self._provider_error("auth_failure", "MAPBOX_ACCESS_TOKEN is not configured")
        return self._access_token

    def _provider_error(self, code, message: str, cause: object | None = None) -> ProviderError:
        return ProviderError(provider=self.name, kind="map", code=code, message=message, cause=cause)


def normalize_mapbox_feature(feature: dict[str, Any]) -> NormalizedPlace:
    coordinates = ((feature.get("geometry") or {}).get("coordinates") or [])
    lng = coordinates[0] if len(coordinates) >= 1 else None
    lat = coordinates[1] if len(coordinates) >= 2 else None
    properties = feature.get("properties") or {}
    name = properties.get("name") or feature.get("text") or feature.get("place_name")
    coordinate = {"lat": lat, "lng": lng} if isinstance(lat, (int, float)) and isinstance(lng, (int, float)) else None
    fallback_id = quote(f"{name or 'place'}:{lng},{lat}", safe="")
    return NormalizedPlace.model_validate({
        "id": f"mapbox:{feature.get('id') or fallback_id}",
        "name": name,
        "coordinate": coordinate,
        "address": properties.get("full_address") or feature.get("place_name"),
        "category": properties.get("feature_type") or feature.get("type"),
        "provider": "mapbox",
    })


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
```

- [ ] **Step 5.4: 跑测试,确认通过**

Run: `cd api && uv run pytest tests/providers/test_mapbox.py -v`

Expected: 6 PASS。

- [ ] **Step 5.5: 提交**

```bash
git add api/app/providers/map/mapbox.py api/tests/providers/test_mapbox.py
git commit -m "feat(api): add mapbox map provider adapter"
```

---

## Task 6 — Tavily Search Provider + Legacy Shim

**Files:**
- Create: `api/app/providers/search/tavily.py`
- Modify: `api/app/services/tavily.py`
- Create: `api/tests/providers/test_tavily.py`

**Reference:** current `api/app/services/tavily.py`, `web/src/server/providers/search/index.ts`

- [ ] **Step 6.1: 写 provider 测试**

写到 `api/tests/providers/test_tavily.py`:

```python
from __future__ import annotations

import re

import pytest
from pytest_httpx import HTTPXMock

from app.providers.search.tavily import TavilySearchProvider, build_search_queries
from app.providers.types import ProviderError, SearchRequest
from app.services.tavily import search_tavily_three_sections


def test_build_search_queries_returns_three_chinese_queries() -> None:
    q1, q2, q3 = build_search_queries("上海")

    assert "上海" in q1 and "景点" in q1
    assert "上海" in q2 and "交通" in q2
    assert "上海" in q3 and "美食" in q3


async def test_tavily_health_reports_missing_key() -> None:
    provider = TavilySearchProvider(api_key=None)

    health = await provider.health()

    assert health.ok is False
    assert health.reason == "TAVILY_API_KEY is not configured"


async def test_tavily_search_normalizes_results(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.tavily.com/search",
        json={
            "results": [{
                "title": "Shanghai guide",
                "url": "https://example.com/shanghai",
                "content": "Useful guide",
            }]
        },
    )
    provider = TavilySearchProvider(api_key="key")

    results = await provider.search(SearchRequest(query="Shanghai guide", country_code="CN", limit=1))

    assert len(results) == 1
    assert results[0].title == "Shanghai guide"
    assert results[0].url == "https://example.com/shanghai"
    assert results[0].snippet == "Useful guide"
    assert results[0].source_note is not None
    assert results[0].source_note.provider == "tavily"


async def test_tavily_search_maps_401_to_auth_failure(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", url="https://api.tavily.com/search", status_code=401, json={})
    provider = TavilySearchProvider(api_key="bad")

    with pytest.raises(ProviderError) as ei:
        await provider.search(SearchRequest(query="x"))
    assert ei.value.code == "auth_failure"


async def test_legacy_three_section_shim_returns_search_items(httpx_mock: HTTPXMock) -> None:
    for title in ["A", "B", "C"]:
        httpx_mock.add_response(
            method="POST",
            url="https://api.tavily.com/search",
            json={"results": [{"title": title, "url": f"https://example.com/{title}", "content": "snippet"}]},
        )

    experience, transport, food = await search_tavily_three_sections("上海", "key")

    assert experience[0].title == "A"
    assert transport[0].title == "B"
    assert food[0].title == "C"
```

- [ ] **Step 6.2: 跑测试,确认失败**

Run: `cd api && uv run pytest tests/providers/test_tavily.py -v`

Expected: `ModuleNotFoundError` 或 legacy shim 尚未改写导致导入失败。

- [ ] **Step 6.3: 实现 `providers/search/tavily.py`**

实现要求:
- `TavilySearchProvider.name == "tavily"`。
- `health()` 缺 key 时返回明确 reason。
- `search()` POST `https://api.tavily.com/search`,body 包含 `api_key`,`query`,`search_depth="basic"`,`max_results`,`include_answer=False`。
- `limit` 默认 8。
- 401/403 映射 `auth_failure`;其他非 2xx 映射 `network_failure`。
- Tavily result 映射为 `SearchResult(title,url,snippet,source_note)`。

关键实现骨架:

```python
"""Tavily search provider adapter."""
from __future__ import annotations

from typing import Any

import httpx

from app.models.schemas import SourceNote
from app.providers.types import ProviderError, ProviderHealth, SearchRequest, SearchResult

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def build_search_queries(destination: str) -> tuple[str, str, str]:
    return (
        f"{destination} 必去景点 旅游体验 攻略 2025",
        f"{destination} 交通攻略 怎么去 市内出行 交通方式",
        f"{destination} 美食推荐 必吃 餐厅 小吃 2025",
    )


class TavilySearchProvider:
    name = "tavily"

    def __init__(self, *, api_key: str | None = None, search_url: str = TAVILY_SEARCH_URL) -> None:
        self._api_key = api_key
        self._search_url = search_url

    async def health(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(ok=False, reason="TAVILY_API_KEY is not configured")
        return ProviderHealth(ok=True)

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        api_key = self._require_api_key()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self._search_url,
                    json={
                        "api_key": api_key,
                        "query": request.query,
                        "search_depth": "basic",
                        "max_results": request.limit or 8,
                        "include_answer": False,
                    },
                )
        except httpx.HTTPError as exc:
            raise self._provider_error("network_failure", "Tavily search network failure", exc) from exc
        if response.status_code in (401, 403):
            raise self._provider_error("auth_failure", "Tavily search auth failure")
        if response.status_code >= 400:
            raise self._provider_error("network_failure", f"Tavily search HTTP {response.status_code}")
        data = response.json()
        return [_normalize_tavily_result(result) for result in data.get("results", [])]

    def _require_api_key(self) -> str:
        if not self._api_key:
            raise self._provider_error("auth_failure", "TAVILY_API_KEY is not configured")
        return self._api_key

    def _provider_error(self, code, message: str, cause: object | None = None) -> ProviderError:
        return ProviderError(provider=self.name, kind="search", code=code, message=message, cause=cause)


def _normalize_tavily_result(result: dict[str, Any]) -> SearchResult:
    url = result.get("url") or None
    return SearchResult(
        title=result.get("title") or "",
        url=url,
        snippet=result.get("content") or "",
        source_note=SourceNote(provider="tavily", url=url, note="Tavily search result") if url else None,
    )
```

- [ ] **Step 6.4: 改写 `api/app/services/tavily.py` 为兼容 shim**

保留旧函数名和旧返回类型,内部调用新 provider:

```python
"""Compatibility shim for legacy /api/discover route.

Plan 3 moves real Tavily access to app.providers.search.tavily. This module
keeps the old route and tests working until Plan 6 removes the legacy routes.
"""
from __future__ import annotations

import asyncio

from app.prompts.discover import SearchItem
from app.providers.search.tavily import TavilySearchProvider, build_search_queries
from app.providers.types import SearchRequest, SearchResult


async def search_tavily(query: str, api_key: str) -> list[SearchItem]:
    provider = TavilySearchProvider(api_key=api_key)
    results = await provider.search(SearchRequest(query=query, limit=8))
    return [_to_search_item(result) for result in results]


async def search_tavily_three_sections(
    destination: str, api_key: str
) -> tuple[list[SearchItem], list[SearchItem], list[SearchItem]]:
    q1, q2, q3 = build_search_queries(destination)
    results = await asyncio.gather(
        search_tavily(q1, api_key),
        search_tavily(q2, api_key),
        search_tavily(q3, api_key),
        return_exceptions=True,
    )

    def safe(result: object) -> list[SearchItem]:
        return result if isinstance(result, list) else []

    return safe(results[0]), safe(results[1]), safe(results[2])


def _to_search_item(result: SearchResult) -> SearchItem:
    return SearchItem(
        title=result.title,
        snippet=result.snippet,
        link=result.url or "",
        imageUrl="",
    )
```

- [ ] **Step 6.5: 跑 provider 和 legacy 测试**

Run: `cd api && uv run pytest tests/providers/test_tavily.py tests/test_tavily_query_builder.py -v`

Expected: provider 测试和旧 query builder 测试全部 PASS。

- [ ] **Step 6.6: 提交**

```bash
git add api/app/providers/search/tavily.py api/app/services/tavily.py api/tests/providers/test_tavily.py
git commit -m "feat(api): add tavily search provider adapter"
```

---

## Task 7 — Provider Registry

**Files:**
- Create: `api/app/providers/registry.py`
- Create: `api/tests/providers/test_registry.py`

**Reference:** `web/src/server/providers/registry.ts`, `web/src/server/providers/registry.test.ts`

- [ ] **Step 7.1: 写测试**

写到 `api/tests/providers/test_registry.py`:

```python
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

import pytest

from app.models.schemas import NormalizedPlace
from app.providers.registry import (
    ProviderRegistryError,
    TravelDataProviderRegistry,
    create_default_provider_registry,
    create_provider_registry,
    get_map_provider_order,
)
from app.providers.types import GeocodeRequest, ProviderHealth


def _place(provider: str, name: str = "Shanghai") -> NormalizedPlace:
    return NormalizedPlace(
        id=f"{provider}:shanghai",
        name=name,
        coordinate={"lat": 31.2304, "lng": 121.4737},
        address=name,
        category="city",
        provider=provider,
    )


@dataclass
class FixtureMapProvider:
    name: str
    geocode_handler: Callable[[GeocodeRequest], Awaitable[object]]
    ok: bool = True

    async def health(self) -> ProviderHealth:
        return ProviderHealth(ok=self.ok, reason=None if self.ok else "fixture unhealthy")

    async def geocode(self, request: GeocodeRequest) -> object:
        return await self.geocode_handler(request)

    async def reverse_geocode(self, request):
        return await self.geocode_handler(GeocodeRequest(query="reverse fixture"))

    async def search_places(self, request):
        return [await self.geocode_handler(GeocodeRequest(query="search fixture"))]

    async def route(self, request):
        raise RuntimeError("route fixture unused")


def test_provider_order_uses_country_code_only() -> None:
    assert get_map_provider_order("CN")[:2] == ["amap", "baidu"]
    assert get_map_provider_order("US")[:2] == ["mapbox", "google"]
    assert get_map_provider_order("cn")[:2] == ["mapbox", "google"]


async def test_routes_china_destinations_to_amap() -> None:
    registry = create_provider_registry(
        map_providers={
            "amap": FixtureMapProvider("amap", lambda request: _async_value(_place("amap"))),
            "mapbox": FixtureMapProvider("mapbox", lambda request: _async_value(_place("mapbox"))),
        }
    )

    place = await registry.geocode(GeocodeRequest(country_code="CN", query="Shanghai"))

    assert place.provider == "amap"


async def test_routes_international_destinations_to_mapbox_even_for_chinese_query() -> None:
    registry = create_provider_registry(
        map_providers={
            "amap": FixtureMapProvider("amap", lambda request: _async_value(_place("amap"))),
            "mapbox": FixtureMapProvider("mapbox", lambda request: _async_value(_place("mapbox"))),
        }
    )

    place = await registry.geocode(GeocodeRequest(country_code="US", query="北京"))

    assert place.provider == "mapbox"


async def test_falls_back_when_primary_times_out() -> None:
    async def never(_: GeocodeRequest) -> NormalizedPlace:
        await asyncio.sleep(10)
        return _place("amap")

    registry = create_provider_registry(
        operation_timeout_ms=1,
        map_providers={
            "amap": FixtureMapProvider("amap", never),
            "mapbox": FixtureMapProvider("mapbox", lambda request: _async_value(_place("mapbox"))),
        },
    )

    place = await registry.geocode(GeocodeRequest(country_code="CN", query="Shanghai"))

    assert place.provider == "mapbox"


async def test_falls_back_when_primary_returns_invalid_payload() -> None:
    registry = create_provider_registry(
        map_providers={
            "amap": FixtureMapProvider("amap", lambda request: _async_value({"coordinate": "31,121"})),
            "mapbox": FixtureMapProvider("mapbox", lambda request: _async_value(_place("mapbox"))),
        },
    )

    place = await registry.geocode(GeocodeRequest(country_code="CN", query="Shanghai"))

    assert place.provider == "mapbox"


async def test_returns_registry_error_when_fallback_also_fails() -> None:
    registry = create_provider_registry(
        map_providers={
            "amap": FixtureMapProvider("amap", lambda request: _async_value({"coordinate": "31,121"})),
            "mapbox": FixtureMapProvider("mapbox", lambda request: _async_value({"provider": "bad"})),
        },
    )

    with pytest.raises(ProviderRegistryError) as ei:
        await registry.geocode(GeocodeRequest(country_code="CN", query="Shanghai"))

    assert ei.value.code == "PROVIDER_FALLBACK_FAILED"
    assert [attempt.provider for attempt in ei.value.attempts] == ["amap", "mapbox"]
    assert ei.value.attempts[0].code == "invalid_normalized_payload"


async def test_default_registry_with_missing_env_gives_clear_provider_attempts() -> None:
    registry = create_default_provider_registry(env={})

    with pytest.raises(ProviderRegistryError) as ei:
        await registry.geocode(GeocodeRequest(country_code="CN", query="Shanghai"))

    assert ei.value.attempts
    assert "AMAP_API_KEY is not configured" in ei.value.attempts[0].message


async def _async_value(value):
    return value
```

- [ ] **Step 7.2: 跑测试,确认失败**

Run: `cd api && uv run pytest tests/providers/test_registry.py -v`

Expected: `ModuleNotFoundError`。

- [ ] **Step 7.3: 实现 `registry.py`**

实现要求:
- `get_map_provider_order("CN") -> ["amap","baidu","mapbox","google"]`,其他国家 -> `["mapbox","google","amap","baidu"]`。
- 每次 map operation 最多跑主 provider + 第一个可用 fallback provider,与 TS 行为一致。
- provider health false 记录 attempt 并继续 fallback。
- operation timeout 用 `asyncio.wait_for`,timeout 映射 `ProviderError(code="timeout")`。
- provider 返回值用 Pydantic 校验:
  - `NormalizedPlace.model_validate(value)`
  - `TypeAdapter(list[NormalizedPlace]).validate_python(value)`
  - `NormalizedRoute.model_validate(value)`
- `ProviderRegistryError.attempts` 保留全部失败 attempt。
- `create_default_provider_registry(env)` wiring:
  - AMapMapProvider(api_key=env.get("AMAP_API_KEY"))
  - MapboxMapProvider(access_token=env.get("MAPBOX_ACCESS_TOKEN"))
  - TavilySearchProvider(api_key=env.get("TAVILY_API_KEY"))
  - unavailable weather/supplier providers

关键实现骨架:

```python
"""Provider registry and map fallback orchestration."""
from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import TypeAdapter, ValidationError

from app.domain.geography import is_china_destination
from app.models.schemas import NormalizedPlace, NormalizedRoute
from app.providers.map.amap import AMapMapProvider
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
            validate=lambda value: NormalizedPlace.model_validate(value),
        )

    async def reverse_geocode(self, country_code: str, request: ReverseGeocodeRequest) -> NormalizedPlace:
        return await self._run_map_operation(
            country_code=country_code,
            operation="reverseGeocode",
            execute=lambda provider: provider.reverse_geocode(request),
            validate=lambda value: NormalizedPlace.model_validate(value),
        )

    async def search_places(self, request: PlaceSearchRequest) -> list[NormalizedPlace]:
        if not request.country_code:
            raise ValueError("country_code is required for registry search_places")
        return await self._run_map_operation(
            country_code=request.country_code,
            operation="searchPlaces",
            execute=lambda provider: provider.search_places(request),
            validate=lambda value: _NORMALIZED_PLACE_LIST.validate_python(value),
        )

    async def route(self, country_code: str, request: RouteRequest) -> NormalizedRoute:
        return await self._run_map_operation(
            country_code=country_code,
            operation="route",
            execute=lambda provider: provider.route(request),
            validate=lambda value: NormalizedRoute.model_validate(value),
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
        providers = self._get_map_provider_run_list(country_code)

        for provider in providers:
            health = await self._check_health(provider, operation)
            if not health.ok:
                attempts.append(ProviderAttemptFailure(
                    provider=provider.name,
                    kind="map",
                    operation=operation,
                    code="unhealthy",
                    message=health.reason or f"{provider.name} is unhealthy",
                ))
                continue
            try:
                raw = await self._with_timeout(
                    lambda: execute(provider),
                    provider.name,
                    "map",
                    operation,
                )
                return validate(raw)
            except Exception as exc:
                attempts.append(to_attempt_failure(provider.name, "map", operation, exc))

        raise ProviderRegistryError(operation, attempts)

    def _get_map_provider_run_list(self, country_code: str) -> list[MapProvider]:
        provider_order = get_map_provider_order(country_code)
        primary_id, *fallback_ids = provider_order
        providers: list[MapProvider] = []
        primary = self._map_providers.get(primary_id)
        if primary:
            providers.append(primary)
        fallback = next((self._map_providers.get(provider_id) for provider_id in fallback_ids if self._map_providers.get(provider_id)), None)
        if fallback:
            providers.append(fallback)
        if not providers and self._map_providers:
            providers.append(next(iter(self._map_providers.values())))
        return providers

    async def _check_health(self, provider: MapProvider, operation: str) -> ProviderHealth:
        try:
            return await self._with_timeout(lambda: provider.health(), provider.name, "map", f"{operation}:health")
        except Exception as exc:
            failure = to_attempt_failure(provider.name, "map", f"{operation}:health", exc)
            return ProviderHealth(ok=False, reason=failure.message)

    async def _with_timeout(
        self,
        operation: Callable[[], Awaitable[T]],
        provider: ProviderId,
        kind: ProviderKind,
        operation_name: str,
    ) -> T:
        try:
            return await asyncio.wait_for(operation(), timeout=self._operation_timeout_ms / 1000)
        except asyncio.TimeoutError as exc:
            raise ProviderError(
                provider=provider,
                kind=kind,
                code="timeout",
                message=f"{provider} {operation_name} timed out after {self._operation_timeout_ms}ms",
                cause=exc,
            ) from exc


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


def create_default_provider_registry(env: Mapping[str, str] | None = None) -> TravelDataProviderRegistry:
    env = env if env is not None else os.environ
    return create_provider_registry(
        map_providers={
            "amap": AMapMapProvider(api_key=env.get("AMAP_API_KEY")),
            "mapbox": MapboxMapProvider(access_token=env.get("MAPBOX_ACCESS_TOKEN")),
        },
        search_provider=TavilySearchProvider(api_key=env.get("TAVILY_API_KEY")),
        weather_provider=create_unavailable_weather_provider(),
        supplier_provider=create_unavailable_supplier_provider(),
    )


def get_map_provider_order(country_code: str) -> list[MapProviderId]:
    return ["amap", "baidu", "mapbox", "google"] if is_china_destination(country_code) else ["mapbox", "google", "amap", "baidu"]


def to_attempt_failure(
    provider: ProviderId,
    kind: ProviderKind,
    operation: str,
    error: object,
) -> ProviderAttemptFailure:
    if isinstance(error, ProviderError):
        return ProviderAttemptFailure(provider=provider, kind=kind, operation=operation, code=error.code, message=str(error))
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


def infer_provider_failure_code(error: object) -> ProviderFailureCode:
    return "network_failure" if isinstance(error, (ConnectionError, TimeoutError)) else "unknown_failure"
```

- [ ] **Step 7.4: 跑 registry 测试,确认通过**

Run: `cd api && uv run pytest tests/providers/test_registry.py -v`

Expected: 7 PASS。

- [ ] **Step 7.5: 提交**

```bash
git add api/app/providers/registry.py api/tests/providers/test_registry.py
git commit -m "feat(api): add provider registry with map fallback"
```

---

## Task 8 — Public Exports + Full Verification

**Files:**
- Modify: `api/app/providers/__init__.py`
- Modify: `api/app/providers/map/__init__.py`
- Modify: `api/app/providers/search/__init__.py`

- [ ] **Step 8.1: 填写 package exports**

写到 `api/app/providers/__init__.py`:

```python
"""Provider adapters and registry for travel data."""

from app.providers.registry import (
    ProviderRegistryConfig,
    ProviderRegistryError,
    TravelDataProviderRegistry,
    create_default_provider_registry,
    create_provider_registry,
    get_map_provider_order,
)
from app.providers.types import (
    GeocodeRequest,
    MapProvider,
    PlaceSearchRequest,
    ProviderAttemptFailure,
    ProviderError,
    ProviderHealth,
    ReverseGeocodeRequest,
    RouteRequest,
    SearchProvider,
    SearchRequest,
    SearchResult,
    SupplierProvider,
    SupplierReference,
    SupplierRequest,
    WeatherProvider,
    WeatherRequest,
    WeatherSummary,
)

__all__ = [
    "GeocodeRequest",
    "MapProvider",
    "PlaceSearchRequest",
    "ProviderAttemptFailure",
    "ProviderError",
    "ProviderHealth",
    "ProviderRegistryConfig",
    "ProviderRegistryError",
    "ReverseGeocodeRequest",
    "RouteRequest",
    "SearchProvider",
    "SearchRequest",
    "SearchResult",
    "SupplierProvider",
    "SupplierReference",
    "SupplierRequest",
    "TravelDataProviderRegistry",
    "WeatherProvider",
    "WeatherRequest",
    "WeatherSummary",
    "create_default_provider_registry",
    "create_provider_registry",
    "get_map_provider_order",
]
```

写到 `api/app/providers/map/__init__.py`:

```python
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
```

写到 `api/app/providers/search/__init__.py`:

```python
"""Search provider adapters."""

from app.providers.search.tavily import TavilySearchProvider, build_search_queries

__all__ = ["TavilySearchProvider", "build_search_queries"]
```

- [ ] **Step 8.2: 跑 Plan3 provider 测试**

Run: `cd api && uv run pytest tests/providers -v`

Expected: 所有 `tests/providers` 测试 PASS。

- [ ] **Step 8.3: 跑旧 Tavily shim 测试**

Run: `cd api && uv run pytest tests/test_tavily_query_builder.py -v`

Expected: 5 PASS。

- [ ] **Step 8.4: 跑全量后端测试**

Run: `cd api && uv run pytest -v`

Expected: 全部测试 PASS。

- [ ] **Step 8.5: 跑 ruff**

Run: `cd api && uv run ruff check app tests/providers tests/test_tavily_query_builder.py`

Expected: `All checks passed!`

- [ ] **Step 8.6: 提交**

```bash
git add api/app/providers/__init__.py api/app/providers/map/__init__.py api/app/providers/search/__init__.py
git commit -m "feat(api): expose provider adapter public surface"
```

---

## Definition of Done

- [ ] `cd api && uv run pytest tests/providers -v` 全绿。
- [ ] `cd api && uv run pytest tests/test_tavily_query_builder.py -v` 全绿,证明 legacy shim 未断。
- [ ] `cd api && uv run pytest -v` 全绿。
- [ ] `cd api && uv run ruff check app tests/providers tests/test_tavily_query_builder.py` 通过。
- [ ] `api/app/providers/registry.py:create_default_provider_registry(env={})` 缺 env 时能产生明确 provider attempt,而不是静默空结果。
- [ ] AMap normalization 不泄漏 GCJ02 原坐标到 `NormalizedPlace.coordinate`。
- [ ] Mapbox route 对 `transit/rail/flight` 返回 `capability_unavailable`,不伪造 route。
- [ ] `api/app/services/tavily.py` 只是兼容 shim,真实 Tavily HTTP 逻辑只在 `api/app/providers/search/tavily.py`。

## Follow-up Notes For Plan 5

- Discovery 节点优先使用 `registry.search_provider.search(...)`;若 Tavily health false 或 search 抛错,节点应降级为空搜索输入,让 LLM 仍可生成基础 discovery。
- Stay / transport / planner 节点需要 map data 时只调用 `registry.geocode/search_places/route`,不要直接 import AMap/Mapbox。
- Weather / supplier 当前是明确 unavailable provider;Plan 5 可以把它们的 health reason 写入 source notes 或 planning notes,不要把 unavailable 当成 hard failure。
- Plan 6 删除旧 route 时,可以一起删除 `api/app/services/tavily.py` shim 和旧 `api/tests/test_tavily_query_builder.py`,或把该测试迁到 `tests/providers/test_tavily.py`。
