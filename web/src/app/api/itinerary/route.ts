import { NextRequest, NextResponse } from "next/server"
import { planningOrchestrator } from "@/server/agents/orchestrator"
import { safeAppendMetricEvent } from "@/server/metrics/events"
import { getDefaultSessionRepository } from "@/server/persistence/fileSessionRepository"

export async function POST(request: NextRequest) {
  const body = (await request.json()) as { session_id?: string; planner_only_reason?: string }
  if (!body.session_id) {
    return NextResponse.json({ error: "session_id is required" }, { status: 400 })
  }

  const repository = getDefaultSessionRepository()
  const session = await repository.get(body.session_id)
  if (!session) return NextResponse.json({ error: "Session not found" }, { status: 404 })

  const result =
    body.planner_only_reason && session.stay_recommendation && session.transport_recommendation
      ? await planningOrchestrator.runPlannerOnly(session, body.planner_only_reason)
      : await planningOrchestrator.runFullPlanning(session)

  await repository.updateStayRecommendation(session.session_id, result.stay)
  await repository.updateTransportRecommendation(session.session_id, result.transport)
  const updated = await repository.writeItinerary(
    session.session_id,
    result.itinerary,
    result.validatorIssues
  )

  await safeAppendMetricEvent({
    name: "itinerary_finalized",
    session_id: session.session_id,
    payload: { version: result.itinerary.version },
  })

  const residualErrors = result.validatorIssues.filter((issue) => issue.severity === "error")
  if (residualErrors.length) {
    await safeAppendMetricEvent({
      name: "validator_error_finalized",
      session_id: session.session_id,
      payload: { codes: residualErrors.map((issue) => issue.code) },
    })
  }

  return NextResponse.json(updated)
}
