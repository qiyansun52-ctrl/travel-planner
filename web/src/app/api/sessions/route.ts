import { NextRequest, NextResponse } from "next/server"
import { HardConstraintsSchema } from "@/domain/schemas"
import { safeAppendMetricEvent } from "@/server/metrics/events"
import { travelSessionCookie } from "@/server/persistence/cookies"
import { getDefaultSessionRepository } from "@/server/persistence/fileSessionRepository"

export async function POST(request: NextRequest) {
  const body = await request.json()
  const hardConstraints = HardConstraintsSchema.parse(body)
  const session = await getDefaultSessionRepository().create(hardConstraints)
  await safeAppendMetricEvent({
    name: "step1_submitted",
    session_id: session.session_id,
    payload: {
      destination_country_code: hardConstraints.destination_country_code,
      duration_days: hardConstraints.duration_days,
    },
  })

  const response = NextResponse.json(session, { status: 201 })
  response.cookies.set(travelSessionCookie(session.session_id))
  return response
}
