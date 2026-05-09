"use client"

import type {
  AdjustmentRequest,
  DiscoveryOutput,
  HardConstraints,
  PlanningSession,
  Preference,
} from "@/domain/schemas"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? ""

if (!API_URL && typeof window !== "undefined") {
  console.warn("NEXT_PUBLIC_API_URL not set — falling back to same-origin Next.js routes")
}

function url(path: string): string {
  return API_URL ? `${API_URL}${path}` : path
}

export async function discoverDestination(destination: string): Promise<unknown> {
  const res = await fetch(
    url(`/api/discover?destination=${encodeURIComponent(destination)}`)
  )
  if (!res.ok) throw new Error(`Discover failed: ${res.status}`)
  return res.json()
}

export async function generatePlan(body: object): Promise<string> {
  const res = await fetch(url("/api/plan/generate"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Generate failed: ${res.status}`)
  return res.text()
}

export async function createSession(body: HardConstraints): Promise<PlanningSession> {
  const res = await fetch("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Create session failed: ${res.status}`)
  return res.json()
}

export async function getSession(sessionId: string): Promise<PlanningSession> {
  const res = await fetch(`/api/sessions/${sessionId}`, { cache: "no-store" })
  if (!res.ok) throw new Error(`Load session failed: ${res.status}`)
  return res.json()
}

export async function runDiscovery(sessionId: string): Promise<PlanningSession> {
  const res = await fetch("/api/discovery", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  })
  if (!res.ok) throw new Error(`Discovery failed: ${res.status}`)
  return res.json()
}

export async function updateSelectedCards(
  sessionId: string,
  selectedCardIds: string[]
): Promise<PlanningSession> {
  const res = await fetch(`/api/sessions/${sessionId}/selection`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selected_card_ids: selectedCardIds }),
  })
  if (!res.ok) throw new Error(`Selection update failed: ${res.status}`)
  return res.json()
}

export async function savePreferences(
  sessionId: string,
  preferences: Preference
): Promise<PlanningSession> {
  const res = await fetch("/api/preferences", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, preferences }),
  })
  if (!res.ok) throw new Error(`Preference save failed: ${res.status}`)
  return res.json()
}

export async function runItinerary(sessionId: string): Promise<PlanningSession> {
  const res = await fetch("/api/itinerary", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  })
  if (!res.ok) throw new Error(`Itinerary failed: ${res.status}`)
  return res.json()
}

export async function updateStayOverride(
  sessionId: string,
  stayOptionId: string | null
): Promise<PlanningSession> {
  const res = await fetch(`/api/sessions/${sessionId}/stay-override`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stay_option_id: stayOptionId }),
  })
  if (!res.ok) throw new Error(`Stay override failed: ${res.status}`)
  return res.json()
}

export interface AdjustmentResponse {
  session: PlanningSession
  classification: AdjustmentRequest
  message: string
  confirmation?: {
    detected_change: string
    rerun_stages: string[]
    discard_estimate: string
  }
}

export async function submitAdjustment(input: {
  sessionId: string
  message: string
  typeCAction?: "replan" | "save_and_start_new" | "cancel"
}): Promise<AdjustmentResponse> {
  const res = await fetch("/api/adjustments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: input.sessionId,
      message: input.message,
      type_c_action: input.typeCAction,
    }),
  })
  if (!res.ok) throw new Error(`Adjustment failed: ${res.status}`)
  return res.json()
}

export type { DiscoveryOutput }
