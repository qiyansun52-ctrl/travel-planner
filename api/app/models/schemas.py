"""Pydantic v2 schemas mirroring web/src/domain/schemas.ts.

Single source of truth for all session, discovery, and itinerary entities.
Field names match the TypeScript Zod schemas so JSON payloads stay interchangeable.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

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
    """Zod `.strict()` equivalent for all domain entities."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=False)


class Coordinate(_StrictModel):
    lat: float
    lng: float


class NormalizedPlace(_StrictModel):
    id: NonEmpty
    name: NonEmpty
    coordinate: Coordinate | None
    address: str | None
    category: str | None
    provider: Provider


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


class NormalizedRoute(_StrictModel):
    from_: NormalizedPlace = Field(alias="from")
    to: NormalizedPlace
    mode: Literal["walk", "transit", "drive", "rail", "flight"]
    duration_minutes: float = Field(ge=0)
    distance_meters: float = Field(ge=0)
    cost_estimate: BudgetBand | None
    provider: Provider


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
    conversation_history: list[ConversationTurn] | list[dict[str, Any]]
    validator_issues: list[ValidatorIssue]
    parent_session_id: str | None
    snapshot_label: str | None
    status: Literal["active", "archived"]
    created_at: datetime
    updated_at: datetime
