import { render, screen, within } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import type { PlanningSession } from "@/lib/types"
import { ItineraryView } from "./ItineraryView"

function band(low: number, high: number) {
  return {
    basis: "per_trip" as const,
    confidence: "medium" as const,
    currency: "CNY",
    low,
    high,
  }
}

function sessionFixture(): PlanningSession {
  const centralArea = {
    id: "central",
    name: "People's Square",
    note: "Central and easy to connect from.",
    vibe_tags: ["central", "walkable"],
    center: { lat: 31.2304, lng: 121.4737 },
  }

  const bundPlace = {
    id: "place_bund",
    name: "The Bund",
    provider: "mapbox" as const,
    address: "Zhongshan East 1st Road",
    category: "attraction",
    coordinate: { lat: 31.2402, lng: 121.4903 },
  }

  return {
    session_id: "session_1",
    created_at: "2026-05-11T00:00:00",
    updated_at: "2026-05-11T00:00:00",
    parent_session_id: null,
    snapshot_label: null,
    status: "active",
    conversation_history: [],
    hard_constraints: {
      departure_city: "北京",
      departure_date: "2026-06-01",
      destination_city: "上海",
      destination_country_code: "CN",
      duration_days: 2,
      traveler_count: 2,
      total_budget: 6000,
      currency: "CNY",
    },
    discovery_state: {
      selected_card_ids: ["bund", "museum"],
      payload: {
        cards: [
          {
            id: "bund",
            name: "The Bund waterfront walk",
            reason: "Classic skyline walk that anchors the first evening.",
            category: "attraction",
            tags: ["waterfront", "night view"],
            suggested_duration_minutes: 120,
            cost_signal: "free",
            cost_estimate: band(0, 0),
            image_url: "https://images.example/bund.jpg",
            reservation_hint: null,
            enrichment_status: "complete",
            place: bundPlace,
          },
          {
            id: "museum",
            name: "Shanghai Museum",
            reason: "A compact cultural block near People's Square.",
            category: "museum",
            tags: ["culture", "rain-safe"],
            suggested_duration_minutes: 150,
            cost_signal: "low",
            cost_estimate: band(0, 120),
            image_url: "https://images.example/museum.jpg",
            reservation_hint: "Reserve in advance during holidays.",
            enrichment_status: "partial",
            place: null,
          },
        ],
        food_summaries: [],
        area_summaries: [centralArea],
        budget_estimate: {
          currency: "CNY",
          user_budget: 6000,
          overrun_flag: false,
          transport: band(600, 900),
          stay: band(1600, 2200),
          food: band(600, 900),
          attractions: band(200, 500),
          other: band(150, 400),
          total: band(3150, 4900),
        },
        source_notes: [],
      },
    },
    preferences: {
      area_vibe: "central, walkable, good food nearby",
      quiet_vs_lively: "balanced",
      stay_type: "homestay",
      willing_to_change_hotels: false,
      intercity_transport_preference: "rail",
      early_departure_tolerance: "medium",
      transfer_tolerance: "medium",
      pay_more_to_save_time: true,
    },
    stay_recommendation: {
      user_override_id: null,
      primary: {
        id: "stay_central",
        area: centralArea,
        fit_reason: "Central for selected sights and food access.",
        price_band: band(1600, 2200),
        sample_hotels: [],
      },
      alternatives: [],
    },
    transport_recommendation: {
      arrival: {
        mode: "rail",
        duration_minutes: 330,
        cost_band: band(550, 750),
        note: "Arrive by rail.",
      },
      departure: {
        mode: "rail",
        duration_minutes: 330,
        cost_band: band(550, 750),
        note: "Return by rail.",
      },
      intracity: {
        primary_mode: "transit",
        daily_cost_band: band(60, 120),
        note: "Use metro plus short walks.",
      },
      tradeoffs: ["Rail keeps arrival predictable."],
    },
    itinerary: {
      id: "itinerary_1",
      session_id: "session_1",
      version: 1,
      budget: {
        currency: "CNY",
        user_budget: 6000,
        overrun_flag: false,
        transport: band(1100, 1500),
        stay: band(1600, 2200),
        food: band(600, 900),
        attractions: band(200, 500),
        other: band(150, 400),
        total: band(3650, 5500),
      },
      validator_issues: [
        {
          code: "reservation_check",
          severity: "warning",
          scope: { day_index: 2 },
          message: "Museum reservation may be required.",
          suggested_action: "Confirm the opening window.",
        },
      ],
      days: [
        {
          day_index: 1,
          date: "2026-06-01",
          notes: ["Start with a skyline evening."],
          segments: [
            {
              type: "hotel_checkin",
              start_time: "09:00",
              end_time: "09:30",
              place: null,
              card_ref: null,
              description: "Drop bags near People's Square.",
              cost_estimate: null,
            },
            {
              type: "attraction",
              start_time: "10:00",
              end_time: "12:00",
              place: bundPlace,
              card_ref: "bund",
              description: "Walk the riverfront and save photo time.",
              cost_estimate: band(0, 0),
            },
          ],
        },
        {
          day_index: 2,
          date: "2026-06-02",
          notes: ["Culture-heavy day with a lighter evening."],
          segments: [
            {
              type: "attraction",
              start_time: "10:00",
              end_time: "12:30",
              place: null,
              card_ref: "museum",
              description: "Visit the museum collection.",
              cost_estimate: band(0, 120),
            },
            {
              type: "rest",
              start_time: "14:00",
              end_time: "16:00",
              place: null,
              card_ref: null,
              description: "Flexible rest block.",
              cost_estimate: null,
            },
          ],
        },
      ],
    },
    validator_issues: [],
  }
}

function renderItinerary(session = sessionFixture()) {
  render(
    <ItineraryView
      adjustmentPanel={<section aria-label="Adjustment panel">Adjustment panel slot</section>}
      session={session}
      onStayOverride={vi.fn()}
    />,
  )
}

describe("ItineraryView", () => {
  it("renders story-led command center sections with itinerary validation details", () => {
    renderItinerary()

    expect(screen.getByText("Destination story")).toBeVisible()
    expect(screen.getByText("Budget fit")).toBeVisible()
    expect(screen.getByText("Narrative route")).toBeVisible()

    const executionRegion = screen.getByRole("region", { name: "Detailed itinerary" })
    expect(executionRegion).toBeVisible()
    expect(within(executionRegion).getByText("Day-by-day execution")).toBeVisible()

    expect(screen.getByRole("heading", { name: "Companion brief" })).toBeVisible()
    expect(screen.getByText("Adjustment panel slot")).toBeVisible()
    expect(screen.getByText("reservation_check")).toBeVisible()
    expect(screen.getByText(/Museum reservation may be required/)).toBeVisible()
  })

  it("renders the route texture fallback when discovery images are missing", () => {
    const session = sessionFixture()
    const discovery = session.discovery_state
    if (discovery?.payload) {
      discovery.payload.cards = discovery.payload.cards.map((card) => ({
        ...card,
        image_url: null,
      }))
    }

    renderItinerary(session)

    expect(screen.getByText("Route texture")).toBeVisible()
  })

  it("surfaces the over-budget metric when the itinerary exceeds budget", () => {
    const session = sessionFixture()
    if (session.itinerary) {
      session.itinerary.budget = {
        ...session.itinerary.budget,
        overrun_flag: true,
        total: band(6200, 7000),
      }
    }

    renderItinerary(session)

    expect(screen.getByText("Over budget")).toBeVisible()
  })
})
