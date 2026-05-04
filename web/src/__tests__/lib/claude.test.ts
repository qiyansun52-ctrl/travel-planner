import {
  buildPlanPrompt,
  buildPlanPromptWithAttractions,
  buildAdjustmentPrompt,
  buildDiscoverPrompt,
} from "@/lib/claude"
import { UserPreferences, AttractionCard } from "@/lib/types"
import { SearchItem } from "@/lib/googleSearch"

const mockPrefs: UserPreferences = {
  destination: "上海",
  departureCity: "北京",
  departureDate: "2026-05-10",
  days: 3,
  totalBudget: 5000,
  accommodationDescription: "想住在老城区的精品民宿",
  experienceDescription: "想去当地人才知道的小馆子",
}

const mockCards: AttractionCard[] = [
  {
    id: "c1",
    name: "外滩",
    section: "experience",
    description: "上海标志性的滨江景观",
    estimatedCost: "免费",
    imageUrl: "",
    tags: ["地标", "夜景"],
  },
  {
    id: "c2",
    name: "高铁 G1",
    section: "transport",
    description: "北京→上海 4.5小时",
    estimatedCost: "¥553",
    imageUrl: "",
    tags: ["高铁"],
  },
  {
    id: "c3",
    name: "南翔小笼",
    section: "food",
    description: "豫园内的百年老店",
    estimatedCost: "¥30–60",
    imageUrl: "",
    tags: ["小吃"],
  },
]

describe("buildPlanPrompt", () => {
  it("includes destination", () => expect(buildPlanPrompt(mockPrefs)).toContain("上海"))
  it("includes budget", () => expect(buildPlanPrompt(mockPrefs)).toContain("5000"))
  it("includes accommodation description", () =>
    expect(buildPlanPrompt(mockPrefs)).toContain("精品民宿"))
  it("includes experience description", () =>
    expect(buildPlanPrompt(mockPrefs)).toContain("小馆子"))
})

describe("buildPlanPromptWithAttractions", () => {
  it("includes all three selected items by name", () => {
    const prompt = buildPlanPromptWithAttractions(mockPrefs, mockCards)
    expect(prompt).toContain("外滩")
    expect(prompt).toContain("高铁 G1")
    expect(prompt).toContain("南翔小笼")
  })
  it("labels sections correctly in the prompt", () => {
    const prompt = buildPlanPromptWithAttractions(mockPrefs, mockCards)
    expect(prompt).toMatch(/体验|experience/i)
    expect(prompt).toMatch(/交通|transport/i)
    expect(prompt).toMatch(/美食|food/i)
  })
  it("works with empty selections", () => {
    const prompt = buildPlanPromptWithAttractions(mockPrefs, [])
    expect(prompt).toContain("上海")
  })
})

describe("buildAdjustmentPrompt", () => {
  it("includes the user request", () => {
    const prompt = buildAdjustmentPrompt('{"days":[]}', "改成轻松一点", mockCards)
    expect(prompt).toContain("改成轻松一点")
  })
  it("includes original attraction names for context", () => {
    const prompt = buildAdjustmentPrompt('{"days":[]}', "改行程", mockCards)
    expect(prompt).toContain("外滩")
    expect(prompt).toContain("南翔小笼")
  })
  it("works with empty attractions", () => {
    const prompt = buildAdjustmentPrompt('{"days":[]}', "调整", [])
    expect(prompt).toContain("调整")
  })
})

describe("buildDiscoverPrompt", () => {
  it("includes destination in prompt", () => {
    const prompt = buildDiscoverPrompt("上海", [], [], [])
    expect(prompt).toContain("上海")
  })
  it("includes experience search results", () => {
    const items: SearchItem[] = [
      { title: "外滩夜景", snippet: "标志性景点", link: "https://x.com", imageUrl: "" },
    ]
    const prompt = buildDiscoverPrompt("上海", items, [], [])
    expect(prompt).toContain("外滩夜景")
  })
  it("includes transport search results", () => {
    const items: SearchItem[] = [
      { title: "上海地铁攻略", snippet: "地铁线路", link: "https://x.com", imageUrl: "" },
    ]
    const prompt = buildDiscoverPrompt("上海", [], items, [])
    expect(prompt).toContain("上海地铁攻略")
  })
  it("includes food search results", () => {
    const items: SearchItem[] = [
      { title: "小笼包推荐", snippet: "必吃美食", link: "https://x.com", imageUrl: "" },
    ]
    const prompt = buildDiscoverPrompt("上海", [], [], items)
    expect(prompt).toContain("小笼包推荐")
  })
  it("requests JSON with three section arrays", () => {
    const prompt = buildDiscoverPrompt("上海", [], [], [])
    expect(prompt).toContain("experience")
    expect(prompt).toContain("transport")
    expect(prompt).toContain("food")
    expect(prompt).toContain("JSON")
  })
})
