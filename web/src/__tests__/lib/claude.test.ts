import { buildPlanPrompt } from "@/lib/claude"
import { UserPreferences } from "@/lib/types"

const mockPrefs: UserPreferences = {
  destination: "上海",
  departureCity: "北京",
  departureDate: "2026-05-10",
  days: 3,
  totalBudget: 5000,
  accommodationDescription: "想住在老城区的精品民宿，有本地生活气息",
  experienceDescription: "想去当地人才知道的小馆子，避开景区人潮",
}

describe("buildPlanPrompt", () => {
  it("includes destination in prompt", () => {
    const prompt = buildPlanPrompt(mockPrefs)
    expect(prompt).toContain("上海")
  })

  it("includes budget in prompt", () => {
    const prompt = buildPlanPrompt(mockPrefs)
    expect(prompt).toContain("5000")
  })

  it("includes accommodation description", () => {
    const prompt = buildPlanPrompt(mockPrefs)
    expect(prompt).toContain("精品民宿")
  })

  it("includes experience description", () => {
    const prompt = buildPlanPrompt(mockPrefs)
    expect(prompt).toContain("小馆子")
  })
})
