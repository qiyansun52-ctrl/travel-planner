import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { PreferenceForm } from "./PreferenceForm"

describe("PreferenceForm", () => {
  it("submits stay and transport preferences after discovery", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<PreferenceForm onSubmit={onSubmit} />)

    fireEvent.change(screen.getByLabelText(/住宿区域偏好/i), {
      target: { value: "中心、方便步行、附近有好吃的" },
    })
    fireEvent.change(screen.getByLabelText(/住宿类型/i), {
      target: { value: "homestay" },
    })
    fireEvent.change(screen.getByLabelText(/城际交通/i), {
      target: { value: "flight" },
    })
    fireEvent.click(screen.getByLabelText(/愿意多花一点钱来节省时间/i))
    fireEvent.click(screen.getByRole("button", { name: /生成完整行程/i }))

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      area_vibe: "中心、方便步行、附近有好吃的",
      stay_type: "homestay",
      intercity_transport_preference: "flight",
      pay_more_to_save_time: true,
    })
  })
})
