# Result Page Product Expression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a story-led planning command center for the trip result page using existing session, discovery, itinerary, budget, stay, transport, and validator data.

**Architecture:** Keep backend schemas and the planning graph unchanged. Add deterministic frontend model helpers under the itinerary component area, then compose focused React sections around those helpers. Update the trip page shell so the existing adjustment workflow remains functional in the new right rail.

**Tech Stack:** Next.js App Router, React 19, TypeScript, Tailwind CSS, Vitest, Testing Library, Playwright.

---

## Scope Check

This plan implements the first result-page product-expression release from `docs/superpowers/specs/2026-05-11-result-page-product-expression-design.md`.

In scope:

- Result page layout and presentation.
- Frontend-only derived helpers.
- Hero image selection and fallback presentation.
- Budget, pace, route, and risk metric cards.
- Narrative route summary.
- Richer day-by-day itinerary cards.
- Existing stay override and adjustment panel continuity.
- Unit, component, and fixture-backed e2e updates.

Out of scope:

- New backend providers.
- New image scraping.
- Full conversational AI backend.
- Map provider overhaul.
- Schema migrations.
- Intake, discovery, and preferences redesigns.

## File Structure

- Create `web/src/components/itinerary/resultPageModel.ts`
  - Pure deterministic helpers for selected discovery cards, hero images, tags, metric statuses, narrative route items, and adjustment prompts.
- Create `web/src/components/itinerary/resultPageModel.test.ts`
  - Unit tests for the derived helpers.
- Create `web/src/components/itinerary/ResultHero.tsx`
  - Destination story hero with image collage and non-image fallback rendering.
- Create `web/src/components/itinerary/ResultMetrics.tsx`
  - Four command metric cards.
- Create `web/src/components/itinerary/NarrativeRoute.tsx`
  - Story arc cards, one per itinerary day.
- Create `web/src/components/itinerary/TripSpine.tsx`
  - Orientation rail for trip spine and travel tone.
- Create `web/src/components/itinerary/CompanionRail.tsx`
  - Right rail with spatial summary, companion brief, smart adjustments, and existing adjustment panel slot.
- Modify `web/src/components/itinerary/ItineraryDayCard.tsx`
  - Upgrade segment presentation while preserving props.
- Modify `web/src/components/itinerary/ItineraryView.tsx`
  - Compose the new command center and accept an optional adjustment panel slot.
- Modify `web/src/app/trips/[sessionId]/page.tsx`
  - Remove the old two-column page shell and pass the existing adjustment panel into `ItineraryView`.
- Create `web/src/components/itinerary/ItineraryView.test.tsx`
  - Component tests for full data, missing images, budget overrun, and validator warnings.
- Modify `web/e2e/helpers/mvpFlow.ts`
  - Update assertions from the old result page labels to the new section labels.
- Modify `web/e2e/mvp-flow.spec.ts`
  - Keep adjustment behavior covered in the new layout.

## Task 1: Add Result Page Model Tests

**Files:**

- Create: `web/src/components/itinerary/resultPageModel.test.ts`
- Create later: `web/src/components/itinerary/resultPageModel.ts`

- [ ] **Step 1: Write failing helper tests**

Create `web/src/components/itinerary/resultPageModel.test.ts`:

```ts
import { describe, expect, it } from "vitest"
import type { PlanningSession } from "@/lib/types"
import {
  budgetFitStatus,
  destinationTags,
  heroImages,
  narrativeRouteItems,
  paceStatus,
  riskStatus,
  routeStatus,
  selectedDiscoveryCards,
  smartAdjustmentPrompts,
} from "./resultPageModel"

function band(low: number, high: number) {
  return {
    basis: "per_trip" as const,
    confidence: "medium" as const,
    currency: "CNY",
    low,
    high,
  }
}

function sessionFixture(overrides: Partial<PlanningSession> = {}): PlanningSession {
  const session: PlanningSession = {
    session_id: "session_1",
    created_at: "2026-05-11T00:00:00",
    updated_at: "2026-05-11T00:00:00",
    parent_session_id: null,
    snapshot_label: null,
    status: "active",
    conversation_history: [],
    hard_constraints: {
      departure_city: "北京",
      departure_date: "2026-06-01",
      destination_city: "上海",
      destination_country_code: "CN",
      duration_days: 3,
      traveler_count: 2,
      total_budget: 6000,
      currency: "CNY",
    },
    discovery_state: {
      selected_card_ids: ["bund", "museum"],
      payload: {
        cards: [
          {
            id: "bund",
            name: "The Bund waterfront walk",
            reason: "Classic skyline walk that anchors the first evening.",
            category: "attraction",
            tags: ["waterfront", "night view"],
            suggested_duration_minutes: 120,
            cost_signal: "free",
            cost_estimate: band(0, 0),
            image_url: "https://images.example/bund.jpg",
            reservation_hint: null,
            enrichment_status: "complete",
            place: {
              id: "place_bund",
              name: "The Bund",
              provider: "mapbox",
              address: "Zhongshan East 1st Road",
              category: "attraction",
              coordinate: { lat: 31.2402, lng: 121.4903 },
            },
          },
          {
            id: "museum",
            name: "Shanghai Museum",
            reason: "A compact cultural block near People's Square.",
            category: "museum",
            tags: ["culture", "rain-safe"],
            suggested_duration_minutes: 150,
            cost_signal: "low",
            cost_estimate: band(0, 120),
            image_url: null,
            reservation_hint: "Reserve in advance during holidays.",
            enrichment_status: "partial",
            place: {
              id: "place_museum",
              name: "Shanghai Museum",
              provider: "mapbox",
              address: "People's Square",
              category: "museum",
              coordinate: { lat: 31.2304, lng: 121.4737 },
            },
          },
        ],
        food_summaries: [],
        area_summaries: [
          {
            id: "central",
            name: "People's Square",
            note: "Central and easy to connect from.",
            vibe_tags: ["central", "walkable"],
            center: { lat: 31.2304, lng: 121.4737 },
          },
        ],
        budget_estimate: {
          currency: "CNY",
          user_budget: 6000,
          overrun_flag: false,
          transport: band(600, 900),
          stay: band(1600, 2200),
          food: band(600, 900),
          attractions: band(200, 500),
          other: band(150, 400),
          total: band(3150, 4900),
        },
        source_notes: [],
      },
    },
    preferences: {
      area_vibe: "central, walkable, good food nearby",
      quiet_vs_lively: "balanced",
      stay_type: "homestay",
      willing_to_change_hotels: false,
      intercity_transport_preference: "rail",
      early_departure_tolerance: "medium",
      transfer_tolerance: "medium",
      pay_more_to_save_time: true,
    },
    stay_recommendation: {
      user_override_id: null,
      primary: {
        id: "stay_central",
        area: {
          id: "central",
          name: "People's Square",
          note: "Central and easy to connect from.",
          vibe_tags: ["central", "walkable"],
          center: { lat: 31.2304, lng: 121.4737 },
        },
        fit_reason: "Central for selected sights and food access.",
        price_band: band(1600, 2200),
        sample_hotels: [],
      },
      alternatives: [],
    },
    transport_recommendation: {
      arrival: { mode: "rail", duration_minutes: 330, cost_band: band(550, 750), note: "Arrive by rail." },
      departure: { mode: "rail", duration_minutes: 330, cost_band: band(550, 750), note: "Return by rail." },
      intracity: { primary_mode: "transit", daily_cost_band: band(60, 120), note: "Use metro plus short walks." },
      tradeoffs: ["Rail keeps arrival predictable."],
    },
    itinerary: {
      id: "itinerary_1",
      session_id: "session_1",
      version: 1,
      budget: {
        currency: "CNY",
        user_budget: 6000,
        overrun_flag: false,
        transport: band(1100, 1500),
        stay: band(1600, 2200),
        food: band(600, 900),
        attractions: band(200, 500),
        other: band(150, 400),
        total: band(3650, 5500),
      },
      validator_issues: [
        {
          code: "reservation_check",
          severity: "warning",
          scope: { day_index: 2 },
          message: "Museum reservation may be required.",
          suggested_action: "Confirm the opening window.",
        },
      ],
      days: [
        {
          day_index: 1,
          date: "2026-06-01",
          notes: ["Start with a skyline evening."],
          segments: [
            {
              type: "hotel_checkin",
              start_time: "09:00",
              end_time: "09:30",
              place: null,
              card_ref: null,
              description: "Drop bags near People's Square.",
              cost_estimate: null,
            },
            {
              type: "attraction",
              start_time: "10:00",
              end_time: "12:00",
              place: {
                id: "place_bund",
                name: "The Bund",
                provider: "mapbox",
                address: "Zhongshan East 1st Road",
                category: "attraction",
                coordinate: { lat: 31.2402, lng: 121.4903 },
              },
              card_ref: "bund",
              description: "Walk the riverfront and save photo time.",
              cost_estimate: band(0, 0),
            },
            {
              type: "food",
              start_time: "12:15",
              end_time: "13:30",
              place: null,
              card_ref: null,
              description: "Keep lunch flexible near the morning area.",
              cost_estimate: band(80, 180),
            },
          ],
        },
        {
          day_index: 2,
          date: "2026-06-02",
          notes: ["Culture-heavy day with a lighter evening."],
          segments: [
            {
              type: "attraction",
              start_time: "10:00",
              end_time: "12:30",
              place: null,
              card_ref: "museum",
              description: "Visit the museum collection.",
              cost_estimate: band(0, 120),
            },
            {
              type: "rest",
              start_time: "14:00",
              end_time: "16:00",
              place: null,
              card_ref: null,
              description: "Flexible rest block.",
              cost_estimate: null,
            },
          ],
        },
      ],
    },
    validator_issues: [],
  }
  return { ...session, ...overrides }
}

describe("result page model helpers", () => {
  it("selects chosen discovery cards and image URLs in itinerary order", () => {
    const session = sessionFixture()
    expect(selectedDiscoveryCards(session).map((card) => card.id)).toEqual(["bund", "museum"])
    expect(heroImages(session)).toEqual([
      { src: "https://images.example/bund.jpg", alt: "The Bund waterfront walk" },
    ])
  })

  it("derives destination tags from selected cards, area vibes, and preferences", () => {
    expect(destinationTags(sessionFixture())).toEqual([
      "waterfront",
      "night view",
      "culture",
      "rain-safe",
      "central",
      "walkable",
    ])
  })

  it("classifies budget, pace, route, and risk statuses", () => {
    const session = sessionFixture()
    expect(budgetFitStatus(session).status).toBe("Within range")
    expect(paceStatus(session.itinerary).status).toBe("Balanced pace")
    expect(routeStatus(session.itinerary).status).toBe("Some routes need confirmation")
    expect(riskStatus(session.itinerary).status).toBe("1 warning to review")
  })

  it("builds narrative route cards from itinerary days", () => {
    const items = narrativeRouteItems(sessionFixture())
    expect(items[0]).toMatchObject({
      dayIndex: 1,
      title: "Day 1: Check in, then The Bund",
      anchors: ["Drop bags near People's Square.", "The Bund", "Keep lunch flexible near the morning area."],
    })
  })

  it("suggests smart adjustment prompts from session state", () => {
    const prompts = smartAdjustmentPrompts(sessionFixture())
    expect(prompts).toContain("Review 1 itinerary warning")
    expect(prompts).toContain("Confirm route details for segments without mapped places")
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd web
npm run test -- src/components/itinerary/resultPageModel.test.ts
```

Expected: FAIL because `./resultPageModel` does not exist.

## Task 2: Implement Result Page Model Helpers

**Files:**

- Create: `web/src/components/itinerary/resultPageModel.ts`
- Test: `web/src/components/itinerary/resultPageModel.test.ts`

- [ ] **Step 1: Create the helper module**

Create `web/src/components/itinerary/resultPageModel.ts`:

```ts
import type {
  BudgetBand,
  DiscoveryCard,
  Itinerary,
  ItineraryDay,
  ItinerarySegment,
  PlanningSession,
  StayOption,
} from "@/lib/types"

export interface HeroImage {
  src: string
  alt: string
}

export interface ResultMetric {
  label: string
  status: string
  tone: "good" | "neutral" | "warning" | "danger"
  detail: string
  value: string
}

export interface NarrativeRouteItem {
  dayIndex: number
  date: string
  title: string
  anchors: string[]
  note: string
  budgetHint: string
}

export function selectedDiscoveryCards(session: PlanningSession): DiscoveryCard[] {
  const cards = session.discovery_state?.payload?.cards ?? []
  const selectedIds = session.discovery_state?.selected_card_ids ?? []
  if (selectedIds.length === 0) return cards.slice(0, 3)
  const byId = new Map(cards.map((card) => [card.id, card]))
  return selectedIds.flatMap((id) => {
    const card = byId.get(id)
    return card ? [card] : []
  })
}

export function heroImages(session: PlanningSession): HeroImage[] {
  return selectedDiscoveryCards(session)
    .filter((card) => Boolean(card.image_url))
    .slice(0, 4)
    .map((card) => ({ src: String(card.image_url), alt: card.name }))
}

export function destinationTags(session: PlanningSession): string[] {
  const tags: string[] = []
  for (const card of selectedDiscoveryCards(session)) {
    tags.push(...card.tags)
  }
  const areaTags = session.discovery_state?.payload?.area_summaries.flatMap((area) => area.vibe_tags) ?? []
  tags.push(...areaTags)
  if (session.preferences) {
    tags.push(session.preferences.quiet_vs_lively)
    tags.push(session.preferences.stay_type)
  }
  return Array.from(new Set(tags.filter(Boolean))).slice(0, 6)
}

export function activeStayOption(session: PlanningSession): StayOption | null {
  const stay = session.stay_recommendation
  if (!stay) return null
  const options = [stay.primary, ...stay.alternatives]
  return options.find((option) => option.id === stay.user_override_id) ?? stay.primary
}

export function budgetFitStatus(session: PlanningSession): ResultMetric {
  const budget = session.itinerary?.budget
  if (!budget) {
    return {
      label: "Budget fit",
      status: "Budget pending",
      tone: "neutral",
      detail: "The final budget is not available yet.",
      value: formatMoney(session.hard_constraints.total_budget, session.hard_constraints.currency),
    }
  }
  const high = budget.total.high
  const userBudget = budget.user_budget || session.hard_constraints.total_budget
  if (budget.overrun_flag || high > userBudget) {
    return {
      label: "Budget fit",
      status: "Over budget",
      tone: "danger",
      detail: `Estimated high end is ${formatMoney(high, budget.currency)} against your ${formatMoney(userBudget, budget.currency)} budget.`,
      value: formatBand(budget.total),
    }
  }
  return {
    label: "Budget fit",
    status: "Within range",
    tone: "good",
    detail: `Estimated total stays below your ${formatMoney(userBudget, budget.currency)} budget.`,
    value: formatBand(budget.total),
  }
}

export function paceStatus(itinerary: Itinerary | null): ResultMetric {
  if (!itinerary) {
    return {
      label: "Pace",
      status: "Pace pending",
      tone: "neutral",
      detail: "The plan has not been generated yet.",
      value: "Not ready",
    }
  }
  const segmentCounts = itinerary.days.map((day) => day.segments.length)
  const maxSegments = Math.max(...segmentCounts, 0)
  const restBlocks = itinerary.days.flatMap((day) => day.segments).filter((segment) => segment.type === "rest").length
  if (maxSegments >= 6) {
    return {
      label: "Pace",
      status: "Packed days",
      tone: "warning",
      detail: "At least one day has many scheduled blocks. Keep an eye on fatigue.",
      value: `${maxSegments} blocks`,
    }
  }
  if (restBlocks > 0) {
    return {
      label: "Pace",
      status: "Balanced pace",
      tone: "good",
      detail: "The plan includes flexible rest time instead of filling every hour.",
      value: `${restBlocks} rest block${restBlocks === 1 ? "" : "s"}`,
    }
  }
  return {
    label: "Pace",
    status: "Steady pace",
    tone: "neutral",
    detail: "The plan has a moderate number of scheduled blocks per day.",
    value: `${maxSegments} blocks`,
  }
}

export function routeStatus(itinerary: Itinerary | null): ResultMetric {
  if (!itinerary) {
    return {
      label: "Route",
      status: "Route pending",
      tone: "neutral",
      detail: "Route context appears after itinerary generation.",
      value: "Not ready",
    }
  }
  const segments = itinerary.days.flatMap((day) => day.segments)
  const placeSegments = segments.filter((segment) => segment.type === "attraction" || segment.type === "hotel_checkin" || segment.type === "hotel_return")
  const mapped = placeSegments.filter((segment) => Boolean(segment.place?.coordinate)).length
  if (placeSegments.length === 0) {
    return {
      label: "Route",
      status: "Route light",
      tone: "neutral",
      detail: "This itinerary has few mapped place blocks.",
      value: "No route load",
    }
  }
  if (mapped < placeSegments.length) {
    return {
      label: "Route",
      status: "Some routes need confirmation",
      tone: "warning",
      detail: "A few scheduled places are missing coordinates and should be checked before travel.",
      value: `${mapped}/${placeSegments.length} mapped`,
    }
  }
  return {
    label: "Route",
    status: "Mapped route",
    tone: "good",
    detail: "Scheduled place blocks include coordinates for route review.",
    value: `${mapped}/${placeSegments.length} mapped`,
  }
}

export function riskStatus(itinerary: Itinerary | null): ResultMetric {
  if (!itinerary) {
    return {
      label: "Risks",
      status: "Risks pending",
      tone: "neutral",
      detail: "Warnings appear after validation.",
      value: "Not ready",
    }
  }
  const errors = itinerary.validator_issues.filter((issue) => issue.severity === "error")
  const warnings = itinerary.validator_issues.filter((issue) => issue.severity === "warning")
  if (errors.length > 0) {
    return {
      label: "Risks",
      status: `${errors.length} issue${errors.length === 1 ? "" : "s"} to fix`,
      tone: "danger",
      detail: "The validator found problems that can affect trip feasibility.",
      value: `${errors.length} error${errors.length === 1 ? "" : "s"}`,
    }
  }
  if (warnings.length > 0) {
    return {
      label: "Risks",
      status: `${warnings.length} warning${warnings.length === 1 ? "" : "s"} to review`,
      tone: "warning",
      detail: "The plan is usable, but a few details should be confirmed.",
      value: `${warnings.length} warning${warnings.length === 1 ? "" : "s"}`,
    }
  }
  return {
    label: "Risks",
    status: "No issues flagged",
    tone: "good",
    detail: "The validator did not flag itinerary problems.",
    value: "Clear",
  }
}

export function narrativeRouteItems(session: PlanningSession): NarrativeRouteItem[] {
  const itinerary = session.itinerary
  if (!itinerary) return []
  const cards = new Map(selectedDiscoveryCards(session).map((card) => [card.id, card]))
  return itinerary.days.map((day) => {
    const anchors = anchorTexts(day, cards)
    return {
      dayIndex: day.day_index,
      date: day.date,
      title: narrativeTitle(day, cards),
      anchors,
      note: day.notes[0] ?? "A planned day with flexible execution.",
      budgetHint: dayBudgetHint(day, itinerary.budget.currency),
    }
  })
}

export function smartAdjustmentPrompts(session: PlanningSession): string[] {
  const prompts: string[] = []
  if (session.stay_recommendation && session.stay_recommendation.alternatives.length > 0) {
    prompts.push("Compare stay area alternatives")
  }
  if (session.itinerary?.budget.overrun_flag) {
    prompts.push("Review budget and reduce higher-cost blocks")
  }
  const issueCount = session.itinerary?.validator_issues.length ?? 0
  if (issueCount > 0) {
    prompts.push(`Review ${issueCount} itinerary warning${issueCount === 1 ? "" : "s"}`)
  }
  if (session.itinerary && routeStatus(session.itinerary).tone === "warning") {
    prompts.push("Confirm route details for segments without mapped places")
  }
  return prompts.slice(0, 3)
}

export function commandMetrics(session: PlanningSession): ResultMetric[] {
  return [
    budgetFitStatus(session),
    paceStatus(session.itinerary),
    routeStatus(session.itinerary),
    riskStatus(session.itinerary),
  ]
}

export function formatBand(band: BudgetBand): string {
  return `${band.currency} ${Math.round(band.low).toLocaleString()}-${Math.round(band.high).toLocaleString()}`
}

function formatMoney(value: number, currency: string): string {
  return `${currency} ${Math.round(value).toLocaleString()}`
}

function narrativeTitle(day: ItineraryDay, cards: Map<string, DiscoveryCard>): string {
  const first = day.segments.find((segment) => segment.type !== "food" && segment.type !== "rest")
  const second = day.segments.find((segment) => segment.type === "attraction")
  const firstLabel = segmentLabel(first, cards)
  const secondLabel = second && second !== first ? segmentLabel(second, cards) : ""
  return secondLabel ? `Day ${day.day_index}: ${firstLabel}, then ${secondLabel}` : `Day ${day.day_index}: ${firstLabel}`
}

function anchorTexts(day: ItineraryDay, cards: Map<string, DiscoveryCard>): string[] {
  return day.segments.slice(0, 3).map((segment) => {
    if (segment.place?.name) return segment.place.name
    if (segment.card_ref && cards.get(segment.card_ref)?.name) return String(cards.get(segment.card_ref)?.name)
    return segment.description
  })
}

function segmentLabel(segment: ItinerarySegment | undefined, cards: Map<string, DiscoveryCard>): string {
  if (!segment) return "Flexible arrival"
  if (segment.place?.name) return segment.place.name
  if (segment.card_ref && cards.get(segment.card_ref)?.name) return String(cards.get(segment.card_ref)?.name)
  if (segment.type === "hotel_checkin") return "Check in"
  if (segment.type === "hotel_checkout") return "Check out"
  if (segment.type === "hotel_return") return "Return to base"
  if (segment.type === "food") return "Meal break"
  if (segment.type === "rest") return "Rest window"
  return segment.type.replaceAll("_", " ")
}

function dayBudgetHint(day: ItineraryDay, currency: string): string {
  const bands = day.segments.flatMap((segment) => (segment.cost_estimate ? [segment.cost_estimate] : []))
  if (bands.length === 0) return "No scheduled costs"
  const low = bands.reduce((total, item) => total + item.low, 0)
  const high = bands.reduce((total, item) => total + item.high, 0)
  return `${currency} ${Math.round(low).toLocaleString()}-${Math.round(high).toLocaleString()} scheduled`
}
```

- [ ] **Step 2: Run helper tests**

Run:

```bash
cd web
npm run test -- src/components/itinerary/resultPageModel.test.ts
```

Expected: PASS.

- [ ] **Step 3: Commit helper model**

Run:

```bash
git add web/src/components/itinerary/resultPageModel.ts web/src/components/itinerary/resultPageModel.test.ts
git commit -m "feat: add result page derived model"
```

## Task 3: Build Story Hero And Metrics Components

**Files:**

- Create: `web/src/components/itinerary/ResultHero.tsx`
- Create: `web/src/components/itinerary/ResultMetrics.tsx`
- Test later: `web/src/components/itinerary/ItineraryView.test.tsx`

- [ ] **Step 1: Create destination story hero**

Create `web/src/components/itinerary/ResultHero.tsx`:

```tsx
import type { ReactNode } from "react"
import type { PlanningSession } from "@/lib/types"
import { activeStayOption, destinationTags, heroImages } from "./resultPageModel"

export function ResultHero({ session }: { session: PlanningSession }) {
  const constraints = session.hard_constraints
  const images = heroImages(session)
  const tags = destinationTags(session)
  const activeStay = activeStayOption(session)

  return (
    <section className="overflow-hidden rounded-2xl bg-slate-950 text-white shadow-xl shadow-slate-200">
      <div className="grid gap-6 p-6 md:grid-cols-[1.15fr_0.85fr] md:p-8">
        <div className="flex min-h-56 flex-col justify-between gap-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/60">
              Destination story
            </p>
            <h1 className="mt-4 max-w-2xl text-3xl font-semibold leading-tight md:text-5xl">
              {constraints.destination_city} · {constraints.duration_days} day plan
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-white/72 md:text-base">
              A curated route from {constraints.departure_city} for {constraints.traveler_count} traveler{constraints.traveler_count === 1 ? "" : "s"}, shaped around budget, pace, stay area, and route feasibility.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <HeroPill>{constraints.departure_date}</HeroPill>
            <HeroPill>{constraints.currency} {Math.round(constraints.total_budget).toLocaleString()} budget</HeroPill>
            {activeStay && <HeroPill>{activeStay.area.name}</HeroPill>}
            {tags.slice(0, 4).map((tag) => (
              <HeroPill key={tag}>{tag}</HeroPill>
            ))}
          </div>
        </div>
        <HeroVisual images={images} destination={constraints.destination_city} />
      </div>
    </section>
  )
}

function HeroPill({ children }: { children: ReactNode }) {
  return (
    <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-medium text-white/82">
      {children}
    </span>
  )
}

function HeroVisual({ images, destination }: { images: { src: string; alt: string }[]; destination: string }) {
  if (images.length === 0) {
    return (
      <div className="relative min-h-56 overflow-hidden rounded-2xl border border-white/15 bg-gradient-to-br from-emerald-400/25 via-sky-400/20 to-orange-300/25 p-5">
        <div className="absolute left-8 top-10 h-3 w-3 rounded-full bg-white/80" />
        <div className="absolute right-12 top-20 h-3 w-3 rounded-full bg-white/70" />
        <div className="absolute bottom-12 left-24 h-3 w-3 rounded-full bg-white/60" />
        <div className="absolute left-12 top-32 h-1.5 w-40 rotate-12 rounded-full bg-sky-200/60" />
        <div className="relative flex h-full min-h-48 flex-col justify-end">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/60">Route texture</p>
          <p className="mt-2 text-xl font-semibold">{destination}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="grid min-h-56 grid-cols-2 gap-3">
      {images.slice(0, 4).map((image, index) => (
        <div
          key={`${image.src}-${index}`}
          className={`overflow-hidden rounded-2xl border border-white/15 bg-white/10 ${images.length === 1 ? "col-span-2 row-span-2" : ""}`}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={image.src} alt="" className="h-full min-h-24 w-full object-cover" />
        </div>
      ))}
      {images.length === 1 && <div className="hidden" aria-hidden="true" />}
    </div>
  )
}
```

- [ ] **Step 2: Create command metrics component**

Create `web/src/components/itinerary/ResultMetrics.tsx`:

```tsx
import type { ResultMetric } from "./resultPageModel"

const toneClasses: Record<ResultMetric["tone"], string> = {
  good: "border-emerald-200 bg-emerald-50 text-emerald-950",
  neutral: "border-slate-200 bg-white text-slate-950",
  warning: "border-amber-200 bg-amber-50 text-amber-950",
  danger: "border-rose-200 bg-rose-50 text-rose-950",
}

const barClasses: Record<ResultMetric["tone"], string> = {
  good: "bg-emerald-500",
  neutral: "bg-slate-400",
  warning: "bg-amber-500",
  danger: "bg-rose-500",
}

export function ResultMetrics({ metrics }: { metrics: ResultMetric[] }) {
  return (
    <section aria-label="Trip decision metrics" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => (
        <article key={metric.label} className={`rounded-xl border p-4 ${toneClasses[metric.tone]}`}>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] opacity-65">{metric.label}</p>
          <div className="mt-3 flex items-end justify-between gap-3">
            <h2 className="text-lg font-semibold leading-tight">{metric.status}</h2>
            <span className="shrink-0 text-xs font-semibold opacity-70">{metric.value}</span>
          </div>
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-black/10">
            <div className={`h-full w-2/3 rounded-full ${barClasses[metric.tone]}`} />
          </div>
          <p className="mt-3 text-sm leading-6 opacity-75">{metric.detail}</p>
        </article>
      ))}
    </section>
  )
}
```

- [ ] **Step 3: Run typecheck**

Run:

```bash
cd web
npm run typecheck
```

Expected: PASS.

## Task 4: Build Narrative, Spine, And Companion Rail Components

**Files:**

- Create: `web/src/components/itinerary/NarrativeRoute.tsx`
- Create: `web/src/components/itinerary/TripSpine.tsx`
- Create: `web/src/components/itinerary/CompanionRail.tsx`

- [ ] **Step 1: Create narrative route component**

Create `web/src/components/itinerary/NarrativeRoute.tsx`:

```tsx
import type { NarrativeRouteItem } from "./resultPageModel"

export function NarrativeRoute({ items }: { items: NarrativeRouteItem[] }) {
  if (items.length === 0) return null

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            Narrative route
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-950">The trip arc</h2>
        </div>
        <p className="max-w-xl text-sm leading-6 text-slate-600">
          A quick read of how the itinerary unfolds before the detailed schedule.
        </p>
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-2">
        {items.map((item) => (
          <article key={item.dayIndex} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                {item.date}
              </p>
              <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-600">
                {item.budgetHint}
              </span>
            </div>
            <h3 className="mt-3 text-lg font-semibold text-slate-950">{item.title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{item.note}</p>
            <ul className="mt-4 space-y-2">
              {item.anchors.map((anchor) => (
                <li key={anchor} className="flex gap-2 text-sm text-slate-700">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-sky-500" />
                  <span>{anchor}</span>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </section>
  )
}
```

- [ ] **Step 2: Create trip spine component**

Create `web/src/components/itinerary/TripSpine.tsx`:

```tsx
import type { PlanningSession } from "@/lib/types"
import { activeStayOption, destinationTags } from "./resultPageModel"

export function TripSpine({ session }: { session: PlanningSession }) {
  const constraints = session.hard_constraints
  const activeStay = activeStayOption(session)
  const tags = destinationTags(session)
  const transport = session.transport_recommendation

  return (
    <aside className="space-y-4">
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Trip spine</p>
        <dl className="mt-4 space-y-3 text-sm">
          <SpineRow label="Destination" value={`${constraints.destination_city}, ${constraints.destination_country_code}`} />
          <SpineRow label="Duration" value={`${constraints.duration_days} days`} />
          <SpineRow label="Travelers" value={`${constraints.traveler_count}`} />
          <SpineRow label="Stay area" value={activeStay?.area.name ?? "Area pending"} />
          <SpineRow label="Transport" value={transport ? `${transport.arrival.mode} arrival · ${transport.intracity.primary_mode} in city` : "Transport pending"} />
        </dl>
      </section>
      <section className="rounded-2xl border border-orange-200 bg-orange-50 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-orange-800">Travel tone</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {tags.map((tag) => (
            <span key={tag} className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-orange-900">
              {tag}
            </span>
          ))}
        </div>
      </section>
    </aside>
  )
}

function SpineRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-[0.1em] text-slate-400">{label}</dt>
      <dd className="mt-1 font-medium text-slate-900">{value}</dd>
    </div>
  )
}
```

- [ ] **Step 3: Create companion rail component**

Create `web/src/components/itinerary/CompanionRail.tsx`:

```tsx
import type { ReactNode } from "react"
import type { PlanningSession } from "@/lib/types"
import { activeStayOption, smartAdjustmentPrompts } from "./resultPageModel"

export function CompanionRail({
  session,
  adjustmentPanel,
}: {
  session: PlanningSession
  adjustmentPanel?: ReactNode
}) {
  const prompts = smartAdjustmentPrompts(session)
  const activeStay = activeStayOption(session)
  const mappedPlaces = session.itinerary?.days
    .flatMap((day) => day.segments)
    .filter((segment) => Boolean(segment.place?.coordinate)).length ?? 0

  return (
    <aside className="space-y-4">
      <section className="rounded-2xl border border-sky-200 bg-sky-50 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-800">Spatial brief</p>
        <h2 className="mt-2 text-lg font-semibold text-slate-950">
          {mappedPlaces > 0 ? `${mappedPlaces} mapped places` : "Route details need confirmation"}
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          {activeStay ? `${activeStay.area.name} is the active stay base for this itinerary.` : "Choose a stay area to make the route easier to evaluate."}
        </p>
      </section>
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Companion brief</p>
        <p className="mt-3 text-sm leading-6 text-slate-700">
          This plan balances the selected discovery cards with stay area, transport, budget, and validator checks. Use the adjustment box when you want to change pace, budget, stay base, or a specific day.
        </p>
      </section>
      {prompts.length > 0 && (
        <section className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Smart adjustments</p>
          <ul className="mt-3 space-y-2">
            {prompts.map((prompt) => (
              <li key={prompt} className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
                {prompt}
              </li>
            ))}
          </ul>
        </section>
      )}
      {adjustmentPanel}
    </aside>
  )
}
```

- [ ] **Step 4: Run typecheck**

Run:

```bash
cd web
npm run typecheck
```

Expected: PASS.

- [ ] **Step 5: Commit presentation sections**

Run:

```bash
git add web/src/components/itinerary/ResultHero.tsx web/src/components/itinerary/ResultMetrics.tsx web/src/components/itinerary/NarrativeRoute.tsx web/src/components/itinerary/TripSpine.tsx web/src/components/itinerary/CompanionRail.tsx
git commit -m "feat: add result page command sections"
```

## Task 5: Compose The New Itinerary View

**Files:**

- Modify: `web/src/components/itinerary/ItineraryView.tsx`
- Modify: `web/src/components/itinerary/ItineraryDayCard.tsx`
- Modify: `web/src/app/trips/[sessionId]/page.tsx`

- [ ] **Step 1: Upgrade itinerary day card**

Replace `web/src/components/itinerary/ItineraryDayCard.tsx` with:

```tsx
import type { ItineraryDay, ItinerarySegment, ValidatorIssue } from "@/lib/types"
import { ValidatorIssueNote } from "./ValidatorIssueNote"
import { formatBand } from "./resultPageModel"

export function ItineraryDayCard({
  day,
  issues,
}: {
  day: ItineraryDay
  issues: ValidatorIssue[]
}) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            Day {day.day_index}
          </p>
          <h3 className="mt-1 text-xl font-semibold text-slate-950">{day.date}</h3>
        </div>
        {day.notes[0] && <p className="max-w-xl text-sm leading-6 text-slate-600">{day.notes[0]}</p>}
      </div>
      <div className="mt-5 space-y-3">
        {day.segments.map((segment, index) => (
          <SegmentRow key={`${segment.start_time}-${index}`} segment={segment} />
        ))}
      </div>
      {issues.length > 0 && (
        <div className="mt-5 space-y-2">
          {issues.map((issue) => (
            <ValidatorIssueNote key={`${issue.code}-${issue.message}`} issue={issue} />
          ))}
        </div>
      )}
    </article>
  )
}

function SegmentRow({ segment }: { segment: ItinerarySegment }) {
  return (
    <div className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 md:grid-cols-[118px_1fr]">
      <div>
        <p className="text-sm font-semibold text-slate-900">
          {segment.start_time}-{segment.end_time}
        </p>
        <span className="mt-2 inline-flex rounded-full bg-white px-2 py-1 text-xs font-medium capitalize text-slate-600">
          {segment.type.replaceAll("_", " ")}
        </span>
      </div>
      <div>
        <div className="flex flex-col gap-1 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="font-semibold text-slate-950">{segment.place?.name ?? segment.description}</p>
            {segment.place?.address && <p className="mt-1 text-sm text-slate-500">{segment.place.address}</p>}
          </div>
          {segment.cost_estimate && (
            <span className="shrink-0 rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-slate-700">
              {formatBand(segment.cost_estimate)}
            </span>
          )}
        </div>
        {segment.place?.name && <p className="mt-2 text-sm leading-6 text-slate-600">{segment.description}</p>}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Compose new result page view**

Replace `web/src/components/itinerary/ItineraryView.tsx` with:

```tsx
"use client"

import type { ReactNode } from "react"
import type { PlanningSession } from "@/lib/types"
import { CompanionRail } from "./CompanionRail"
import { ItineraryDayCard } from "./ItineraryDayCard"
import { NarrativeRoute } from "./NarrativeRoute"
import { ResultHero } from "./ResultHero"
import { ResultMetrics } from "./ResultMetrics"
import { StayAreaSwitcher } from "./StayAreaSwitcher"
import { TripSpine } from "./TripSpine"
import { commandMetrics, narrativeRouteItems } from "./resultPageModel"

interface ItineraryViewProps {
  session: PlanningSession
  onStayOverride: (stayOptionId: string | null) => Promise<void> | void
  adjustmentPanel?: ReactNode
}

export function ItineraryView({ session, onStayOverride, adjustmentPanel }: ItineraryViewProps) {
  const itinerary = session.itinerary
  if (!itinerary) return null

  return (
    <div className="space-y-6">
      <ResultHero session={session} />
      <div className="grid gap-6 xl:grid-cols-[220px_minmax(0,1fr)_320px]">
        <TripSpine session={session} />
        <main className="space-y-5">
          <ResultMetrics metrics={commandMetrics(session)} />
          {session.stay_recommendation && (
            <StayAreaSwitcher stay={session.stay_recommendation} onSelect={onStayOverride} />
          )}
          <NarrativeRoute items={narrativeRouteItems(session)} />
          <section className="space-y-4" aria-label="Day-by-day execution">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Day-by-day execution
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-950">Detailed itinerary</h2>
            </div>
            {itinerary.days.map((day) => (
              <ItineraryDayCard
                key={day.day_index}
                day={day}
                issues={itinerary.validator_issues.filter(
                  (issue) =>
                    issue.scope.type === "trip" ||
                    Number(issue.scope.day_index) === day.day_index
                )}
              />
            ))}
          </section>
        </main>
        <CompanionRail session={session} adjustmentPanel={adjustmentPanel} />
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Update trip page shell**

Replace the return block in `web/src/app/trips/[sessionId]/page.tsx` with this structure:

```tsx
  return (
    <main className="min-h-screen bg-slate-50 px-4 py-6 text-slate-950 md:px-6 md:py-8">
      <div className="mx-auto w-full max-w-7xl">
        <PlanningProgress active={planning || !session?.itinerary} events={progressEvents} />
        <div className="mt-5">
          {session?.itinerary ? (
            <ItineraryView
              session={session}
              onStayOverride={handleStayOverride}
              adjustmentPanel={<AdjustmentPanel session={session} onSessionChange={setSession} />}
            />
          ) : (
            <div className="rounded-lg border border-slate-200 bg-white p-6 text-slate-600">
              Generating final itinerary...
            </div>
          )}
        </div>
      </div>
    </main>
  )
```

Keep the `AdjustmentPanel` import because it is now passed into `ItineraryView`.

- [ ] **Step 4: Run typecheck**

Run:

```bash
cd web
npm run typecheck
```

Expected: PASS.

## Task 6: Add Component And E2E Coverage

**Files:**

- Create: `web/src/components/itinerary/ItineraryView.test.tsx`
- Modify: `web/e2e/helpers/mvpFlow.ts`
- Test: `web/e2e/mvp-flow.spec.ts`

- [ ] **Step 1: Add component coverage**

Create `web/src/components/itinerary/ItineraryView.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import type { PlanningSession } from "@/lib/types"
import { ItineraryView } from "./ItineraryView"

function band(low: number, high: number) {
  return {
    basis: "per_trip" as const,
    confidence: "medium" as const,
    currency: "CNY",
    low,
    high,
  }
}

function sessionFixture(overrides: Partial<PlanningSession> = {}): PlanningSession {
  const session = {
    session_id: "session_1",
    created_at: "2026-05-11T00:00:00",
    updated_at: "2026-05-11T00:00:00",
    parent_session_id: null,
    snapshot_label: null,
    status: "active",
    conversation_history: [],
    hard_constraints: {
      departure_city: "北京",
      departure_date: "2026-06-01",
      destination_city: "上海",
      destination_country_code: "CN",
      duration_days: 3,
      traveler_count: 2,
      total_budget: 6000,
      currency: "CNY",
    },
    discovery_state: {
      selected_card_ids: ["bund"],
      payload: {
        cards: [
          {
            id: "bund",
            name: "The Bund waterfront walk",
            reason: "Classic skyline walk.",
            category: "attraction",
            tags: ["waterfront", "night view"],
            suggested_duration_minutes: 120,
            cost_signal: "free",
            cost_estimate: band(0, 0),
            image_url: "https://images.example/bund.jpg",
            reservation_hint: null,
            enrichment_status: "complete",
            place: null,
          },
        ],
        food_summaries: [],
        area_summaries: [],
        budget_estimate: {
          currency: "CNY",
          user_budget: 6000,
          overrun_flag: false,
          transport: band(600, 900),
          stay: band(1600, 2200),
          food: band(600, 900),
          attractions: band(200, 500),
          other: band(150, 400),
          total: band(3150, 4900),
        },
        source_notes: [],
      },
    },
    preferences: null,
    stay_recommendation: null,
    transport_recommendation: null,
    itinerary: {
      id: "itinerary_1",
      session_id: "session_1",
      version: 1,
      budget: {
        currency: "CNY",
        user_budget: 6000,
        overrun_flag: false,
        transport: band(1100, 1500),
        stay: band(1600, 2200),
        food: band(600, 900),
        attractions: band(200, 500),
        other: band(150, 400),
        total: band(3650, 5500),
      },
      validator_issues: [
        {
          code: "reservation_check",
          severity: "warning",
          scope: { day_index: 1 },
          message: "Museum reservation may be required.",
          suggested_action: "Confirm the opening window.",
        },
      ],
      days: [
        {
          day_index: 1,
          date: "2026-06-01",
          notes: ["Start with a skyline evening."],
          segments: [
            {
              type: "attraction",
              start_time: "10:00",
              end_time: "12:00",
              place: null,
              card_ref: "bund",
              description: "Walk the riverfront and save photo time.",
              cost_estimate: band(0, 0),
            },
            {
              type: "rest",
              start_time: "14:00",
              end_time: "16:00",
              place: null,
              card_ref: null,
              description: "Flexible rest block.",
              cost_estimate: null,
            },
          ],
        },
      ],
    },
    validator_issues: [],
  } as PlanningSession
  return { ...session, ...overrides }
}

describe("ItineraryView", () => {
  it("renders the story-led command center sections", () => {
    render(
      <ItineraryView
        session={sessionFixture()}
        onStayOverride={vi.fn()}
        adjustmentPanel={<div>Adjustment request</div>}
      />
    )

    expect(screen.getByText("Destination story")).toBeInTheDocument()
    expect(screen.getByText("Budget fit")).toBeInTheDocument()
    expect(screen.getByText("Narrative route")).toBeInTheDocument()
    expect(screen.getByRole("region", { name: "Day-by-day execution" })).toBeInTheDocument()
    expect(screen.getByText("Companion brief")).toBeInTheDocument()
    expect(screen.getByText("Adjustment request")).toBeInTheDocument()
    expect(screen.getByText("reservation_check")).toBeInTheDocument()
  })

  it("renders the route texture path when discovery images are missing", () => {
    const base = sessionFixture()
    const cards = base.discovery_state?.payload?.cards ?? []
    const withoutImages = {
      ...base,
      discovery_state: base.discovery_state
        ? {
            ...base.discovery_state,
            payload: base.discovery_state.payload
              ? { ...base.discovery_state.payload, cards: cards.map((card) => ({ ...card, image_url: null })) }
              : null,
          }
        : null,
    }

    render(<ItineraryView session={withoutImages} onStayOverride={vi.fn()} />)

    expect(screen.getByText("Route texture")).toBeInTheDocument()
  })

  it("surfaces budget overrun in the metrics", () => {
    const base = sessionFixture()
    const overBudget = {
      ...base,
      itinerary: base.itinerary
        ? {
            ...base.itinerary,
            budget: {
              ...base.itinerary.budget,
              overrun_flag: true,
              total: band(6400, 7200),
            },
          }
        : null,
    }

    render(<ItineraryView session={overBudget} onStayOverride={vi.fn()} />)

    expect(screen.getByText("Over budget")).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run component tests**

Run:

```bash
cd web
npm run test -- src/components/itinerary/ItineraryView.test.tsx src/components/itinerary/resultPageModel.test.ts
```

Expected: PASS.

- [ ] **Step 3: Update e2e helper assertions**

In `web/e2e/helpers/mvpFlow.ts`, replace the final expectations in `submitPreferences`:

```ts
  await expect(page.getByRole("heading", { name: /Your .* itinerary/ })).toBeVisible({
    timeout: FLOW_EXPECT_TIMEOUT,
  })
  await expect(page.getByText("Final budget")).toBeVisible()
```

with:

```ts
  await expect(page.getByText("Destination story")).toBeVisible({
    timeout: FLOW_EXPECT_TIMEOUT,
  })
  await expect(page.getByText("Budget fit")).toBeVisible()
  await expect(page.getByText("Narrative route")).toBeVisible()
  await expect(page.getByRole("region", { name: "Day-by-day execution" })).toBeVisible()
```

- [ ] **Step 4: Run e2e target**

Run:

```bash
cd web
npm run test:e2e -- mvp-flow.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Commit result page integration**

Run:

```bash
git add web/src/components/itinerary web/src/app/trips/[sessionId]/page.tsx web/e2e/helpers/mvpFlow.ts
git commit -m "feat: redesign itinerary result page"
```

## Task 7: Final Verification

**Files:**

- No planned source edits.

- [ ] **Step 1: Run frontend verification**

Run:

```bash
cd web
npm run typecheck
npm run lint
npm run test -- src/components/itinerary/resultPageModel.test.ts src/components/itinerary/ItineraryView.test.tsx
npm run build
```

Expected: all commands PASS.

- [ ] **Step 2: Run fixture e2e**

Run:

```bash
cd web
npm run test:e2e
```

Expected: PASS.

- [ ] **Step 3: Run full repo regression if time permits**

Run:

```bash
make regression
```

Expected: PASS. If this is too slow for the local environment, record which narrower gates passed and why full regression was skipped.

- [ ] **Step 4: Manual browser check**

Start the app:

```bash
cd web
npm run dev
```

Open `http://localhost:3000`, complete the fixture-backed flow, and verify:

- Hero appears at the top.
- Metrics are visible before detailed days.
- Narrative route appears before detailed days.
- Adjustment panel remains usable.
- Mobile width does not overlap text or controls.

- [ ] **Step 5: Commit verification notes only if code changes were required**

If verification required fixes, commit them with:

```bash
git add web/src web/e2e
git commit -m "fix: stabilize result page redesign"
```

If no fixes were required, do not create an empty commit.

## Self-Review

Spec coverage:

- Destination Story Hero: Task 3 and Task 5.
- Discovery image priority and fallback: Task 2, Task 3, Task 6.
- Decision metrics: Task 2 and Task 3.
- Narrative route: Task 2 and Task 4.
- Day-by-day execution: Task 5.
- Trip spine: Task 4.
- Right rail companion and smart adjustments: Task 4 and Task 5.
- No backend provider changes: all tasks are frontend only.
- Testing: Task 1, Task 6, Task 7.

Placeholder scan:

- The plan avoids deferred implementation language and gives concrete code for each code-writing task.

Type consistency:

- Helper names used in components match exports in `resultPageModel.ts`.
- Component props use existing generated `PlanningSession`, `ItineraryDay`, `ItinerarySegment`, and `ValidatorIssue` types.
