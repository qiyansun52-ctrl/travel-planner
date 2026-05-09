import { PlanningSession, TransportRecommendation } from "@/domain/schemas"
import { band } from "./discovery"

export async function runTransportAgent(
  session: PlanningSession
): Promise<TransportRecommendation> {
  const currency = session.hard_constraints.currency
  const preferred = session.preferences?.intercity_transport_preference ?? "flexible"
  const mode = preferred === "flight" ? "flight" : preferred === "rail" ? "rail" : "rail"

  return {
    arrival: {
      mode,
      duration_minutes: mode === "flight" ? 160 : 300,
      cost_band: band(currency, mode === "flight" ? 900 : 500, mode === "flight" ? 1600 : 900, "per_trip"),
      note: mode === "flight" ? "Faster arrival with airport transfer padding." : "Lower-friction rail arrival near the city core.",
    },
    departure: {
      mode,
      duration_minutes: mode === "flight" ? 160 : 300,
      cost_band: band(currency, mode === "flight" ? 900 : 500, mode === "flight" ? 1600 : 900, "per_trip"),
      note: "Mirror the arrival mode unless live fares strongly disagree.",
    },
    intracity: {
      primary_mode: "mixed",
      daily_cost_band: band(currency, 40, 120, "per_day"),
      note: "Use transit for cross-city hops and taxi only for late returns.",
    },
    tradeoffs: [
      mode === "flight"
        ? "Flight saves time but adds airport transfer uncertainty."
        : "Rail keeps the trip simpler but can consume more door-to-door time.",
    ],
  }
}
