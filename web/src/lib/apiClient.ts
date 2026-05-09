"use client"

import type {
  AdjustmentRequest,
  HardConstraints,
  PlanningProgressEvent,
  PlanningSession,
  Preference,
} from "@/lib/types"

const DEFAULT_API_URL = "http://localhost:8000"
const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL).replace(/\/$/, "")

function apiUrl(path: string): string {
  return `${API_URL}${path}`
}

async function fetchJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  const res = await fetch(apiUrl(path), {
    ...init,
    headers,
  })
  if (!res.ok) {
    throw new Error(`${init.method ?? "GET"} ${path} failed: ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function createSession(body: HardConstraints): Promise<PlanningSession> {
  return fetchJson<PlanningSession>("/api/sessions", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export async function getSession(sessionId: string): Promise<PlanningSession> {
  return fetchJson<PlanningSession>(`/api/sessions/${sessionId}`, { cache: "no-store" })
}

export async function runDiscovery(sessionId: string): Promise<PlanningSession> {
  return fetchJson<PlanningSession>(`/api/sessions/${sessionId}/discovery`, {
    method: "POST",
  })
}

export async function updateSelectedCards(
  sessionId: string,
  selectedCardIds: string[]
): Promise<PlanningSession> {
  return fetchJson<PlanningSession>(`/api/sessions/${sessionId}/selection`, {
    method: "PATCH",
    body: JSON.stringify({ selected_card_ids: selectedCardIds }),
  })
}

export async function savePreferences(
  sessionId: string,
  preferences: Preference
): Promise<PlanningSession> {
  return fetchJson<PlanningSession>(`/api/sessions/${sessionId}/preferences`, {
    method: "POST",
    body: JSON.stringify({ preferences }),
  })
}

export async function runItinerary(sessionId: string): Promise<PlanningSession> {
  return fetchJson<PlanningSession>(`/api/sessions/${sessionId}/itinerary`, {
    method: "POST",
    body: JSON.stringify({}),
  })
}

export async function updateStayOverride(
  sessionId: string,
  stayOptionId: string | null
): Promise<PlanningSession> {
  return fetchJson<PlanningSession>(`/api/sessions/${sessionId}/stay-override`, {
    method: "PATCH",
    body: JSON.stringify({ stay_option_id: stayOptionId }),
  })
}

export interface AdjustmentResponse {
  session: PlanningSession
  classification: AdjustmentRequest
  message: string
  confirmation?: {
    detected_change: string
    rerun_stages: string[]
    discard_estimate: string
  } | null
}

export async function submitAdjustment(input: {
  sessionId: string
  message: string
  typeCAction?: "replan" | "save_and_start_new" | "cancel"
}): Promise<AdjustmentResponse> {
  return fetchJson<AdjustmentResponse>(`/api/sessions/${input.sessionId}/adjustments`, {
    method: "POST",
    body: JSON.stringify({
      message: input.message,
      type_c_action: input.typeCAction,
    }),
  })
}

export async function streamItinerary(
  sessionId: string,
  handlers: { onProgress?: (event: PlanningProgressEvent) => void } = {}
): Promise<PlanningSession> {
  const res = await fetch(apiUrl(`/api/sessions/${sessionId}/itinerary/stream`), {
    headers: { Accept: "text/event-stream" },
    cache: "no-store",
  })
  if (!res.ok) {
    throw new Error(
      `GET /api/sessions/${sessionId}/itinerary/stream failed: ${res.status}`
    )
  }
  if (!res.body) {
    throw new Error("Itinerary stream did not include a readable body")
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let completedSession: PlanningSession | null = null

  function handleFrame(frame: string) {
    const result = parseSseFrame(frame)
    if (!result) return
    if (result.event === "progress") {
      handlers.onProgress?.(result.data as PlanningProgressEvent)
      return
    }
    if (result.event === "complete") {
      completedSession = (result.data as { session: PlanningSession }).session
      return
    }
    if (result.event === "error") {
      const message = String(
        (result.data as { message?: string }).message ?? "Itinerary stream failed"
      )
      throw new Error(message)
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split("\n\n")
    buffer = frames.pop() ?? ""
    for (const frame of frames) {
      handleFrame(frame)
      if (completedSession) return completedSession
    }
  }

  buffer += decoder.decode()
  if (buffer.trim()) {
    handleFrame(buffer)
  }
  if (completedSession) return completedSession

  throw new Error("Itinerary stream ended before completion")
}

function parseSseFrame(frame: string): { event: string; data: unknown } | null {
  const lines = frame.split("\n")
  const event = lines
    .find((line) => line.startsWith("event: "))
    ?.slice("event: ".length)
  const data = lines
    .filter((line) => line.startsWith("data: "))
    .map((line) => line.slice("data: ".length))
    .join("\n")

  if (!event || !data) return null
  return { event, data: JSON.parse(data) as unknown }
}
