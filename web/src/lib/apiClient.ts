"use client"

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
