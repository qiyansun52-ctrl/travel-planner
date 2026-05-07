import { describe, expect, it } from "vitest"
import {
  DEFAULT_ATTRACTION_SHARE,
  calculateDailyAttractionSlot,
  classifyAttractionCostSignal,
  sumBudgetBands,
  toPerTripBand,
} from "./budget"
import { BudgetBand, HardConstraints } from "./schemas"

const hardConstraints: HardConstraints = {
  departure_city: "Beijing",
  destination_city: "Shanghai",
  destination_country_code: "CN",
  departure_date: "2026-05-10",
  duration_days: 2,
  traveler_count: 2,
  total_budget: 4000,
  currency: "CNY",
}

function band(high: number, basis: BudgetBand["basis"] = "per_person"): BudgetBand {
  return {
    currency: "CNY",
    low: high,
    high,
    confidence: "medium",
    basis,
  }
}

describe("calculateDailyAttractionSlot", () => {
  it("uses the MVP default attraction share", () => {
    expect(DEFAULT_ATTRACTION_SHARE).toBe(0.15)
    expect(calculateDailyAttractionSlot(4000, 2, 2)).toBe(150)
  })
})

describe("classifyAttractionCostSignal", () => {
  it("returns unknown when cost data is missing", () => {
    expect(classifyAttractionCostSignal(null, hardConstraints)).toBe("unknown")
  })

  it("classifies free when cost is zero", () => {
    expect(classifyAttractionCostSignal(band(0), hardConstraints)).toBe("free")
  })

  it("classifies low at or below 30 percent of the daily attraction slot", () => {
    expect(classifyAttractionCostSignal(band(45), hardConstraints)).toBe("low")
  })

  it("classifies medium above 30 percent and at or below 80 percent", () => {
    expect(classifyAttractionCostSignal(band(46), hardConstraints)).toBe("medium")
    expect(classifyAttractionCostSignal(band(120), hardConstraints)).toBe("medium")
  })

  it("classifies high above 80 percent", () => {
    expect(classifyAttractionCostSignal(band(121), hardConstraints)).toBe("high")
  })

  it("can classify the same attraction differently for different budgets", () => {
    const cheaperTrip = { ...hardConstraints, total_budget: 1000 }
    const expensiveTrip = { ...hardConstraints, total_budget: 8000 }
    const ticket = band(80)

    expect(classifyAttractionCostSignal(ticket, cheaperTrip)).toBe("high")
    expect(classifyAttractionCostSignal(ticket, expensiveTrip)).toBe("low")
  })
})

describe("toPerTripBand", () => {
  it("converts per-person bands with traveler count", () => {
    expect(toPerTripBand(band(100), { traveler_count: 3 })).toMatchObject({
      low: 300,
      high: 300,
      basis: "per_trip",
    })
  })

  it("rejects per-person conversion without traveler count", () => {
    expect(() => toPerTripBand(band(100), {})).toThrow(/traveler_count/)
  })

  it("converts per-room-per-night bands with room count and duration", () => {
    expect(
      toPerTripBand(band(400, "per_room_per_night"), {
        room_count: 2,
        duration_days: 3,
      })
    ).toMatchObject({
      low: 2400,
      high: 2400,
      basis: "per_trip",
    })
  })

  it("rejects per-room-per-night conversion without room count", () => {
    expect(() =>
      toPerTripBand(band(400, "per_room_per_night"), { duration_days: 3 })
    ).toThrow(/room_count/)
  })

  it("converts per-day bands with duration", () => {
    expect(toPerTripBand(band(50, "per_day"), { duration_days: 4 })).toMatchObject({
      low: 200,
      high: 200,
      basis: "per_trip",
    })
  })
})

describe("sumBudgetBands", () => {
  it("sums per-trip bands and degrades confidence to the lowest confidence present", () => {
    const result = sumBudgetBands("CNY", [
      { ...band(100, "per_trip"), low: 80, confidence: "high" },
      { ...band(200, "per_trip"), low: 120, confidence: "low" },
    ])

    expect(result).toEqual({
      currency: "CNY",
      low: 200,
      high: 300,
      confidence: "low",
      basis: "per_trip",
    })
  })

  it("rejects mixed-basis inputs", () => {
    expect(() => sumBudgetBands("CNY", [band(100, "per_trip"), band(50)])).toThrow(
      /per_trip/
    )
  })
})
