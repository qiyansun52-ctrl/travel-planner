import { describe, expect, it } from "vitest"
import { DiscoveryCard, PlanningSession } from "@/domain/schemas"
import { computeEnrichmentStatus, runDiscoveryAgent } from "./discovery"

function session(): PlanningSession {
  const now = new Date().toISOString()
  return {
    session_id: "session_test",
    hard_constraints: {
      departure_city: "北京",
      destination_city: "上海",
      destination_country_code: "CN",
      departure_date: "2026-05-10",
      duration_days: 3,
      traveler_count: 2,
      total_budget: 6000,
      currency: "CNY",
    },
    discovery_state: null,
    preferences: null,
    stay_recommendation: null,
    transport_recommendation: null,
    itinerary: null,
    conversation_history: [],
    validator_issues: [],
    parent_session_id: null,
    snapshot_label: null,
    status: "active",
    created_at: now,
    updated_at: now,
  }
}

describe("discovery agent", () => {
  it("computes enrichment status without treating reservation hints as required", () => {
    const base = {
      place: {
        id: "p1",
        name: "外滩",
        coordinate: { lat: 31.24, lng: 121.49 },
        address: "上海",
        category: "landmark",
        provider: "amap",
      },
      image_url: "https://example.com/bund.jpg",
      cost_estimate: {
        currency: "CNY",
        low: 0,
        high: 0,
        confidence: "high",
        basis: "per_person",
      },
      reservation_hint: null,
    } satisfies Pick<DiscoveryCard, "place" | "image_url" | "cost_estimate" | "reservation_hint">

    expect(computeEnrichmentStatus(base)).toBe("complete")
    expect(computeEnrichmentStatus({ ...base, image_url: null })).toBe("partial")
    expect(computeEnrichmentStatus({ ...base, place: null })).toBe("minimal")
  })

  it("returns schema-valid fixture cards that are safe to render", async () => {
    const output = await runDiscoveryAgent(session(), { fixtureMode: true })
    expect(output.cards.length).toBeGreaterThanOrEqual(6)
    expect(output.cards.some((card) => card.enrichment_status === "minimal")).toBe(true)
    expect(output.budget_estimate.total.basis).toBe("per_trip")
  })
})
