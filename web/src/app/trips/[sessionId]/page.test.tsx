import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { PlanningSession } from "@/lib/types"
import TripPage from "./page"

const api = vi.hoisted(() => ({
  getSession: vi.fn(),
  streamItinerary: vi.fn(),
  updateStayOverride: vi.fn(),
}))

vi.mock("next/navigation", () => ({
  useParams: () => ({ sessionId: "session_1" }),
}))

vi.mock("@/lib/apiClient", () => api)

vi.mock("@/components/itinerary/ItineraryView", () => ({
  ItineraryView: () => <div>Trip ready</div>,
}))

vi.mock("@/components/chat/AdjustmentPanel", () => ({
  AdjustmentPanel: ({ session }: { session: PlanningSession }) => (
    <section>Adjustment panel for {session.session_id}</section>
  ),
}))

function sessionWithItinerary(): PlanningSession {
  return {
    session_id: "session_1",
    created_at: "2026-05-16T00:00:00",
    updated_at: "2026-05-16T00:00:00",
    parent_session_id: null,
    snapshot_label: null,
    status: "active",
    conversation_history: [],
    hard_constraints: {
      departure_city: "北京",
      destination_city: "上海",
      destination_country_code: "CN",
      departure_date: "2026-06-01",
      duration_days: 3,
      traveler_count: 2,
      total_budget: 6000,
      currency: "CNY",
    },
    discovery_state: null,
    preferences: null,
    stay_recommendation: null,
    transport_recommendation: null,
    itinerary: {
      id: "itinerary_1",
      session_id: "session_1",
      version: 1,
      days: [],
      validator_issues: [],
      budget: {
        currency: "CNY",
        user_budget: 6000,
        overrun_flag: false,
        transport: band(),
        stay: band(),
        food: band(),
        attractions: band(),
        other: band(),
        total: band(),
      },
    },
    validator_issues: [],
  }
}

function band() {
  return {
    basis: "per_trip" as const,
    confidence: "medium" as const,
    currency: "CNY",
    low: 100,
    high: 200,
  }
}

describe("TripPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("keeps the page shell on load error and retries planning", async () => {
    api.getSession
      .mockRejectedValueOnce(new Error("network down"))
      .mockResolvedValueOnce(sessionWithItinerary())

    render(<TripPage />)

    expect(await screen.findByText("规划出错")).toBeInTheDocument()
    expect(screen.getByText("network down")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "重试" }))

    await waitFor(() => expect(api.getSession).toHaveBeenCalledTimes(2))
    expect(await screen.findByText("Trip ready")).toBeInTheDocument()
  })

  it("opens the adjustment panel in a mobile bottom drawer", async () => {
    api.getSession.mockResolvedValue(sessionWithItinerary())

    render(<TripPage />)

    expect(await screen.findByText("Trip ready")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "打开调整面板" }))

    expect(screen.getByRole("dialog", { name: "调整行程" })).toBeInTheDocument()
    expect(screen.getByText("Adjustment panel for session_1")).toBeInTheDocument()
  })
})
