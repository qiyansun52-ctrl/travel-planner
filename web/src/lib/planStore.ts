import { TravelPlan } from "./types"

const PLANS_KEY = "travel_plans"

export function savePlan(plan: TravelPlan): void {
  if (typeof window === "undefined") return
  const plans = getPlans()
  plans[plan.id] = plan
  localStorage.setItem(PLANS_KEY, JSON.stringify(plans))
}

export function getPlan(id: string): TravelPlan | null {
  if (typeof window === "undefined") return null
  const plans = getPlans()
  return plans[id] ?? null
}

export function getPlans(): Record<string, TravelPlan> {
  if (typeof window === "undefined") return {}
  try {
    return JSON.parse(localStorage.getItem(PLANS_KEY) ?? "{}")
  } catch {
    return {}
  }
}

export function deletePlan(id: string): void {
  if (typeof window === "undefined") return
  const plans = getPlans()
  delete plans[id]
  localStorage.setItem(PLANS_KEY, JSON.stringify(plans))
}
