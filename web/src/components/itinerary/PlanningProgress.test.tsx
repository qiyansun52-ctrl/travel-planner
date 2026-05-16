import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { PlanningProgress } from "./PlanningProgress"

describe("PlanningProgress", () => {
  it("stays hidden until planning starts or events exist", () => {
    const { container } = render(<PlanningProgress active={false} events={[]} />)

    expect(container).toBeEmptyDOMElement()
  })

  it("renders a live animated stepper for the active planning stage", () => {
    render(
      <PlanningProgress
        active={true}
        events={[{ stage: "transport", status: "started", message: "正在分析交通" }]}
      />,
    )

    expect(screen.getByRole("region", { name: "规划进度" })).toBeInTheDocument()
    expect(screen.getByText("AI 规划中")).toBeInTheDocument()
    expect(screen.getByText("交通方案")).toBeInTheDocument()
    expect(screen.getByText("正在分析交通")).toBeInTheDocument()
  })
})
