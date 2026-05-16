import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { HomeStart } from "./HomeStart"

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

describe("HomeStart", () => {
  it("starts in Chinese and can switch the intake flow to English", () => {
    render(<HomeStart />)

    expect(screen.getByRole("heading", { name: "规划一趟单城市旅行" })).toBeInTheDocument()
    expect(screen.getByLabelText("出发城市")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "开始发现灵感" })).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Switch to English" }))

    expect(screen.getByRole("heading", { name: "Plan a single-city trip" })).toBeInTheDocument()
    expect(screen.getByLabelText("Departure city")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "切换到中文" }))

    expect(screen.getByRole("heading", { name: "规划一趟单城市旅行" })).toBeInTheDocument()
  })
})
