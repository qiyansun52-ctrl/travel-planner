import { describe, expect, it } from "vitest"
import {
  BudgetBandSchema,
  DiscoveryCardSchema,
  HardConstraintsSchema,
  ItinerarySegmentSchema,
  NormalizedPlaceSchema,
  PlanningSessionSchema,
  PreferenceSchema,
  StayRecommendationSchema,
} from "./schemas"

const budgetBand = {
  currency: "CNY",
  low: 100,
  high: 200,
  confidence: "medium",
  basis: "per_trip",
}

const place = {
  id: "amap:B0FFG123",
  name: "The Bund",
  coordinate: { lat: 31.2401, lng: 121.4908 },
  address: "Zhongshan East 1st Road",
  category: "landmark",
  provider: "amap",
}

const area = {
  id: "area_huangpu",
  name: "Huangpu",
  vibe_tags: ["central", "walkable"],
  note: "Central and busy, with fast access to classic sights.",
  center: { lat: 31.2304, lng: 121.4737 },
}

const discoveryCard = {
  id: "card_bund",
  name: "The Bund",
  reason: "Classic skyline views and riverside walking.",
  category: "landmark",
  tags: ["landmark", "night view"],
  suggested_duration_minutes: 90,
  cost_signal: "free",
  cost_estimate: null,
  image_url: "https://example.com/bund.jpg",
  reservation_hint: null,
  place,
  enrichment_status: "complete",
}

const budgetSummary = {
  currency: "CNY",
  transport: budgetBand,
  stay: { ...budgetBand, basis: "per_room_per_night" },
  food: budgetBand,
  attractions: budgetBand,
  other: budgetBand,
  total: budgetBand,
  user_budget: 5000,
  overrun_flag: false,
}

const itinerarySegment = {
  type: "attraction",
  start_time: "09:00",
  end_time: "10:30",
  place,
  card_ref: "card_bund",
  description: "Walk the riverfront and take skyline photos.",
  cost_estimate: null,
}

const validatorIssue = {
  code: "DAY_OVERLOADED",
  severity: "warning",
  scope: { type: "day", day_index: 1 },
  message: "Day 1 may feel too dense.",
  suggested_action: "Move one stop to flexible time.",
}

const itinerary = {
  id: "itinerary_1",
  session_id: "session_1",
  days: [
    {
      day_index: 1,
      date: "2026-05-10",
      segments: [itinerarySegment],
      notes: ["Reserve museum tickets if added later."],
    },
  ],
  budget: budgetSummary,
  validator_issues: [validatorIssue],
  version: 1,
}

const discoveryOutput = {
  cards: [discoveryCard],
  food_summaries: [
    {
      id: "food_xiaolongbao",
      name: "Xiaolongbao",
      category: "dumpling",
      description: "Soup dumplings associated with Shanghai snacks.",
      image_url: null,
    },
  ],
  area_summaries: [area],
  budget_estimate: budgetSummary,
  source_notes: [
    {
      provider: "fixture",
      url: null,
      note: "Fixture data for schema contract tests.",
    },
  ],
}

const stayRecommendation = {
  primary: {
    id: "stay_huangpu",
    area,
    fit_reason: "Best default for first-time visitors focused on classic sights.",
    price_band: { ...budgetBand, basis: "per_room_per_night" },
    sample_hotels: [
      {
        name: "Sample Bund Hotel",
        style: "business",
        price_band: { ...budgetBand, basis: "per_room_per_night" },
        place,
      },
    ],
  },
  alternatives: [],
  user_override_id: null,
}

const transportRecommendation = {
  arrival: {
    mode: "rail",
    duration_minutes: 330,
    cost_band: budgetBand,
    note: "High-speed rail is usually city-center friendly.",
  },
  departure: {
    mode: "rail",
    duration_minutes: 330,
    cost_band: budgetBand,
    note: null,
  },
  intracity: {
    primary_mode: "mixed",
    daily_cost_band: { ...budgetBand, basis: "per_day" },
    note: "Metro plus short taxi hops.",
  },
  tradeoffs: ["Rail is slower than flight but easier with luggage."],
}

const hardConstraints = {
  departure_city: "Beijing",
  destination_city: "Shanghai",
  destination_country_code: "CN",
  departure_date: "2026-05-10",
  duration_days: 3,
  traveler_count: 2,
  total_budget: 5000,
  currency: "CNY",
}

const preferences = {
  area_vibe: "central and walkable",
  quiet_vs_lively: "balanced",
  stay_type: "hotel",
  willing_to_change_hotels: false,
  intercity_transport_preference: "rail",
  early_departure_tolerance: "medium",
  transfer_tolerance: "low",
  pay_more_to_save_time: true,
}

describe("normalized travel schemas", () => {
  it("parses a complete planning session contract", () => {
    const session = {
      session_id: "session_1",
      hard_constraints: hardConstraints,
      discovery_state: {
        payload: discoveryOutput,
        selected_card_ids: ["card_bund"],
      },
      preferences,
      stay_recommendation: stayRecommendation,
      transport_recommendation: transportRecommendation,
      itinerary,
      conversation_history: [],
      validator_issues: [validatorIssue],
      parent_session_id: null,
      snapshot_label: null,
      status: "active",
      created_at: "2026-05-07T00:00:00.000Z",
      updated_at: "2026-05-07T00:00:00.000Z",
    }

    expect(PlanningSessionSchema.parse(session).session_id).toBe("session_1")
  })

  it("rejects renamed hard-constraint fields", () => {
    const result = HardConstraintsSchema.safeParse({
      ...hardConstraints,
      destinationCountryCode: "CN",
      destination_country_code: undefined,
    })

    expect(result.success).toBe(false)
  })

  it("requires BudgetBand.basis", () => {
    const missingBasis: Record<string, unknown> = { ...budgetBand }
    delete missingBasis.basis

    expect(BudgetBandSchema.safeParse(missingBasis).success).toBe(false)
  })

  it("allows DiscoveryCard.place to be null", () => {
    const result = DiscoveryCardSchema.safeParse({
      ...discoveryCard,
      place: null,
      enrichment_status: "minimal",
    })

    expect(result.success).toBe(true)
  })

  it("allows StayRecommendation.user_override_id to be null", () => {
    expect(StayRecommendationSchema.safeParse(stayRecommendation).success).toBe(true)
  })

  it("rejects itinerary segment types outside the extended enum", () => {
    const result = ItinerarySegmentSchema.safeParse({
      ...itinerarySegment,
      type: "hotel",
    })

    expect(result.success).toBe(false)
  })

  it("rejects invalid NormalizedPlace providers", () => {
    expect(
      NormalizedPlaceSchema.safeParse({
        ...place,
        provider: "hotel",
      }).success
    ).toBe(false)
  })

  it("rejects invalid destination country codes", () => {
    expect(
      HardConstraintsSchema.safeParse({
        ...hardConstraints,
        destination_country_code: "China",
      }).success
    ).toBe(false)
  })

  it("parses stay and transport preferences", () => {
    expect(PreferenceSchema.safeParse(preferences).success).toBe(true)
  })
})
