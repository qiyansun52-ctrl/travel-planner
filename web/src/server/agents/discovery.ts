import { nanoid } from "nanoid"
import { classifyAttractionCostSignal } from "@/domain/budget"
import {
  BudgetBand,
  BudgetSummary,
  DiscoveryCard,
  DiscoveryOutput,
  DiscoveryOutputSchema,
  FoodSummary,
  PlanningSession,
} from "@/domain/schemas"
import { callLLM } from "@/server/llm/client"

export interface DiscoveryAgentOptions {
  fixtureMode?: boolean
}

type EnrichmentInput = Pick<
  DiscoveryCard,
  "place" | "image_url" | "cost_estimate" | "reservation_hint"
>

export function computeEnrichmentStatus(
  card: EnrichmentInput
): DiscoveryCard["enrichment_status"] {
  if (!card.place) return "minimal"
  if (card.image_url && card.cost_estimate) return "complete"
  return "partial"
}

export async function runDiscoveryAgent(
  session: PlanningSession,
  options: DiscoveryAgentOptions = {}
): Promise<DiscoveryOutput> {
  if (options.fixtureMode || !process.env.LLM_PROVIDER_API_KEY) {
    return DiscoveryOutputSchema.parse(buildFixtureDiscoveryOutput(session))
  }

  const output = await callLLM({
    system: "You are a travel discovery agent. Return only valid JSON matching the schema.",
    user: buildDiscoveryPrompt(session),
    schema: DiscoveryOutputSchema,
    label: "discovery_agent",
  })

  return DiscoveryOutputSchema.parse({
    ...output,
    cards: output.cards.map((card) => normalizeDiscoveryCard(card, session)),
  })
}

function buildDiscoveryPrompt(session: PlanningSession): string {
  const constraints = session.hard_constraints
  return [
    `Destination: ${constraints.destination_city}, ${constraints.destination_country_code}`,
    `Departure city: ${constraints.departure_city}`,
    `Dates: ${constraints.departure_date} for ${constraints.duration_days} days`,
    `Budget: ${constraints.currency} ${constraints.total_budget}`,
    "Generate discovery cards only. Do not choose a final hotel, final transport route, final itinerary, or specific restaurant.",
    "Cards must include attractions and experiences; food and area summaries are planning context.",
  ].join("\n")
}

function normalizeDiscoveryCard(
  card: DiscoveryCard,
  session: PlanningSession
): DiscoveryCard {
  return {
    ...card,
    cost_signal: classifyAttractionCostSignal(card.cost_estimate, session.hard_constraints),
    enrichment_status: computeEnrichmentStatus(card),
  }
}

function buildFixtureDiscoveryOutput(session: PlanningSession): DiscoveryOutput {
  const { hard_constraints: constraints } = session
  const provider = constraints.destination_country_code === "CN" ? "amap" : "mapbox"
  const city = constraints.destination_city
  const currency = constraints.currency
  const freeBand = band(currency, 0, 0, "per_person", "high")
  const lowBand = band(currency, 35, 80, "per_person", "medium")
  const mediumBand = band(currency, 120, 240, "per_party", "medium")
  const highBand = band(currency, 260, 520, "per_party", "low")

  const rawCards: DiscoveryCard[] = [
    {
      id: "disc_waterfront",
      name: `${city} waterfront walk`,
      reason: "A flexible first stop that gives the city shape before the schedule gets dense.",
      category: "landmark",
      tags: ["orientation", "low pressure"],
      suggested_duration_minutes: 120,
      cost_signal: "unknown",
      cost_estimate: freeBand,
      image_url: "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee",
      reservation_hint: null,
      place: place("waterfront", `${city} waterfront`, provider),
      enrichment_status: "complete",
    },
    {
      id: "disc_old_town",
      name: `${city} old town lanes`,
      reason: "Good for browsing small shops, snacks, and architecture in one compact area.",
      category: "neighborhood",
      tags: ["walkable", "local texture"],
      suggested_duration_minutes: 150,
      cost_signal: "unknown",
      cost_estimate: lowBand,
      image_url: null,
      reservation_hint: null,
      place: place("old-town", `${city} old town`, provider),
      enrichment_status: "partial",
    },
    {
      id: "disc_museum",
      name: `${city} city museum`,
      reason: "A weather-proof anchor that adds context without forcing a full-day commitment.",
      category: "museum",
      tags: ["culture", "indoor"],
      suggested_duration_minutes: 150,
      cost_signal: "unknown",
      cost_estimate: lowBand,
      image_url: "https://images.unsplash.com/photo-1518998053901-5348d3961a04",
      reservation_hint: "Reserve a morning entry if weekend demand is high.",
      place: place("museum", `${city} city museum`, provider),
      enrichment_status: "complete",
    },
    {
      id: "disc_market",
      name: `${city} morning market`,
      reason: "A compact food-and-people-watching stop that works before heavier sightseeing.",
      category: "market",
      tags: ["food", "morning"],
      suggested_duration_minutes: 90,
      cost_signal: "unknown",
      cost_estimate: mediumBand,
      image_url: "https://images.unsplash.com/photo-1504674900247-0877df9cc836",
      reservation_hint: null,
      place: place("market", `${city} morning market`, provider),
      enrichment_status: "complete",
    },
    {
      id: "disc_viewpoint",
      name: `${city} sunset viewpoint`,
      reason: "A natural late-day slot that leaves daytime plans easier to rearrange.",
      category: "viewpoint",
      tags: ["sunset", "photo"],
      suggested_duration_minutes: 90,
      cost_signal: "unknown",
      cost_estimate: highBand,
      image_url: null,
      reservation_hint: null,
      place: place("viewpoint", `${city} sunset viewpoint`, provider),
      enrichment_status: "partial",
    },
    {
      id: "disc_hidden_courtyard",
      name: `${city} hidden courtyard`,
      reason: "A lower-confidence local texture idea kept as optional inspiration.",
      category: "experience",
      tags: ["optional", "quiet"],
      suggested_duration_minutes: 60,
      cost_signal: "unknown",
      cost_estimate: null,
      image_url: null,
      reservation_hint: null,
      place: null,
      enrichment_status: "minimal",
    },
  ]

  const cards = rawCards.map((card) => normalizeDiscoveryCard(card, session))
  const budget_estimate = budgetSummary(currency, constraints.total_budget, {
    transport: band(currency, 900, 1300, "per_trip", "medium"),
    stay: band(currency, 1500, 2200, "per_trip", "medium"),
    food: band(currency, 900, 1400, "per_trip", "medium"),
    attractions: band(currency, 300, 700, "per_trip", "medium"),
    other: band(currency, 200, 400, "per_trip", "low"),
  })

  return {
    cards,
    food_summaries: foodSummaries(city),
    area_summaries: [
      {
        id: "area_central",
        name: `${city} central core`,
        vibe_tags: ["walkable", "transit-rich", "busy"],
        note: "Best default for a first visit and low routing friction.",
        center: { lat: 31.23, lng: 121.47 },
      },
      {
        id: "area_quiet",
        name: `${city} quieter residential edge`,
        vibe_tags: ["calmer", "local food", "slower evenings"],
        note: "Better for lighter evenings, with slightly longer cross-city hops.",
        center: { lat: 31.21, lng: 121.43 },
      },
    ],
    budget_estimate,
    source_notes: [
      {
        provider: "fixture",
        url: null,
        note: "Fixture-backed MVP discovery; live enrichment uses configured providers.",
      },
    ],
  }
}

function place(id: string, name: string, provider: "amap" | "mapbox") {
  return {
    id: `place_${id}`,
    name,
    coordinate: { lat: 31.23 + id.length / 1000, lng: 121.47 + id.length / 1000 },
    address: name,
    category: "poi",
    provider,
  }
}

function foodSummaries(city: string): FoodSummary[] {
  return [
    {
      id: "food_noodles",
      name: `${city} noodle shops`,
      category: "casual",
      description: "Good lunch fallback around transit hubs and old neighborhoods.",
      image_url: null,
    },
    {
      id: "food_modern",
      name: `${city} modern local bistros`,
      category: "dinner",
      description: "Better for one planned dinner after the final walking-heavy day.",
      image_url: null,
    },
  ]
}

export function band(
  currency: string,
  low: number,
  high: number,
  basis: BudgetBand["basis"],
  confidence: BudgetBand["confidence"] = "medium"
): BudgetBand {
  return { currency, low, high, confidence, basis }
}

export function budgetSummary(
  currency: string,
  userBudget: number,
  parts: Pick<BudgetSummary, "transport" | "stay" | "food" | "attractions" | "other">
): BudgetSummary {
  const total = band(
    currency,
    parts.transport.low + parts.stay.low + parts.food.low + parts.attractions.low + parts.other.low,
    parts.transport.high + parts.stay.high + parts.food.high + parts.attractions.high + parts.other.high,
    "per_trip",
    "low"
  )
  return {
    currency,
    ...parts,
    total,
    user_budget: userBudget,
    overrun_flag: total.high > userBudget,
  }
}

export function newId(prefix: string): string {
  return `${prefix}_${nanoid(8)}`
}
