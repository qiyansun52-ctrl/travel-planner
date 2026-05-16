import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import type { DiscoveryCard as DiscoveryCardType } from "@/lib/types"
import { DiscoveryCard } from "./DiscoveryCard"

function cardFixture(overrides: Partial<DiscoveryCardType> = {}): DiscoveryCardType {
  return {
    id: "bund",
    name: "The Bund",
    reason: "Classic skyline walk that anchors the first evening.",
    category: "attraction",
    tags: ["waterfront", "night view"],
    suggested_duration_minutes: 120,
    cost_signal: "medium",
    cost_estimate: null,
    image_url: "https://images.example/bund.jpg",
    reservation_hint: null,
    enrichment_status: "complete",
    place: null,
    ...overrides,
  }
}

describe("DiscoveryCard", () => {
  it("renders the polished visual card without enrichment jargon", () => {
    const onToggle = vi.fn()
    const { container } = render(
      <DiscoveryCard card={cardFixture()} selected={true} onToggle={onToggle} />,
    )

    expect(screen.queryByText("已验证")).not.toBeInTheDocument()
    expect(screen.getByText("景点")).toBeInTheDocument()
    expect(screen.getByText("··")).toBeInTheDocument()
    expect(screen.getByLabelText("已选择")).toBeInTheDocument()
    expect(container.querySelector(".aspect-video")).toBeInTheDocument()

    const button = screen.getByRole("button", { name: /取消选择 The Bund/ })
    expect(button).toHaveTextContent("已选")
    fireEvent.click(button)
    expect(onToggle).toHaveBeenCalledWith("bund")
  })
})
