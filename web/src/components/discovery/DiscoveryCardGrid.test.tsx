import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import type { DiscoveryCard as DiscoveryCardType } from "@/lib/types"
import { DiscoveryCardGrid } from "./DiscoveryCardGrid"

const cards: DiscoveryCardType[] = [
  {
    id: "bund",
    name: "The Bund",
    reason: "Classic skyline walk.",
    category: "attraction",
    tags: [],
    suggested_duration_minutes: 120,
    cost_signal: "free",
    cost_estimate: null,
    image_url: null,
    reservation_hint: null,
    enrichment_status: "minimal",
    place: null,
  },
]

describe("DiscoveryCardGrid", () => {
  it("renders six skeleton cards while loading", () => {
    const { container } = render(
      <DiscoveryCardGrid
        cards={cards}
        selectedIds={[]}
        onToggle={vi.fn()}
        loading
      />,
    )

    expect(container.querySelectorAll('[data-testid="discovery-card-skeleton"]')).toHaveLength(6)
    expect(screen.queryByText("The Bund")).not.toBeInTheDocument()
  })
})
