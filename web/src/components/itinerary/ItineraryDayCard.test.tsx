import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import type { ItineraryDay } from "@/lib/types"
import { ItineraryDayCard } from "./ItineraryDayCard"

const day: ItineraryDay = {
  day_index: 1,
  date: "2026-06-01",
  notes: ["Start with a skyline evening."],
  segments: [
    {
      type: "hotel_checkin",
      start_time: "09:00",
      end_time: "09:30",
      place: null,
      card_ref: null,
      description: "Drop bags near People's Square.",
      cost_estimate: null,
    },
    {
      type: "attraction",
      start_time: "10:00",
      end_time: "12:00",
      place: null,
      card_ref: "bund",
      description: "Walk the riverfront.",
      cost_estimate: null,
    },
  ],
}

describe("ItineraryDayCard", () => {
  it("adds a timeline line and one dot per segment", () => {
    const { container } = render(<ItineraryDayCard day={day} issues={[]} />)

    expect(screen.getByText("09:00-09:30")).toBeInTheDocument()
    expect(container.querySelector('[aria-hidden="true"][class*="bottom-2"]')).toBeInTheDocument()
    expect(container.querySelectorAll('[aria-hidden="true"][class*="-left-4"]')).toHaveLength(2)
  })
})
