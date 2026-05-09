import { NextRequest, NextResponse } from "next/server"
import { runDiscoveryAgent } from "@/server/agents/discovery"
import { safeAppendMetricEvent } from "@/server/metrics/events"
import { getDefaultSessionRepository } from "@/server/persistence/fileSessionRepository"

export async function POST(request: NextRequest) {
  const body = (await request.json()) as { session_id?: string }
  if (!body.session_id) {
    return NextResponse.json({ error: "session_id is required" }, { status: 400 })
  }

  const repository = getDefaultSessionRepository()
  const session = await repository.get(body.session_id)
  if (!session) {
    return NextResponse.json({ error: "Session not found" }, { status: 404 })
  }

  if (session.discovery_state?.payload) {
    return NextResponse.json(session)
  }

  const payload = await runDiscoveryAgent(session, { fixtureMode: process.env.E2E_FIXTURE_MODE === "1" })
  const updated = await repository.updateDiscovery(session.session_id, {
    payload,
    selected_card_ids: [],
  })

  const counts = payload.cards.reduce(
    (summary, card) => ({
      ...summary,
      [`${card.enrichment_status}_count`]: summary[`${card.enrichment_status}_count`] + 1,
    }),
    { complete_count: 0, partial_count: 0, minimal_count: 0 }
  )

  await safeAppendMetricEvent({
    name: "discovery_arrived",
    session_id: session.session_id,
    payload: {},
  })
  await safeAppendMetricEvent({
    name: "discovery_enrichment_summary",
    session_id: session.session_id,
    payload: { total_cards: payload.cards.length, ...counts },
  })

  return NextResponse.json(updated)
}
