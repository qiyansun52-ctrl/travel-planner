import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { ToastContainer } from "./Toast"

describe("ToastContainer", () => {
  it("renders dismissible toast messages", () => {
    const dismiss = vi.fn()

    render(
      <ToastContainer
        toasts={[{ id: 1, text: "调整出错，请重试", variant: "error" }]}
        onDismiss={dismiss}
      />,
    )

    expect(screen.getByRole("status")).toHaveTextContent("调整出错，请重试")
    fireEvent.click(screen.getByRole("button", { name: "关闭提示" }))
    expect(dismiss).toHaveBeenCalledWith(1)
  })
})
