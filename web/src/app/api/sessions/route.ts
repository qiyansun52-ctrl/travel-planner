import { NextRequest, NextResponse } from "next/server"
import { HardConstraintsSchema } from "@/domain/schemas"
import { travelSessionCookie } from "@/server/persistence/cookies"
import { getDefaultSessionRepository } from "@/server/persistence/fileSessionRepository"

export async function POST(request: NextRequest) {
  const body = await request.json()
  const hardConstraints = HardConstraintsSchema.parse(body)
  const session = await getDefaultSessionRepository().create(hardConstraints)

  const response = NextResponse.json(session, { status: 201 })
  response.cookies.set(travelSessionCookie(session.session_id))
  return response
}
