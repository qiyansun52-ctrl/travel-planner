import { NextRequest, NextResponse } from "next/server"
import { randomUUID } from "node:crypto"
import { classifyAdjustment } from "@/server/agents/adjustmentClassifier"
import { planningOrchestrator } from "@/server/agents/orchestrator"
import { runStayAgent } from "@/server/agents/stay"
import { runTransportAgent } from "@/server/agents/transport"
import { safeAppendMetricEvent } from "@/server/metrics/events"
import { getDefaultSessionRepository } from "@/server/persistence/fileSessionRepository"

type TypeCAction = "replan" | "save_and_start_new" | "cancel"

export async function POST(request: NextRequest) {
  const body = (await request.json()) as {
    session_id?: string
    message?: string
    type_c_action?: TypeCAction
  }
  if (!body.session_id || !body.message) {
    return NextResponse.json({ error: "session_id and message are required" }, { status: 400 })
  }

  const repository = getDefaultSessionRepository()
  const session = await repository.get(body.session_id)
  if (!session) return NextResponse.json({ error: "Session not found" }, { status: 404 })

  const classification = classifyAdjustment(body.message)
  await repository.appendConversationTurn(session.session_id, {
    id: `turn_${randomUUID()}`,
    raw_text: body.message,
    classification,
    created_at: new Date().toISOString(),
  })

  await safeAppendMetricEvent({
    name: "adjustment_classified",
    session_id: session.session_id,
    payload: { type: classification.type, confidence: classification.confidence },
  })

  if (classification.type === "unknown" || classification.confidence < 0.55) {
    return NextResponse.json({
      session,
      classification,
      message: "Can you clarify whether this changes the itinerary, stay, transport, or core trip constraints?",
    })
  }

  if (classification.type === "C") {
    return handleTypeC(body.type_c_action, session, body.message, classification)
  }

  let working = (await repository.get(session.session_id)) ?? session
  if (classification.type === "B" && classification.target_scope === "stay") {
    const stay = await runStayAgent({ ...working, stay_recommendation: null })
    working = await repository.updateStayRecommendation(session.session_id, {
      ...stay,
      user_override_id: null,
    })
  }
  if (classification.type === "B" && classification.target_scope === "transport") {
    const transport = await runTransportAgent(working)
    working = await repository.updateTransportRecommendation(session.session_id, transport)
  }

  const result = await planningOrchestrator.runPlannerOnly(working, `type_${classification.type.toLowerCase()}_adjustment`)
  await repository.updateStayRecommendation(session.session_id, result.stay)
  await repository.updateTransportRecommendation(session.session_id, result.transport)
  const updated = await repository.writeItinerary(
    session.session_id,
    result.itinerary,
    result.validatorIssues
  )

  return NextResponse.json({
    session: updated,
    classification,
    message: "Itinerary updated.",
  })
}

async function handleTypeC(
  action: TypeCAction | undefined,
  session: NonNullable<Awaited<ReturnType<ReturnType<typeof getDefaultSessionRepository>["get"]>>>,
  message: string,
  classification: ReturnType<typeof classifyAdjustment>
) {
  const repository = getDefaultSessionRepository()

  if (!action) {
    return NextResponse.json({
      session,
      classification,
      message: "This changes core trip constraints.",
      confirmation: {
        detected_change: message,
        rerun_stages: ["discovery", "preferences", "itinerary"],
        discard_estimate: "Most downstream planning state will be refreshed.",
      },
    })
  }

  await safeAppendMetricEvent({
    name: "type_c_action_taken",
    session_id: session.session_id,
    payload: { action },
  })

  if (action === "cancel") {
    const updated = await repository.appendConversationTurn(session.session_id, {
      id: `turn_${randomUUID()}`,
      raw_text: `Cancelled root change: ${message}`,
      classification,
      created_at: new Date().toISOString(),
    })
    return NextResponse.json({ session: updated, classification, message: "Root change cancelled." })
  }

  if (action === "save_and_start_new") {
    const fork = await repository.archiveAndFork(
      session.session_id,
      "Before root constraint change",
      session.hard_constraints
    )
    return NextResponse.json({ session: fork, classification, message: "New session started." })
  }

  const reset = await repository.resetToStep(session.session_id, "discovery", session.hard_constraints)
  return NextResponse.json({ session: reset, classification, message: "Session reset to discovery." })
}
