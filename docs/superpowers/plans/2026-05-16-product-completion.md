# Travel Planner — Product Completion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the functional MVP into a premium, usable single-city travel planning product with excellent UI/UX across all four pages.

**Architecture:** All work is frontend-only (`web/`). The Python FastAPI + LangGraph backend (`api/`) is solid and unchanged. No new routes, schemas, or API contracts are introduced—only existing types and endpoints are consumed. The product-polish branch (`codex/product-polish`) is the working branch.

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS v4, Vitest, Playwright

---

## Branch & Working Directory

All paths are relative to the **product-polish worktree root**:
`.worktrees/product-polish/` (git branch `codex/product-polish`)

Run commands from inside `web/`:
```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/product-polish/web
```

Run tests:
```bash
npm run test          # Vitest unit tests
npm run test:e2e      # Playwright e2e
npm run typecheck     # tsc --noEmit
```

---

## ⚠️ Reality Sync (2026-05-16)

This plan was first drafted as if the `codex/product-polish` worktree were a clean baseline. **It is not.** The sections below were audited against the live worktree on 2026-05-16 and corrected.

### What's already on the branch

The branch carries a substantial *separate* polish effort — a story-led result page (commits such as `feat: compose story led itinerary view`, `fix: keep hero texture behind image layer`, plus result-page support sections). That work touches many files this plan also targets, but it is **not** an execution of the tasks below.

### Uncommitted state — PREFLIGHT GATE

The worktree has **47 uncommitted files** (`git status --short`) from that separate effort, including most files this plan modifies: `DiscoveryCard.tsx`, `PlanningProgress.tsx`, `AdjustmentPanel.tsx`, `HomeStart.tsx`, `ItineraryDayCard.tsx`, and the trips / preferences pages.

**Before starting Task 1 you MUST:**

1. Run `git status --short` and show the full list to the user.
2. Ask the user how to handle the dirty tree — commit it as a baseline, stash it, or stop. Do not guess.
3. Do **not** proceed with a dirty tree. The per-task pattern below is `git add <file> && git commit`; if a target file still carries unrelated uncommitted changes, that commit silently bundles someone else's work under this task's message.

### None of Tasks 1–11 are done

Despite the dirty tree, no plan task is complete: `globals.css` has no design tokens; `Skeleton.tsx`, `DiscoveryCardSkeleton.tsx`, `Toast.tsx`, and `useToast.ts` do not exist; `DiscoveryCard` still shows the `已验证 / 部分验证 / 文本线索` badge; `PlanningProgress` is still a `grid-cols-4` box grid.

### Corrections applied below

- **Every "Replace the entire content of X"** is downgraded to "read X first and reconcile any uncommitted changes before replacing" — full-file replacement would destroy the in-progress result-page work in those files.
- **Task 4** — `DiscoveryCardGrid` already exists with `selectedIds: string[]` (not `Set<string>`), and `DiscoveryBoard`'s aside already renders a selection count, density warning, and a gated continue button. The selection-banner half of the original task is **superseded**; only the skeleton-loading half remains. Task 4 is rewritten accordingly.
- **Task 7** — the original HomeStart rewrite dropped the `language` prop on `<RecentTrips>` (the real component requires it) and dropped `switchLabel` from `copy`. Both would fail `typecheck`. Code block corrected.
- **Task 11** — the original invented a `transport_mode` field with values `public_transit / taxi_rideshare / mixed / walking`. No such field exists. The real field is `intercity_transport_preference` (default `"rail"`, options `rail / flight / flexible`), rendered through a `Select` labeled "城际交通". Task rewritten against the real form.
- **Task 13** — the worktree-removal step is dropped; the user's standing preference is to manage branches with `git checkout`, not worktrees.

---

## 最终产品构想 (Final Product Vision)

这个产品应该感觉像一位高效的旅行顾问：流程清晰、判断有力、呈现精美。

**四页流程的情绪弧线：**
1. **首页（Intake）** — 自信、清晰。用户一眼知道这是做什么的，两分钟填完出发。
2. **探索（Discovery）** — 好奇、愉悦。AI 推荐的地方以视觉卡片呈现，选卡片像在整理心愿单。
3. **规划中（Planning）** — 托付感。用户看到 AI 在认真工作，有清晰的阶段反馈。
4. **行程结果（Trips）** — 惊喜感。结果不是表格，是一个有叙事感的故事线，调整也是自然的对话。

---

## File Map

### Modified files (existing)

| File | Change |
|---|---|
| `web/src/components/discovery/DiscoveryCard.tsx` | Larger image, selection overlay, remove jargon badge |
| `web/src/components/discovery/DiscoveryCardGrid.tsx` | Selection count banner, confirm CTA, skeleton state |
| `web/src/components/discovery/DiscoveryBoard.tsx` | Category section headers, skeleton integration |
| `web/src/components/itinerary/PlanningProgress.tsx` | Animated stepper, pulse indicator, live message |
| `web/src/components/chat/AdjustmentPanel.tsx` | Chat history bubbles, typing indicator, loading state |
| `web/src/components/itinerary/ItineraryDayCard.tsx` | Timeline line for segments, better segment type labels |
| `web/src/components/intake/HomeStart.tsx` | Two-column hero layout with gradient background |
| `web/src/components/intake/HardConstraintForm.tsx` | Better validation states, character limits |
| `web/src/components/itinerary/CompanionRail.tsx` | Mobile bottom-sheet behavior, sticky on desktop |
| `web/src/app/trips/[sessionId]/page.tsx` | Mobile CompanionRail drawer toggle |
| `web/src/globals.css` | CSS custom properties for consistent tokens |

### Created files (new)

| File | Purpose |
|---|---|
| `web/src/components/ui/Skeleton.tsx` | Reusable skeleton loading block |
| `web/src/components/discovery/DiscoveryCardSkeleton.tsx` | Skeleton for discovery card |
| `web/src/components/ui/Toast.tsx` | Simple toast notification |
| `web/src/components/ui/useToast.ts` | Toast state hook |

---

## Task 1: Design Token Baseline

**Goal:** Establish CSS custom properties so all components share consistent radius, shadow, and timing values. No visual change—just variables to use in later tasks.

**Files:**
- Modify: `web/src/app/globals.css`

- [ ] **Step 1: Add design tokens**

Open `web/src/app/globals.css` and append after the existing Tailwind directives:

```css
:root {
  --radius-card: 0.75rem;
  --radius-badge: 0.375rem;
  --shadow-card: 0 1px 3px 0 rgb(0 0 0 / 0.08), 0 1px 2px -1px rgb(0 0 0 / 0.05);
  --shadow-card-hover: 0 4px 12px 0 rgb(0 0 0 / 0.10), 0 2px 4px -1px rgb(0 0 0 / 0.06);
  --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-base: 220ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: 350ms cubic-bezier(0.4, 0, 0.2, 1);
}
```

- [ ] **Step 2: Verify no build error**

```bash
cd web && npm run typecheck
```

Expected: exits 0

- [ ] **Step 3: Commit**

```bash
git add web/src/app/globals.css
git commit -m "style: add design token custom properties"
```

---

## Task 2: Skeleton Loading Block

**Goal:** Create a reusable skeleton block so discovery cards and other loading states look polished.

**Files:**
- Create: `web/src/components/ui/Skeleton.tsx`
- Create: `web/src/components/discovery/DiscoveryCardSkeleton.tsx`

- [ ] **Step 1: Write the Skeleton component**

Create `web/src/components/ui/Skeleton.tsx`:

```tsx
interface SkeletonProps {
  className?: string
}

export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse rounded-md bg-slate-200 ${className}`}
    />
  )
}
```

- [ ] **Step 2: Write DiscoveryCardSkeleton**

Create `web/src/components/discovery/DiscoveryCardSkeleton.tsx`:

```tsx
import { Skeleton } from "@/components/ui/Skeleton"

export function DiscoveryCardSkeleton() {
  return (
    <div className="flex min-h-64 flex-col overflow-hidden rounded-[var(--radius-card)] border border-slate-200 bg-white shadow-[var(--shadow-card)]">
      <Skeleton className="h-40 w-full rounded-none" />
      <div className="flex flex-1 flex-col gap-3 p-4">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <div className="flex gap-2">
          <Skeleton className="h-5 w-12" />
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-5 w-10" />
        </div>
        <div className="mt-auto flex items-center justify-between">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-9 w-16 rounded-md" />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify types**

```bash
cd web && npm run typecheck
```

Expected: exits 0

- [ ] **Step 4: Commit**

```bash
git add web/src/components/ui/Skeleton.tsx web/src/components/discovery/DiscoveryCardSkeleton.tsx
git commit -m "feat: add skeleton loading components"
```

---

## Task 3: Discovery Card Visual Excellence

**Goal:** Make each discovery card visually compelling—larger image, clear selection state with overlay, remove jargon badges.

**Files:**
- Modify: `web/src/components/discovery/DiscoveryCard.tsx`

The current card has a small `h-28` image and a selection button. The new design:
- `aspect-video` image area (16:9 proportions, ~10rem on typical card width)
- When `selected`: teal ring around the entire card + green checkmark badge in corner
- When not selected: normal card with hover shadow lift
- Remove "已验证/部分验证/文本线索" badge — users don't need to know enrichment status
- Show a colored category chip instead
- Cost signal uses `·` dot bullets not a free-text label

**Current state:** The file currently shows an `已验证 / 部分验证 / 文本线索` status badge, gates the image on `card.enrichment_status !== "minimal"`, and uses a local `formatCostSignal` helper. It also carries uncommitted changes.

- [ ] **Step 1: Rewrite DiscoveryCard**

Read the current file first and confirm (against the Reality Sync preflight gate) that no uncommitted changes will be lost. Then replace its content with:

```tsx
"use client"

import type { DiscoveryCard as DiscoveryCardType } from "@/lib/types"

const CATEGORY_COLORS: Record<string, string> = {
  attraction: "bg-violet-50 text-violet-700",
  food: "bg-amber-50 text-amber-700",
  neighborhood: "bg-teal-50 text-teal-700",
  activity: "bg-blue-50 text-blue-700",
  accommodation: "bg-rose-50 text-rose-700",
}

const CATEGORY_LABELS: Record<string, string> = {
  attraction: "景点",
  food: "餐饮",
  neighborhood: "街区",
  activity: "活动",
  accommodation: "住宿",
}

const COST_DOTS: Record<string, string> = {
  free: "免费",
  low: "·",
  medium: "··",
  high: "···",
}

interface DiscoveryCardProps {
  card: DiscoveryCardType
  selected: boolean
  onToggle: (id: string) => void
}

export function DiscoveryCard({ card, selected, onToggle }: DiscoveryCardProps) {
  const categoryColor = CATEGORY_COLORS[card.category] ?? "bg-slate-50 text-slate-700"
  const categoryLabel = CATEGORY_LABELS[card.category] ?? card.category
  const costDots = COST_DOTS[card.cost_signal] ?? card.cost_signal

  return (
    <article
      className={`
        group relative flex min-h-64 flex-col overflow-hidden rounded-[var(--radius-card)] border bg-white
        shadow-[var(--shadow-card)] transition-[box-shadow,border-color] duration-[var(--transition-base)]
        ${selected
          ? "border-teal-500 shadow-[0_0_0_2px_theme(colors.teal.500)]"
          : "border-slate-200 hover:shadow-[var(--shadow-card-hover)]"
        }
      `}
    >
      {/* Image area */}
      <div className="relative aspect-video overflow-hidden bg-slate-100">
        {card.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={card.image_url}
            alt=""
            className="h-full w-full object-cover transition-transform duration-[var(--transition-slow)] group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200">
            <span className="text-3xl">{getCategoryEmoji(card.category)}</span>
          </div>
        )}

        {/* Category chip */}
        <span
          className={`absolute left-3 top-3 rounded-[var(--radius-badge)] px-2 py-0.5 text-xs font-semibold ${categoryColor}`}
        >
          {categoryLabel}
        </span>

        {/* Selected checkmark badge */}
        {selected && (
          <span
            aria-label="已选择"
            className="absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-full bg-teal-500 text-white shadow-sm"
          >
            <CheckIcon />
          </span>
        )}
      </div>

      {/* Card body */}
      <div className="flex flex-1 flex-col gap-3 p-4">
        <h3 className="break-words text-base font-semibold leading-snug text-slate-950">
          {card.name}
        </h3>
        <p className="line-clamp-3 text-sm leading-6 text-slate-600">{card.reason}</p>

        {card.reservation_hint && (
          <p className="rounded-md bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
            ⚠ {card.reservation_hint}
          </p>
        )}

        {card.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {card.tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="rounded-[var(--radius-badge)] bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="mt-auto flex items-center justify-between gap-3 pt-1">
          <span className="text-sm font-medium text-slate-500">{costDots}</span>
          <button
            type="button"
            aria-label={`${selected ? "取消选择" : "选择"} ${card.name}`}
            onClick={() => onToggle(card.id)}
            className={`
              h-9 rounded-md px-4 text-sm font-semibold transition-colors duration-[var(--transition-fast)]
              ${selected
                ? "bg-teal-600 text-white hover:bg-teal-700"
                : "border border-slate-300 bg-white text-slate-800 hover:bg-slate-50"
              }
            `}
          >
            {selected ? "已选 ✓" : "选择"}
          </button>
        </div>
      </div>
    </article>
  )
}

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function getCategoryEmoji(category: string): string {
  const emojis: Record<string, string> = {
    attraction: "🏛",
    food: "🍜",
    neighborhood: "🏘",
    activity: "🎭",
    accommodation: "🏨",
  }
  return emojis[category] ?? "📍"
}
```

- [ ] **Step 2: Run tests**

```bash
cd web && npm run test -- --reporter=verbose 2>&1 | grep -E "PASS|FAIL|✓|✗"
```

Expected: no failures related to DiscoveryCard

- [ ] **Step 3: Type check**

```bash
cd web && npm run typecheck
```

Expected: exits 0

- [ ] **Step 4: Commit**

```bash
git add web/src/components/discovery/DiscoveryCard.tsx
git commit -m "feat: redesign discovery card with visual selection state and larger image"
```

---

## Task 4: Discovery Card Grid — Skeleton Loading

**Goal:** Show skeleton cards while discovery output is loading.

> **Superseded:** The original Task 4 also added a "selection count banner" and a confirm CTA to `DiscoveryCardGrid`. That is **already done** — `DiscoveryBoard`'s aside (`web/src/components/discovery/DiscoveryBoard.tsx`) renders the selection count, a density warning (`hasDensityWarning`), and a "继续设置偏好" button gated by `isContinueDisabled`. Do not duplicate it. Only the skeleton-loading half below remains.

**Current state:** `DiscoveryCardGrid` already exists with this signature — keep it:

```tsx
interface DiscoveryCardGridProps {
  cards: DiscoveryCardType[]
  selectedIds: string[]   // an array, NOT a Set
  onToggle: (id: string) => void
}
```

`DiscoveryBoard` builds `selectedIds` from `session.discovery_state?.selected_card_ids` and persists toggles via `onSelectionChange`. Do not change that contract.

**Files:**
- Modify: `web/src/components/discovery/DiscoveryCardGrid.tsx`
- Read: `web/src/app/discovery/[sessionId]/page.tsx` (to find the loading state)

- [ ] **Step 1: Add an optional `loading` prop to DiscoveryCardGrid**

Read `web/src/components/discovery/DiscoveryCardGrid.tsx` first. Add an optional `loading?: boolean` prop. When `loading` is true, render six `<DiscoveryCardSkeleton />` (from Task 2) instead of the cards. Keep the existing `selectedIds: string[]` signature and the existing grid classes (`grid gap-4 md:grid-cols-2 xl:grid-cols-3`).

```tsx
"use client"

import type { DiscoveryCard as DiscoveryCardType } from "@/lib/types"
import { DiscoveryCard } from "./DiscoveryCard"
import { DiscoveryCardSkeleton } from "./DiscoveryCardSkeleton"

interface DiscoveryCardGridProps {
  cards: DiscoveryCardType[]
  selectedIds: string[]
  onToggle: (id: string) => void
  loading?: boolean
}

export function DiscoveryCardGrid({
  cards,
  selectedIds,
  onToggle,
  loading = false,
}: DiscoveryCardGridProps) {
  const selected = new Set(selectedIds)
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {loading
        ? Array.from({ length: 6 }, (_, i) => <DiscoveryCardSkeleton key={i} />)
        : cards.map((card) => (
            <DiscoveryCard
              key={card.id}
              card={card}
              selected={selected.has(card.id)}
              onToggle={onToggle}
            />
          ))}
    </div>
  )
}
```

- [ ] **Step 2: Wire `loading` from the discovery page**

Read `web/src/app/discovery/[sessionId]/page.tsx`. `DiscoveryBoard` requires a fully-loaded `output: DiscoveryOutput`, so the skeleton most likely belongs in the page's *pre-`output`* loading branch rather than inside `DiscoveryBoard`. If the page already renders a placeholder while discovery is loading, swap it for `<DiscoveryCardGrid cards={[]} selectedIds={[]} onToggle={() => {}} loading />`. Use whichever wiring matches the existing loading pattern — do not invent a new one, and do not add `loading`/`onConfirm` props to `DiscoveryBoard`.

- [ ] **Step 3: Type check**

```bash
cd web && npm run typecheck
```

Expected: exits 0

- [ ] **Step 4: Commit**

```bash
git add web/src/components/discovery/DiscoveryCardGrid.tsx web/src/app/discovery/
git commit -m "feat: add skeleton loading state to discovery card grid"
```

---

## Task 5: Planning Progress — Animated Stepper

**Goal:** Replace the static grid of colored boxes with an animated linear stepper that pulses on the active step and shows checkmarks on completed steps.

**Files:**
- Modify: `web/src/components/itinerary/PlanningProgress.tsx`

The current component shows 4 boxes in a `grid-cols-4`. New design:
- Horizontal stepper (mobile: vertical stack)
- Active step: pulsing teal ring + spinning arc
- Completed step: solid teal circle with checkmark
- Pending step: slate circle
- Below stepper: live message from `latest.message`
- Only visible when `active === true` or there are events

**Current state:** The file is a static `grid-cols-4` box grid with a `formatStatus` helper. Its `{ active, events }` prop signature already matches the new version. It carries uncommitted changes.

- [ ] **Step 1: Rewrite PlanningProgress**

Read the current file first and reconcile any uncommitted changes against the Reality Sync preflight gate. Then replace its content with:

```tsx
import type { PlanningProgressEvent } from "@/lib/types"

const STEPS = [
  { id: "stay",      label: "住宿区域", icon: "🏨" },
  { id: "transport", label: "交通方案", icon: "🚇" },
  { id: "planner",   label: "每日行程", icon: "📅" },
  { id: "validator", label: "预算校验", icon: "✅" },
] as const

type StepId = typeof STEPS[number]["id"]
type StepStatus = "pending" | "active" | "done" | "error"

function resolveStepStatus(
  stepId: StepId,
  events: PlanningProgressEvent[],
  activeStage: string | undefined,
  planning: boolean,
): StepStatus {
  const stepEvents = events.filter((e) => e.stage === stepId)
  const last = stepEvents.at(-1)
  if (last?.status === "finish" || last?.status === "completed") return "done"
  if (last?.status === "error" || last?.status === "failed") return "error"
  if (planning && activeStage === stepId) return "active"
  return "pending"
}

export function PlanningProgress({
  active,
  events = [],
}: {
  active: boolean
  events?: PlanningProgressEvent[]
}) {
  const latest = events.at(-1)
  const activeStage = active ? latest?.stage : undefined

  if (!active && events.length === 0) return null

  return (
    <section
      aria-label="规划进度"
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
    >
      <div className="mb-5 flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">
            AI 规划中
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">
            {active ? "正在为你生成行程…" : "规划完成"}
          </h2>
        </div>
        {active && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-700">
            <SpinnerIcon />
            生成中
          </span>
        )}
      </div>

      {/* Stepper */}
      <ol className="relative flex flex-col gap-4 sm:flex-row sm:gap-0">
        {STEPS.map((step, index) => {
          const status = resolveStepStatus(step.id, events, activeStage, active)
          const isLast = index === STEPS.length - 1

          return (
            <li key={step.id} className="flex flex-1 items-start gap-3 sm:flex-col sm:items-center sm:gap-2">
              {/* Circle + connector line */}
              <div className="flex flex-col items-center sm:flex-row sm:w-full">
                <StepCircle status={status} icon={step.icon} />
                {!isLast && (
                  <div
                    className={`
                      mx-2 hidden h-0.5 flex-1 sm:block
                      ${status === "done" ? "bg-teal-400" : "bg-slate-200"}
                      transition-colors duration-500
                    `}
                  />
                )}
              </div>
              <div className="pt-0.5 sm:pt-2 sm:text-center">
                <p className={`text-sm font-medium ${status === "pending" ? "text-slate-400" : "text-slate-900"}`}>
                  {step.label}
                </p>
              </div>
            </li>
          )
        })}
      </ol>

      {/* Live message */}
      {latest?.message && (
        <p className="mt-4 border-t border-slate-100 pt-4 text-sm text-slate-500">
          {latest.message}
        </p>
      )}
    </section>
  )
}

function StepCircle({ status, icon }: { status: StepStatus; icon: string }) {
  if (status === "done") {
    return (
      <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-teal-500 text-white shadow-sm">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M3 8l4 4 6-6" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    )
  }
  if (status === "active") {
    return (
      <span className="relative flex h-9 w-9 flex-shrink-0 items-center justify-center">
        <span className="absolute inset-0 animate-ping rounded-full bg-teal-200 opacity-75" />
        <span className="relative flex h-9 w-9 items-center justify-center rounded-full border-2 border-teal-500 bg-white text-base">
          {icon}
        </span>
      </span>
    )
  }
  if (status === "error") {
    return (
      <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border-2 border-red-400 bg-red-50 text-base">
        ✗
      </span>
    )
  }
  return (
    <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border-2 border-slate-200 bg-white text-base opacity-50">
      {icon}
    </span>
  )
}

function SpinnerIcon() {
  return (
    <svg className="animate-spin" width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}
```

- [ ] **Step 2: Run type check**

```bash
cd web && npm run typecheck
```

Expected: exits 0

- [ ] **Step 3: Commit**

```bash
git add web/src/components/itinerary/PlanningProgress.tsx
git commit -m "feat: redesign planning progress as animated stepper with pulse indicator"
```

---

## Task 6: Adjustment Panel — Chat History UI

**Goal:** Give the AdjustmentPanel a chat-style history so users can see their previous requests and the AI's responses. Add a typing indicator during processing.

**Files:**
- Modify: `web/src/components/chat/AdjustmentPanel.tsx`

**Current state:** The file is a simple form with a single `status` string (no chat history). It carries uncommitted changes.

- [ ] **Step 1: Rewrite AdjustmentPanel with chat history**

Read the current file first and reconcile any uncommitted changes against the Reality Sync preflight gate. Then replace its content with:

```tsx
"use client"

import { FormEvent, useRef, useState } from "react"
import { submitAdjustment, type AdjustmentResponse } from "@/lib/apiClient"
import type { PlanningSession } from "@/lib/types"
import { TypeCConfirmationCard } from "./TypeCConfirmationCard"

interface ChatMessage {
  role: "user" | "assistant"
  text: string
  timestamp: string
}

interface AdjustmentPanelProps {
  session: PlanningSession
  onSessionChange: (session: PlanningSession) => void
}

export function AdjustmentPanel({ session, onSessionChange }: AdjustmentPanelProps) {
  const [message, setMessage] = useState("")
  const [history, setHistory] = useState<ChatMessage[]>([])
  const [sending, setSending] = useState(false)
  const [pendingConfirmation, setPendingConfirmation] = useState<AdjustmentResponse | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function pushMessage(role: "user" | "assistant", text: string) {
    setHistory((prev) => [
      ...prev,
      { role, text, timestamp: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) },
    ])
  }

  async function send(action?: "replan" | "save_and_start_new" | "cancel") {
    const trimmed = message.trim()
    if (!trimmed && !action) return
    setSending(true)
    if (trimmed) {
      pushMessage("user", trimmed)
      setMessage("")
    }
    try {
      const response = await submitAdjustment({
        sessionId: session.session_id,
        message: trimmed,
        typeCAction: action,
      })
      onSessionChange(response.session)
      pushMessage("assistant", response.message)
      setPendingConfirmation(response.confirmation ? response : null)
    } catch {
      pushMessage("assistant", "调整失败，请重试。")
    } finally {
      setSending(false)
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await send()
  }

  const QUICK_PROMPTS = ["换一个景点", "调整预算分配", "缩短某天行程"]

  return (
    <section className="flex flex-col rounded-xl border border-slate-200 bg-white shadow-sm">
      {/* Header */}
      <header className="border-b border-slate-100 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-950">调整行程</h2>
        <p className="text-xs text-slate-500">告诉我哪里不满意，我来修改</p>
      </header>

      {/* Chat history */}
      {history.length > 0 && (
        <div className="max-h-64 overflow-y-auto px-4 py-3 space-y-3">
          {history.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-2 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
            >
              <div
                className={`
                  max-w-[85%] rounded-xl px-3 py-2 text-sm leading-6
                  ${msg.role === "user"
                    ? "bg-teal-600 text-white rounded-tr-sm"
                    : "bg-slate-100 text-slate-800 rounded-tl-sm"
                  }
                `}
              >
                <p>{msg.text}</p>
                <p className={`mt-1 text-[10px] ${msg.role === "user" ? "text-teal-100 text-right" : "text-slate-400"}`}>
                  {msg.timestamp}
                </p>
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {sending && (
            <div className="flex gap-2">
              <div className="rounded-xl rounded-tl-sm bg-slate-100 px-4 py-3">
                <TypingDots />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Quick prompts (only when no history) */}
      {history.length === 0 && !sending && (
        <div className="flex flex-wrap gap-2 px-4 py-3">
          {QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => setMessage(prompt)}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600 hover:bg-slate-100 transition-colors"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      {/* TypeC confirmation */}
      {pendingConfirmation?.confirmation && (
        <div className="px-4 py-3 border-t border-slate-100">
          <TypeCConfirmationCard
            confirmation={pendingConfirmation.confirmation}
            onAction={(action) => void send(action)}
          />
        </div>
      )}

      {/* Input form */}
      <form onSubmit={handleSubmit} className="border-t border-slate-100 p-3">
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                void send()
              }
            }}
            placeholder="描述你想调整的内容…"
            rows={2}
            disabled={sending}
            className="
              flex-1 resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm
              text-slate-950 placeholder:text-slate-400
              outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-50
              disabled:opacity-50
            "
          />
          <button
            type="submit"
            disabled={sending || !message.trim()}
            aria-label="发送"
            className="
              flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl
              bg-teal-600 text-white
              disabled:cursor-not-allowed disabled:opacity-40
              hover:bg-teal-700 transition-colors
            "
          >
            <SendIcon />
          </button>
        </div>
        <p className="mt-1.5 text-[10px] text-slate-400">Enter 发送 · Shift+Enter 换行</p>
      </form>
    </section>
  )
}

function TypingDots() {
  return (
    <span className="flex gap-1 items-center h-4" aria-label="AI 正在思考">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </span>
  )
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
```

- [ ] **Step 2: Type check**

```bash
cd web && npm run typecheck
```

Expected: exits 0

- [ ] **Step 3: Commit**

```bash
git add web/src/components/chat/AdjustmentPanel.tsx
git commit -m "feat: redesign adjustment panel as chat history with typing indicator"
```

---

## Task 7: Homepage Visual Identity

**Goal:** Give the homepage a clear visual identity so users immediately understand the product and trust it. The current layout is prose + form. The new layout uses a two-column split: left = brand statement, right = intake form card.

**Current state:** `HomeStart` already renders `HardConstraintForm` and `RecentTrips` with a language toggle. Two contracts the rewrite below MUST preserve, or `typecheck` fails:
- `<RecentTrips>` requires a `language` prop — `RecentTrips` is typed `{ sessions, language }`.
- The `copy` object keeps `switchLabel` (used as the toggle's `aria-label`) alongside `switchText`.

The file carries uncommitted changes — read it first.

**Files:**
- Modify: `web/src/components/intake/HomeStart.tsx`

- [ ] **Step 1: Read the current HardConstraintForm signature**

```bash
grep -n "interface\|function\|export" web/src/components/intake/HardConstraintForm.tsx | head -20
```

Note: do not change HardConstraintForm—only wrap it in the new layout.

- [ ] **Step 2: Replace HomeStart layout**

Replace `web/src/components/intake/HomeStart.tsx` with:

```tsx
"use client"

import { useEffect, useState } from "react"
import { listSessions } from "@/lib/apiClient"
import type { PlanningSession } from "@/lib/types"
import { HardConstraintForm, type IntakeLanguage } from "./HardConstraintForm"
import { RecentTrips } from "./RecentTrips"

const copy = {
  en: {
    eyebrow: "Single-city travel planning",
    title: "Plan a trip that actually fits you.",
    body: "Tell us your constraints. We'll find what's worth doing—then build a full itinerary around it.",
    switchLabel: "切换到中文",
    switchText: "中文",
  },
  zh: {
    eyebrow: "AI 单城市旅行规划",
    title: "一次真正适合你的旅行。",
    body: "锁定时间、预算和人数，AI 筛选值得去的体验，然后生成住宿、交通和每日行程。",
    switchLabel: "Switch to English",
    switchText: "EN",
  },
} satisfies Record<IntakeLanguage, Record<string, string>>

export function HomeStart() {
  const [language, setLanguage] = useState<IntakeLanguage>("zh")
  const [recentSessions, setRecentSessions] = useState<PlanningSession[]>([])
  const text = copy[language]

  useEffect(() => {
    let active = true
    listSessions()
      .then((sessions) => { if (active) setRecentSessions(sessions) })
      .catch(() => { if (active) setRecentSessions([]) })
    return () => { active = false }
  }, [])

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Hero band */}
      <div className="bg-slate-950 px-5 py-14 sm:px-10 lg:px-16">
        <div className="mx-auto grid max-w-5xl gap-10 lg:grid-cols-[1fr_420px] lg:items-start lg:gap-16">
          {/* Left: Brand statement */}
          <div className="text-white">
            <button
              type="button"
              aria-label={text.switchLabel}
              onClick={() => setLanguage((l) => (l === "zh" ? "en" : "zh"))}
              className="mb-6 rounded-full border border-white/20 px-3 py-1 text-xs text-white/60 hover:text-white/90 transition-colors"
            >
              {text.switchText}
            </button>
            <p className="text-sm font-semibold uppercase tracking-widest text-teal-400">
              {text.eyebrow}
            </p>
            <h1 className="mt-4 max-w-md text-4xl font-bold leading-tight sm:text-5xl">
              {text.title}
            </h1>
            <p className="mt-5 max-w-sm text-base leading-7 text-slate-300">
              {text.body}
            </p>
            <div className="mt-8 flex gap-6 text-sm text-slate-400">
              <span>📍 单城市深度</span>
              <span>🤖 AI 多 agent 规划</span>
              <span>✏️ 对话式调整</span>
            </div>
          </div>

          {/* Right: Form card */}
          <div className="rounded-2xl border border-white/10 bg-white/5 p-5 backdrop-blur-sm sm:p-6">
            <HardConstraintForm language={language} />
          </div>
        </div>
      </div>

      {/* Recent trips */}
      {recentSessions.length > 0 && (
        <div className="mx-auto max-w-5xl px-5 py-10 sm:px-10 lg:px-16">
          <RecentTrips sessions={recentSessions} language={language} />
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Verify HardConstraintForm accepts `language` prop**

```bash
grep "language" web/src/components/intake/HardConstraintForm.tsx | head -5
```

If `HardConstraintForm` doesn't accept a `language` prop yet but the existing code passes it, verify the prop signature matches. If it uses `IntakeLanguage` internally, keep it consistent.

- [ ] **Step 4: Remove the `main` wrapper from `web/src/app/page.tsx`** since HomeStart now controls its own background

```tsx
// web/src/app/page.tsx — replace with:
import { HomeStart } from "@/components/intake/HomeStart"

export default function HomePage() {
  return <HomeStart />
}
```

- [ ] **Step 5: Type check**

```bash
cd web && npm run typecheck
```

Expected: exits 0

- [ ] **Step 6: Commit**

```bash
git add web/src/components/intake/HomeStart.tsx web/src/app/page.tsx
git commit -m "feat: add two-column hero layout to homepage with dark brand band"
```

---

## Task 8: ItineraryDayCard — Timeline Line for Segments

**Goal:** Add a visual timeline line down the left side of the segment list so the day's time flow is obvious at a glance.

**Files:**
- Modify: `web/src/components/itinerary/ItineraryDayCard.tsx`

**Current state:** As of the 2026-05-16 audit the `space-y-3` block below matches the file exactly. The file carries uncommitted changes, so re-read it first in case the result-page work has shifted this block.

- [ ] **Step 1: Add timeline line to segment list**

In `ItineraryDayCard.tsx`, find the `space-y-3` segment list div and replace it with a timeline layout. The segment list gets a `relative` container and each segment gets a left dot:

Find this block:
```tsx
<div className="mt-4 space-y-3">
  {day.segments.map((segment, index) => (
    <div
      key={`${segment.start_time}-${index}`}
      className="grid min-w-0 gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-3 sm:grid-cols-[104px_minmax(0,1fr)] sm:px-4"
    >
```

Replace with:
```tsx
<div className="relative mt-4 pl-4">
  {/* Timeline line */}
  <div className="absolute bottom-2 left-[11px] top-2 w-0.5 bg-slate-200" aria-hidden="true" />

  <div className="space-y-3">
    {day.segments.map((segment, index) => (
      <div key={`${segment.start_time}-${index}`} className="relative">
        {/* Timeline dot */}
        <div
          className="absolute -left-4 top-3.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-slate-300 shadow-sm"
          aria-hidden="true"
        />
        <div
          className="grid min-w-0 gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-3 sm:grid-cols-[104px_minmax(0,1fr)] sm:px-4"
        >
```

Close the extra wrapping div after each segment's closing `</div>` for the inner content:
```tsx
        </div>
      </div>
    ))}
  </div>
</div>
```

Make sure the bracket nesting is correct after the edit by running typecheck.

- [ ] **Step 2: Type check**

```bash
cd web && npm run typecheck
```

Expected: exits 0

- [ ] **Step 3: Commit**

```bash
git add web/src/components/itinerary/ItineraryDayCard.tsx
git commit -m "feat: add timeline line to itinerary day card segment list"
```

---

## Task 9: Mobile Layout — CompanionRail as Bottom Drawer

**Goal:** On mobile (`< lg`), CompanionRail is hidden behind a floating button. Tapping the button opens a bottom drawer. On desktop, the existing sticky sidebar layout is unchanged.

**Files:**
- Modify: `web/src/app/trips/[sessionId]/page.tsx`

- [ ] **Step 1: Add mobile drawer to TripPage**

In `web/src/app/trips/[sessionId]/page.tsx`, add a state variable and drawer UI.

Find the existing `return` statement. The current JSX has `ItineraryView` with `adjustmentPanel` as a prop. The CompanionRail is rendered inside `ItineraryView` on desktop via the grid.

Add this state at the top of `TripPage` (after existing state declarations):

```tsx
const [drawerOpen, setDrawerOpen] = useState(false)
```

Then, after the closing `</div>` of the main content (and before the closing `</main>`), add the mobile drawer:

```tsx
{/* Mobile: floating adjustment button */}
{session?.itinerary && (
  <div className="fixed bottom-5 right-5 z-40 lg:hidden">
    <button
      type="button"
      onClick={() => setDrawerOpen(true)}
      className="flex h-14 w-14 items-center justify-center rounded-full bg-teal-600 text-white shadow-lg hover:bg-teal-700"
      aria-label="打开调整面板"
    >
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  </div>
)}

{/* Mobile: bottom drawer */}
{drawerOpen && session?.itinerary && (
  <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-label="调整行程">
    {/* Backdrop */}
    <div
      className="absolute inset-0 bg-slate-950/50"
      onClick={() => setDrawerOpen(false)}
      aria-hidden="true"
    />
    {/* Drawer panel */}
    <div className="absolute bottom-0 left-0 right-0 max-h-[80vh] overflow-y-auto rounded-t-2xl bg-white pb-safe">
      <div className="sticky top-0 flex items-center justify-between border-b border-slate-100 bg-white px-4 py-3">
        <span className="text-sm font-semibold text-slate-950">调整行程</span>
        <button
          type="button"
          onClick={() => setDrawerOpen(false)}
          className="rounded-md p-1 text-slate-500 hover:text-slate-700"
          aria-label="关闭"
        >
          ✕
        </button>
      </div>
      <div className="p-4">
        <AdjustmentPanel session={session} onSessionChange={setSession} />
      </div>
    </div>
  </div>
)}
```

- [ ] **Step 2: Add `import { useState }` if not already imported**

Check that `useState` is already imported from `"react"` at the top of the file. It should be. If `drawerOpen` causes a TS error because `useState` isn't imported, add it.

- [ ] **Step 3: Type check**

```bash
cd web && npm run typecheck
```

Expected: exits 0

- [ ] **Step 4: Commit**

```bash
git add web/src/app/trips/[sessionId]/page.tsx
git commit -m "feat: add mobile bottom drawer for adjustment panel on trip page"
```

---

## Task 10: Error States & Toast Notification

**Goal:** Create a simple toast notification system and replace bare `if (error) return <Centered message={error} />` with an inline error banner + retry button.

**Files:**
- Create: `web/src/components/ui/Toast.tsx`
- Create: `web/src/components/ui/useToast.ts`
- Modify: `web/src/app/trips/[sessionId]/page.tsx`

- [ ] **Step 1: Write useToast hook**

Create `web/src/components/ui/useToast.ts`:

```ts
import { useCallback, useState } from "react"

export interface ToastMessage {
  id: number
  text: string
  variant: "error" | "success" | "info"
}

let nextId = 0

export function useToast() {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const toast = useCallback((text: string, variant: ToastMessage["variant"] = "info") => {
    const id = ++nextId
    setToasts((prev) => [...prev, { id, text, variant }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }, [])

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return { toasts, toast, dismiss }
}
```

- [ ] **Step 2: Write Toast component**

Create `web/src/components/ui/Toast.tsx`:

```tsx
"use client"

import type { ToastMessage } from "./useToast"

const VARIANT_STYLES: Record<ToastMessage["variant"], string> = {
  error: "border-red-200 bg-red-50 text-red-800",
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  info: "border-slate-200 bg-white text-slate-800",
}

interface ToastContainerProps {
  toasts: ToastMessage[]
  onDismiss: (id: number) => void
}

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  if (toasts.length === 0) return null

  return (
    <div
      aria-live="polite"
      aria-atomic="false"
      className="fixed bottom-5 left-1/2 z-[60] flex -translate-x-1/2 flex-col gap-2"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className={`flex min-w-64 max-w-sm items-center justify-between gap-4 rounded-xl border px-4 py-3 shadow-md ${VARIANT_STYLES[t.variant]}`}
        >
          <p className="text-sm font-medium">{t.text}</p>
          <button
            type="button"
            onClick={() => onDismiss(t.id)}
            aria-label="关闭提示"
            className="flex-shrink-0 opacity-60 hover:opacity-100"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: Integrate Toast into TripPage**

In `web/src/app/trips/[sessionId]/page.tsx`:

Add imports:
```tsx
import { ToastContainer } from "@/components/ui/Toast"
import { useToast } from "@/components/ui/useToast"
```

Inside `TripPage`, add:
```tsx
const { toasts, toast, dismiss } = useToast()
```

Replace the bare error pattern:
```tsx
// Remove:
if (error) return <Centered message={error} />

// Instead, show error inline — keep the page shell and show an error banner:
// In the JSX, after the main content div, add:
{error && (
  <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-red-800">
    <p className="font-semibold">规划出错</p>
    <p className="mt-1 text-sm">{error}</p>
    <button
      type="button"
      onClick={() => { setError(""); void load() }}  // expose load as a named fn
      className="mt-3 rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
    >
      重试
    </button>
  </div>
)}
```

Also call `toast("调整出错，请重试", "error")` inside `AdjustmentPanel` when `send()` catches an error (already done in Task 6 — that version uses `pushMessage`). No further changes needed there.

Add `<ToastContainer toasts={toasts} onDismiss={dismiss} />` at the bottom of the `<main>` element.

- [ ] **Step 4: Extract the `load` function so retry can call it**

In `TripPage`, refactor the `useEffect` to call a named `load` function:

```tsx
const [retryKey, setRetryKey] = useState(0)

useEffect(() => {
  let active = true
  async function load() {
    setError("")
    try {
      const current = await getSession(sessionId)
      if (!active) return
      setSession(current)
      if (current.itinerary) return
      setPlanning(true)
      setProgressEvents([])
      const planned = await streamItinerary(sessionId, {
        onProgress: (event) => {
          if (active) setProgressEvents((events) => [...events, event])
        },
      })
      if (active) setSession(planned)
    } catch (loadError) {
      if (active) setError(loadError instanceof Error ? loadError.message : "规划失败")
    } finally {
      if (active) setPlanning(false)
    }
  }
  void load()
  return () => { active = false }
}, [sessionId, retryKey])
```

Then the retry button calls `setRetryKey((k) => k + 1)`.

- [ ] **Step 5: Type check**

```bash
cd web && npm run typecheck
```

Expected: exits 0

- [ ] **Step 6: Commit**

```bash
git add web/src/components/ui/Toast.tsx web/src/components/ui/useToast.ts web/src/app/trips/[sessionId]/page.tsx
git commit -m "feat: add toast notification system and inline error state with retry to trip page"
```

---

## Task 11: Preferences Page — Visual Transport Selector

**Goal:** Replace the plain `城际交通` dropdown in `PreferenceForm` with visual icon buttons. The other four `Select`s stay as-is — only intercity transport gets the upgrade, to keep scope tight.

**Current state:** `web/src/components/preferences/PreferenceForm.tsx` holds all preference state in one component. The relevant field is:

```tsx
const [transport, setTransport] =
  useState<Preference["intercity_transport_preference"]>("rail")
```

rendered as:

```tsx
<Select label="城际交通" value={transport} onChange={setTransport}>
  <option value="rail">高铁/火车优先</option>
  <option value="flight">飞机优先</option>
  <option value="flexible">都可以</option>
</Select>
```

There is **no** within-city `transport_mode` field — do not add one. The submit payload key is `intercity_transport_preference`. The file carries uncommitted changes — read it first.

**Files:**
- Modify: `web/src/components/preferences/PreferenceForm.tsx`

- [ ] **Step 1: Read the current PreferenceForm**

```bash
cat web/src/components/preferences/PreferenceForm.tsx
```

Confirm the `transport` / `setTransport` state and the `城际交通` `<Select>` still match the snippet above.

- [ ] **Step 2: Replace the 城际交通 Select with icon buttons**

Replace the single `<Select label="城际交通" ...>` block with a labelled button group. Keep the `transport` state and the `intercity_transport_preference` payload key unchanged. Leave the `Select` helper in place — the other four selects still use it.

```tsx
<fieldset className="flex flex-col gap-2 text-sm font-semibold text-slate-700">
  <legend className="mb-1">城际交通</legend>
  <div className="grid grid-cols-3 gap-2">
    {[
      { value: "rail", label: "高铁/火车", icon: "🚄" },
      { value: "flight", label: "飞机优先", icon: "✈️" },
      { value: "flexible", label: "都可以", icon: "🔀" },
    ].map((opt) => (
      <button
        key={opt.value}
        type="button"
        onClick={() =>
          setTransport(opt.value as Preference["intercity_transport_preference"])
        }
        className={`
          flex flex-col items-center gap-1.5 rounded-xl border p-3 text-sm font-medium transition-colors
          ${transport === opt.value
            ? "border-teal-500 bg-teal-50 text-teal-800 shadow-[0_0_0_2px_theme(colors.teal.500)]"
            : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
          }
        `}
      >
        <span className="text-xl">{opt.icon}</span>
        {opt.label}
      </button>
    ))}
  </div>
</fieldset>
```

- [ ] **Step 3: Type check**

```bash
cd web && npm run typecheck
```

Expected: exits 0

- [ ] **Step 4: Commit**

```bash
git add web/src/components/preferences/PreferenceForm.tsx
git commit -m "feat: replace intercity transport dropdown with visual icon buttons"
```

---

## Task 12: E2E Smoke Test — Full Flow Verification

**Goal:** Verify the complete 4-page flow works end-to-end in Playwright after all UI changes.

**Files:**
- Read: `web/src/app/trips/[sessionId]/page.test.tsx` (if it exists)
- Existing e2e test files in `web/test-results/` or wherever e2e specs live

- [ ] **Step 1: Find the existing e2e spec**

```bash
find web -name "*.spec.ts" -o -name "*.e2e.ts" 2>/dev/null | head -10
```

- [ ] **Step 2: Run the e2e suite**

```bash
cd web && npm run test:e2e 2>&1 | tail -30
```

If any test fails due to the UI changes (selector changes, new layout), read the failing test and update the selectors to match the new HTML. Common changes:
- `"选择"` button text unchanged ✅
- `"已选择"` → `"已选 ✓"` (Task 3 changed the label) — update any e2e that checks button text
- Discovery card wrapper: was `article.min-h-64` still matches
- Planning progress: `"规划进度"` → section with `aria-label="规划进度"` — update selector if needed

- [ ] **Step 3: Fix any failing selectors**

For each failing test, update the selector to match the new component structure. Do not weaken assertions — keep the same behavioral checks.

- [ ] **Step 4: Run unit tests**

```bash
cd web && npm run test 2>&1 | tail -20
```

Expected: all pass

- [ ] **Step 5: Final build check**

```bash
cd web && npm run build 2>&1 | tail -20
```

Expected: exits 0

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "test: update e2e selectors for redesigned UI components"
```

---

## Task 13: Final Integration — Branch Merge to Main

**Goal:** Merge all product-polish work to main so the codebase is unified.

- [ ] **Step 1: Check current branch state**

```bash
git status
git log --oneline main..codex/product-polish | head -10
```

- [ ] **Step 2: Run full test suite one more time**

```bash
cd web && npm run typecheck && npm run test && npm run build
```

All must pass.

- [ ] **Step 3: Merge to main**

```bash
git checkout main
git merge codex/product-polish --no-ff -m "feat: merge product-polish — complete UI/UX redesign"
```

- [ ] **Step 4: Push**

```bash
git push origin main
```

- [ ] **Step 5: Clean up**

The user manages branches with `git checkout`, not worktrees. After a successful merge, delete the feature branch if it is no longer needed:

```bash
git branch -d codex/product-polish
```

Do **not** run `git worktree remove` or otherwise alter the worktree layout — coordinate with the user first.

---

## Self-Review Checklist

After writing this plan, checked against the stated goals:

| Goal | Covered by |
|---|---|
| Discovery cards visual excellence | Task 3 |
| Discovery card skeleton loading | Task 4 (selection-count banner superseded — see Reality Sync) |
| Planning progress animation | Task 5 |
| Adjustment panel chat history | Task 6 |
| Homepage visual identity | Task 7 |
| Day card timeline line | Task 8 |
| Mobile bottom drawer | Task 9 |
| Error states + toast | Task 10 |
| Preferences visual icons | Task 11 |
| E2E verification | Task 12 |
| Branch integration | Task 13 |
| Backend unchanged | ✅ No api/ changes |
| TDD discipline | Unit/type checks after each task |
| Frequent commits | One commit per task |

---

## 注意事项 (Notes for Codex)

1. **先做 Reality Sync 的 preflight gate。** 47 个未提交文件来自另一项 result-page 工作，动手前必须先和用户确认如何处理脏工作树。
2. **不要修改 `api/` 目录。** 所有改动只在 `web/src/` 内。
3. **每个 Task 做完立刻 commit**，不要攒在一起。
4. **每个标了 "Replace the entire content / Rewrite" 的文件先读当前内容**，确认没有未提交改动会被覆盖。
5. **Task 4** 选择计数横幅已被 `DiscoveryBoard` 现有实现取代，只需补 skeleton 加载状态。不要给 `DiscoveryBoard` 新增 `onConfirm`/`loading` props。
6. **Task 7 / Task 11** 的代码块已按真实签名修正：`RecentTrips` 需要 `language` prop；偏好页只有 `intercity_transport_preference`，没有 `transport_mode`。
7. 遇到 TypeScript 报错：先修复类型，再提交。不要用 `as any` 跳过。
8. 遇到测试失败：修复选择器或行为，不要注释掉测试。
