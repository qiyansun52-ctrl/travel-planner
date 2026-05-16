import { StrictMode } from "react"
import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { PlanningSession } from "@/lib/types"
import DiscoveryPage from "./page"

const api = vi.hoisted(() => ({
  getSession: vi.fn(),
  runDiscovery: vi.fn(),
  updateSelectedCards: vi.fn(),
}))

vi.mock("next/navigation", () => ({
  useParams: () => ({ sessionId: "session_1" }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock("@/lib/apiClient", () => api)

vi.mock("@/components/discovery/DiscoveryBoard", () => ({
  DiscoveryBoard: ({ output }: { output: { cards: { name: string }[] } }) => (
    <div>Discovery ready: {output.cards[0].name}</div>
  ),
}))

function sessionWithDiscovery(): PlanningSession {
  return {
    session_id: "session_1",
    hard_constraints: {
      departure_city: "杭州",
      destination_city: "上海",
      destination_country_code: "CN",
      departure_date: "2026-06-01",
      duration_days: 3,
      traveler_count: 2,
      total_budget: 6000,
      currency: "CNY",
    },
    discovery_state: {
      payload: {
        cards: [{ id: "card_1", name: "The Bund" }],
      },
      selected_card_ids: [],
    },
  } as unknown as PlanningSession
}

describe("DiscoveryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("dedupes discovery loading under React StrictMode", async () => {
    api.getSession.mockResolvedValue({
      session_id: "session_1",
      discovery_state: null,
    })
    api.runDiscovery.mockResolvedValue(sessionWithDiscovery())

    render(
      <StrictMode>
        <DiscoveryPage />
      </StrictMode>,
    )

    expect(await screen.findByText("Discovery ready: The Bund")).toBeInTheDocument()
    await waitFor(() => expect(api.runDiscovery).toHaveBeenCalledTimes(1))
  })

  it("renders discovery card skeletons while loading", () => {
    api.getSession.mockReturnValue(new Promise(() => undefined))

    const { container } = render(<DiscoveryPage />)

    expect(screen.queryByText("正在整理发现卡片...")).not.toBeInTheDocument()
    expect(container.querySelectorAll('[data-testid="discovery-card-skeleton"]')).toHaveLength(6)
  })
})
