import { NextRequest, NextResponse } from "next/server"
import { PreferenceSchema } from "@/domain/schemas"
import { safeAppendMetricEvent } from "@/server/metrics/events"
import { getDefaultSessionRepository } from "@/server/persistence/fileSessionRepository"

export async function POST(request: NextRequest) {
  const body = (await request.json()) as { session_id?: string; preferences?: unknown }
  if (!body.session_id) {
    return NextResponse.json({ error: "session_id is required" }, { status: 400 })
  }

  const preferences = PreferenceSchema.parse(body.preferences)
  const session = await getDefaultSessionRepository().updatePreferences(body.session_id, preferences)
  await safeAppendMetricEvent({
    name: "preferences_completed",
    session_id: session.session_id,
    payload: {
      stay_type: preferences.stay_type,
      intercity_transport_preference: preferences.intercity_transport_preference,
    },
  })

  return NextResponse.json(session)
}
