import { describe, expect, it } from "vitest"
import {
  BudgetSummary,
  Itinerary,
  PlanningSession,
  StayRecommendation,
  TransportRecommendation,
  ValidatorIssue,
} from "@/domain/schemas"
import { createPlanningOrchestrator } from "./orchestrator"

const now = new Date().toISOString()

function budget(): BudgetSummary {
  const band = {
    currency: "CNY",
    low: 100,
    high: 200,
    confidence: "medium" as const,
    basis: "per_trip" as const,
  }
  return {
    currency: "CNY",
    transport: band,
    stay: band,
    food: band,
    attractions: band,
    other: band,
    total: { ...band, low: 500, high: 1000 },
    user_budget: 6000,
    overrun_flag: false,
  }
}

function itinerary(id: string): Itinerary {
  return {
    id,
    session_id: "session_test",
    days: [],
    budget: budget(),
    validator_issues: [],
    version: 1,
  }
}

function session(): PlanningSession {
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
    discovery_state: { payload: null, selected_card_ids: [] },
    preferences: {
      area_vibe: "walkable",
      quiet_vs_lively: "balanced",
      stay_type: "hotel",
      willing_to_change_hotels: false,
      intercity_transport_preference: "rail",
      early_departure_tolerance: "medium",
      transfer_tolerance: "medium",
      pay_more_to_save_time: true,
    },
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

const stay: StayRecommendation = {
  primary: {
    id: "stay_primary",
    area: {
      id: "area_1",
      name: "人民广场",
      vibe_tags: ["central"],
      note: "Convenient",
      center: { lat: 31.23, lng: 121.47 },
    },
    fit_reason: "Central and easy",
    price_band: {
      currency: "CNY",
      low: 800,
      high: 1200,
      confidence: "medium",
      basis: "per_trip",
    },
    sample_hotels: [],
  },
  alternatives: [],
  user_override_id: null,
}

const transport: TransportRecommendation = {
  arrival: {
    mode: "rail",
    duration_minutes: 300,
    cost_band: {
      currency: "CNY",
      low: 500,
      high: 700,
      confidence: "medium",
      basis: "per_trip",
    },
    note: "High-speed rail",
  },
  departure: {
    mode: "rail",
    duration_minutes: 300,
    cost_band: {
      currency: "CNY",
      low: 500,
      high: 700,
      confidence: "medium",
      basis: "per_trip",
    },
    note: "High-speed rail",
  },
  intracity: {
    primary_mode: "transit",
    daily_cost_band: {
      currency: "CNY",
      low: 20,
      high: 60,
      confidence: "medium",
      basis: "per_day",
    },
    note: "Metro",
  },
  tradeoffs: [],
}

describe("planning orchestrator", () => {
  it("finalizes without a corrective pass when validation has no errors", async () => {
    let plannerCalls = 0
    const orchestrator = createPlanningOrchestrator({
      runStayAgent: async () => stay,
      runTransportAgent: async () => transport,
      runPlannerAgent: async () => {
        plannerCalls += 1
        return itinerary(`plan_${plannerCalls}`)
      },
      validate: () => [],
    })

    const result = await orchestrator.runFullPlanning(session())
    expect(plannerCalls).toBe(1)
    expect(result.itinerary.id).toBe("plan_1")
    expect(result.validatorIssues).toEqual([])
  })

  it("runs exactly one corrective planner pass for errors and stores final issues", async () => {
    let plannerCalls = 0
    const persistentError: ValidatorIssue = {
      code: "BUDGET_OVERRUN",
      severity: "error",
      scope: { type: "trip" },
      message: "Still expensive",
      suggested_action: "Warn user",
    }
    const orchestrator = createPlanningOrchestrator({
      runStayAgent: async () => stay,
      runTransportAgent: async () => transport,
      runPlannerAgent: async () => {
        plannerCalls += 1
        return itinerary(`plan_${plannerCalls}`)
      },
      validate: () => [persistentError],
    })

    const result = await orchestrator.runFullPlanning(session())
    expect(plannerCalls).toBe(2)
    expect(result.itinerary.id).toBe("plan_2")
    expect(result.itinerary.validator_issues).toEqual([persistentError])
  })

  it("does not rerun planner for warning-only validation results", async () => {
    let plannerCalls = 0
    const warning: ValidatorIssue = {
      code: "DAY_OVERLOADED",
      severity: "warning",
      scope: { type: "day", day_index: 1 },
      message: "Dense day",
      suggested_action: "Move one stop",
    }
    const orchestrator = createPlanningOrchestrator({
      runStayAgent: async () => stay,
      runTransportAgent: async () => transport,
      runPlannerAgent: async () => {
        plannerCalls += 1
        return itinerary(`plan_${plannerCalls}`)
      },
      validate: () => [warning],
    })

    const result = await orchestrator.runFullPlanning(session())
    expect(plannerCalls).toBe(1)
    expect(result.itinerary.validator_issues).toEqual([warning])
  })
})
