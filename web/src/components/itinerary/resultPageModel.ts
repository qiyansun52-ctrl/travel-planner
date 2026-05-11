import type {
  BudgetBand,
  DiscoveryCard,
  Itinerary,
  ItineraryDay,
  ItinerarySegment,
  PlanningSession,
  StayOption,
} from "@/lib/types"

export interface HeroImage {
  src: string
  alt: string
}

export interface ResultMetric {
  label: string
  status: string
  tone: "good" | "warning" | "danger" | "neutral"
  detail: string
  value: string
}

export interface NarrativeRouteItem {
  dayIndex: number
  date: string
  title: string
  anchors: string[]
  note: string
  budgetHint: string
}

const PLACE_SEGMENT_TYPES = new Set<ItinerarySegment["type"]>([
  "attraction",
  "hotel_checkin",
  "hotel_return",
])

export function selectedDiscoveryCards(session: PlanningSession): DiscoveryCard[] {
  const cards = session.discovery_state?.payload?.cards ?? []
  const selectedIds = session.discovery_state?.selected_card_ids ?? []

  if (selectedIds.length === 0) {
    return cards.slice(0, 3)
  }

  const cardsById = new Map(cards.map((card) => [card.id, card]))
  return selectedIds.flatMap((id) => {
    const card = cardsById.get(id)
    return card ? [card] : []
  })
}

export function heroImages(session: PlanningSession): HeroImage[] {
  return selectedDiscoveryCards(session)
    .filter((card) => Boolean(card.image_url))
    .slice(0, 4)
    .map((card) => ({
      src: card.image_url as string,
      alt: card.name,
    }))
}

export function destinationTags(session: PlanningSession): string[] {
  const tags = [
    ...selectedDiscoveryCards(session).flatMap((card) => card.tags),
    ...(session.discovery_state?.payload?.area_summaries ?? []).flatMap((area) => area.vibe_tags),
    ...preferenceTags(session),
  ]

  return uniqueCompact(tags).slice(0, 6)
}

export function activeStayOption(session: PlanningSession): StayOption | null {
  const recommendation = session.stay_recommendation
  if (!recommendation) {
    return null
  }

  const options = [recommendation.primary, ...recommendation.alternatives]
  const override = recommendation.user_override_id
  return options.find((option) => option.id === override) ?? recommendation.primary
}

export function budgetFitStatus(session: PlanningSession): ResultMetric {
  const budget = session.itinerary?.budget ?? null
  const userBudget = budget ? budget.user_budget || session.hard_constraints.total_budget : 0

  if (!userBudget || userBudget <= 0 || !budget) {
    return metric("Budget fit", "Budget pending", "neutral", "Generate an itinerary to confirm total trip cost.", "Pending")
  }

  if (budget.overrun_flag || budget.total.high > userBudget) {
    return metric(
      "Budget fit",
      "Over budget",
      "danger",
      `Planned total ${formatBand(budget.total)} vs ${budget.currency} ${formatAmount(userBudget)} budget.`,
      formatBand(budget.total),
    )
  }

  return metric(
    "Budget fit",
    "Within range",
    "good",
    `Planned total ${formatBand(budget.total)} stays within the trip budget.`,
    formatBand(budget.total),
  )
}

export function paceStatus(itinerary: Itinerary | null): ResultMetric {
  if (!itinerary) {
    return metric("Pace", "Pace pending", "neutral", "Generate an itinerary to review daily pacing.", "Pending")
  }

  if (itinerary.days.some((day) => day.segments.length >= 6)) {
    const packedDays = itinerary.days.filter((day) => day.segments.length >= 6).length
    return metric(
      "Pace",
      "Packed days",
      "warning",
      `${packedDays} ${packedDays === 1 ? "day has" : "days have"} six or more scheduled blocks.`,
      `${packedDays} packed`,
    )
  }

  if (itinerary.days.some((day) => day.segments.some((segment) => segment.type === "rest"))) {
    const restBlocks = itinerary.days.reduce(
      (count, day) => count + day.segments.filter((segment) => segment.type === "rest").length,
      0,
    )
    return metric(
      "Pace",
      "Balanced pace",
      "good",
      `${restBlocks} flexible rest ${restBlocks === 1 ? "block is" : "blocks are"} scheduled.`,
      `${restBlocks} rest`,
    )
  }

  return metric(
    "Pace",
    "Steady pace",
    "neutral",
    `${itinerary.days.length} ${itinerary.days.length === 1 ? "day" : "days"} scheduled without rest blocks.`,
    `${itinerary.days.length} days`,
  )
}

export function routeStatus(itinerary: Itinerary | null): ResultMetric {
  if (!itinerary) {
    return metric("Route", "Route pending", "neutral", "Generate an itinerary to confirm mapped places.", "Pending")
  }

  const placeSegments = itinerary.days.flatMap((day) =>
    day.segments.filter((segment) => PLACE_SEGMENT_TYPES.has(segment.type)),
  )

  if (placeSegments.length === 0) {
    return metric("Route", "Route light", "neutral", "No place-based segments need mapping yet.", "0 stops")
  }

  const mappedCount = placeSegments.filter((segment) => segment.place?.coordinate).length
  if (mappedCount < placeSegments.length) {
    return metric(
      "Route",
      "Some routes need confirmation",
      "warning",
      `${placeSegments.length - mappedCount} of ${placeSegments.length} place segments need mapped coordinates.`,
      `${mappedCount}/${placeSegments.length}`,
    )
  }

  return metric(
    "Route",
    "Mapped route",
    "good",
    `All ${placeSegments.length} place segments include mapped coordinates.`,
    `${mappedCount}/${placeSegments.length}`,
  )
}

export function riskStatus(itinerary: Itinerary | null): ResultMetric {
  if (!itinerary) {
    return metric("Risks", "Risks pending", "neutral", "Generate an itinerary to run validation checks.", "Pending")
  }

  const errorCount = itinerary.validator_issues.filter((issue) => issue.severity === "error").length
  if (errorCount > 0) {
    return metric(
      "Risks",
      pluralize(errorCount, "issue", "to fix"),
      "danger",
      `${errorCount} validation ${errorCount === 1 ? "error needs" : "errors need"} attention.`,
      `${errorCount} errors`,
    )
  }

  const warningCount = itinerary.validator_issues.filter((issue) => issue.severity === "warning").length
  if (warningCount > 0) {
    return metric(
      "Risks",
      pluralize(warningCount, "warning", "to review"),
      "warning",
      `${warningCount} validation ${warningCount === 1 ? "warning needs" : "warnings need"} review.`,
      `${warningCount} warnings`,
    )
  }

  return metric("Risks", "No issues flagged", "good", "Validation found no itinerary issues.", "0 issues")
}

export function narrativeRouteItems(session: PlanningSession): NarrativeRouteItem[] {
  const cardsById = new Map((session.discovery_state?.payload?.cards ?? []).map((card) => [card.id, card]))

  return (session.itinerary?.days ?? []).map((day) => ({
    dayIndex: day.day_index,
    date: day.date,
    title: dayTitle(day, cardsById),
    anchors: day.segments.slice(0, 3).map((segment) => segmentAnchor(segment, cardsById)),
    note: day.notes[0] ?? "",
    budgetHint: dayBudgetHint(day),
  }))
}

export function smartAdjustmentPrompts(session: PlanningSession): string[] {
  const prompts: string[] = []

  if ((session.stay_recommendation?.alternatives.length ?? 0) > 0) {
    prompts.push("Compare stay area alternatives")
  }

  if (session.itinerary?.budget.overrun_flag) {
    prompts.push("Review budget and reduce higher-cost blocks")
  }

  const issues = session.itinerary?.validator_issues ?? []
  const errorCount = issues.filter((issue) => issue.severity === "error").length
  const warningCount = issues.filter((issue) => issue.severity === "warning").length
  const issueCount = issues.length
  if (errorCount > 0) {
    prompts.push(`Review ${issueCount} itinerary ${issueCount === 1 ? "issue" : "issues"}`)
  } else if (warningCount > 0) {
    prompts.push(`Review ${warningCount} itinerary ${warningCount === 1 ? "warning" : "warnings"}`)
  }

  if (routeStatus(session.itinerary).tone === "warning") {
    prompts.push("Confirm route details for segments without mapped places")
  }

  return prompts.slice(0, 3)
}

export function commandMetrics(session: PlanningSession): ResultMetric[] {
  return [
    budgetFitStatus(session),
    paceStatus(session.itinerary),
    routeStatus(session.itinerary),
    riskStatus(session.itinerary),
  ]
}

export function formatBand(band: BudgetBand): string {
  return `${band.currency} ${formatAmount(band.low)}-${formatAmount(band.high)}`
}

function preferenceTags(session: PlanningSession): string[] {
  const preferences = session.preferences
  if (!preferences) {
    return []
  }

  return [
    ...preferences.area_vibe.split(","),
    preferences.quiet_vs_lively,
    preferences.stay_type,
    preferences.intercity_transport_preference,
  ]
}

function uniqueCompact(values: string[]): string[] {
  const seen = new Set<string>()
  const result: string[] = []

  for (const value of values) {
    const normalized = value.trim()
    if (!normalized || seen.has(normalized)) {
      continue
    }

    seen.add(normalized)
    result.push(normalized)
  }

  return result
}

function dayTitle(day: ItineraryDay, cardsById: Map<string, DiscoveryCard>): string {
  const labels = uniqueCompact(
    day.segments
      .filter((segment) => segment.type !== "food" && segment.type !== "rest" && segment.type !== "transit")
      .map((segment) => segmentLabel(segment, cardsById)),
  ).slice(0, 2)

  if (labels.length === 0) {
    return `Day ${day.day_index}: Flexible day`
  }

  if (labels.length === 1) {
    return `Day ${day.day_index}: ${labels[0]}`
  }

  return `Day ${day.day_index}: ${labels[0]}, then ${labels[1]}`
}

function segmentLabel(segment: ItinerarySegment, cardsById: Map<string, DiscoveryCard>): string {
  if (segment.type === "hotel_checkin") {
    return "Check in"
  }

  if (segment.type === "hotel_checkout") {
    return "Check out"
  }

  if (segment.type === "hotel_return") {
    return "Return to hotel"
  }

  return segment.place?.name ?? cardName(segment, cardsById) ?? friendlyType(segment.type)
}

function segmentAnchor(segment: ItinerarySegment, cardsById: Map<string, DiscoveryCard>): string {
  return segment.place?.name ?? cardName(segment, cardsById) ?? segment.description
}

function cardName(segment: ItinerarySegment, cardsById: Map<string, DiscoveryCard>): string | null {
  return segment.card_ref ? (cardsById.get(segment.card_ref)?.name ?? null) : null
}

function friendlyType(type: ItinerarySegment["type"]): string {
  return type
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

function dayBudgetHint(day: ItineraryDay): string {
  const costs = day.segments.flatMap((segment) => (segment.cost_estimate ? [segment.cost_estimate] : []))
  if (costs.length === 0) {
    return "No scheduled costs"
  }

  const currency = costs[0].currency
  const low = costs.reduce((sum, cost) => sum + cost.low, 0)
  const high = costs.reduce((sum, cost) => sum + cost.high, 0)
  return `${currency} ${formatAmount(low)}-${formatAmount(high)} scheduled`
}

function formatAmount(value: number): string {
  return Math.round(value).toLocaleString("en-US")
}

function pluralize(count: number, singular: string, suffix: string): string {
  return `${count} ${singular}${count === 1 ? "" : "s"} ${suffix}`
}

function metric(
  label: string,
  status: string,
  tone: ResultMetric["tone"],
  detail: string,
  value: string,
): ResultMetric {
  return { label, status, tone, detail, value }
}
