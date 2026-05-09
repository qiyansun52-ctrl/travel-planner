import { NextRequest, NextResponse } from "next/server"
import { z } from "zod"
import { normalizeSelectedCardIds } from "@/domain/selection"
import { safeAppendMetricEvent } from "@/server/metrics/events"
import { getDefaultSessionRepository } from "@/server/persistence/fileSessionRepository"

interface RouteContext {
  params: Promise<{ sessionId: string }>
}

const SelectionSchema = z.object({
  selected_card_ids: z.array(z.string()),
})

export async function PATCH(request: NextRequest, context: RouteContext) {
  const { sessionId } = await context.params
  const body = SelectionSchema.parse(await request.json())
  const repository = getDefaultSessionRepository()
  const session = await repository.get(sessionId)

  if (!session?.discovery_state) {
    return NextResponse.json({ error: "Discovery state not found" }, { status: 404 })
  }

  const selectedCardIds = normalizeSelectedCardIds(body.selected_card_ids)
  const updated = await repository.updateDiscovery(sessionId, {
    ...session.discovery_state,
    selected_card_ids: selectedCardIds,
  })

  await safeAppendMetricEvent({
    name: "attraction_selected",
    session_id: sessionId,
    payload: { selected_count: selectedCardIds.length },
  })

  return NextResponse.json(updated)
}
