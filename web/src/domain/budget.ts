import { BudgetBand, HardConstraints } from "./schemas"

export const DEFAULT_ATTRACTION_SHARE = 0.15

export type CostSignal = "free" | "low" | "medium" | "high" | "unknown"

export interface BudgetConversionContext {
  traveler_count?: number
  duration_days?: number
  room_count?: number
}

export function calculateDailyAttractionSlot(
  totalBudget: number,
  durationDays: number,
  travelerCount: number,
  attractionShare = DEFAULT_ATTRACTION_SHARE
): number {
  return (totalBudget * attractionShare) / (durationDays * travelerCount)
}

export function classifyAttractionCostSignal(
  costEstimate: BudgetBand | null | undefined,
  hardConstraints: HardConstraints,
  attractionShare = DEFAULT_ATTRACTION_SHARE
): CostSignal {
  if (!costEstimate) return "unknown"

  const perPersonCost = estimatePerPersonCost(costEstimate, hardConstraints.traveler_count)
  if (perPersonCost === null) return "unknown"
  if (perPersonCost === 0) return "free"

  const dailyAttractionSlot = calculateDailyAttractionSlot(
    hardConstraints.total_budget,
    hardConstraints.duration_days,
    hardConstraints.traveler_count,
    attractionShare
  )

  if (perPersonCost <= dailyAttractionSlot * 0.3) return "low"
  if (perPersonCost <= dailyAttractionSlot * 0.8) return "medium"
  return "high"
}

export function toPerTripBand(
  band: BudgetBand,
  context: BudgetConversionContext
): BudgetBand {
  switch (band.basis) {
    case "per_trip":
      return { ...band }
    case "per_party":
      return { ...band, basis: "per_trip" }
    case "per_person": {
      const travelerCount = requirePositiveContext(context.traveler_count, "traveler_count")
      return multiplyBand(band, travelerCount)
    }
    case "per_day": {
      const durationDays = requirePositiveContext(context.duration_days, "duration_days")
      return multiplyBand(band, durationDays)
    }
    case "per_room_per_night": {
      const roomCount = requirePositiveContext(context.room_count, "room_count")
      const durationDays = requirePositiveContext(context.duration_days, "duration_days")
      return multiplyBand(band, roomCount * durationDays)
    }
  }
}

export function sumBudgetBands(currency: string, bands: BudgetBand[]): BudgetBand {
  for (const band of bands) {
    if (band.currency !== currency) {
      throw new Error(`Expected all budget bands to use ${currency}`)
    }
    if (band.basis !== "per_trip") {
      throw new Error("sumBudgetBands expects all inputs to have per_trip basis")
    }
  }

  return {
    currency,
    low: bands.reduce((sum, band) => sum + band.low, 0),
    high: bands.reduce((sum, band) => sum + band.high, 0),
    confidence: lowestConfidence(bands.map((band) => band.confidence)),
    basis: "per_trip",
  }
}

function estimatePerPersonCost(band: BudgetBand, travelerCount: number): number | null {
  switch (band.basis) {
    case "per_person":
      return band.high
    case "per_party":
    case "per_trip":
      return band.high / travelerCount
    case "per_day":
    case "per_room_per_night":
      return null
  }
}

function multiplyBand(band: BudgetBand, multiplier: number): BudgetBand {
  return {
    ...band,
    low: band.low * multiplier,
    high: band.high * multiplier,
    basis: "per_trip",
  }
}

function requirePositiveContext(value: number | undefined, name: string): number {
  if (typeof value !== "number" || value <= 0) {
    throw new Error(`Budget conversion requires ${name}`)
  }
  return value
}

function lowestConfidence(confidences: BudgetBand["confidence"][]): BudgetBand["confidence"] {
  if (confidences.includes("low")) return "low"
  if (confidences.includes("medium")) return "medium"
  return "high"
}
