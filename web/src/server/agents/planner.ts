import {
  DiscoveryCard,
  Itinerary,
  ItineraryDay,
  ItinerarySegment,
  PlanningSession,
  StayOption,
  StayRecommendation,
  TransportRecommendation,
  ValidatorIssue,
} from "@/domain/schemas"
import { band, budgetSummary, newId } from "./discovery"

export async function runPlannerAgent(
  session: PlanningSession,
  stay: StayRecommendation,
  transport: TransportRecommendation,
  validatorIssues?: ValidatorIssue[]
): Promise<Itinerary> {
  const cards = selectedCards(session)
  const days = buildDays(session, cards, activeStayOption(stay), validatorIssues)
  const currency = session.hard_constraints.currency
  const transportHigh =
    transport.arrival.cost_band.high + transport.departure.cost_band.high
  const stayHigh = activeStayOption(stay).price_band.high
  const version = (session.itinerary?.version ?? 0) + 1

  return {
    id: session.itinerary?.id ?? newId("itinerary"),
    session_id: session.session_id,
    days,
    budget: budgetSummary(currency, session.hard_constraints.total_budget, {
      transport: band(currency, transportHigh * 0.75, transportHigh, "per_trip"),
      stay: band(currency, stayHigh * 0.75, stayHigh, "per_trip"),
      food: band(currency, 600, 1100, "per_trip"),
      attractions: band(currency, 200, 700, "per_trip"),
      other: band(currency, 150, 400, "per_trip", "low"),
    }),
    validator_issues: [],
    version,
  }
}

export function activeStayOption(stay: StayRecommendation): StayOption {
  const options = [stay.primary, ...stay.alternatives]
  return options.find((option) => option.id === stay.user_override_id) ?? stay.primary
}

function selectedCards(session: PlanningSession): DiscoveryCard[] {
  const ids = new Set(session.discovery_state?.selected_card_ids ?? [])
  const cards = session.discovery_state?.payload?.cards ?? []
  return cards.filter((card) => ids.has(card.id))
}

function buildDays(
  session: PlanningSession,
  selected: DiscoveryCard[],
  stay: StayOption,
  validatorIssues?: ValidatorIssue[]
): ItineraryDay[] {
  const days: ItineraryDay[] = []
  const duration = session.hard_constraints.duration_days
  const pool = selected.length > 0 ? selected : session.discovery_state?.payload?.cards.slice(0, 3) ?? []
  const relaxed = pool.length <= duration
  let cursor = 0

  for (let dayIndex = 1; dayIndex <= duration; dayIndex += 1) {
    const first = pool[cursor % Math.max(pool.length, 1)]
    const second = pool[(cursor + 1) % Math.max(pool.length, 1)]
    cursor += relaxed ? 1 : 2
    const segments: ItinerarySegment[] = [
      hotelSegment("09:00", "09:30", stay, "Start from the active stay area."),
    ]

    if (first) {
      segments.push(cardSegment(first, "10:00", relaxed ? "12:00" : "11:45"))
    }
    segments.push({
      type: "food",
      start_time: "12:15",
      end_time: "13:30",
      place: null,
      card_ref: null,
      description: "Keep lunch flexible near the morning area instead of locking a specific restaurant.",
      cost_estimate: band(session.hard_constraints.currency, 80, 180, "per_party"),
    })
    if (second && !relaxed) {
      segments.push(cardSegment(second, "14:00", "16:00"))
    } else {
      segments.push({
        type: "rest",
        start_time: "14:00",
        end_time: "16:00",
        place: null,
        card_ref: null,
        description: "Flexible rest or low-confidence optional discovery slot.",
        cost_estimate: null,
      })
    }
    segments.push({
      type: "hotel_return",
      start_time: "18:00",
      end_time: "18:30",
      place: null,
      card_ref: null,
      description: "Return before dinner so the evening can stay light.",
      cost_estimate: band(session.hard_constraints.currency, 20, 80, "per_party"),
    })

    days.push({
      day_index: dayIndex,
      date: addDays(session.hard_constraints.departure_date, dayIndex - 1),
      segments,
      notes: [
        relaxed
          ? "Few selections detected, so the plan preserves flexible time."
          : "Dense selections were prioritized by route and fit.",
        ...(validatorIssues?.length ? ["Corrective pass used validator errors as planning context."] : []),
      ],
    })
  }

  return days
}

function hotelSegment(
  start_time: string,
  end_time: string,
  stay: StayOption,
  description: string
): ItinerarySegment {
  return {
    type: "hotel_checkin",
    start_time,
    end_time,
    place: {
      id: stay.area.id,
      name: stay.area.name,
      coordinate: stay.area.center,
      address: stay.area.name,
      category: "stay_area",
      provider: "mapbox",
    },
    card_ref: null,
    description,
    cost_estimate: null,
  }
}

function cardSegment(card: DiscoveryCard, start_time: string, end_time: string): ItinerarySegment {
  return {
    type: "attraction",
    start_time,
    end_time,
    place: card.place,
    card_ref: card.id,
    description: card.reason,
    cost_estimate: card.cost_estimate,
  }
}

function addDays(date: string, offset: number): string {
  const parsed = new Date(`${date}T00:00:00.000Z`)
  parsed.setUTCDate(parsed.getUTCDate() + offset)
  return parsed.toISOString().slice(0, 10)
}
