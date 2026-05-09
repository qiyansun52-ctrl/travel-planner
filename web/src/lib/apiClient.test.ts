import { afterEach, describe, expect, it, vi } from "vitest"
import {
  createSession,
  getSession,
  runDiscovery,
  runItinerary,
  savePreferences,
  streamItinerary,
  submitAdjustment,
  updateSelectedCards,
  updateStayOverride,
} from "./apiClient"
import type { HardConstraints, PlanningProgressEvent, Preference } from "./types"

const hardConstraints: HardConstraints = {
  departure_city: "北京",
  destination_city: "上海",
  destination_country_code: "CN",
  departure_date: "2026-05-10",
  duration_days: 3,
  traveler_count: 2,
  total_budget: 6000,
  currency: "CNY",
}

const preferences: Preference = {
  area_vibe: "central",
  quiet_vs_lively: "balanced",
  stay_type: "hotel",
  willing_to_change_hotels: false,
  intercity_transport_preference: "rail",
  early_departure_tolerance: "medium",
  transfer_tolerance: "medium",
  pay_more_to_save_time: false,
}

function mockJsonResponse(payload: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(payload),
  } as Response)
}

function mockStreamResponse(text: string) {
  const encoder = new TextEncoder()
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode(text))
      controller.close()
    },
  })

  return Promise.resolve({
    ok: true,
    status: 200,
    body,
  } as Response)
}

describe("apiClient", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("uses the Python API URL by default", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => mockJsonResponse({ session_id: "s1" }))

    await createSession(hardConstraints)

    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/api/sessions")
  })

  it("maps session workflow calls to canonical nested routes", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => mockJsonResponse({ session_id: "s1" }))

    await getSession("s1")
    await runDiscovery("s1")
    await updateSelectedCards("s1", ["card-a"])
    await savePreferences("s1", preferences)
    await runItinerary("s1")
    await updateStayOverride("s1", "stay-a")
    await submitAdjustment({
      sessionId: "s1",
      message: "Make day two lighter",
      typeCAction: "replan",
    })

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "http://localhost:8000/api/sessions/s1",
      "http://localhost:8000/api/sessions/s1/discovery",
      "http://localhost:8000/api/sessions/s1/selection",
      "http://localhost:8000/api/sessions/s1/preferences",
      "http://localhost:8000/api/sessions/s1/itinerary",
      "http://localhost:8000/api/sessions/s1/stay-override",
      "http://localhost:8000/api/sessions/s1/adjustments",
    ])

    expect(JSON.parse(String(fetchMock.mock.calls[2][1]?.body))).toEqual({
      selected_card_ids: ["card-a"],
    })
    expect(JSON.parse(String(fetchMock.mock.calls[3][1]?.body))).toEqual({
      preferences,
    })
    expect(JSON.parse(String(fetchMock.mock.calls[6][1]?.body))).toEqual({
      message: "Make day two lighter",
      type_c_action: "replan",
    })
  })

  it("parses itinerary stream progress and completion frames", async () => {
    const progress: PlanningProgressEvent[] = []
    vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockStreamResponse(
        [
          'event: progress\ndata: {"stage":"stay","status":"started","message":"stay started"}',
          'event: complete\ndata: {"session":{"session_id":"s1"}}',
          "",
        ].join("\n\n")
      )
    )

    const session = await streamItinerary("s1", {
      onProgress: (event) => progress.push(event),
    })

    expect(progress).toEqual([
      { stage: "stay", status: "started", message: "stay started" },
    ])
    expect(session.session_id).toBe("s1")
  })
})
