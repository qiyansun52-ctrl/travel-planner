import { mkdir, readFile, appendFile } from "node:fs/promises"
import path from "node:path"

export type MetricEventName =
  | "step1_submitted"
  | "discovery_arrived"
  | "discovery_enrichment_summary"
  | "attraction_selected"
  | "preferences_completed"
  | "itinerary_finalized"
  | "validator_error_finalized"
  | "adjustment_classified"
  | "type_c_action_taken"
  | "provider_fallback_used"
  | "stay_override_set"

export interface MetricEvent {
  name: MetricEventName
  session_id: string
  payload: Record<string, unknown>
  created_at?: string
}

export interface MetricSummary {
  eventCounts: Partial<Record<MetricEventName, number>>
  sessionsSubmitted: number
  sessionsWithFinalItinerary: number
  sessionsWithResidualValidatorErrors: number
}

export function defaultMetricFilePath(): string {
  return path.join(process.cwd(), ".data/events.jsonl")
}

export async function appendMetricEvent(
  event: MetricEvent,
  filePath = defaultMetricFilePath()
): Promise<void> {
  await mkdir(path.dirname(filePath), { recursive: true })
  const line = JSON.stringify({
    ...event,
    created_at: event.created_at ?? new Date().toISOString(),
  })
  await appendFile(filePath, `${line}\n`, "utf8")
}

export async function safeAppendMetricEvent(
  event: MetricEvent,
  filePath = defaultMetricFilePath()
): Promise<void> {
  try {
    await appendMetricEvent(event, filePath)
  } catch {
    // Metrics must never block the planning flow.
  }
}

export async function computeMetricSummary(
  filePath = defaultMetricFilePath()
): Promise<MetricSummary> {
  const events = await readMetricEvents(filePath)
  const eventCounts: Partial<Record<MetricEventName, number>> = {}
  const submitted = new Set<string>()
  const finalized = new Set<string>()
  const residualErrors = new Set<string>()

  for (const event of events) {
    eventCounts[event.name] = (eventCounts[event.name] ?? 0) + 1
    if (event.name === "step1_submitted") submitted.add(event.session_id)
    if (event.name === "itinerary_finalized") finalized.add(event.session_id)
    if (event.name === "validator_error_finalized") residualErrors.add(event.session_id)
  }

  return {
    eventCounts,
    sessionsSubmitted: submitted.size,
    sessionsWithFinalItinerary: finalized.size,
    sessionsWithResidualValidatorErrors: residualErrors.size,
  }
}

async function readMetricEvents(filePath: string): Promise<MetricEvent[]> {
  let content = ""
  try {
    content = await readFile(filePath, "utf8")
  } catch {
    return []
  }

  return content
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line) as MetricEvent)
}
