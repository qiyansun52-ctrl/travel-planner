import type { ResponseCookie } from "next/dist/compiled/@edge-runtime/cookies"

export const TRAVEL_SESSION_COOKIE = "travel_session_id"

export function travelSessionCookie(sessionId: string): ResponseCookie {
  return {
    name: TRAVEL_SESSION_COOKIE,
    value: sessionId,
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 90,
  }
}
