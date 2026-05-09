import {
  PlanningSession,
  StayOption,
  StayRecommendation,
} from "@/domain/schemas"
import { band } from "./discovery"

export async function runStayAgent(session: PlanningSession): Promise<StayRecommendation> {
  const city = session.hard_constraints.destination_city
  const currency = session.hard_constraints.currency
  const areas = session.discovery_state?.payload?.area_summaries ?? []

  const primaryArea =
    areas[0] ?? {
      id: "area_central",
      name: `${city} central core`,
      vibe_tags: ["central", "walkable"],
      note: "Balanced base for first-time planning.",
      center: { lat: 31.23, lng: 121.47 },
    }

  const alternativeArea =
    areas[1] ?? {
      id: "area_quiet",
      name: `${city} quieter edge`,
      vibe_tags: ["calm", "local"],
      note: "Softer evenings with longer transfer tradeoffs.",
      center: { lat: 31.21, lng: 121.43 },
    }

  return {
    primary: option("stay_primary", primaryArea, currency, "Best balance of transit access and recovery time."),
    alternatives: [
      option("stay_alt_quiet", alternativeArea, currency, "Better if quiet evenings matter more than transfer time."),
      option("stay_alt_value", primaryArea, currency, "Value-first backup near the same transit spine."),
    ],
    user_override_id: session.stay_recommendation?.user_override_id ?? null,
  }
}

function option(
  id: string,
  area: StayOption["area"],
  currency: string,
  fitReason: string
): StayOption {
  return {
    id,
    area,
    fit_reason: fitReason,
    price_band: band(currency, 1200, 2200, "per_trip", "medium"),
    sample_hotels: [],
  }
}
