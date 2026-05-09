# LangGraph MVP — Plan 1: Domain Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `web/src/domain/` 的 5 个 TS 模块(schemas、budget、validator、geography、selection)逐文件移植到 Python `api/app/`,作为 Pydantic v2 单一事实源。本子计划只写纯逻辑层,不动 LLM、provider、graph。

**Architecture:** Pydantic v2 替代 Zod;所有字段名 snake_case 与 TS 一致;`extra="forbid"` 等价于 Zod `.strict()`。budget/validator/geography/selection 全部为纯函数,测试用 pytest 直接调用。本子计划完成后老 `api/app/models/{plan,preferences,attraction}.py` 暂不删,Plan 6 删除路由时一起清。

**Tech Stack:** Python 3.12, Pydantic v2, pytest, ruff(已在 pyproject 中)

---

## File Structure

**Create:**
- `api/app/models/schemas.py` — 全部 Pydantic 模型(等价于 `web/src/domain/schemas.ts`)
- `api/app/domain/__init__.py`
- `api/app/domain/budget.py` — `calculate_daily_attraction_slot` / `classify_attraction_cost_signal` / `to_per_trip_band` / `sum_budget_bands` / `DEFAULT_ATTRACTION_SHARE`
- `api/app/domain/validator.py` — `validate_itinerary(itinerary, context) -> list[ValidatorIssue]`
- `api/app/domain/geography.py` — `is_china_destination`
- `api/app/domain/selection.py` — `is_continue_disabled` / `has_density_warning` / `normalize_selected_card_ids`
- `api/tests/domain/__init__.py`
- `api/tests/domain/test_schemas.py`
- `api/tests/domain/test_budget.py`
- `api/tests/domain/test_validator.py`
- `api/tests/domain/test_geography.py`
- `api/tests/domain/test_selection.py`

**Untouched (deleted in later plans):**
- `api/app/models/{plan,preferences,attraction}.py`
- `api/app/routes/{plan,discover}.py`
- `api/tests/test_models_serialization.py` 等老测试

**Reference (read-only — TS 源文件,不改):**
- `web/src/domain/{schemas,budget,validator,geography,selection}.ts`
- `web/src/domain/*.test.ts`

---

## Task 0 — Setup

**Files:**
- Create: `api/app/domain/__init__.py`(空文件)
- Create: `api/tests/domain/__init__.py`(空文件)
- Modify: 无(pyproject 已有 pytest / pydantic)

- [ ] **Step 0.1: 创建空目录占位**

```bash
mkdir -p api/app/domain api/tests/domain
touch api/app/domain/__init__.py api/tests/domain/__init__.py
```

- [ ] **Step 0.2: 确认 pyproject 满足要求**

读 `api/pyproject.toml`,确认 `pydantic>=2.9.0` 已存在(已存在,无需改动)。

- [ ] **Step 0.3: 跑现有测试基线**

Run: `cd api && uv run pytest -v`
Expected: 现有测试全绿(test_models_serialization、test_prompts_*、test_tavily_query_builder)。这是基线,后续每个 task 跑完都要回来确保它仍绿。

- [ ] **Step 0.4: 提交**

```bash
git add api/app/domain/__init__.py api/tests/domain/__init__.py
git commit -m "chore(api): scaffold domain package"
```

---

## Task 1 — Pydantic schemas.py

**Files:**
- Create: `api/app/models/schemas.py`
- Create: `api/tests/domain/test_schemas.py`

**TS reference:** `web/src/domain/schemas.ts`(行 1-358)

- [ ] **Step 1.1: 写 schemas 测试(失败的)**

写到 `api/tests/domain/test_schemas.py`:

```python
"""Validate Pydantic schemas mirror Zod behavior in web/src/domain/schemas.ts."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    BudgetBand,
    Coordinate,
    DiscoveryCard,
    HardConstraints,
    Itinerary,
    NormalizedPlace,
    Preference,
    PlanningSession,
    ValidatorIssue,
)


# ---------- Coordinate ----------

def test_coordinate_accepts_valid_lat_lng() -> None:
    Coordinate(lat=39.9, lng=116.4)


def test_coordinate_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Coordinate(lat=39.9, lng=116.4, alt=10)  # type: ignore[call-arg]


# ---------- BudgetBand ----------

def test_budget_band_requires_high_ge_low() -> None:
    with pytest.raises(ValidationError) as ei:
        BudgetBand(currency="CNY", low=200, high=100, confidence="high", basis="per_trip")
    assert "high" in str(ei.value)


def test_budget_band_currency_must_be_3_chars() -> None:
    with pytest.raises(ValidationError):
        BudgetBand(currency="CN", low=100, high=200, confidence="high", basis="per_trip")


def test_budget_band_negative_amounts_rejected() -> None:
    with pytest.raises(ValidationError):
        BudgetBand(currency="CNY", low=-1, high=100, confidence="high", basis="per_trip")


# ---------- NormalizedPlace ----------

def test_normalized_place_allows_null_coordinate() -> None:
    place = NormalizedPlace(
        id="poi-1",
        name="天安门",
        coordinate=None,
        address=None,
        category=None,
        provider="amap",
    )
    assert place.coordinate is None


def test_normalized_place_rejects_unknown_provider() -> None:
    with pytest.raises(ValidationError):
        NormalizedPlace(
            id="poi-1",
            name="x",
            coordinate=None,
            address=None,
            category=None,
            provider="yahoo",  # type: ignore[arg-type]
        )


# ---------- HardConstraints ----------

def test_hard_constraints_country_code_pattern() -> None:
    with pytest.raises(ValidationError):
        HardConstraints(
            departure_city="Beijing",
            destination_city="Shanghai",
            destination_country_code="cn",  # must be uppercase
            departure_date="2026-05-10",
            duration_days=2,
            traveler_count=2,
            total_budget=4000,
            currency="CNY",
        )


def test_hard_constraints_date_format() -> None:
    with pytest.raises(ValidationError):
        HardConstraints(
            departure_city="Beijing",
            destination_city="Shanghai",
            destination_country_code="CN",
            departure_date="May 10, 2026",
            duration_days=2,
            traveler_count=2,
            total_budget=4000,
            currency="CNY",
        )


# ---------- Preference ----------

def test_preference_enum_values() -> None:
    Preference(
        area_vibe="historic",
        quiet_vs_lively="balanced",
        stay_type="hotel",
        willing_to_change_hotels=False,
        intercity_transport_preference="rail",
        early_departure_tolerance="medium",
        transfer_tolerance="medium",
        pay_more_to_save_time=False,
    )
    with pytest.raises(ValidationError):
        Preference(
            area_vibe="historic",
            quiet_vs_lively="ultra-loud",  # type: ignore[arg-type]
            stay_type="hotel",
            willing_to_change_hotels=False,
            intercity_transport_preference="rail",
            early_departure_tolerance="medium",
            transfer_tolerance="medium",
            pay_more_to_save_time=False,
        )


# ---------- ValidatorIssue ----------

def test_validator_issue_scope_is_open_dict() -> None:
    issue = ValidatorIssue(
        code="BUDGET_OVERRUN",
        severity="error",
        scope={"type": "trip"},
        message="too high",
        suggested_action=None,
    )
    assert issue.scope == {"type": "trip"}


# ---------- Itinerary roundtrip ----------

def _minimal_itinerary_dict() -> dict:
    band = {"currency": "CNY", "low": 0, "high": 0, "confidence": "high", "basis": "per_trip"}
    return {
        "id": "it-1",
        "session_id": "ses-1",
        "days": [],
        "budget": {
            "currency": "CNY",
            "transport": band,
            "stay": band,
            "food": band,
            "attractions": band,
            "other": band,
            "total": band,
            "user_budget": 0,
            "overrun_flag": False,
        },
        "validator_issues": [],
        "version": 1,
    }


def test_itinerary_roundtrip() -> None:
    payload = _minimal_itinerary_dict()
    obj = Itinerary.model_validate(payload)
    assert obj.model_dump() == payload


# ---------- PlanningSession datetime ----------

def test_planning_session_accepts_iso_datetime() -> None:
    session = PlanningSession.model_validate({
        "session_id": "ses-1",
        "hard_constraints": {
            "departure_city": "Beijing",
            "destination_city": "Shanghai",
            "destination_country_code": "CN",
            "departure_date": "2026-05-10",
            "duration_days": 2,
            "traveler_count": 2,
            "total_budget": 4000,
            "currency": "CNY",
        },
        "discovery_state": None,
        "preferences": None,
        "stay_recommendation": None,
        "transport_recommendation": None,
        "itinerary": None,
        "conversation_history": [],
        "validator_issues": [],
        "parent_session_id": None,
        "snapshot_label": None,
        "status": "active",
        "created_at": "2026-05-09T12:00:00Z",
        "updated_at": "2026-05-09T12:00:00Z",
    })
    assert session.session_id == "ses-1"
```

- [ ] **Step 1.2: 跑测试,确认全失败**

Run: `cd api && uv run pytest tests/domain/test_schemas.py -v`
Expected: ImportError on `app.models.schemas` 或所有用例 ERROR(因为模块还不存在)。

- [ ] **Step 1.3: 实现 schemas.py**

写到 `api/app/models/schemas.py`:

```python
"""Pydantic v2 schemas mirroring web/src/domain/schemas.ts.

Single source of truth for all session / discovery / itinerary entities.
Field names match the TypeScript Zod schemas character-for-character so that
JSON payloads are interchangeable.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

# ---------- shared primitive types ----------

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")
_COUNTRY_CODE_PATTERN = re.compile(r"^[A-Z]{2}$")

IsoDate = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$")]
TimeOfDay = Annotated[str, StringConstraints(pattern=r"^\d{2}:\d{2}$")]
CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
Currency = Annotated[str, StringConstraints(min_length=3, max_length=3)]
NonEmpty = Annotated[str, StringConstraints(min_length=1)]

Provider = Literal["amap", "mapbox", "baidu", "google"]
CostSignal = Literal["free", "low", "medium", "high", "unknown"]
Confidence = Literal["high", "medium", "low"]
BudgetBasis = Literal["per_person", "per_party", "per_room_per_night", "per_day", "per_trip"]


class _StrictModel(BaseModel):
    """Base model with Zod-strict equivalent: forbid extra fields, populate by name."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=False)


# ---------- Coordinate ----------

class Coordinate(_StrictModel):
    lat: float
    lng: float


# ---------- NormalizedPlace ----------

class NormalizedPlace(_StrictModel):
    id: NonEmpty
    name: NonEmpty
    coordinate: Coordinate | None
    address: str | None
    category: str | None
    provider: Provider


# ---------- BudgetBand ----------

class BudgetBand(_StrictModel):
    currency: Currency
    low: float = Field(ge=0)
    high: float = Field(ge=0)
    confidence: Confidence
    basis: BudgetBasis

    @model_validator(mode="after")
    def _check_high_ge_low(self) -> "BudgetBand":
        if self.high < self.low:
            raise ValueError("BudgetBand.high must be greater than or equal to low")
        return self


# ---------- NormalizedRoute ----------

class NormalizedRoute(_StrictModel):
    from_: NormalizedPlace = Field(alias="from")
    to: NormalizedPlace
    mode: Literal["walk", "transit", "drive", "rail", "flight"]
    duration_minutes: float = Field(ge=0)
    distance_meters: float = Field(ge=0)
    cost_estimate: BudgetBand | None
    provider: Provider


# ---------- DiscoveryCard / AreaSummary / FoodSummary / SourceNote ----------

class DiscoveryCard(_StrictModel):
    id: NonEmpty
    name: NonEmpty
    reason: NonEmpty
    category: NonEmpty
    tags: list[str]
    suggested_duration_minutes: float = Field(gt=0)
    cost_signal: CostSignal
    cost_estimate: BudgetBand | None
    image_url: str | None
    reservation_hint: str | None
    place: NormalizedPlace | None
    enrichment_status: Literal["complete", "partial", "minimal"]


class AreaSummary(_StrictModel):
    id: NonEmpty
    name: NonEmpty
    vibe_tags: list[str]
    note: NonEmpty
    center: Coordinate


class FoodSummary(_StrictModel):
    id: NonEmpty
    name: NonEmpty
    category: NonEmpty
    description: NonEmpty
    image_url: str | None


class SourceNote(_StrictModel):
    provider: NonEmpty
    url: str | None
    note: NonEmpty


# ---------- BudgetSummary / DiscoveryOutput ----------

class BudgetSummary(_StrictModel):
    currency: Currency
    transport: BudgetBand
    stay: BudgetBand
    food: BudgetBand
    attractions: BudgetBand
    other: BudgetBand
    total: BudgetBand
    user_budget: float = Field(ge=0)
    overrun_flag: bool


class DiscoveryOutput(_StrictModel):
    cards: list[DiscoveryCard]
    food_summaries: list[FoodSummary]
    area_summaries: list[AreaSummary]
    budget_estimate: BudgetSummary
    source_notes: list[SourceNote]


# ---------- Stay ----------

class SampleHotel(_StrictModel):
    name: NonEmpty
    style: NonEmpty
    price_band: BudgetBand
    place: NormalizedPlace


class StayOption(_StrictModel):
    id: NonEmpty
    area: AreaSummary
    fit_reason: NonEmpty
    price_band: BudgetBand
    sample_hotels: list[SampleHotel]


class StayRecommendation(_StrictModel):
    primary: StayOption
    alternatives: list[StayOption]
    user_override_id: str | None


# ---------- Transport ----------

class TransportLeg(_StrictModel):
    mode: Literal["rail", "flight", "drive", "bus", "mixed"]
    duration_minutes: float = Field(ge=0)
    cost_band: BudgetBand
    note: str | None


class IntracityStrategy(_StrictModel):
    primary_mode: Literal["walk", "transit", "taxi", "mixed"]
    daily_cost_band: BudgetBand
    note: str | None


class TransportRecommendation(_StrictModel):
    arrival: TransportLeg
    departure: TransportLeg
    intracity: IntracityStrategy
    tradeoffs: list[str]


# ---------- Itinerary + Validator ----------

class ValidatorIssue(_StrictModel):
    code: NonEmpty
    severity: Literal["warning", "error"]
    scope: dict[str, Any]
    message: NonEmpty
    suggested_action: str | None


class ItinerarySegment(_StrictModel):
    type: Literal[
        "attraction",
        "food",
        "transit",
        "rest",
        "hotel_checkin",
        "hotel_checkout",
        "hotel_return",
    ]
    start_time: TimeOfDay
    end_time: TimeOfDay
    place: NormalizedPlace | None
    card_ref: str | None
    description: NonEmpty
    cost_estimate: BudgetBand | None


class ItineraryDay(_StrictModel):
    day_index: int = Field(gt=0)
    date: IsoDate
    segments: list[ItinerarySegment]
    notes: list[str]


class Itinerary(_StrictModel):
    id: NonEmpty
    session_id: NonEmpty
    days: list[ItineraryDay]
    budget: BudgetSummary
    validator_issues: list[ValidatorIssue]
    version: int = Field(gt=0)


# ---------- HardConstraints / Preference ----------

class HardConstraints(_StrictModel):
    departure_city: NonEmpty
    destination_city: NonEmpty
    destination_country_code: CountryCode
    departure_date: IsoDate
    duration_days: int = Field(gt=0)
    traveler_count: int = Field(gt=0)
    total_budget: float = Field(gt=0)
    currency: Currency


class Preference(_StrictModel):
    area_vibe: NonEmpty
    quiet_vs_lively: Literal["quiet", "balanced", "lively"]
    stay_type: Literal["hotel", "homestay", "flexible"]
    willing_to_change_hotels: bool
    intercity_transport_preference: Literal["rail", "flight", "flexible"]
    early_departure_tolerance: Literal["low", "medium", "high"]
    transfer_tolerance: Literal["low", "medium", "high"]
    pay_more_to_save_time: bool


# ---------- Adjustment + Conversation ----------

class AdjustmentRequest(_StrictModel):
    raw_text: str
    type: Literal["A", "B", "C", "unknown"]
    confidence: float = Field(ge=0, le=1)
    target_scope: Literal[
        "day",
        "segment",
        "stay",
        "transport",
        "budget",
        "duration",
        "destination",
        "traveler_count",
        "none",
    ]
    proposed_change: str | None


class ConversationTurn(_StrictModel):
    id: NonEmpty
    raw_text: str
    classification: AdjustmentRequest | None
    created_at: datetime


# ---------- Discovery / PlanningSession ----------

class DiscoveryState(_StrictModel):
    payload: DiscoveryOutput | None
    selected_card_ids: list[str]


class PlanningSession(_StrictModel):
    session_id: NonEmpty
    hard_constraints: HardConstraints
    discovery_state: DiscoveryState | None
    preferences: Preference | None
    stay_recommendation: StayRecommendation | None
    transport_recommendation: TransportRecommendation | None
    itinerary: Itinerary | None
    conversation_history: list[ConversationTurn]
    validator_issues: list[ValidatorIssue]
    parent_session_id: str | None
    snapshot_label: str | None
    status: Literal["active", "archived"]
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 1.4: 跑测试,确认全过**

Run: `cd api && uv run pytest tests/domain/test_schemas.py -v`
Expected: 全部 PASS。如果有失败逐个修(常见:`from_` alias、`Literal` 使用、`StringConstraints` 写法)。

- [ ] **Step 1.5: 跑老测试基线**

Run: `cd api && uv run pytest -v`
Expected: 老测试仍全绿(我们没动 `app/models/{plan,preferences,attraction}.py`)。

- [ ] **Step 1.6: 提交**

```bash
git add api/app/models/schemas.py api/tests/domain/test_schemas.py
git commit -m "feat(api): add Pydantic schemas mirroring web/src/domain/schemas.ts"
```

---

## Task 2 — Budget 纯函数

**Files:**
- Create: `api/app/domain/budget.py`
- Create: `api/tests/domain/test_budget.py`

**TS reference:** `web/src/domain/budget.ts`(行 1-122)、`web/src/domain/budget.test.ts`(行 1-133)

- [ ] **Step 2.1: 写 budget 测试**

写到 `api/tests/domain/test_budget.py`:

```python
"""Mirror of web/src/domain/budget.test.ts."""
from __future__ import annotations

import pytest

from app.domain.budget import (
    DEFAULT_ATTRACTION_SHARE,
    calculate_daily_attraction_slot,
    classify_attraction_cost_signal,
    sum_budget_bands,
    to_per_trip_band,
)
from app.models.schemas import BudgetBand, BudgetBasis, HardConstraints


HARD_CONSTRAINTS = HardConstraints(
    departure_city="Beijing",
    destination_city="Shanghai",
    destination_country_code="CN",
    departure_date="2026-05-10",
    duration_days=2,
    traveler_count=2,
    total_budget=4000,
    currency="CNY",
)


def _band(high: float, basis: BudgetBasis = "per_person") -> BudgetBand:
    return BudgetBand(currency="CNY", low=high, high=high, confidence="medium", basis=basis)


# ---------- calculate_daily_attraction_slot ----------

def test_calculate_daily_attraction_slot_uses_default_share() -> None:
    assert DEFAULT_ATTRACTION_SHARE == 0.15
    assert calculate_daily_attraction_slot(4000, 2, 2) == 150


# ---------- classify_attraction_cost_signal ----------

def test_classify_returns_unknown_when_cost_missing() -> None:
    assert classify_attraction_cost_signal(None, HARD_CONSTRAINTS) == "unknown"


def test_classify_free_when_zero() -> None:
    assert classify_attraction_cost_signal(_band(0), HARD_CONSTRAINTS) == "free"


def test_classify_low_at_or_below_30pct_of_slot() -> None:
    assert classify_attraction_cost_signal(_band(45), HARD_CONSTRAINTS) == "low"


def test_classify_medium_above_30pct_and_at_or_below_80pct() -> None:
    assert classify_attraction_cost_signal(_band(46), HARD_CONSTRAINTS) == "medium"
    assert classify_attraction_cost_signal(_band(120), HARD_CONSTRAINTS) == "medium"


def test_classify_high_above_80pct() -> None:
    assert classify_attraction_cost_signal(_band(121), HARD_CONSTRAINTS) == "high"


def test_classify_same_attraction_different_for_different_budgets() -> None:
    cheap = HARD_CONSTRAINTS.model_copy(update={"total_budget": 1000})
    pricey = HARD_CONSTRAINTS.model_copy(update={"total_budget": 8000})
    ticket = _band(80)
    assert classify_attraction_cost_signal(ticket, cheap) == "high"
    assert classify_attraction_cost_signal(ticket, pricey) == "low"


# ---------- to_per_trip_band ----------

def test_to_per_trip_converts_per_person_with_traveler_count() -> None:
    band = to_per_trip_band(_band(100), traveler_count=3)
    assert band.low == 300
    assert band.high == 300
    assert band.basis == "per_trip"


def test_to_per_trip_rejects_per_person_without_traveler_count() -> None:
    with pytest.raises(ValueError, match="traveler_count"):
        to_per_trip_band(_band(100))


def test_to_per_trip_converts_per_room_per_night() -> None:
    band = to_per_trip_band(
        _band(400, "per_room_per_night"),
        room_count=2,
        duration_days=3,
    )
    assert band.low == 2400
    assert band.high == 2400
    assert band.basis == "per_trip"


def test_to_per_trip_rejects_per_room_per_night_without_room_count() -> None:
    with pytest.raises(ValueError, match="room_count"):
        to_per_trip_band(_band(400, "per_room_per_night"), duration_days=3)


def test_to_per_trip_converts_per_day_with_duration() -> None:
    band = to_per_trip_band(_band(50, "per_day"), duration_days=4)
    assert band.low == 200
    assert band.high == 200
    assert band.basis == "per_trip"


# ---------- sum_budget_bands ----------

def test_sum_budget_bands_degrades_to_lowest_confidence() -> None:
    a = BudgetBand(currency="CNY", low=80, high=100, confidence="high", basis="per_trip")
    b = BudgetBand(currency="CNY", low=120, high=200, confidence="low", basis="per_trip")
    result = sum_budget_bands("CNY", [a, b])
    assert result.currency == "CNY"
    assert result.low == 200
    assert result.high == 300
    assert result.confidence == "low"
    assert result.basis == "per_trip"


def test_sum_budget_bands_rejects_mixed_basis() -> None:
    a = BudgetBand(currency="CNY", low=100, high=100, confidence="high", basis="per_trip")
    b = BudgetBand(currency="CNY", low=50, high=50, confidence="high", basis="per_person")
    with pytest.raises(ValueError, match="per_trip"):
        sum_budget_bands("CNY", [a, b])


def test_sum_budget_bands_rejects_currency_mismatch() -> None:
    a = BudgetBand(currency="CNY", low=100, high=100, confidence="high", basis="per_trip")
    b = BudgetBand(currency="USD", low=20, high=20, confidence="high", basis="per_trip")
    with pytest.raises(ValueError, match="CNY"):
        sum_budget_bands("CNY", [a, b])
```

- [ ] **Step 2.2: 跑测试,确认全失败**

Run: `cd api && uv run pytest tests/domain/test_budget.py -v`
Expected: ImportError (`app.domain.budget` 不存在)。

- [ ] **Step 2.3: 实现 budget.py**

写到 `api/app/domain/budget.py`:

```python
"""Budget calculation helpers — port of web/src/domain/budget.ts."""
from __future__ import annotations

from typing import Iterable

from app.models.schemas import BudgetBand, Confidence, CostSignal, HardConstraints

DEFAULT_ATTRACTION_SHARE = 0.15


def calculate_daily_attraction_slot(
    total_budget: float,
    duration_days: int,
    traveler_count: int,
    attraction_share: float = DEFAULT_ATTRACTION_SHARE,
) -> float:
    return (total_budget * attraction_share) / (duration_days * traveler_count)


def classify_attraction_cost_signal(
    cost_estimate: BudgetBand | None,
    hard_constraints: HardConstraints,
    attraction_share: float = DEFAULT_ATTRACTION_SHARE,
) -> CostSignal:
    if cost_estimate is None:
        return "unknown"

    per_person = _estimate_per_person_cost(cost_estimate, hard_constraints.traveler_count)
    if per_person is None:
        return "unknown"
    if per_person == 0:
        return "free"

    daily_slot = calculate_daily_attraction_slot(
        hard_constraints.total_budget,
        hard_constraints.duration_days,
        hard_constraints.traveler_count,
        attraction_share,
    )
    if per_person <= daily_slot * 0.3:
        return "low"
    if per_person <= daily_slot * 0.8:
        return "medium"
    return "high"


def to_per_trip_band(
    band: BudgetBand,
    *,
    traveler_count: int | None = None,
    duration_days: int | None = None,
    room_count: int | None = None,
) -> BudgetBand:
    match band.basis:
        case "per_trip":
            return band.model_copy()
        case "per_party":
            return band.model_copy(update={"basis": "per_trip"})
        case "per_person":
            mult = _require_positive("traveler_count", traveler_count)
            return _multiply_band(band, mult)
        case "per_day":
            mult = _require_positive("duration_days", duration_days)
            return _multiply_band(band, mult)
        case "per_room_per_night":
            rooms = _require_positive("room_count", room_count)
            days = _require_positive("duration_days", duration_days)
            return _multiply_band(band, rooms * days)


def sum_budget_bands(currency: str, bands: Iterable[BudgetBand]) -> BudgetBand:
    bands = list(bands)
    for b in bands:
        if b.currency != currency:
            raise ValueError(f"Expected all budget bands to use {currency}")
        if b.basis != "per_trip":
            raise ValueError("sum_budget_bands expects all inputs to have per_trip basis")

    return BudgetBand(
        currency=currency,
        low=sum(b.low for b in bands),
        high=sum(b.high for b in bands),
        confidence=_lowest_confidence([b.confidence for b in bands]),
        basis="per_trip",
    )


# ---------- helpers ----------

def _estimate_per_person_cost(band: BudgetBand, traveler_count: int) -> float | None:
    match band.basis:
        case "per_person":
            return band.high
        case "per_party" | "per_trip":
            return band.high / traveler_count
        case "per_day" | "per_room_per_night":
            return None


def _multiply_band(band: BudgetBand, multiplier: float) -> BudgetBand:
    return band.model_copy(update={
        "low": band.low * multiplier,
        "high": band.high * multiplier,
        "basis": "per_trip",
    })


def _require_positive(name: str, value: int | None) -> int:
    if value is None or value <= 0:
        raise ValueError(f"Budget conversion requires {name}")
    return value


def _lowest_confidence(values: list[Confidence]) -> Confidence:
    if "low" in values:
        return "low"
    if "medium" in values:
        return "medium"
    return "high"
```

- [ ] **Step 2.4: 跑测试,确认全过**

Run: `cd api && uv run pytest tests/domain/test_budget.py -v`
Expected: 全部 PASS。

- [ ] **Step 2.5: 跑全套基线**

Run: `cd api && uv run pytest -v`
Expected: 包括老测试在内全绿。

- [ ] **Step 2.6: 提交**

```bash
git add api/app/domain/budget.py api/tests/domain/test_budget.py
git commit -m "feat(api): add domain budget helpers ported from web/src/domain/budget.ts"
```

---

## Task 3 — Itinerary Validator

**Files:**
- Create: `api/app/domain/validator.py`
- Create: `api/tests/domain/test_validator.py`

**TS reference:** `web/src/domain/validator.ts`(行 1-119)、`web/src/domain/validator.test.ts`(行 1-256)

- [ ] **Step 3.1: 写 validator 测试**

写到 `api/tests/domain/test_validator.py`:

```python
"""Mirror of web/src/domain/validator.test.ts. Pure function: build inputs, assert issue codes."""
from __future__ import annotations

from app.domain.validator import OperatingWindow, ValidatorContext, validate_itinerary
from app.models.schemas import (
    BudgetBand,
    BudgetSummary,
    DiscoveryCard,
    Itinerary,
    ItineraryDay,
    ItinerarySegment,
)


def _band(amount: float = 0) -> BudgetBand:
    return BudgetBand(currency="CNY", low=amount, high=amount, confidence="high", basis="per_trip")


def _summary(total_high: float, user_budget: float) -> BudgetSummary:
    band = _band()
    total = BudgetBand(
        currency="CNY", low=total_high, high=total_high, confidence="high", basis="per_trip"
    )
    return BudgetSummary(
        currency="CNY",
        transport=band,
        stay=band,
        food=band,
        attractions=band,
        other=band,
        total=total,
        user_budget=user_budget,
        overrun_flag=total_high > user_budget,
    )


def _seg(
    *,
    type: str = "attraction",
    start: str = "09:00",
    end: str = "11:00",
    card_ref: str | None = None,
    description: str = "visit",
) -> ItinerarySegment:
    return ItinerarySegment(
        type=type,  # type: ignore[arg-type]
        start_time=start,
        end_time=end,
        place=None,
        card_ref=card_ref,
        description=description,
        cost_estimate=None,
    )


def _card(card_id: str, *, suggested_minutes: float = 60, reservation_hint: str | None = None) -> DiscoveryCard:
    return DiscoveryCard(
        id=card_id,
        name=f"card-{card_id}",
        reason="r",
        category="c",
        tags=[],
        suggested_duration_minutes=suggested_minutes,
        cost_signal="unknown",
        cost_estimate=None,
        image_url=None,
        reservation_hint=reservation_hint,
        place=None,
        enrichment_status="minimal",
    )


def _itinerary(days: list[ItineraryDay], *, total_high: float = 0, user_budget: float = 1000) -> Itinerary:
    return Itinerary(
        id="it-1",
        session_id="ses-1",
        days=days,
        budget=_summary(total_high, user_budget),
        validator_issues=[],
        version=1,
    )


# ---------- BUDGET_OVERRUN ----------

def test_flags_budget_overrun_above_15pct() -> None:
    it = _itinerary(days=[], total_high=1151, user_budget=1000)
    issues = validate_itinerary(it, ValidatorContext(discovery_cards=[]))
    codes = [i.code for i in issues]
    assert "BUDGET_OVERRUN" in codes


def test_does_not_flag_budget_overrun_at_or_below_15pct() -> None:
    it = _itinerary(days=[], total_high=1150, user_budget=1000)
    issues = validate_itinerary(it, ValidatorContext(discovery_cards=[]))
    assert all(i.code != "BUDGET_OVERRUN" for i in issues)


# ---------- DAY_OVERLOADED ----------

def test_flags_day_with_more_than_8_hours_active_attractions() -> None:
    day = ItineraryDay(
        day_index=1,
        date="2026-05-10",
        segments=[
            _seg(start="08:00", end="13:00", type="attraction"),
            _seg(start="14:00", end="18:00", type="attraction"),
        ],  # 9h
        notes=[],
    )
    issues = validate_itinerary(_itinerary([day]), ValidatorContext(discovery_cards=[]))
    assert any(i.code == "DAY_OVERLOADED" for i in issues)


def test_flags_day_with_more_than_5_attraction_segments() -> None:
    segs = [_seg(start=f"{8+i:02d}:00", end=f"{8+i:02d}:30", type="attraction") for i in range(6)]
    day = ItineraryDay(day_index=1, date="2026-05-10", segments=segs, notes=[])
    issues = validate_itinerary(_itinerary([day]), ValidatorContext(discovery_cards=[]))
    assert any(i.code == "DAY_OVERLOADED" for i in issues)


# ---------- WASTEFUL_ROUTING ----------

def test_flags_wasteful_routing_when_transit_exceeds_40pct_of_active() -> None:
    day = ItineraryDay(
        day_index=1,
        date="2026-05-10",
        segments=[
            _seg(start="09:00", end="10:00", type="attraction"),  # 60m active
            _seg(start="10:00", end="10:30", type="transit"),     # 30m
            _seg(start="10:30", end="11:30", type="attraction"),  # 60m active
            # active=120, transit=30 => 25% — should NOT flag
        ],
        notes=[],
    )
    issues = validate_itinerary(_itinerary([day]), ValidatorContext(discovery_cards=[]))
    assert all(i.code != "WASTEFUL_ROUTING" for i in issues)

    day_bad = ItineraryDay(
        day_index=1,
        date="2026-05-10",
        segments=[
            _seg(start="09:00", end="10:00", type="attraction"),  # 60m active
            _seg(start="10:00", end="11:00", type="transit"),     # 60m
            _seg(start="11:00", end="12:00", type="attraction"),  # 60m active
            # active=120, transit=60 => 50% — flag
        ],
        notes=[],
    )
    issues_bad = validate_itinerary(_itinerary([day_bad]), ValidatorContext(discovery_cards=[]))
    assert any(i.code == "WASTEFUL_ROUTING" for i in issues_bad)


# ---------- TIMING_UNREALISTIC: too short ----------

def test_flags_timing_unrealistic_when_under_half_suggested_duration() -> None:
    card = _card("c1", suggested_minutes=120)
    day = ItineraryDay(
        day_index=1,
        date="2026-05-10",
        segments=[_seg(start="09:00", end="09:30", card_ref="c1")],  # 30m, half=60
        notes=[],
    )
    issues = validate_itinerary(_itinerary([day]), ValidatorContext(discovery_cards=[card]))
    assert any(i.code == "TIMING_UNREALISTIC" for i in issues)


# ---------- TIMING_UNREALISTIC: outside operating window ----------

def test_flags_timing_unrealistic_outside_operating_window() -> None:
    card = _card("c1", suggested_minutes=60, reservation_hint="advance booking")
    day = ItineraryDay(
        day_index=1,
        date="2026-05-10",
        segments=[_seg(start="07:00", end="08:00", card_ref="c1")],
        notes=[],
    )
    ctx = ValidatorContext(
        discovery_cards=[card],
        operating_windows_by_card_id={"c1": OperatingWindow(open_time="09:00", close_time="17:00")},
    )
    issues = validate_itinerary(_itinerary([day]), ctx)
    assert any(i.code == "TIMING_UNREALISTIC" for i in issues)


# ---------- pure: no issues path ----------

def test_returns_empty_when_no_problems() -> None:
    card = _card("c1", suggested_minutes=60)
    day = ItineraryDay(
        day_index=1,
        date="2026-05-10",
        segments=[_seg(start="09:00", end="10:00", card_ref="c1")],
        notes=[],
    )
    issues = validate_itinerary(_itinerary([day]), ValidatorContext(discovery_cards=[card]))
    assert issues == []
```

- [ ] **Step 3.2: 跑测试,确认全失败**

Run: `cd api && uv run pytest tests/domain/test_validator.py -v`
Expected: ImportError 或 module not found。

- [ ] **Step 3.3: 实现 validator.py**

写到 `api/app/domain/validator.py`:

```python
"""Itinerary validator — port of web/src/domain/validator.ts.

Pure function: takes a complete itinerary and a context and returns a list of issues.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models.schemas import (
    DiscoveryCard,
    Itinerary,
    ItinerarySegment,
    ValidatorIssue,
)


@dataclass(frozen=True)
class OperatingWindow:
    open_time: str
    close_time: str


@dataclass(frozen=True)
class ValidatorContext:
    discovery_cards: list[DiscoveryCard]
    operating_windows_by_card_id: dict[str, OperatingWindow] = field(default_factory=dict)


def validate_itinerary(itinerary: Itinerary, context: ValidatorContext) -> list[ValidatorIssue]:
    issues: list[ValidatorIssue] = []
    card_by_id = {card.id: card for card in context.discovery_cards}

    if itinerary.budget.total.high > itinerary.budget.user_budget * 1.15:
        issues.append(ValidatorIssue(
            code="BUDGET_OVERRUN",
            severity="error",
            scope={"type": "trip"},
            message=(
                f"Estimated total {itinerary.budget.total.high} "
                f"exceeds the user budget by more than 15%."
            ),
            suggested_action=(
                "Reduce optional costs or ask the user before changing stay or transport assumptions."
            ),
        ))

    for day in itinerary.days:
        attraction_segments = [s for s in day.segments if s.type == "attraction"]
        active_minutes = sum(_segment_duration_minutes(s) for s in attraction_segments)

        if active_minutes > 8 * 60 or len(attraction_segments) > 5:
            issues.append(ValidatorIssue(
                code="DAY_OVERLOADED",
                severity="warning",
                scope={"type": "day", "day_index": day.day_index},
                message=f"Day {day.day_index} may feel too dense.",
                suggested_action="Move one stop into flexible time or another day.",
            ))

        movement_minutes = sum(
            _segment_duration_minutes(s) for s in day.segments if s.type == "transit"
        )
        if active_minutes > 0 and movement_minutes > active_minutes * 0.4:
            issues.append(ValidatorIssue(
                code="WASTEFUL_ROUTING",
                severity="warning",
                scope={"type": "day", "day_index": day.day_index},
                message=f"Day {day.day_index} spends a large share of active time in transit.",
                suggested_action="Group nearby stops or consider a different stay area.",
            ))

        for segment_index, segment in enumerate(day.segments):
            if segment.type != "attraction" or not segment.card_ref:
                continue
            card = card_by_id.get(segment.card_ref)
            if card is None:
                continue

            duration = _segment_duration_minutes(segment)
            if duration < card.suggested_duration_minutes * 0.5:
                issues.append(ValidatorIssue(
                    code="TIMING_UNREALISTIC",
                    severity="error",
                    scope={
                        "type": "segment",
                        "day_index": day.day_index,
                        "segment_index": segment_index,
                        "card_ref": segment.card_ref,
                    },
                    message=f"{card.name} is scheduled for less than half its suggested visit duration.",
                    suggested_action="Lengthen the visit or remove the stop.",
                ))

            window = context.operating_windows_by_card_id.get(segment.card_ref)
            if card.reservation_hint and window and _outside_window(segment, window):
                issues.append(ValidatorIssue(
                    code="TIMING_UNREALISTIC",
                    severity="error",
                    scope={
                        "type": "segment",
                        "day_index": day.day_index,
                        "segment_index": segment_index,
                        "card_ref": segment.card_ref,
                    },
                    message=f"{card.name} is placed outside its known operating window.",
                    suggested_action=f"Schedule it between {window.open_time} and {window.close_time}.",
                ))

    return issues


def _outside_window(segment: ItinerarySegment, window: OperatingWindow) -> bool:
    return (
        _time_to_minutes(segment.start_time) < _time_to_minutes(window.open_time)
        or _time_to_minutes(segment.end_time) > _time_to_minutes(window.close_time)
    )


def _segment_duration_minutes(segment: ItinerarySegment) -> int:
    return max(0, _time_to_minutes(segment.end_time) - _time_to_minutes(segment.start_time))


def _time_to_minutes(value: str) -> int:
    hours, minutes = (int(x) for x in value.split(":"))
    return hours * 60 + minutes
```

- [ ] **Step 3.4: 跑测试,确认全过**

Run: `cd api && uv run pytest tests/domain/test_validator.py -v`
Expected: 全部 PASS。

- [ ] **Step 3.5: 提交**

```bash
git add api/app/domain/validator.py api/tests/domain/test_validator.py
git commit -m "feat(api): add itinerary validator ported from web/src/domain/validator.ts"
```

---

## Task 4 — Geography 与 Selection

**Files:**
- Create: `api/app/domain/geography.py`
- Create: `api/app/domain/selection.py`
- Create: `api/tests/domain/test_geography.py`
- Create: `api/tests/domain/test_selection.py`

**TS reference:** `web/src/domain/geography.ts`(3 行)、`web/src/domain/selection.ts`(11 行)及对应测试。

- [ ] **Step 4.1: 写 geography 测试**

写到 `api/tests/domain/test_geography.py`:

```python
from app.domain.geography import is_china_destination


def test_is_china_destination_returns_true_for_cn() -> None:
    assert is_china_destination("CN") is True


def test_is_china_destination_returns_false_for_other() -> None:
    assert is_china_destination("US") is False
    assert is_china_destination("JP") is False
    assert is_china_destination("") is False
```

- [ ] **Step 4.2: 写 selection 测试**

写到 `api/tests/domain/test_selection.py`:

```python
from app.domain.selection import (
    has_density_warning,
    is_continue_disabled,
    normalize_selected_card_ids,
)


def test_normalize_dedupes_and_drops_falsy() -> None:
    assert normalize_selected_card_ids(["a", "b", "a", "", "c"]) == ["a", "b", "c"]


def test_is_continue_disabled_when_no_real_selection() -> None:
    assert is_continue_disabled([]) is True
    assert is_continue_disabled(["", ""]) is True


def test_is_continue_disabled_false_when_at_least_one_real_id() -> None:
    assert is_continue_disabled(["x"]) is False


def test_has_density_warning_above_5_per_day() -> None:
    assert has_density_warning(11, 2) is True   # 11 > 10
    assert has_density_warning(10, 2) is False  # 10 == 10
    assert has_density_warning(0, 2) is False
```

- [ ] **Step 4.3: 跑测试,确认全失败**

Run: `cd api && uv run pytest tests/domain/test_geography.py tests/domain/test_selection.py -v`
Expected: ImportError。

- [ ] **Step 4.4: 实现 geography.py**

写到 `api/app/domain/geography.py`:

```python
"""Geography helpers — port of web/src/domain/geography.ts."""
from __future__ import annotations


def is_china_destination(country_code: str) -> bool:
    return country_code == "CN"
```

- [ ] **Step 4.5: 实现 selection.py**

写到 `api/app/domain/selection.py`:

```python
"""Discovery selection helpers — port of web/src/domain/selection.ts."""
from __future__ import annotations


def normalize_selected_card_ids(selected: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for card_id in selected:
        if not card_id:
            continue
        if card_id in seen:
            continue
        seen.add(card_id)
        result.append(card_id)
    return result


def is_continue_disabled(selected: list[str]) -> bool:
    return len(normalize_selected_card_ids(selected)) == 0


def has_density_warning(selected_count: int, duration_days: int) -> bool:
    return selected_count > duration_days * 5
```

- [ ] **Step 4.6: 跑两个测试文件,确认全过**

Run: `cd api && uv run pytest tests/domain/test_geography.py tests/domain/test_selection.py -v`
Expected: 全部 PASS。

- [ ] **Step 4.7: 提交**

```bash
git add api/app/domain/geography.py api/app/domain/selection.py \
        api/tests/domain/test_geography.py api/tests/domain/test_selection.py
git commit -m "feat(api): add geography and selection domain helpers"
```

---

## Task 5 — 回归与清理

**Files:**
- Modify: `api/app/domain/__init__.py`(导出便利符号)

- [ ] **Step 5.1: 配置 domain 包的公开 API**

写到 `api/app/domain/__init__.py`:

```python
"""Pure domain logic — no I/O, no LLM, no provider calls."""

from app.domain.budget import (
    DEFAULT_ATTRACTION_SHARE,
    calculate_daily_attraction_slot,
    classify_attraction_cost_signal,
    sum_budget_bands,
    to_per_trip_band,
)
from app.domain.geography import is_china_destination
from app.domain.selection import (
    has_density_warning,
    is_continue_disabled,
    normalize_selected_card_ids,
)
from app.domain.validator import (
    OperatingWindow,
    ValidatorContext,
    validate_itinerary,
)

__all__ = [
    "DEFAULT_ATTRACTION_SHARE",
    "calculate_daily_attraction_slot",
    "classify_attraction_cost_signal",
    "sum_budget_bands",
    "to_per_trip_band",
    "is_china_destination",
    "has_density_warning",
    "is_continue_disabled",
    "normalize_selected_card_ids",
    "OperatingWindow",
    "ValidatorContext",
    "validate_itinerary",
]
```

- [ ] **Step 5.2: 跑全套测试**

Run: `cd api && uv run pytest -v`
Expected: 全绿。包含 5 个新增 domain 测试文件 + 老的 4 个 scaffold 测试。

- [ ] **Step 5.3: lint 检查**

Run: `cd api && uv run python -m compileall app/domain app/models/schemas.py tests/domain`
Expected: 无 SyntaxError。
(如果项目已安装 ruff,跑 `uv run ruff check app/domain app/models/schemas.py tests/domain` 也应通过。)

- [ ] **Step 5.4: 总验收 — Plan 1 DoD 对账**

确认以下条件全部成立:
1. `api/app/models/schemas.py` 存在,所有 30 个 entity 都有对应 Pydantic 模型
2. `api/app/domain/{budget,validator,geography,selection,__init__}.py` 全部存在
3. `api/tests/domain/test_*.py` 5 个测试文件全部存在
4. `cd api && uv run pytest -v` 全绿
5. 老 `api/app/models/{plan,preferences,attraction}.py` 仍在(由 Plan 6 删除)
6. `web/src/domain/*.ts` 没动(由 Plan 7 删除)

- [ ] **Step 5.5: 提交收尾**

```bash
git add api/app/domain/__init__.py
git commit -m "feat(api): expose domain package public surface"
```

- [ ] **Step 5.6: 推送(可选)**

```bash
git push origin feature/mvp-web-app
```

---

## Self-Review 备忘

实施过程中如果遇到以下场景,按提示调整:

| 场景 | 处理 |
|---|---|
| Pydantic v2 报 `ValidationError` 但应当通过 | 检查 `_StrictModel` 的 `extra="forbid"` 是否被某子类覆盖了;`Literal` 拼写是否大小写一致 |
| `to_per_trip_band` 用 `match` 报语法错 | 确认 Python 版本 ≥ 3.10(本项目要求 3.12) |
| Validator 测试用 `_seg(type=...)` 报类型错 | 是 mypy 警告,不影响 pytest;给 `type: ignore[arg-type]` 即可 |
| `from datetime import datetime` 接受字符串失败 | Pydantic v2 默认接受 ISO 8601 字符串,如失败检查输入是否带 `Z` 结尾 |
| `Annotated[str, StringConstraints(...)]` IDE 报红 | 是 IDE 误报,运行时正常 |

## 不做的事(Out of Scope,留给后续 Plan)

- ❌ 不动 `web/src/domain/`(Plan 7 一起删)
- ❌ 不动 `api/app/models/{plan,preferences,attraction}.py`(Plan 6 一起删)
- ❌ 不写 LLM client(Plan 2)
- ❌ 不写 provider 适配(Plan 3)
- ❌ 不接 FastAPI 路由(Plan 6)
- ❌ 不做 Pydantic→TS 自动生成(Plan 8)
