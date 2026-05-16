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
    return metric("预算匹配", "预算待确认", "neutral", "生成行程后会确认整趟旅行的费用区间。", "待确认")
  }

  if (budget.overrun_flag || budget.total.high > userBudget) {
    return metric(
      "预算匹配",
      "超出预算",
      "danger",
      `计划合计 ${formatBand(budget.total)}，高于 ${budget.currency} ${formatAmount(userBudget)} 的预算。`,
      formatBand(budget.total),
    )
  }

  return metric(
    "预算匹配",
    "预算内",
    "good",
    `计划合计 ${formatBand(budget.total)}，仍在整趟旅行预算内。`,
    formatBand(budget.total),
  )
}

export function paceStatus(itinerary: Itinerary | null): ResultMetric {
  if (!itinerary) {
    return metric("节奏", "节奏待确认", "neutral", "生成行程后会检查每天安排是否过密。", "待确认")
  }

  if (itinerary.days.some((day) => day.segments.length >= 6)) {
    const packedDays = itinerary.days.filter((day) => day.segments.length >= 6).length
    return metric(
      "节奏",
      "密度偏高",
      "warning",
      `${packedDays} 天安排了 6 个或更多时间块。`,
      `${packedDays} 天偏满`,
    )
  }

  if (itinerary.days.some((day) => day.segments.some((segment) => segment.type === "rest"))) {
    const restBlocks = itinerary.days.reduce(
      (count, day) => count + day.segments.filter((segment) => segment.type === "rest").length,
      0,
    )
    return metric(
      "节奏",
      "节奏均衡",
      "good",
      `已安排 ${restBlocks} 个弹性休息时间块。`,
      `${restBlocks} 个休息`,
    )
  }

  return metric(
    "节奏",
    "节奏稳定",
    "neutral",
    `${itinerary.days.length} 天已排入日程，暂未安排专门休息块。`,
    `${itinerary.days.length} 天`,
  )
}

export function routeStatus(itinerary: Itinerary | null): ResultMetric {
  if (!itinerary) {
    return metric("路线", "路线待确认", "neutral", "生成行程后会确认地点坐标与移动路线。", "待确认")
  }

  const placeSegments = itinerary.days.flatMap((day) =>
    day.segments.filter((segment) => PLACE_SEGMENT_TYPES.has(segment.type)),
  )

  if (placeSegments.length === 0) {
    return metric("路线", "路线较轻", "neutral", "当前没有需要地图确认的地点型安排。", "0 站")
  }

  const mappedCount = placeSegments.filter((segment) => segment.place?.coordinate).length
  if (mappedCount < placeSegments.length) {
    return metric(
      "路线",
      "部分路线需确认",
      "warning",
      `${placeSegments.length - mappedCount}/${placeSegments.length} 个地点安排还缺少坐标。`,
      `${mappedCount}/${placeSegments.length}`,
    )
  }

  return metric(
    "路线",
    "路线已映射",
    "good",
    `${placeSegments.length} 个地点安排都已有地图坐标。`,
    `${mappedCount}/${placeSegments.length}`,
  )
}

export function riskStatus(itinerary: Itinerary | null): ResultMetric {
  if (!itinerary) {
    return metric("风险", "风险待确认", "neutral", "生成行程后会运行预算、节奏和时间窗口检查。", "待确认")
  }

  const errorCount = itinerary.validator_issues.filter((issue) => issue.severity === "error").length
  if (errorCount > 0) {
    return metric(
      "风险",
      `${errorCount} 条问题待修正`,
      "danger",
      `${errorCount} 条校验错误需要处理。`,
      `${errorCount} 错误`,
    )
  }

  const warningCount = itinerary.validator_issues.filter((issue) => issue.severity === "warning").length
  if (warningCount > 0) {
    return metric(
      "风险",
      `${warningCount} 条提醒待确认`,
      "warning",
      `${warningCount} 条校验提醒需要复核。`,
      `${warningCount} 提醒`,
    )
  }

  return metric("风险", "暂无风险", "good", "校验未发现行程问题。", "0 问题")
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
    prompts.push("比较住宿区域备选")
  }

  if (session.itinerary?.budget.overrun_flag) {
    prompts.push("复核预算并压缩高成本安排")
  }

  if (routeStatus(session.itinerary).tone === "warning") {
    prompts.push("确认缺少地图坐标的路线")
  }

  const issues = session.itinerary?.validator_issues ?? []
  const errorCount = issues.filter((issue) => issue.severity === "error").length
  const warningCount = issues.filter((issue) => issue.severity === "warning").length
  const issueCount = issues.length
  if (errorCount > 0) {
    prompts.push(`查看 ${issueCount} 条行程问题`)
  } else if (warningCount > 0) {
    prompts.push(`查看 ${warningCount} 条行程提醒`)
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
    return `第 ${day.day_index} 天：弹性安排`
  }

  if (labels.length === 1) {
    return `第 ${day.day_index} 天：${labels[0]}`
  }

  return `第 ${day.day_index} 天：${labels[0]}，然后 ${labels[1]}`
}

function segmentLabel(segment: ItinerarySegment, cardsById: Map<string, DiscoveryCard>): string {
  if (segment.type === "hotel_checkin") {
    return "入住"
  }

  if (segment.type === "hotel_checkout") {
    return "退房"
  }

  if (segment.type === "hotel_return") {
    return "返回住宿"
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
    return "暂无已排费用"
  }

  const currency = costs[0].currency
  const low = costs.reduce((sum, cost) => sum + cost.low, 0)
  const high = costs.reduce((sum, cost) => sum + cost.high, 0)
  return `${currency} ${formatAmount(low)}-${formatAmount(high)} 已排入日程`
}

function formatAmount(value: number): string {
  return Math.round(value).toLocaleString("en-US")
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
