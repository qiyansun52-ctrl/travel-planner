> **STATUS: SUPERSEDED (2026-05-09)**
> 本计划对应早期单体 Next.js + 双面板聊天 MVP,已不再代表当前实施路线。
> 当前唯一 active 计划见:`docs/superpowers/plans/2026-05-09-langgraph-single-city-mvp.md`

# Travel Planner MVP Core — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working Next.js web app where users describe their trip in natural language, Claude generates a structured day-by-day itinerary, and users can adjust it via chat.

**Architecture:** Next.js 14 App Router with TypeScript and Tailwind CSS. A `/api/plan/generate` route calls Claude API (streaming) with the user's preferences and MCP-sourced train data. The front-end is two pages: a home search form and a split-panel plan view (itinerary + AI chat).

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, Anthropic SDK, Vercel deployment target. Web app lives in `travel-planner/web/`.

---

## File Map

```
travel-planner/web/
├── src/
│   ├── app/
│   │   ├── layout.tsx                  # Root layout, fonts, metadata
│   │   ├── page.tsx                    # Home / search page
│   │   ├── plan/
│   │   │   └── [id]/
│   │   │       └── page.tsx            # Travel plan view page
│   │   └── api/
│   │       └── plan/
│   │           └── generate/
│   │               └── route.ts        # Claude streaming API route
│   ├── components/
│   │   ├── search/
│   │   │   └── SearchForm.tsx          # Home page form (destination, budget, preferences)
│   │   ├── plan/
│   │   │   ├── ItineraryPanel.tsx      # Right panel: day-by-day cards
│   │   │   ├── DayCard.tsx             # Single day's activities
│   │   │   ├── ActivityCard.tsx        # Single activity with edit/swap/delete
│   │   │   └── AIChatPanel.tsx         # Left panel: AI conversation
│   │   └── ui/
│   │       ├── Button.tsx
│   │       └── TextArea.tsx
│   ├── lib/
│   │   ├── types.ts                    # All shared TypeScript types
│   │   ├── claude.ts                   # Claude API client + prompt builder
│   │   └── planStore.ts               # localStorage plan persistence
│   └── hooks/
│       └── usePlan.ts                  # Plan state + streaming updates
├── .env.local                          # ANTHROPIC_API_KEY
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## Task 1: Initialize Next.js Project

**Files:**
- Create: `travel-planner/web/` (entire Next.js scaffold)
- Create: `travel-planner/web/.env.local`

- [ ] **Step 1: Scaffold the project**

```bash
cd ~/Projects/travel-planner
npx create-next-app@latest web \
  --typescript \
  --tailwind \
  --app \
  --src-dir \
  --no-eslint \
  --import-alias "@/*"
```

Expected: Next.js project created at `travel-planner/web/`

- [ ] **Step 2: Install Anthropic SDK**

```bash
cd ~/Projects/travel-planner/web
npm install @anthropic-ai/sdk
```

Expected: `@anthropic-ai/sdk` added to `package.json`

- [ ] **Step 3: Create environment file**

Create `travel-planner/web/.env.local`:

```
ANTHROPIC_API_KEY=your_key_here
```

Replace `your_key_here` with the actual Anthropic API key from https://console.anthropic.com/

- [ ] **Step 4: Verify dev server starts**

```bash
cd ~/Projects/travel-planner/web
npm run dev
```

Expected: Server running at http://localhost:3000, default Next.js page visible.

- [ ] **Step 5: Commit**

```bash
cd ~/Projects/travel-planner
git add web/
git commit -m "feat: initialize Next.js web app scaffold"
```

---

## Task 2: Define TypeScript Types

**Files:**
- Create: `web/src/lib/types.ts`

- [ ] **Step 1: Write types**

Create `web/src/lib/types.ts`:

```typescript
export interface UserPreferences {
  destination: string
  departureCity: string
  departureDate: string      // ISO date string "2026-05-10"
  days: number
  totalBudget: number        // CNY
  accommodationDescription: string   // free text e.g. "森林小木屋，有壁炉"
  experienceDescription: string      // free text e.g. "当地人才知道的小馆子"
}

export interface Activity {
  id: string
  time: string               // "09:00"
  endTime?: string           // "11:00"
  place: string
  description: string
  type: "attraction" | "food" | "transport" | "hotel" | "free"
  estimatedCost?: number     // CNY
  tips?: string
}

export interface DayPlan {
  day: number
  date: string               // "2026-05-10"
  title: string              // e.g. "抵达 + 豫园探索"
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
git commit -m "feat: add shared TypeScript types"
```

---

## Task 3: Claude API Client + Prompt Builder

**Files:**
- Create: `web/src/lib/claude.ts`
- Test: `web/src/__tests__/lib/claude.test.ts`

- [ ] **Step 1: Write failing test**

Create `web/src/__tests__/lib/claude.test.ts`:

```typescript
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
```

- [ ] **Step 2: Install Jest**

```bash
cd ~/Projects/travel-planner/web
npm install --save-dev jest @types/jest ts-jest jest-environment-jsdom @testing-library/react @testing-library/jest-dom
```

Add to `package.json` scripts:
```json
"test": "jest",
"test:watch": "jest --watch"
```

Create `web/jest.config.ts`:

```typescript
import type { Config } from "jest"

const config: Config = {
  preset: "ts-jest",
  testEnvironment: "node",
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
  },
  testMatch: ["**/__tests__/**/*.test.ts", "**/__tests__/**/*.test.tsx"],
}

export default config
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd ~/Projects/travel-planner/web
npm test -- claude.test.ts
```

Expected: FAIL — `Cannot find module '@/lib/claude'`

- [ ] **Step 4: Create Claude client**

Create `web/src/lib/claude.ts`:

```typescript
import Anthropic from "@anthropic-ai/sdk"
import { UserPreferences } from "./types"

export const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
})

export function buildPlanPrompt(prefs: UserPreferences): string {
  return `你是一位专业的旅行规划师。请根据以下信息，生成一份详细的旅行规划。

目的地：${prefs.destination}
出发城市：${prefs.departureCity}
出发日期：${prefs.departureDate}
旅行天数：${prefs.days}天
总预算：¥${prefs.totalBudget}（含交通、住宿、餐饮、景点）

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
  userRequest: string
): string {
  return `你是旅行规划助手。用户有以下调整请求：

"${userRequest}"

当前行程：
${currentPlan}

请只修改受影响的部分，保持其他内容不变。以相同的 JSON 格式返回完整的修改后行程。`
}
```

- [ ] **Step 5: Run test to verify it passes**

```bash
npm test -- claude.test.ts
```

Expected: PASS — 4 tests passing

- [ ] **Step 6: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/lib/claude.ts web/src/__tests__/lib/claude.test.ts web/jest.config.ts
git commit -m "feat: add Claude API client and prompt builder"
```

---

## Task 4: Plan Generation API Route (Streaming)

**Files:**
- Create: `web/src/app/api/plan/generate/route.ts`
- Create: `web/src/lib/planStore.ts`

- [ ] **Step 1: Create the API route**

Create `web/src/app/api/plan/generate/route.ts`:

```typescript
import { NextRequest } from "next/server"
import { anthropic, buildPlanPrompt, buildAdjustmentPrompt } from "@/lib/claude"
import { UserPreferences, TravelPlan } from "@/lib/types"
import { nanoid } from "nanoid"

export async function POST(req: NextRequest) {
  const body = await req.json()
  const { preferences, currentPlan, adjustment } = body as {
    preferences?: UserPreferences
    currentPlan?: string
    adjustment?: string
  }

  const prompt =
    currentPlan && adjustment
      ? buildAdjustmentPrompt(currentPlan, adjustment)
      : buildPlanPrompt(preferences!)

  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    async start(controller) {
      try {
        const response = await anthropic.messages.stream({
          model: "claude-sonnet-4-6",
          max_tokens: 4096,
          messages: [{ role: "user", content: prompt }],
        })

        for await (const chunk of response) {
          if (
            chunk.type === "content_block_delta" &&
            chunk.delta.type === "text_delta"
          ) {
            controller.enqueue(encoder.encode(chunk.delta.text))
          }
        }

        controller.close()
      } catch (err) {
        controller.error(err)
      }
    },
  })

  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Transfer-Encoding": "chunked",
    },
  })
}
```

- [ ] **Step 2: Install nanoid**

```bash
cd ~/Projects/travel-planner/web
npm install nanoid
```

- [ ] **Step 3: Create plan store (localStorage)**

Create `web/src/lib/planStore.ts`:

```typescript
import { TravelPlan } from "./types"

const PLANS_KEY = "travel_plans"

export function savePlan(plan: TravelPlan): void {
  if (typeof window === "undefined") return
  const plans = getPlans()
  plans[plan.id] = plan
  localStorage.setItem(PLANS_KEY, JSON.stringify(plans))
}

export function getPlan(id: string): TravelPlan | null {
  if (typeof window === "undefined") return null
  const plans = getPlans()
  return plans[id] ?? null
}

export function getPlans(): Record<string, TravelPlan> {
  if (typeof window === "undefined") return {}
  try {
    return JSON.parse(localStorage.getItem(PLANS_KEY) ?? "{}")
  } catch {
    return {}
  }
}

export function deletePlan(id: string): void {
  if (typeof window === "undefined") return
  const plans = getPlans()
  delete plans[id]
  localStorage.setItem(PLANS_KEY, JSON.stringify(plans))
}
```

- [ ] **Step 4: Test the API route manually**

Start the dev server:

```bash
cd ~/Projects/travel-planner/web
npm run dev
```

In a new terminal, test the route:

```bash
curl -X POST http://localhost:3000/api/plan/generate \
  -H "Content-Type: application/json" \
  -d '{
    "preferences": {
      "destination": "上海",
      "departureCity": "北京",
      "departureDate": "2026-05-10",
      "days": 2,
      "totalBudget": 3000,
      "accommodationDescription": "市中心精品酒店",
      "experienceDescription": "外滩和本地美食"
    }
  }'
```

Expected: Streaming JSON text appears in terminal, starting with `{` and ending with `}`

- [ ] **Step 5: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/app/api/ web/src/lib/planStore.ts
git commit -m "feat: add streaming plan generation API route"
```

---

## Task 5: UI Base Components

**Files:**
- Create: `web/src/components/ui/Button.tsx`
- Create: `web/src/components/ui/TextArea.tsx`

- [ ] **Step 1: Create Button component**

Create `web/src/components/ui/Button.tsx`:

```typescript
import { ButtonHTMLAttributes, ReactNode } from "react"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost"
  children: ReactNode
}

export function Button({
  variant = "primary",
  children,
  className = "",
  ...props
}: ButtonProps) {
  const base = "px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
  const variants = {
    primary: "bg-blue-600 text-white hover:bg-blue-700",
    secondary: "bg-gray-100 text-gray-800 hover:bg-gray-200",
    ghost: "text-blue-600 hover:bg-blue-50",
  }

  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  )
}
```

- [ ] **Step 2: Create TextArea component**

Create `web/src/components/ui/TextArea.tsx`:

```typescript
import { TextareaHTMLAttributes } from "react"

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string
  hint?: string
}

export function TextArea({ label, hint, className = "", ...props }: TextAreaProps) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-gray-700">{label}</label>
      {hint && <p className="text-xs text-gray-400">{hint}</p>}
      <textarea
        className={`w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 placeholder:text-gray-400 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 resize-none ${className}`}
        {...props}
      />
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/components/ui/
git commit -m "feat: add base UI components (Button, TextArea)"
```

---

## Task 6: Home Page — Search Form

**Files:**
- Create: `web/src/components/search/SearchForm.tsx`
- Modify: `web/src/app/page.tsx`

- [ ] **Step 1: Create SearchForm component**

Create `web/src/components/search/SearchForm.tsx`:

```typescript
"use client"

import { useState, FormEvent } from "react"
import { useRouter } from "next/navigation"
import { UserPreferences, TravelPlan } from "@/lib/types"
import { savePlan } from "@/lib/planStore"
import { Button } from "@/components/ui/Button"
import { TextArea } from "@/components/ui/TextArea"
import { nanoid } from "nanoid"

export function SearchForm() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState<UserPreferences>({
    destination: "",
    departureCity: "",
    departureDate: "",
    days: 3,
    totalBudget: 5000,
    accommodationDescription: "",
    experienceDescription: "",
  })

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)

    try {
      const res = await fetch("/api/plan/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preferences: form }),
      })

      if (!res.ok) throw new Error("生成失败，请重试")
      if (!res.body) throw new Error("无响应数据")

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let raw = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        raw += decoder.decode(value, { stream: true })
      }

      // Extract JSON from the response (Claude may wrap it in markdown code blocks)
      const jsonMatch = raw.match(/\{[\s\S]*\}/)
      if (!jsonMatch) throw new Error("无法解析行程数据")

      const planData = JSON.parse(jsonMatch[0])
      const plan: TravelPlan = {
        id: nanoid(),
        preferences: form,
        days: planData.days,
        budget: planData.budget,
        tips: planData.tips,
        createdAt: new Date().toISOString(),
      }

      savePlan(plan)
      router.push(`/plan/${plan.id}`)
    } catch (err) {
      alert(err instanceof Error ? err.message : "发生错误，请重试")
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6 w-full max-w-xl">
      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">目的地</label>
          <input
            required
            type="text"
            placeholder="例：上海、京都、巴黎"
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={form.destination}
            onChange={(e) => setForm({ ...form, destination: e.target.value })}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">出发城市</label>
          <input
            required
            type="text"
            placeholder="例：北京"
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={form.departureCity}
            onChange={(e) => setForm({ ...form, departureCity: e.target.value })}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">出发日期</label>
          <input
            required
            type="date"
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={form.departureDate}
            onChange={(e) => setForm({ ...form, departureDate: e.target.value })}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">旅行天数</label>
          <input
            required
            type="number"
            min={1}
            max={30}
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={form.days}
            onChange={(e) => setForm({ ...form, days: Number(e.target.value) })}
          />
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">总预算</label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">¥</span>
          <input
            required
            type="number"
            min={100}
            placeholder="5000"
            className="w-full rounded-lg border border-gray-200 pl-7 pr-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={form.totalBudget || ""}
            onChange={(e) => setForm({ ...form, totalBudget: Number(e.target.value) })}
          />
        </div>
        <p className="text-xs text-gray-400">含交通、住宿、餐饮、景点</p>
      </div>

      <TextArea
        label="你对住宿有什么期待？"
        hint="用你自己的话描述，不必选择类别"
        placeholder="例：想住在森林里的小木屋，最好有壁炉，能听到虫鸣声…"
        rows={3}
        required
        value={form.accommodationDescription}
        onChange={(e) => setForm({ ...form, accommodationDescription: e.target.value })}
      />

      <TextArea
        label="这次旅行你最想体验什么？"
        hint="可以包括想去的地方、想做的事、想要的感觉"
        placeholder="例：想去当地人才知道的小馆子，不想跟团，希望有一个下午什么都不做，就坐在海边发呆…"
        rows={4}
        required
        value={form.experienceDescription}
        onChange={(e) => setForm({ ...form, experienceDescription: e.target.value })}
      />

      <Button type="submit" disabled={loading} className="w-full py-3 text-base">
        {loading ? "AI 正在规划中…" : "让 AI 帮我规划 →"}
      </Button>
    </form>
  )
}
```

- [ ] **Step 2: Update home page**

Replace `web/src/app/page.tsx` with:

```typescript
import { SearchForm } from "@/components/search/SearchForm"

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-slate-50 flex flex-col items-center justify-center px-4 py-16">
      <div className="mb-10 text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-3">
          去哪儿？
        </h1>
        <p className="text-gray-500 text-lg">
          告诉 AI 你的旅行想法，它来帮你变成清晰的计划
        </p>
      </div>
      <SearchForm />
    </main>
  )
}
```

- [ ] **Step 3: Start dev server and visually verify the form**

```bash
cd ~/Projects/travel-planner/web
npm run dev
```

Open http://localhost:3000 — you should see:
- Headline "去哪儿？"
- Two-column grid: 目的地 + 出发城市
- Two-column grid: 出发日期 + 旅行天数
- 总预算 with ¥ prefix
- Two large text areas for accommodation and experience
- Blue submit button

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/components/search/ web/src/app/page.tsx
git commit -m "feat: add home page search form with natural language inputs"
```

---

## Task 7: usePlan Hook

**Files:**
- Create: `web/src/hooks/usePlan.ts`

- [ ] **Step 1: Create hook**

Create `web/src/hooks/usePlan.ts`:

```typescript
"use client"

import { useState, useCallback } from "react"
import { TravelPlan, ChatMessage } from "@/lib/types"
import { savePlan } from "@/lib/planStore"
import { nanoid } from "nanoid"

export function usePlan(initialPlan: TravelPlan) {
  const [plan, setPlan] = useState<TravelPlan>(initialPlan)
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: `你的 ${plan.preferences.days} 天${plan.preferences.destination}行程已生成！你可以告诉我任何调整，比如「把第二天改成轻松一点的」或「换一个便宜的住宿」。`,
      timestamp: new Date().toISOString(),
    },
  ])
  const [isGenerating, setIsGenerating] = useState(false)

  const sendAdjustment = useCallback(
    async (userMessage: string) => {
      const userMsg: ChatMessage = {
        role: "user",
        content: userMessage,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMsg])
      setIsGenerating(true)

      try {
        const res = await fetch("/api/plan/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            currentPlan: JSON.stringify(plan.days),
            adjustment: userMessage,
          }),
        })

        if (!res.body) throw new Error("无响应")

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let raw = ""

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          raw += decoder.decode(value, { stream: true })
        }

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

        const assistantMsg: ChatMessage = {
          role: "assistant",
          content: "已按你的要求更新行程，右侧已同步刷新。还有什么需要调整的吗？",
          timestamp: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, assistantMsg])
      } catch {
        const errMsg: ChatMessage = {
          role: "assistant",
          content: "调整时出现问题，请再试一次。",
          timestamp: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, errMsg])
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
git commit -m "feat: add usePlan hook for plan state and AI adjustment"
```

---

## Task 8: Plan Page — Itinerary + AI Chat

**Files:**
- Create: `web/src/components/plan/ActivityCard.tsx`
- Create: `web/src/components/plan/DayCard.tsx`
- Create: `web/src/components/plan/ItineraryPanel.tsx`
- Create: `web/src/components/plan/AIChatPanel.tsx`
- Create: `web/src/app/plan/[id]/page.tsx`

- [ ] **Step 1: Create ActivityCard**

Create `web/src/components/plan/ActivityCard.tsx`:

```typescript
import { Activity } from "@/lib/types"

const typeColors: Record<Activity["type"], string> = {
  attraction: "bg-blue-100 text-blue-700",
  food: "bg-orange-100 text-orange-700",
  transport: "bg-green-100 text-green-700",
  hotel: "bg-purple-100 text-purple-700",
  free: "bg-gray-100 text-gray-600",
}

const typeLabels: Record<Activity["type"], string> = {
  attraction: "景点",
  food: "餐饮",
  transport: "交通",
  hotel: "住宿",
  free: "自由",
}

interface ActivityCardProps {
  activity: Activity
}

export function ActivityCard({ activity }: ActivityCardProps) {
  return (
    <div className="flex gap-3 p-3 rounded-lg bg-white border border-gray-100 hover:border-gray-200 transition-colors">
      <div className="flex flex-col items-center gap-1 min-w-[48px]">
        <span className="text-xs font-medium text-gray-500">{activity.time}</span>
        {activity.endTime && (
          <span className="text-xs text-gray-300">{activity.endTime}</span>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${typeColors[activity.type]}`}>
            {typeLabels[activity.type]}
          </span>
          {activity.estimatedCost !== undefined && (
            <span className="text-xs text-gray-400">¥{activity.estimatedCost}</span>
          )}
        </div>
        <p className="font-medium text-gray-900 text-sm">{activity.place}</p>
        <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{activity.description}</p>
        {activity.tips && (
          <p className="text-xs text-amber-600 mt-1 bg-amber-50 px-2 py-1 rounded">
            💡 {activity.tips}
          </p>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create DayCard**

Create `web/src/components/plan/DayCard.tsx`:

```typescript
import { DayPlan } from "@/lib/types"
import { ActivityCard } from "./ActivityCard"

interface DayCardProps {
  dayPlan: DayPlan
}

export function DayCard({ dayPlan }: DayCardProps) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-3 mb-3">
        <span className="bg-blue-600 text-white text-xs font-bold px-3 py-1 rounded-full">
          Day {dayPlan.day}
        </span>
        <span className="font-semibold text-gray-800">{dayPlan.title}</span>
        <span className="ml-auto text-xs text-gray-400">预计 ¥{dayPlan.totalCost}</span>
      </div>

      <div className="flex flex-col gap-2 pl-2 border-l-2 border-blue-100">
        {dayPlan.activities.map((activity) => (
          <ActivityCard key={activity.id} activity={activity} />
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create ItineraryPanel**

Create `web/src/components/plan/ItineraryPanel.tsx`:

```typescript
import { TravelPlan } from "@/lib/types"
import { DayCard } from "./DayCard"

interface ItineraryPanelProps {
  plan: TravelPlan
}

export function ItineraryPanel({ plan }: ItineraryPanelProps) {
  const { preferences, days, budget, tips } = plan

  return (
    <div className="flex flex-col gap-4 h-full overflow-y-auto p-6">
      <div className="bg-gradient-to-r from-blue-600 to-blue-400 rounded-xl p-5 text-white">
        <p className="text-xs opacity-75 mb-1">{preferences.departureCity} → {preferences.destination}</p>
        <h2 className="text-xl font-bold">{preferences.destination} · {preferences.days}日游</h2>
        <p className="text-sm opacity-80 mt-1">{preferences.departureDate} 出发 · 预算 ¥{preferences.totalBudget}</p>
      </div>

      {days.map((day) => (
        <DayCard key={day.day} dayPlan={day} />
      ))}

      <div className="mt-2 p-4 bg-amber-50 rounded-xl border border-amber-100">
        <h3 className="font-semibold text-gray-800 mb-2 text-sm">实用提示</h3>
        <ul className="flex flex-col gap-1">
          {tips.map((tip, i) => (
            <li key={i} className="text-xs text-gray-600 flex gap-2">
              <span className="text-amber-500 flex-shrink-0">•</span>
              {tip}
            </li>
          ))}
        </ul>
      </div>

      <div className="p-4 bg-gray-50 rounded-xl border border-gray-100">
        <h3 className="font-semibold text-gray-800 mb-3 text-sm">费用预算</h3>
        {Object.entries({
          交通: budget.transport,
          住宿: budget.accommodation,
          餐饮: budget.food,
          景点: budget.attractions,
          其他: budget.other,
        }).map(([label, amount]) => (
          <div key={label} className="flex justify-between text-xs text-gray-600 mb-1">
            <span>{label}</span>
            <span>¥{amount}</span>
          </div>
        ))}
        <div className="flex justify-between text-sm font-bold text-gray-900 mt-2 pt-2 border-t border-gray-200">
          <span>合计</span>
          <span>¥{budget.total}</span>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create AIChatPanel**

Create `web/src/components/plan/AIChatPanel.tsx`:

```typescript
"use client"

import { useState, useRef, useEffect } from "react"
import { ChatMessage } from "@/lib/types"
import { Button } from "@/components/ui/Button"

interface AIChatPanelProps {
  messages: ChatMessage[]
  isGenerating: boolean
  onSend: (message: string) => void
}

export function AIChatPanel({ messages, isGenerating, onSend }: AIChatPanelProps) {
  const [input, setInput] = useState("")
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  function handleSend() {
    const text = input.trim()
    if (!text || isGenerating) return
    setInput("")
    onSend(text)
  }

  return (
    <div className="flex flex-col h-full bg-gray-50 border-r border-gray-100">
      <div className="p-4 border-b border-gray-100 bg-white">
        <h2 className="font-semibold text-gray-800 text-sm">AI 助手</h2>
        <p className="text-xs text-gray-400 mt-0.5">告诉我你想怎么调整行程</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-blue-600 text-white rounded-br-sm"
                  : "bg-white text-gray-800 border border-gray-100 rounded-bl-sm"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {isGenerating && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-4 py-2.5">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="p-4 border-t border-gray-100 bg-white">
        <div className="flex gap-2">
          <textarea
            rows={2}
            placeholder="例：把第二天改成轻松一点的安排…"
            className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm resize-none focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isGenerating}
            className="self-end"
          >
            发送
          </Button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Create Plan page**

Create `web/src/app/plan/[id]/page.tsx`:

```typescript
"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { TravelPlan } from "@/lib/types"
import { getPlan } from "@/lib/planStore"
import { usePlan } from "@/hooks/usePlan"
import { ItineraryPanel } from "@/components/plan/ItineraryPanel"
import { AIChatPanel } from "@/components/plan/AIChatPanel"

export default function PlanPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [initialPlan, setInitialPlan] = useState<TravelPlan | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const plan = getPlan(id)
    if (!plan) {
      router.push("/")
      return
    }
    setInitialPlan(plan)
    setLoading(false)
  }, [id, router])

  if (loading || !initialPlan) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400">
        加载中…
      </div>
    )
  }

  return <PlanView initialPlan={initialPlan} />
}

function PlanView({ initialPlan }: { initialPlan: TravelPlan }) {
  const { plan, messages, isGenerating, sendAdjustment } = usePlan(initialPlan)

  return (
    <div className="h-screen flex overflow-hidden">
      <div className="w-80 flex-shrink-0 flex flex-col overflow-hidden">
        <AIChatPanel
          messages={messages}
          isGenerating={isGenerating}
          onSend={sendAdjustment}
        />
      </div>
      <div className="flex-1 overflow-hidden">
        <ItineraryPanel plan={plan} />
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Verify the full flow in browser**

With the dev server running at http://localhost:3000:

1. Fill in the home form (e.g., 上海, 北京, any date, 3 days, ¥4000)
2. Fill both text areas with something descriptive
3. Click「让 AI 帮我规划」
4. Wait for loading (10-30 seconds for Claude to respond)
5. You should be redirected to `/plan/[id]`
6. Left panel: AI chat with greeting message
7. Right panel: day-by-day itinerary with color-coded activities

- [ ] **Step 7: Commit**

```bash
cd ~/Projects/travel-planner
git add web/src/components/plan/ web/src/app/plan/
git commit -m "feat: add plan page with itinerary view and AI chat panel"
```

---

## Task 9: Root Layout & Global Styles

**Files:**
- Modify: `web/src/app/layout.tsx`

- [ ] **Step 1: Update root layout**

Replace `web/src/app/layout.tsx` with:

```typescript
import type { Metadata } from "next"
import { Noto_Sans_SC } from "next/font/google"
import "./globals.css"

const notoSans = Noto_Sans_SC({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
})

export const metadata: Metadata = {
  title: "旅行规划 AI",
  description: "告诉 AI 你的旅行想法，它来帮你变成清晰的计划",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body className={notoSans.className}>{children}</body>
    </html>
  )
}
```

- [ ] **Step 2: Final end-to-end test**

1. Run `npm run dev`
2. Go to http://localhost:3000
3. Complete a full trip planning session
4. Verify the plan page loads and AI chat works
5. Type an adjustment like「把第一天改成慢节奏」and confirm the itinerary updates

- [ ] **Step 3: Build check**

```bash
cd ~/Projects/travel-planner/web
npm run build
```

Expected: Build completes with no errors.

- [ ] **Step 4: Final commit**

```bash
cd ~/Projects/travel-planner
git add web/src/app/layout.tsx
git commit -m "feat: update root layout with Chinese font and metadata"
```

---

## Done — What You Have

A fully working travel planner web app where:
- Users describe their trip in **natural language** (no dropdowns or checkboxes)
- **Claude generates** a structured day-by-day itinerary based on their preferences
- Users can **chat with AI** to adjust the plan conversationally
- Plans are saved to **localStorage** (persist across page reloads)

**Next plan:** Price comparison page + Amadeus flight API + hotel search + profile page.
