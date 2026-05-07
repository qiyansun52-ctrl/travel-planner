import { describe, expect, it } from "vitest"
import { validateItinerary } from "./validator"
import { BudgetBand, DiscoveryCard, Itinerary, ItinerarySegment } from "./schemas"

const place = {
  id: "amap:bund",
  name: "The Bund",
  coordinate: { lat: 31.2401, lng: 121.4908 },
  address: null,
  category: "landmark",
  provider: "amap" as const,
}

const perTripBand: BudgetBand = {
  currency: "CNY",
  low: 100,
  high: 200,
  confidence: "medium",
  basis: "per_trip",
}

const discoveryCards: DiscoveryCard[] = [
  {
    id: "card_bund",
    name: "The Bund",
    reason: "Skyline views.",
    category: "landmark",
    tags: ["landmark"],
    suggested_duration_minutes: 120,
    cost_signal: "free",
    cost_estimate: null,
    image_url: null,
    reservation_hint: "Reserve a timed entry.",
    place,
    enrichment_status: "partial",
  },
]

function segment(
  overrides: Partial<ItinerarySegment> & Pick<ItinerarySegment, "type" | "start_time" | "end_time">
): ItinerarySegment {
  return {
    place,
    card_ref: overrides.type === "attraction" ? "card_bund" : null,
    description: "Segment",
    cost_estimate: null,
    ...overrides,
  }
}

function itinerary(overrides: Partial<Itinerary> = {}): Itinerary {
  return {
    id: "itinerary_1",
    session_id: "session_1",
    days: [
      {
        day_index: 1,
        date: "2026-05-10",
        segments: [segment({ type: "attraction", start_time: "09:00", end_time: "11:00" })],
        notes: [],
      },
    ],
    budget: {
      currency: "CNY",
      transport: perTripBand,
      stay: perTripBand,
      food: perTripBand,
      attractions: perTripBand,
      other: perTripBand,
      total: { ...perTripBand, low: 900, high: 1000 },
      user_budget: 1000,
      overrun_flag: false,
    },
    validator_issues: [],
    version: 1,
    ...overrides,
  }
}

describe("validateItinerary", () => {
  it("emits BUDGET_OVERRUN when total high exceeds budget by more than 15 percent", () => {
    const result = validateItinerary(
      itinerary({
        budget: {
          ...itinerary().budget,
          total: { ...perTripBand, low: 1000, high: 1160 },
          user_budget: 1000,
        },
      }),
      { discoveryCards }
    )

    expect(result).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          code: "BUDGET_OVERRUN",
          severity: "error",
          scope: { type: "trip" },
        }),
      ])
    )
  })

  it("emits DAY_OVERLOADED when a day has more than five attraction stops", () => {
    const overloaded = itinerary({
      days: [
        {
          day_index: 1,
          date: "2026-05-10",
          segments: Array.from({ length: 6 }, (_, index) =>
            segment({
              type: "attraction",
              start_time: `${String(9 + index).padStart(2, "0")}:00`,
              end_time: `${String(9 + index).padStart(2, "0")}:30`,
            })
          ),
          notes: [],
        },
      ],
    })

    const result = validateItinerary(overloaded, { discoveryCards })

    expect(result).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          code: "DAY_OVERLOADED",
          severity: "warning",
          scope: { type: "day", day_index: 1 },
        }),
      ])
    )
  })

  it("emits DAY_OVERLOADED when attraction active time exceeds eight hours", () => {
    const result = validateItinerary(
      itinerary({
        days: [
          {
            day_index: 1,
            date: "2026-05-10",
            segments: [segment({ type: "attraction", start_time: "09:00", end_time: "17:30" })],
            notes: [],
          },
        ],
      }),
      { discoveryCards }
    )

    expect(result.some((issue) => issue.code === "DAY_OVERLOADED")).toBe(true)
  })

  it("emits WASTEFUL_ROUTING when movement time exceeds 40 percent of active hours", () => {
    const result = validateItinerary(
      itinerary({
        days: [
          {
            day_index: 1,
            date: "2026-05-10",
            segments: [
              segment({ type: "attraction", start_time: "09:00", end_time: "11:00" }),
              segment({ type: "transit", start_time: "11:00", end_time: "12:00" }),
            ],
            notes: [],
          },
        ],
      }),
      { discoveryCards }
    )

    expect(result).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          code: "WASTEFUL_ROUTING",
          severity: "warning",
        }),
      ])
    )
  })

  it("emits TIMING_UNREALISTIC when reservation-required attraction is outside its operating window", () => {
    const result = validateItinerary(
      itinerary({
        days: [
          {
            day_index: 1,
            date: "2026-05-10",
            segments: [segment({ type: "attraction", start_time: "08:00", end_time: "09:00" })],
            notes: [],
          },
        ],
      }),
      {
        discoveryCards,
        operatingWindowsByCardId: {
          card_bund: { open_time: "10:00", close_time: "18:00" },
        },
      }
    )

    expect(result).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          code: "TIMING_UNREALISTIC",
          severity: "error",
        }),
      ])
    )
  })

  it("emits TIMING_UNREALISTIC when visit duration is shorter than half the suggested duration", () => {
    const result = validateItinerary(
      itinerary({
        days: [
          {
            day_index: 1,
            date: "2026-05-10",
            segments: [segment({ type: "attraction", start_time: "09:00", end_time: "09:45" })],
            notes: [],
          },
        ],
      }),
      { discoveryCards }
    )

    expect(result.some((issue) => issue.code === "TIMING_UNREALISTIC")).toBe(true)
  })

  it("returns no issues for a realistic simple day", () => {
    expect(
      validateItinerary(itinerary(), {
        discoveryCards,
        operatingWindowsByCardId: {
          card_bund: { open_time: "09:00", close_time: "18:00" },
        },
      })
    ).toEqual([])
  })

  it("is pure and returns identical output for identical input", () => {
    const input = itinerary({
      budget: {
        ...itinerary().budget,
        total: { ...perTripBand, low: 1000, high: 1160 },
        user_budget: 1000,
      },
    })
    const serializedBefore = JSON.stringify(input)

    const first = validateItinerary(input, { discoveryCards })
    const second = validateItinerary(input, { discoveryCards })

    expect(second).toEqual(first)
    expect(JSON.stringify(input)).toBe(serializedBefore)
  })
})
