import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { PreferenceForm } from "./PreferenceForm"

describe("PreferenceForm", () => {
  it("submits stay and transport preferences after discovery", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<PreferenceForm onSubmit={onSubmit} />)

    fireEvent.change(screen.getByLabelText(/Area vibe/i), {
      target: { value: "central, walkable, good food nearby" },
    })
    fireEvent.change(screen.getByLabelText(/Stay type/i), {
      target: { value: "homestay" },
    })
    fireEvent.change(screen.getByLabelText(/Intercity transport/i), {
      target: { value: "flight" },
    })
    fireEvent.click(screen.getByLabelText(/Spend more to save time/i))
    fireEvent.click(screen.getByRole("button", { name: /Generate itinerary/i }))

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      area_vibe: "central, walkable, good food nearby",
      stay_type: "homestay",
      intercity_transport_preference: "flight",
      pay_more_to_save_time: true,
    })
  })
})
