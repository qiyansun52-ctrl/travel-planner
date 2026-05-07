import { DiscoveryCard, Itinerary, ItinerarySegment, ValidatorIssue } from "./schemas"

export interface OperatingWindow {
  open_time: string
  close_time: string
}

export interface ValidatorContext {
  discoveryCards: DiscoveryCard[]
  operatingWindowsByCardId?: Record<string, OperatingWindow>
}

export function validateItinerary(
  itinerary: Itinerary,
  context: ValidatorContext
): ValidatorIssue[] {
  const issues: ValidatorIssue[] = []
  const cardById = new Map(context.discoveryCards.map((card) => [card.id, card]))

  if (itinerary.budget.total.high > itinerary.budget.user_budget * 1.15) {
    issues.push({
      code: "BUDGET_OVERRUN",
      severity: "error",
      scope: { type: "trip" },
      message: `Estimated total ${itinerary.budget.total.high} exceeds the user budget by more than 15%.`,
      suggested_action: "Reduce optional costs or ask the user before changing stay or transport assumptions.",
    })
  }

  for (const day of itinerary.days) {
    const attractionSegments = day.segments.filter((segment) => segment.type === "attraction")
    const activeMinutes = attractionSegments.reduce(
      (sum, segment) => sum + segmentDurationMinutes(segment),
      0
    )

    if (activeMinutes > 8 * 60 || attractionSegments.length > 5) {
      issues.push({
        code: "DAY_OVERLOADED",
        severity: "warning",
        scope: { type: "day", day_index: day.day_index },
        message: `Day ${day.day_index} may feel too dense.`,
        suggested_action: "Move one stop into flexible time or another day.",
      })
    }

    const movementMinutes = day.segments
      .filter((segment) => segment.type === "transit")
      .reduce((sum, segment) => sum + segmentDurationMinutes(segment), 0)

    if (activeMinutes > 0 && movementMinutes > activeMinutes * 0.4) {
      issues.push({
        code: "WASTEFUL_ROUTING",
        severity: "warning",
        scope: { type: "day", day_index: day.day_index },
        message: `Day ${day.day_index} spends a large share of active time in transit.`,
        suggested_action: "Group nearby stops or consider a different stay area.",
      })
    }

    for (const [segmentIndex, segment] of day.segments.entries()) {
      if (segment.type !== "attraction" || !segment.card_ref) continue

      const card = cardById.get(segment.card_ref)
      if (!card) continue

      const duration = segmentDurationMinutes(segment)
      if (duration < card.suggested_duration_minutes * 0.5) {
        issues.push({
          code: "TIMING_UNREALISTIC",
          severity: "error",
          scope: {
            type: "segment",
            day_index: day.day_index,
            segment_index: segmentIndex,
            card_ref: segment.card_ref,
          },
          message: `${card.name} is scheduled for less than half its suggested visit duration.`,
          suggested_action: "Lengthen the visit or remove the stop.",
        })
      }

      const operatingWindow = context.operatingWindowsByCardId?.[segment.card_ref]
      if (card.reservation_hint && operatingWindow && outsideWindow(segment, operatingWindow)) {
        issues.push({
          code: "TIMING_UNREALISTIC",
          severity: "error",
          scope: {
            type: "segment",
            day_index: day.day_index,
            segment_index: segmentIndex,
            card_ref: segment.card_ref,
          },
          message: `${card.name} is placed outside its known operating window.`,
          suggested_action: `Schedule it between ${operatingWindow.open_time} and ${operatingWindow.close_time}.`,
        })
      }
    }
  }

  return issues
}

function outsideWindow(segment: ItinerarySegment, window: OperatingWindow): boolean {
  return (
    timeToMinutes(segment.start_time) < timeToMinutes(window.open_time) ||
    timeToMinutes(segment.end_time) > timeToMinutes(window.close_time)
  )
}

function segmentDurationMinutes(segment: Pick<ItinerarySegment, "start_time" | "end_time">): number {
  return Math.max(0, timeToMinutes(segment.end_time) - timeToMinutes(segment.start_time))
}

function timeToMinutes(value: string): number {
  const [hours, minutes] = value.split(":").map(Number)
  return hours * 60 + minutes
}
