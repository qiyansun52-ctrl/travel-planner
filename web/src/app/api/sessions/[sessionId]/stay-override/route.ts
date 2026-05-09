import { NextRequest, NextResponse } from "next/server"
import { planningOrchestrator } from "@/server/agents/orchestrator"
import { safeAppendMetricEvent } from "@/server/metrics/events"
import { getDefaultSessionRepository } from "@/server/persistence/fileSessionRepository"

interface RouteContext {
  params: Promise<{ sessionId: string }>
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  const { sessionId } = await context.params
  const body = (await request.json()) as { stay_option_id?: string | null }
  const repository = getDefaultSessionRepository()

  const withOverride = await repository.updateStayOverride(sessionId, body.stay_option_id ?? null)
  const result = await planningOrchestrator.runPlannerOnly(withOverride, "stay_override")
  const updated = await repository.writeItinerary(
    sessionId,
    result.itinerary,
    result.validatorIssues
  )

  await safeAppendMetricEvent({
    name: "stay_override_set",
    session_id: sessionId,
    payload: { override_set: Boolean(body.stay_option_id) },
  })

  return NextResponse.json(updated)
}
