import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { HardConstraintForm } from "./HardConstraintForm"

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

describe("HardConstraintForm", () => {
  it("submits only hard constraints with resolved destination country code", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<HardConstraintForm onSubmit={onSubmit} />)

    fireEvent.change(screen.getByLabelText(/Departure city/i), {
      target: { value: "北京" },
    })
    fireEvent.change(screen.getByLabelText(/Destination city/i), {
      target: { value: "上海" },
    })
    fireEvent.change(screen.getByLabelText(/Departure date/i), {
      target: { value: "2026-05-10" },
    })
    fireEvent.change(screen.getByLabelText(/Trip duration/i), {
      target: { value: "3" },
    })
    fireEvent.change(screen.getByLabelText(/Traveler count/i), {
      target: { value: "2" },
    })
    fireEvent.change(screen.getByLabelText(/Total trip budget/i), {
      target: { value: "6000" },
    })
    fireEvent.click(screen.getByRole("button", { name: /Start discovering ideas/i }))

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    expect(onSubmit).toHaveBeenCalledWith({
      departure_city: "北京",
      destination_city: "上海",
      destination_country_code: "CN",
      departure_date: "2026-05-10",
      duration_days: 3,
      traveler_count: 2,
      total_budget: 6000,
      currency: "CNY",
    })
  })

  it("blocks unresolved destinations instead of guessing", async () => {
    const onSubmit = vi.fn()
    render(<HardConstraintForm onSubmit={onSubmit} />)

    fireEvent.change(screen.getByLabelText(/Departure city/i), {
      target: { value: "北京" },
    })
    fireEvent.change(screen.getByLabelText(/Destination city/i), {
      target: { value: "Atlantis" },
    })
    fireEvent.change(screen.getByLabelText(/Departure date/i), {
      target: { value: "2026-05-10" },
    })
    fireEvent.click(screen.getByRole("button", { name: /Start discovering ideas/i }))

    expect(await screen.findByText(/Choose a supported destination/i)).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it("renders Chinese labels and validation copy when language is zh", async () => {
    const onSubmit = vi.fn()
    render(<HardConstraintForm language="zh" onSubmit={onSubmit} />)

    expect(screen.getByLabelText("出发城市")).toBeInTheDocument()
    expect(screen.getByLabelText("目的地城市")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "开始发现灵感" })).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText("目的地城市"), {
      target: { value: "Atlantis" },
    })
    fireEvent.click(screen.getByRole("button", { name: "开始发现灵感" }))

    expect(await screen.findByText(/请选择支持的目的地/)).toBeInTheDocument()
  })
})
