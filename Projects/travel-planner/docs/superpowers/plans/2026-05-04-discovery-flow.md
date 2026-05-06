# Discovery Flow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Google-search-powered discovery step with three mandatory sections — 体验 (Experience), 交通 (Transport), 食物 (Food) — each populated from dedicated internet searches. Users browse AI-structured cards, select what interests them, then generate a personalized itinerary with conversational adjustment aware of original selections.

**Architecture:** Three-step flow: (1) Home — destination + budget only; (2) Discover page — three parallel Google CSE searches (one per section) → Gemini structures each into cards → scrollable three-section gallery with multi-select; (3) Plan page with selected cards baked into both generation and adjustment prompts. `AttractionCard.section` replaces `category` with values `"experience" | "transport" | "food"`. API returns `{ sections: { experience, transport, food } }`.

**Tech Stack:** Next.js 16 App Router, TypeScript, Tailwind CSS, `@google/generative-ai` (installed), Google Custom Search JSON API, `nanoid` (installed).

---

## File Map

```
web/src/
├── lib/
│   ├── types.ts                          MODIFY — AttractionCard.section, update TravelPlan
│   ├── googleSearch.ts                   CREATE — 3-query builder + response parser
│   └── claude.ts                         MODIFY — buildDiscoverPrompt (3-section), update plan+adjustment prompts
├── app/
│   ├── page.tsx                          (unchanged — SearchForm handles navigation)
│   ├── api/
│   │   ├── discover/
│   │   │   └── route.ts                  CREATE — 3 parallel searches + Gemini → 3-section response
│   │   └── plan/
│   │       └── generate/
│   │           └── route.ts              MODIFY — accept selectedAttractions
│   └── discover/
│       └── [destination]/
│           └── page.tsx                  CREATE — 3-section gallery page
├── components/
│   ├── search/
│   │   └── SearchForm.tsx                MODIFY — destination + budget only
│   └── discover/
│       ├── AttractionCard.tsx            CREATE — card with section-aware icon fallback + toggle
│       ├── SectionBlock.tsx              CREATE — section header + horizontal card row
│       └── SelectionBar.tsx             CREATE — sticky bottom: selected count + trip-detail form
└── hooks/
    └── usePlan.ts                        MODIFY — pass selectedAttractions in adjustment calls
```

**New env vars needed in `web/.env.local`:**
```
GOOGLE_CSE_KEY=your_google_api_key
GOOGLE_CSE_CX=your_custom_search_engine_id
```

---

## Task 1: Extend Types

**Files:**
- Modify: `web/src/lib/types.ts`

- [ ] **Step 1: Add AttractionCard with section field and extend TravelPlan**

Replace `web/src/lib/types.ts` with:

```typescript
export interface UserPreferences {
  destination: string
  departureCity: string
  departureDate: string
  days: number
  totalBudget: number
  accommodationDescription: string
  experienceDescription: string
}

export type CardSection = "experience" | "transport" | "food"

export interface AttractionCard {
  id: string
  name: string
  section: CardSection
  description: string
  estimatedCost: string   // e.g. "¥50–100" or "免费"
  imageUrl: string        // may be empty string — UI shows emoji fallback
  tags: string[]
}

export interface DiscoverSections {
  experience: AttractionCard[]
  transport: AttractionCard[]
  food: AttractionCard[]
}

export interface Activity {
  id: string
  time: string
  endTime?: string
  place: string
  description: string
  type: "attraction" | "food" | "transport" | "hotel" | "free"
  estimatedCost?: number
  tips?: string
}

export interface DayPlan {
  day: number
  date: string
  title: string
  activities: Activity[]
  totalCost: number
}

export interface BudgetBreakdown {
  transport: number
  accommodation: number
  food: number
  attractions: number
  other: number
  total: number
}

export interface TravelPlan {
  id: string
  preferences: UserPreferences
  selectedAttractions: AttractionCard[]
  days: DayPlan[]
  budget: BudgetBreakdown
  tips: string[]
  createdAt: string
}

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  timestamp: string
}
```

- [ ] **Step 2: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/lib/types.ts
git commit -m "feat: add CardSection type and DiscoverSections, extend TravelPlan with selectedAttractions"
```

---

## Task 2: Google Search Client (3 queries)

**Files:**
- Create: `web/src/lib/googleSearch.ts`
- Test: `web/src/__tests__/lib/googleSearch.test.ts`

- [ ] **Step 1: Write failing tests**

Create `web/src/__tests__/lib/googleSearch.test.ts`:

```typescript
import { buildSearchQueries, parseSearchItems } from "@/lib/googleSearch"

describe("buildSearchQueries", () => {
  it("returns exactly 3 queries", () => {
    const queries = buildSearchQueries("上海")
    expect(queries).toHaveLength(3)
  })

  it("all queries contain the destination", () => {
    const queries = buildSearchQueries("北京")
    queries.forEach((q) => expect(q).toContain("北京"))
  })

  it("query[0] targets experiences and attractions", () => {
    const [q] = buildSearchQueries("成都")
    expect(q).toMatch(/景点|体验|攻略/)
  })

  it("query[1] targets transport and getting around", () => {
    const [, q] = buildSearchQueries("成都")
    expect(q).toMatch(/交通|出行|怎么去/)
  })

  it("query[2] targets food and restaurants", () => {
    const [, , q] = buildSearchQueries("成都")
    expect(q).toMatch(/美食|餐厅|必吃/)
  })
})

describe("parseSearchItems", () => {
  it("extracts title, snippet, link, and og:image", () => {
    const mockItems = [
      {
        title: "外滩夜景攻略",
        snippet: "上海最著名的景点之一",
        link: "https://example.com",
        pagemap: {
          metatags: [{ "og:image": "https://example.com/img.jpg" }],
        },
      },
    ]
    const result = parseSearchItems(mockItems)
    expect(result).toHaveLength(1)
    expect(result[0].title).toBe("外滩夜景攻略")
    expect(result[0].snippet).toBe("上海最著名的景点之一")
    expect(result[0].link).toBe("https://example.com")
    expect(result[0].imageUrl).toBe("https://example.com/img.jpg")
  })

  it("falls back to csthumbnail when og:image absent", () => {
    const mockItems = [
      {
        title: "豫园",
        snippet: "古典园林",
        link: "https://x.com",
        pagemap: { csthumbnail: [{ src: "https://x.com/thumb.jpg" }] },
      },
    ]
    const result = parseSearchItems(mockItems)
    expect(result[0].imageUrl).toBe("https://x.com/thumb.jpg")
  })

  it("returns empty imageUrl when pagemap is absent", () => {
    const mockItems = [{ title: "南京路", snippet: "步行街", link: "https://x.com" }]
    const result = parseSearchItems(mockItems)
    expect(result[0].imageUrl).toBe("")
  })
})
```

- [ ] **Step 2: Run to verify failure**

```bash
cd ~/Projects/travel-planner/web
npm test -- googleSearch.test.ts
```

Expected: FAIL — `Cannot find module '@/lib/googleSearch'`

- [ ] **Step 3: Create the Google Search client**

Create `web/src/lib/googleSearch.ts`:

```typescript
export interface SearchItem {
  title: string
  snippet: string
  link: string
  imageUrl: string
}

export function buildSearchQueries(
  destination: string
): [string, string, string] {
  return [
    `${destination} 必去景点 旅游体验 攻略 2025`,
    `${destination} 交通攻略 怎么去 市内出行 交通方式`,
    `${destination} 美食推荐 必吃 餐厅 小吃 2025`,
  ]
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function parseSearchItems(items: any[]): SearchItem[] {
  return items.map((item) => ({
    title: item.title ?? "",
    snippet: item.snippet ?? "",
    link: item.link ?? "",
    imageUrl:
      item.pagemap?.metatags?.[0]?.["og:image"] ??
      item.pagemap?.csthumbnail?.[0]?.src ??
      "",
  }))
}

export async function searchGoogle(
  query: string,
  apiKey: string,
  cx: string
): Promise<SearchItem[]> {
  const url = new URL("https://www.googleapis.com/customsearch/v1")
  url.searchParams.set("key", apiKey)
  url.searchParams.set("cx", cx)
  url.searchParams.set("q", query)
  url.searchParams.set("num", "8")
  url.searchParams.set("lr", "lang_zh-CN")

  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`Google CSE error: ${res.status}`)
  const data = await res.json()
  return parseSearchItems(data.items ?? [])
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- googleSearch.test.ts
```

Expected: PASS — 8 tests passing

- [ ] **Step 5: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/lib/googleSearch.ts web/src/__tests__/lib/googleSearch.test.ts
git commit -m "feat: add Google CSE client with 3-query builder (experience/transport/food)"
```

---

## Task 3: Prompt Builders

**Files:**
- Modify: `web/src/lib/claude.ts`
- Modify: `web/src/__tests__/lib/claude.test.ts`

- [ ] **Step 1: Write failing tests**

Replace `web/src/__tests__/lib/claude.test.ts` with:

```typescript
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
```

- [ ] **Step 2: Run to verify failures**

```bash
npm test -- claude.test.ts
```

Expected: FAIL — missing exports and wrong signatures

- [ ] **Step 3: Rewrite `web/src/lib/claude.ts`**

```typescript
import { UserPreferences, AttractionCard } from "./types"
import { SearchItem } from "./googleSearch"

const sectionLabel: Record<AttractionCard["section"], string> = {
  experience: "体验/景点",
  transport: "交通",
  food: "美食",
}

export function buildPlanPrompt(prefs: UserPreferences): string {
  return buildPlanPromptWithAttractions(prefs, [])
}

export function buildPlanPromptWithAttractions(
  prefs: UserPreferences,
  selected: AttractionCard[]
): string {
  let attractionsSection = ""
  if (selected.length > 0) {
    const bySection = {
      experience: selected.filter((c) => c.section === "experience"),
      transport: selected.filter((c) => c.section === "transport"),
      food: selected.filter((c) => c.section === "food"),
    }
    const lines: string[] = ["\n用户已选择的感兴趣内容（请优先将这些安排进行程中）："]
    for (const [sec, cards] of Object.entries(bySection)) {
      if (cards.length === 0) continue
      lines.push(
        `【${sectionLabel[sec as AttractionCard["section"]]}】${cards
          .map((c) => `${c.name}（${c.estimatedCost}）`)
          .join("、")}`
      )
    }
    attractionsSection = lines.join("\n") + "\n"
  }

  return `你是一位专业的旅行规划师。请根据以下信息，生成一份详细的旅行规划。

目的地：${prefs.destination}
出发城市：${prefs.departureCity}
出发日期：${prefs.departureDate}
旅行天数：${prefs.days}天
总预算：¥${prefs.totalBudget}（含交通、住宿、餐饮、景点）
${attractionsSection}
住宿期待：
${prefs.accommodationDescription}

旅行体验期待：
${prefs.experienceDescription}

请生成以下内容：
1. 逐日行程（每天5-7个活动，包含时间、地点、活动描述、预计费用）
2. 预算分配（交通/住宿/餐饮/景点/其他）
3. 实用提示（3-5条，关于当地注意事项）

输出格式为 JSON，结构如下：
{
  "days": [
    {
      "day": 1,
      "date": "YYYY-MM-DD",
      "title": "今日主题",
      "activities": [
        {
          "id": "act_1_1",
          "time": "09:00",
          "endTime": "11:00",
          "place": "地点名称",
          "description": "活动描述",
          "type": "attraction|food|transport|hotel|free",
          "estimatedCost": 40,
          "tips": "注意事项（可选）"
        }
      ],
      "totalCost": 300
    }
  ],
  "budget": {
    "transport": 1200,
    "accommodation": 1800,
    "food": 1200,
    "attractions": 600,
    "other": 200,
    "total": 5000
  },
  "tips": ["提示1", "提示2", "提示3"]
}`
}

export function buildAdjustmentPrompt(
  currentPlan: string,
  userRequest: string,
  selectedAttractions: AttractionCard[] = []
): string {
  const context =
    selectedAttractions.length > 0
      ? `\n用户最初感兴趣的内容：${selectedAttractions.map((c) => c.name).join("、")}\n`
      : ""

  return `你是旅行规划助手。用户有以下调整请求：

"${userRequest}"
${context}
当前行程：
${currentPlan}

请只修改受影响的部分，保持其他内容不变。以相同的 JSON 格式返回完整的修改后行程。`
}

function formatItems(items: SearchItem[]): string {
  if (items.length === 0) return "（无搜索结果，请根据你的知识补充）"
  return items
    .map((item, i) => `[${i + 1}] ${item.title}\n    ${item.snippet}`)
    .join("\n")
}

export function buildDiscoverPrompt(
  destination: string,
  experienceItems: SearchItem[],
  transportItems: SearchItem[],
  foodItems: SearchItem[]
): string {
  return `你是一位旅游信息整理专家。根据以下三组关于「${destination}」的搜索结果，分别整理出体验景点、交通方式、美食推荐的信息卡片。

===== 体验/景点 搜索结果 =====
${formatItems(experienceItems)}

===== 交通 搜索结果 =====
${formatItems(transportItems)}

===== 美食 搜索结果 =====
${formatItems(foodItems)}

请为每个分类整理出 5–8 张信息卡片，要求：
- 内容来自搜索结果中提及最多、最具代表性的内容
- name：简洁名称，不超过15字
- description：一句话描述，不超过40字，突出亮点
- estimatedCost：预计费用，格式如 "¥50–100"、"免费" 或 "¥553（二等座）"
- tags：2–3个标签

以 JSON 格式返回，结构：
{
  "experience": [
    {
      "name": "外滩",
      "description": "上海最具代表性的滨江历史建筑群，夜景尤为壮观",
      "estimatedCost": "免费",
      "tags": ["地标", "夜景", "必去"]
    }
  ],
  "transport": [
    {
      "name": "高铁（北京→上海）",
      "description": "G字头高铁约4.5小时，是最主流的城际方案",
      "estimatedCost": "¥553（二等座）",
      "tags": ["高铁", "城际", "推荐"]
    }
  ],
  "food": [
    {
      "name": "南翔小笼包",
      "description": "豫园内百年老店，皮薄汁多，必吃经典",
      "estimatedCost": "¥30–60",
      "tags": ["小吃", "老字号", "必吃"]
    }
  ]
}`
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- claude.test.ts
```

Expected: PASS — 14 tests passing

- [ ] **Step 5: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/lib/claude.ts web/src/__tests__/lib/claude.test.ts
git commit -m "feat: update prompt builders for 3-section discovery (experience/transport/food)"
```

---

## Task 4: Add env vars for Google CSE

**Files:**
- Modify: `web/.env.local`

- [ ] **Step 1: Append keys to `.env.local`**

```
GOOGLE_CSE_KEY=your_google_api_key_here
GOOGLE_CSE_CX=your_custom_search_engine_id_here
```

**How to get these:**
1. Go to https://programmablesearchengine.google.com → "新建搜索引擎" → 搜索范围选「搜索整个网络」→ 创建 → 复制 **Search engine ID** (即 `cx`)
2. Go to https://console.cloud.google.com → APIs & Services → Credentials → Create API Key → 在 API Library 启用 **Custom Search API** → 复制 key

- [ ] **Step 2: Verify env vars are readable**

```bash
cd ~/Projects/travel-planner/web
node -e "require('dotenv').config({path:'.env.local'}); console.log('KEY:', process.env.GOOGLE_CSE_KEY?.slice(0,8), 'CX:', process.env.GOOGLE_CSE_CX?.slice(0,8))"
```

Expected: prints first 8 chars of each value (not `undefined`)

---

## Task 5: Discover API Route (3-section)

**Files:**
- Create: `web/src/app/api/discover/route.ts`

- [ ] **Step 1: Create the route**

Create `web/src/app/api/discover/route.ts`:

```typescript
import { NextRequest, NextResponse } from "next/server"
import { GoogleGenerativeAI } from "@google/generative-ai"
import { buildDiscoverPrompt } from "@/lib/claude"
import { searchGoogle, buildSearchQueries, SearchItem } from "@/lib/googleSearch"
import { AttractionCard, DiscoverSections } from "@/lib/types"
import { nanoid } from "nanoid"

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!)
const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" })

type RawCard = Omit<AttractionCard, "id" | "imageUrl" | "section">

function attachIds(
  cards: RawCard[],
  section: AttractionCard["section"],
  imageMap: Map<string, string>
): AttractionCard[] {
  return cards.map((card) => {
    const matchKey = [...imageMap.keys()].find((k) =>
      card.name.includes(k.slice(0, 6))
    )
    return {
      ...card,
      id: nanoid(),
      section,
      imageUrl: matchKey ? (imageMap.get(matchKey) ?? "") : "",
    }
  })
}

export async function GET(req: NextRequest) {
  const destination = req.nextUrl.searchParams.get("destination")
  if (!destination) {
    return NextResponse.json({ error: "destination is required" }, { status: 400 })
  }

  const apiKey = process.env.GOOGLE_CSE_KEY
  const cx = process.env.GOOGLE_CSE_CX
  const [q1, q2, q3] = buildSearchQueries(destination)

  let experienceItems: SearchItem[] = []
  let transportItems: SearchItem[] = []
  let foodItems: SearchItem[] = []

  if (apiKey && cx) {
    const [r1, r2, r3] = await Promise.allSettled([
      searchGoogle(q1, apiKey, cx),
      searchGoogle(q2, apiKey, cx),
      searchGoogle(q3, apiKey, cx),
    ])
    if (r1.status === "fulfilled") experienceItems = r1.value
    if (r2.status === "fulfilled") transportItems = r2.value
    if (r3.status === "fulfilled") foodItems = r3.value
  }

  const allItems = [...experienceItems, ...transportItems, ...foodItems]
  const imageMap = new Map(allItems.map((item) => [item.title, item.imageUrl]))

  const prompt = buildDiscoverPrompt(destination, experienceItems, transportItems, foodItems)

  try {
    const result = await model.generateContent(prompt)
    const raw = result.response.text()

    const jsonMatch = raw.match(/\{[\s\S]*\}/)
    if (!jsonMatch) throw new Error("Gemini returned no JSON")

    const parsed = JSON.parse(jsonMatch[0]) as {
      experience: RawCard[]
      transport: RawCard[]
      food: RawCard[]
    }

    const sections: DiscoverSections = {
      experience: attachIds(parsed.experience ?? [], "experience", imageMap),
      transport: attachIds(parsed.transport ?? [], "transport", imageMap),
      food: attachIds(parsed.food ?? [], "food", imageMap),
    }

    return NextResponse.json({ sections })
  } catch (err) {
    console.error("Discover error:", err)
    return NextResponse.json({ error: "Failed to generate cards" }, { status: 500 })
  }
}
```

- [ ] **Step 2: Start dev server and test manually**

```bash
cd ~/Projects/travel-planner/web
npm run dev
```

In a new terminal:

```bash
curl "http://localhost:3000/api/discover?destination=上海" | python3 -m json.tool | head -60
```

Expected: JSON with `{ "sections": { "experience": [...], "transport": [...], "food": [...] } }`, each array has 5–8 cards.

- [ ] **Step 3: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/app/api/discover/
git commit -m "feat: add /api/discover — 3 parallel searches + Gemini 3-section card extraction"
```

---

## Task 6: AttractionCard Component

**Files:**
- Create: `web/src/components/discover/AttractionCard.tsx`

- [ ] **Step 1: Create the component**

Create `web/src/components/discover/AttractionCard.tsx`:

```typescript
import { AttractionCard as AttractionCardType } from "@/lib/types"

const sectionIcons: Record<AttractionCardType["section"], string> = {
  experience: "🏛️",
  transport: "🚄",
  food: "🍜",
}

interface AttractionCardProps {
  card: AttractionCardType
  selected: boolean
  onToggle: (id: string) => void
}

export function AttractionCard({ card, selected, onToggle }: AttractionCardProps) {
  return (
    <button
      type="button"
      onClick={() => onToggle(card.id)}
      className={`relative w-full text-left rounded-xl overflow-hidden border-2 transition-all ${
        selected
          ? "border-blue-500 shadow-md shadow-blue-100"
          : "border-gray-100 hover:border-gray-300"
      }`}
    >
      {selected && (
        <div className="absolute top-2 right-2 z-10 bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold">
          ✓
        </div>
      )}

      <div className="h-28 bg-gray-100 overflow-hidden flex-shrink-0">
        {card.imageUrl ? (
          <img
            src={card.imageUrl}
            alt={card.name}
            className="w-full h-full object-cover"
            onError={(e) => {
              const target = e.target as HTMLImageElement
              target.style.display = "none"
              target.parentElement!.innerHTML = `<div class="w-full h-full flex items-center justify-center text-4xl">${sectionIcons[card.section]}</div>`
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl">
            {sectionIcons[card.section]}
          </div>
        )}
      </div>

      <div className="p-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-400">{card.estimatedCost}</span>
        </div>
        <p className="font-semibold text-gray-900 text-sm leading-snug">{card.name}</p>
        <p className="text-xs text-gray-500 mt-0.5 leading-relaxed line-clamp-2">
          {card.description}
        </p>
        {card.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {card.tags.map((tag) => (
              <span
                key={tag}
                className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </button>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/components/discover/AttractionCard.tsx
git commit -m "feat: add AttractionCard component with section-aware emoji fallback"
```

---

## Task 7: SectionBlock Component

`SectionBlock` renders a section header with a count badge and a responsive card grid. Each of the three sections on the discover page uses one `SectionBlock`.

**Files:**
- Create: `web/src/components/discover/SectionBlock.tsx`

- [ ] **Step 1: Create the component**

Create `web/src/components/discover/SectionBlock.tsx`:

```typescript
import { AttractionCard as AttractionCardType } from "@/lib/types"
import { AttractionCard } from "./AttractionCard"

interface SectionConfig {
  icon: string
  label: string
  color: string       // Tailwind bg class for the header accent bar
  emptyHint: string
}

const sectionConfig: Record<AttractionCardType["section"], SectionConfig> = {
  experience: {
    icon: "🏛️",
    label: "体验 & 景点",
    color: "bg-blue-500",
    emptyHint: "暂无景点信息",
  },
  transport: {
    icon: "🚄",
    label: "交通方式",
    color: "bg-emerald-500",
    emptyHint: "暂无交通信息",
  },
  food: {
    icon: "🍜",
    label: "美食推荐",
    color: "bg-orange-500",
    emptyHint: "暂无美食信息",
  },
}

interface SectionBlockProps {
  section: AttractionCardType["section"]
  cards: AttractionCardType[]
  selected: Set<string>
  onToggle: (id: string) => void
}

export function SectionBlock({ section, cards, selected, onToggle }: SectionBlockProps) {
  const cfg = sectionConfig[section]

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <div className={`w-1 h-6 rounded-full ${cfg.color}`} />
        <span className="text-lg">{cfg.icon}</span>
        <h2 className="font-bold text-gray-900 text-lg">{cfg.label}</h2>
        <span className="text-sm text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
          {cards.length} 个
        </span>
      </div>

      {cards.length === 0 ? (
        <p className="text-gray-400 text-sm py-6 text-center">{cfg.emptyHint}</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {cards.map((card) => (
            <AttractionCard
              key={card.id}
              card={card}
              selected={selected.has(card.id)}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </section>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/components/discover/SectionBlock.tsx
git commit -m "feat: add SectionBlock component with section header and card grid"
```

---

## Task 8: SelectionBar Component

**Files:**
- Create: `web/src/components/discover/SelectionBar.tsx`

- [ ] **Step 1: Create the component**

Create `web/src/components/discover/SelectionBar.tsx`:

```typescript
"use client"

import { useState, FormEvent } from "react"
import { AttractionCard, UserPreferences } from "@/lib/types"
import { Button } from "@/components/ui/Button"

interface SelectionBarProps {
  selected: AttractionCard[]
  destination: string
  budget: number
  onGenerate: (prefs: UserPreferences) => void
  generating: boolean
}

export function SelectionBar({
  selected,
  destination,
  budget,
  onGenerate,
  generating,
}: SelectionBarProps) {
  const [expanded, setExpanded] = useState(false)
  const [form, setForm] = useState({
    departureCity: "",
    departureDate: "",
    days: 3,
    accommodationDescription: "",
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onGenerate({
      destination,
      departureCity: form.departureCity,
      departureDate: form.departureDate,
      days: form.days,
      totalBudget: budget,
      accommodationDescription: form.accommodationDescription,
      experienceDescription: selected.map((c) => c.name).join("、"),
    })
  }

  if (selected.length === 0) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg z-50">
      {expanded ? (
        <form onSubmit={handleSubmit} className="max-w-2xl mx-auto p-4 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <p className="font-semibold text-gray-800">
              已选 {selected.length} 项 — 填写出行信息
            </p>
            <button
              type="button"
              onClick={() => setExpanded(false)}
              className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            >
              ×
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-600">出发城市</label>
              <input
                required
                type="text"
                placeholder="例：北京"
                className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                value={form.departureCity}
                onChange={(e) => setForm({ ...form, departureCity: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-600">出发日期</label>
              <input
                required
                type="date"
                className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                value={form.departureDate}
                onChange={(e) => setForm({ ...form, departureDate: e.target.value })}
              />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600">旅行天数</label>
            <input
              required
              type="number"
              min={1}
              max={30}
              className="w-32 rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              value={form.days}
              onChange={(e) => setForm({ ...form, days: Number(e.target.value) })}
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-600">
              住宿期待
              <span className="text-gray-400 font-normal ml-1">（可选）</span>
            </label>
            <textarea
              rows={2}
              placeholder="例：想住在老城区，有本地生活气息…"
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm resize-none focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              value={form.accommodationDescription}
              onChange={(e) =>
                setForm({ ...form, accommodationDescription: e.target.value })
              }
            />
          </div>

          <Button type="submit" disabled={generating} className="w-full py-3 text-base">
            {generating ? "AI 正在规划中…" : "生成我的行程 →"}
          </Button>
        </form>
      ) : (
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <span className="font-semibold text-gray-900">已选 {selected.length} 项</span>
            <span className="text-gray-400 text-sm ml-2">
              {selected
                .slice(0, 3)
                .map((c) => c.name)
                .join("、")}
              {selected.length > 3 ? " 等" : ""}
            </span>
          </div>
          <Button onClick={() => setExpanded(true)}>继续规划 →</Button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/components/discover/SelectionBar.tsx
git commit -m "feat: add SelectionBar with expandable trip-detail form"
```

---

## Task 9: Discover Page (3-section layout)

**Files:**
- Create: `web/src/app/discover/[destination]/page.tsx`

- [ ] **Step 1: Create the page**

Create `web/src/app/discover/[destination]/page.tsx`:

```typescript
"use client"

import { useEffect, useState, useMemo } from "react"
import { useParams, useRouter, useSearchParams } from "next/navigation"
import {
  AttractionCard as AttractionCardType,
  DiscoverSections,
  TravelPlan,
  UserPreferences,
} from "@/lib/types"
import { SectionBlock } from "@/components/discover/SectionBlock"
import { SelectionBar } from "@/components/discover/SelectionBar"
import { savePlan } from "@/lib/planStore"
import { nanoid } from "nanoid"

const LOADING_STEPS = [
  "正在搜索旅游攻略…",
  "收集交通与景点信息…",
  "收集美食与体验信息…",
  "AI 正在整理卡片…",
]

const EMPTY_SECTIONS: DiscoverSections = {
  experience: [],
  transport: [],
  food: [],
}

export default function DiscoverPage() {
  const params = useParams<{ destination: string }>()
  const searchParams = useSearchParams()
  const router = useRouter()

  const destination = decodeURIComponent(params.destination)
  const budget = Number(searchParams.get("budget") ?? 5000)

  const [sections, setSections] = useState<DiscoverSections>(EMPTY_SECTIONS)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loadingStep, setLoadingStep] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    const cacheKey = `discover_${destination}`
    const cached = sessionStorage.getItem(cacheKey)
    if (cached) {
      setSections(JSON.parse(cached))
      setLoading(false)
      return
    }

    const interval = setInterval(() => {
      setLoadingStep((prev) => Math.min(prev + 1, LOADING_STEPS.length - 1))
    }, 2000)

    fetch(`/api/discover?destination=${encodeURIComponent(destination)}`)
      .then((res) => {
        if (!res.ok) throw new Error("搜索失败，请返回重试")
        return res.json()
      })
      .then((data: { sections: DiscoverSections }) => {
        setSections(data.sections)
        sessionStorage.setItem(cacheKey, JSON.stringify(data.sections))
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => {
        clearInterval(interval)
        setLoading(false)
      })

    return () => clearInterval(interval)
  }, [destination])

  const allCards = useMemo(
    () => [...sections.experience, ...sections.transport, ...sections.food],
    [sections]
  )

  const selectedCards = useMemo(
    () => allCards.filter((c) => selected.has(c.id)),
    [allCards, selected]
  )

  function toggleCard(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  async function handleGenerate(prefs: UserPreferences) {
    setGenerating(true)
    try {
      const res = await fetch("/api/plan/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preferences: prefs, selectedAttractions: selectedCards }),
      })
      if (!res.ok) throw new Error("生成失败，请重试")
      const raw = await res.text()
      const jsonMatch = raw.match(/\{[\s\S]*\}/)
      if (!jsonMatch) throw new Error("无法解析行程数据")
      const planData = JSON.parse(jsonMatch[0])
      const plan: TravelPlan = {
        id: nanoid(),
        preferences: prefs,
        selectedAttractions: selectedCards,
        days: planData.days,
        budget: planData.budget,
        tips: planData.tips,
        createdAt: new Date().toISOString(),
      }
      savePlan(plan)
      router.push(`/plan/${plan.id}`)
    } catch (err) {
      alert(err instanceof Error ? err.message : "发生错误，请重试")
      setGenerating(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-gradient-to-br from-blue-50 to-slate-50">
        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-gray-700 text-lg font-medium">{LOADING_STEPS[loadingStep]}</p>
        <p className="text-gray-400 text-sm">正在搜索 {destination} 的旅游信息</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-red-500">{error}</p>
        <button onClick={() => router.push("/")} className="text-blue-600 underline">
          返回首页
        </button>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-32">
      <div className="bg-white border-b border-gray-100 px-4 py-4 sticky top-0 z-40 shadow-sm">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <button
            onClick={() => router.push("/")}
            className="text-gray-400 hover:text-gray-600 text-xl"
          >
            ←
          </button>
          <div>
            <h1 className="font-bold text-gray-900 text-xl">{destination}</h1>
            <p className="text-xs text-gray-400">
              选择感兴趣的内容，AI 将为你量身制定行程
            </p>
          </div>
          {selected.size > 0 && (
            <span className="ml-auto bg-blue-500 text-white text-xs font-bold px-3 py-1 rounded-full">
              已选 {selected.size}
            </span>
          )}
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 pt-8 flex flex-col gap-12">
        <SectionBlock
          section="experience"
          cards={sections.experience}
          selected={selected}
          onToggle={toggleCard}
        />
        <SectionBlock
          section="transport"
          cards={sections.transport}
          selected={selected}
          onToggle={toggleCard}
        />
        <SectionBlock
          section="food"
          cards={sections.food}
          selected={selected}
          onToggle={toggleCard}
        />
      </div>

      <SelectionBar
        selected={selectedCards}
        destination={destination}
        budget={budget}
        onGenerate={handleGenerate}
        generating={generating}
      />
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/app/discover/
git commit -m "feat: add discover page with 3 independent sections (experience/transport/food)"
```

---

## Task 10: Simplify Home Page

**Files:**
- Modify: `web/src/components/search/SearchForm.tsx`

- [ ] **Step 1: Replace SearchForm**

Replace `web/src/components/search/SearchForm.tsx` with:

```typescript
"use client"

import { useState, FormEvent } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/Button"

export function SearchForm() {
  const router = useRouter()
  const [destination, setDestination] = useState("")
  const [budget, setBudget] = useState(5000)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    router.push(`/discover/${encodeURIComponent(destination)}?budget=${budget}`)
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5 w-full max-w-md">
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">你想去哪里？</label>
        <input
          required
          autoFocus
          type="text"
          placeholder="例：上海、京都、巴黎"
          className="rounded-xl border border-gray-200 px-4 py-3 text-base focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
          value={destination}
          onChange={(e) => setDestination(e.target.value)}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">预算大概多少？</label>
        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">¥</span>
          <input
            required
            type="number"
            min={100}
            placeholder="5000"
            className="w-full rounded-xl border border-gray-200 pl-8 pr-4 py-3 text-base focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={budget || ""}
            onChange={(e) => setBudget(Number(e.target.value))}
          />
        </div>
        <p className="text-xs text-gray-400">含交通、住宿、餐饮、景点</p>
      </div>

      <Button type="submit" className="w-full py-3 text-base">
        探索目的地 →
      </Button>
    </form>
  )
}
```

- [ ] **Step 2: Start dev server and verify**

```bash
cd ~/Projects/travel-planner/web
npm run dev
```

Open http://localhost:3000:
- Two fields only: 目的地 + 预算
- Submitting "上海" navigates to `/discover/上海?budget=5000`

- [ ] **Step 3: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/components/search/SearchForm.tsx
git commit -m "feat: simplify home page form to destination + budget only"
```

---

## Task 11: Update Plan Generation Route

**Files:**
- Modify: `web/src/app/api/plan/generate/route.ts`

- [ ] **Step 1: Update the route to accept selectedAttractions**

Replace `web/src/app/api/plan/generate/route.ts` with:

```typescript
import { NextRequest } from "next/server"
import { GoogleGenerativeAI } from "@google/generative-ai"
import { buildPlanPromptWithAttractions, buildAdjustmentPrompt } from "@/lib/claude"
import { UserPreferences, AttractionCard } from "@/lib/types"

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!)
const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" })

export async function POST(req: NextRequest) {
  const body = await req.json()
  const { preferences, selectedAttractions, currentPlan, adjustment } = body as {
    preferences?: UserPreferences
    selectedAttractions?: AttractionCard[]
    currentPlan?: string
    adjustment?: string
  }

  const prompt =
    currentPlan && adjustment
      ? buildAdjustmentPrompt(currentPlan, adjustment, selectedAttractions ?? [])
      : buildPlanPromptWithAttractions(preferences!, selectedAttractions ?? [])

  try {
    const result = await model.generateContent(prompt)
    const text = result.response.text()
    return new Response(text, {
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    })
  } catch (err) {
    console.error("Gemini error:", err)
    return new Response("生成失败，请重试", { status: 500 })
  }
}
```

- [ ] **Step 2: Test with curl**

```bash
curl -X POST http://localhost:3000/api/plan/generate \
  -H "Content-Type: application/json" \
  -d '{
    "preferences": {
      "destination": "上海",
      "departureCity": "北京",
      "departureDate": "2026-06-01",
      "days": 2,
      "totalBudget": 3000,
      "accommodationDescription": "市中心",
      "experienceDescription": "外滩"
    },
    "selectedAttractions": [
      {"id":"c1","name":"外滩","section":"experience","description":"滨江夜景","estimatedCost":"免费","imageUrl":"","tags":["地标"]},
      {"id":"c2","name":"高铁 G1","section":"transport","description":"北京→上海","estimatedCost":"¥553","imageUrl":"","tags":["高铁"]}
    ]
  }'
```

Expected: JSON plan that includes 外滩 in day activities and references high-speed rail for transport.

- [ ] **Step 3: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/app/api/plan/generate/route.ts
git commit -m "feat: update plan generation to use selectedAttractions from all 3 sections"
```

---

## Task 12: Update usePlan Hook

**Files:**
- Modify: `web/src/hooks/usePlan.ts`

- [ ] **Step 1: Update hook to carry selectedAttractions through adjustment calls**

Replace `web/src/hooks/usePlan.ts` with:

```typescript
"use client"

import { useState, useCallback } from "react"
import { TravelPlan, ChatMessage } from "@/lib/types"
import { savePlan } from "@/lib/planStore"

export function usePlan(initialPlan: TravelPlan) {
  const [plan, setPlan] = useState<TravelPlan>(initialPlan)
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const sel = initialPlan.selectedAttractions
    const selText =
      sel.length > 0
        ? `已将你选择的${sel.map((c) => c.name).join("、")}安排进行程。`
        : ""
    return [
      {
        role: "assistant",
        content: `你的 ${initialPlan.preferences.days} 天${initialPlan.preferences.destination}行程已生成！${selText}你可以告诉我任何调整，比如「把第二天改成轻松一点的」或「把交通方案换成飞机」。`,
        timestamp: new Date().toISOString(),
      },
    ]
  })
  const [isGenerating, setIsGenerating] = useState(false)

  const sendAdjustment = useCallback(
    async (userMessage: string) => {
      setMessages((prev) => [
        ...prev,
        { role: "user", content: userMessage, timestamp: new Date().toISOString() },
      ])
      setIsGenerating(true)

      try {
        const res = await fetch("/api/plan/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            currentPlan: JSON.stringify(plan.days),
            adjustment: userMessage,
            selectedAttractions: plan.selectedAttractions,
          }),
        })

        if (!res.ok) throw new Error("调整失败")
        const raw = await res.text()
        const jsonMatch = raw.match(/\{[\s\S]*\}/)
        if (!jsonMatch) throw new Error("无法解析调整结果")

        const updated = JSON.parse(jsonMatch[0])
        const newPlan: TravelPlan = {
          ...plan,
          days: updated.days ?? plan.days,
          budget: updated.budget ?? plan.budget,
          tips: updated.tips ?? plan.tips,
        }
        setPlan(newPlan)
        savePlan(newPlan)

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "已按你的要求更新行程，右侧已同步刷新。还有什么需要调整的吗？",
            timestamp: new Date().toISOString(),
          },
        ])
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "调整时出现问题，请再试一次。",
            timestamp: new Date().toISOString(),
          },
        ])
      } finally {
        setIsGenerating(false)
      }
    },
    [plan]
  )

  return { plan, messages, isGenerating, sendAdjustment }
}
```

- [ ] **Step 2: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/hooks/usePlan.ts
git commit -m "feat: update usePlan — carry selectedAttractions in adjustment calls, section-aware greeting"
```

---

## Task 13: Full End-to-End Verification

- [ ] **Step 1: Run all tests**

```bash
cd ~/Projects/travel-planner/web
npm test
```

Expected: All tests pass.

- [ ] **Step 2: Walk through the complete flow**

```bash
npm run dev
```

1. http://localhost:3000 → enter `上海` + `¥5000` → "探索目的地 →"
2. `/discover/上海?budget=5000` — spinner with 4-step progress messages
3. Page loads with **3 sections**:
   - 🏛️ 体验 & 景点 — 5–8 cards
   - 🚄 交通方式 — 5–8 cards (高铁/飞机/地铁等)
   - 🍜 美食推荐 — 5–8 cards
4. Select 2 experience cards + 1 transport card + 2 food cards
5. Bottom bar: "已选 5 项" + "继续规划 →"
6. Click "继续规划 →" → form expands
7. Fill in: 北京 / 2026-06-15 / 3天 / "市区精品酒店"
8. Click "生成我的行程 →" — loading…
9. Redirected to `/plan/[id]`
10. Chat greeting mentions selected attraction names
11. Type "把第一天改轻松一点" → itinerary updates, right panel refreshes
12. Reload page — plan still there (localStorage)

- [ ] **Step 3: Build check**

```bash
npm run build
```

Expected: Zero errors.

- [ ] **Step 4: Final commit**

```bash
cd ~/Projects/travel-planner
git add .
git commit -m "feat: complete 3-section discovery flow (experience/transport/food) with context-aware AI planning"
```

---

## Done — What You Have

| Module | Content |
|--------|---------|
| 🏛️ 体验 & 景点 | Popular attractions from Google search `[destination] 必去景点 旅游体验 攻略 2025` |
| 🚄 交通方式 | Intercity + local transport from `[destination] 交通攻略 怎么去 市内出行` |
| 🍜 美食推荐 | Restaurants and local food from `[destination] 美食推荐 必吃 餐厅 小吃 2025` |

- Each section has its own dedicated search → content guaranteed even if one search returns few results (Gemini fills gaps from its knowledge)
- Selected cards from all 3 sections are baked into the plan generation prompt and every subsequent adjustment call
- `sessionStorage` caches per-destination to avoid re-fetching
