"""Discovery graph node."""

from __future__ import annotations

import os
from typing import Literal

from app.domain.budget import classify_attraction_cost_signal
from app.graph.state import GraphState, PlanState, append_progress, validate_graph_state
from app.llm.client import LLMProvider, generate_structured
from app.llm.cost_logger import LLMCostLogger
from app.models.schemas import (
    AreaSummary,
    BudgetBand,
    BudgetSummary,
    Coordinate,
    DiscoveryCard,
    DiscoveryOutput,
    FoodSummary,
    NormalizedPlace,
    PlanningSession,
    SourceNote,
)


def compute_enrichment_status(card: DiscoveryCard) -> Literal["complete", "partial", "minimal"]:
    if card.place is None:
        return "minimal"
    if card.image_url and card.cost_estimate:
        return "complete"
    return "partial"


async def run_discovery_agent(
    session: PlanningSession,
    *,
    fixture_mode: bool = False,
    llm_provider: LLMProvider | None = None,
    cost_logger: LLMCostLogger | None = None,
) -> DiscoveryOutput:
    if fixture_mode or not _has_llm_api_key():
        return _build_fixture_discovery_output(session)

    output = await generate_structured(
        system="You are a travel discovery agent. Return only valid JSON matching the schema.",
        user=_build_discovery_prompt(session),
        schema=DiscoveryOutput,
        label="discovery_agent",
        provider=llm_provider,
        cost_logger=cost_logger,
    )
    return output.model_copy(
        update={"cards": [_normalize_discovery_card(card, session) for card in output.cards]}
    )


async def run_discovery_node(state: PlanState) -> GraphState:
    parsed = validate_graph_state(state)
    output = await run_discovery_agent(parsed.session, fixture_mode=parsed.fixture_mode)
    updated = append_progress(
        parsed.model_copy(update={"discovery_output": output}),
        "discovery",
        "completed",
        {"card_count": len(output.cards)},
    )
    return GraphState(
        discovery_output=output.model_dump(mode="json"),
        progress_events=[event.model_dump(mode="json") for event in updated.progress_events],
    )


def band(
    currency: str,
    low: float,
    high: float,
    basis: str,
    confidence: str = "medium",
) -> BudgetBand:
    return BudgetBand(
        currency=currency,
        low=low,
        high=high,
        confidence=confidence,
        basis=basis,
    )


def budget_summary(
    currency: str,
    user_budget: float,
    *,
    transport: BudgetBand,
    stay: BudgetBand,
    food: BudgetBand,
    attractions: BudgetBand,
    other: BudgetBand,
) -> BudgetSummary:
    total = band(
        currency,
        transport.low + stay.low + food.low + attractions.low + other.low,
        transport.high + stay.high + food.high + attractions.high + other.high,
        "per_trip",
        "low",
    )
    return BudgetSummary(
        currency=currency,
        transport=transport,
        stay=stay,
        food=food,
        attractions=attractions,
        other=other,
        total=total,
        user_budget=user_budget,
        overrun_flag=total.high > user_budget,
    )


def _has_llm_api_key() -> bool:
    return bool(os.environ.get("LLM_PROVIDER_API_KEY") or os.environ.get("GEMINI_API_KEY"))


def _build_discovery_prompt(session: PlanningSession) -> str:
    constraints = session.hard_constraints
    return "\n".join(
        [
            f"Destination: {constraints.destination_city}, {constraints.destination_country_code}",
            f"Departure city: {constraints.departure_city}",
            f"Dates: {constraints.departure_date} for {constraints.duration_days} days",
            f"Budget: {constraints.currency} {constraints.total_budget}",
            (
                "Generate discovery cards only. Do not choose a final hotel, final transport "
                "route, final itinerary, or specific restaurant."
            ),
            "Cards must include attractions and experiences; food and area summaries are planning context.",
        ]
    )


def _normalize_discovery_card(card: DiscoveryCard, session: PlanningSession) -> DiscoveryCard:
    return card.model_copy(
        update={
            "cost_signal": classify_attraction_cost_signal(
                card.cost_estimate,
                session.hard_constraints,
            ),
            "enrichment_status": compute_enrichment_status(card),
        }
    )


def _build_fixture_discovery_output(session: PlanningSession) -> DiscoveryOutput:
    constraints = session.hard_constraints
    provider = "amap" if constraints.destination_country_code == "CN" else "mapbox"
    city = constraints.destination_city
    currency = constraints.currency
    free_band = band(currency, 0, 0, "per_person", "high")
    low_band = band(currency, 35, 80, "per_person")
    medium_band = band(currency, 120, 240, "per_party")
    high_band = band(currency, 260, 520, "per_party", "low")

    raw_cards = [
        DiscoveryCard(
            id="disc_waterfront",
            name=f"{city} waterfront walk",
            reason="A flexible first stop that gives the city shape before the schedule gets dense.",
            category="landmark",
            tags=["orientation", "low pressure"],
            suggested_duration_minutes=120,
            cost_signal="unknown",
            cost_estimate=free_band,
            image_url="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee",
            reservation_hint=None,
            place=_place("waterfront", f"{city} waterfront", provider),
            enrichment_status="complete",
        ),
        DiscoveryCard(
            id="disc_old_town",
            name=f"{city} old town lanes",
            reason="Good for browsing small shops, snacks, and architecture in one compact area.",
            category="neighborhood",
            tags=["walkable", "local texture"],
            suggested_duration_minutes=150,
            cost_signal="unknown",
            cost_estimate=low_band,
            image_url=None,
            reservation_hint=None,
            place=_place("old-town", f"{city} old town", provider),
            enrichment_status="partial",
        ),
        DiscoveryCard(
            id="disc_museum",
            name=f"{city} city museum",
            reason="A weather-proof anchor that adds context without forcing a full-day commitment.",
            category="museum",
            tags=["culture", "indoor"],
            suggested_duration_minutes=150,
            cost_signal="unknown",
            cost_estimate=low_band,
            image_url="https://images.unsplash.com/photo-1518998053901-5348d3961a04",
            reservation_hint="Reserve a morning entry if weekend demand is high.",
            place=_place("museum", f"{city} city museum", provider),
            enrichment_status="complete",
        ),
        DiscoveryCard(
            id="disc_market",
            name=f"{city} morning market",
            reason="A compact food-and-people-watching stop that works before heavier sightseeing.",
            category="market",
            tags=["food", "morning"],
            suggested_duration_minutes=90,
            cost_signal="unknown",
            cost_estimate=medium_band,
            image_url="https://images.unsplash.com/photo-1504674900247-0877df9cc836",
            reservation_hint=None,
            place=_place("market", f"{city} morning market", provider),
            enrichment_status="complete",
        ),
        DiscoveryCard(
            id="disc_viewpoint",
            name=f"{city} sunset viewpoint",
            reason="A natural late-day slot that leaves daytime plans easier to rearrange.",
            category="viewpoint",
            tags=["sunset", "photo"],
            suggested_duration_minutes=90,
            cost_signal="unknown",
            cost_estimate=high_band,
            image_url=None,
            reservation_hint=None,
            place=_place("viewpoint", f"{city} sunset viewpoint", provider),
            enrichment_status="partial",
        ),
        DiscoveryCard(
            id="disc_hidden_courtyard",
            name=f"{city} hidden courtyard",
            reason="A lower-confidence local texture idea kept as optional inspiration.",
            category="experience",
            tags=["optional", "quiet"],
            suggested_duration_minutes=60,
            cost_signal="unknown",
            cost_estimate=None,
            image_url=None,
            reservation_hint=None,
            place=None,
            enrichment_status="minimal",
        ),
    ]

    return DiscoveryOutput(
        cards=[_normalize_discovery_card(card, session) for card in raw_cards],
        food_summaries=_food_summaries(city),
        area_summaries=[
            AreaSummary(
                id="area_central",
                name=f"{city} central core",
                vibe_tags=["walkable", "transit-rich", "busy"],
                note="Best default for a first visit and low routing friction.",
                center=Coordinate(lat=31.23, lng=121.47),
            ),
            AreaSummary(
                id="area_quiet",
                name=f"{city} quieter residential edge",
                vibe_tags=["calmer", "local food", "slower evenings"],
                note="Better for lighter evenings, with slightly longer cross-city hops.",
                center=Coordinate(lat=31.21, lng=121.43),
            ),
        ],
        budget_estimate=budget_summary(
            currency,
            constraints.total_budget,
            transport=band(currency, 900, 1300, "per_trip"),
            stay=band(currency, 1500, 2200, "per_trip"),
            food=band(currency, 900, 1400, "per_trip"),
            attractions=band(currency, 300, 700, "per_trip"),
            other=band(currency, 200, 400, "per_trip", "low"),
        ),
        source_notes=[
            SourceNote(
                provider="fixture",
                url=None,
                note="Fixture-backed MVP discovery; live enrichment uses configured providers.",
            )
        ],
    )


def _place(id_suffix: str, name: str, provider: str) -> NormalizedPlace:
    offset = len(id_suffix) / 1000
    return NormalizedPlace(
        id=f"place_{id_suffix}",
        name=name,
        coordinate=Coordinate(lat=31.23 + offset, lng=121.47 + offset),
        address=name,
        category="poi",
        provider=provider,
    )


def _food_summaries(city: str) -> list[FoodSummary]:
    return [
        FoodSummary(
            id="food_noodles",
            name=f"{city} noodle shops",
            category="casual",
            description="Good lunch fallback around transit hubs and old neighborhoods.",
            image_url=None,
        ),
        FoodSummary(
            id="food_modern",
            name=f"{city} modern local bistros",
            category="dinner",
            description="Better for one planned dinner after the final walking-heavy day.",
            image_url=None,
        ),
    ]
