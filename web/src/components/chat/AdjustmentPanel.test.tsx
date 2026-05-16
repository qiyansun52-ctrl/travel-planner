import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import type { PlanningSession } from "@/lib/types"
import { AdjustmentPanel } from "./AdjustmentPanel"

const api = vi.hoisted(() => ({
  submitAdjustment: vi.fn(),
}))

vi.mock("@/lib/apiClient", () => api)

const session = {
  session_id: "session_1",
} as PlanningSession

describe("AdjustmentPanel", () => {
  it("submits adjustments as a chat turn and renders the assistant response", async () => {
    api.submitAdjustment.mockResolvedValue({
      session,
      classification: {},
      message: "Itinerary updated",
      confirmation: null,
    })
    const onSessionChange = vi.fn()

    render(<AdjustmentPanel session={session} onSessionChange={onSessionChange} />)

    fireEvent.click(screen.getByRole("button", { name: "换一个景点" }))
    expect(screen.getByPlaceholderText("描述你想调整的内容…")).toHaveValue("换一个景点")

    fireEvent.change(screen.getByPlaceholderText("描述你想调整的内容…"), {
      target: { value: "把第二天下午改轻松一点" },
    })
    fireEvent.click(screen.getByRole("button", { name: "发送" }))

    await waitFor(() => expect(api.submitAdjustment).toHaveBeenCalledTimes(1))
    expect(api.submitAdjustment).toHaveBeenCalledWith({
      sessionId: "session_1",
      message: "把第二天下午改轻松一点",
      typeCAction: undefined,
    })
    expect(screen.getByText("把第二天下午改轻松一点")).toBeInTheDocument()
    expect(await screen.findByText("Itinerary updated")).toBeInTheDocument()
    expect(onSessionChange).toHaveBeenCalledWith(session)
  })
})
