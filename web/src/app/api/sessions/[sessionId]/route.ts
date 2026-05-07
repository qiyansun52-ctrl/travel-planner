import { NextResponse } from "next/server"
import { getDefaultSessionRepository } from "@/server/persistence/fileSessionRepository"

interface RouteContext {
  params: Promise<{
    sessionId: string
  }>
}

export async function GET(_request: Request, context: RouteContext) {
  const { sessionId } = await context.params
  const session = await getDefaultSessionRepository().get(sessionId)

  if (!session) {
    return NextResponse.json({ error: "Session not found" }, { status: 404 })
  }

  return NextResponse.json(session)
}
