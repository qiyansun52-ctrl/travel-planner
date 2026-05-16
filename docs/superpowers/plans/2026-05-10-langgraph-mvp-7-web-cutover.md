# LangGraph MVP Plan 7 Web Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slim the Next.js app into a UI and route shell that talks directly to the canonical FastAPI routes from Plan 6.

**Architecture:** Python FastAPI owns sessions, discovery, preferences, planning, adjustments, persistence, metrics, providers, and LangGraph orchestration. Next.js keeps only the client pages and reusable UI components for `/`, `/discovery/[sessionId]`, `/preferences/[sessionId]`, and `/trips/[sessionId]`. Until Plan 8 generates TypeScript from Pydantic, `web/src/lib/types.ts` is the temporary UI contract.

**Tech Stack:** Next.js 16 App Router, React 19 client components, TypeScript strict mode, FastAPI Plan 6 canonical routes, browser `fetch`, and text/event-stream parsing for itinerary progress.

---

## Context Notes

- Baseline before Plan 7 execution: `cd web && npm run typecheck` passes, and `cd web && npm run lint` passes.
- Read `web/AGENTS.md` and the bundled Next.js 16 docs at `web/node_modules/next/dist/docs/01-app/03-api-reference/05-config/01-next-config-js/rewrites.md` before editing `next.config.ts`.
- Roadmap line 171 says delete `web/src/app/{plan,discover,discovery}/`, but the same section says to keep the new `discovery/[sessionId]` flow. Treat this as: delete legacy `web/src/app/discover/` and `web/src/app/plan/`, keep `web/src/app/discovery/[sessionId]/`.
- Roadmap line 173 says delete `components/{chat,intake,itinerary}`. Current canonical flow uses `components/intake`, `components/chat`, and `components/itinerary`, so this plan keeps those UI components and only changes their imports from `@/domain/*` to `@/lib/*`.
- Do not add new npm packages in this plan. `concurrently` is not installed; use a POSIX `sh` script in `package.json` for `npm run dev`.

## File Structure

- Modify `web/src/lib/types.ts`: replace legacy plan/discover types with minimal Plan 6 UI types.
- Create `web/src/lib/selection.ts`: move the three pure selection helpers out of `web/src/domain/selection.ts`.
- Create `web/src/lib/apiClient.test.ts`: assert canonical FastAPI endpoint paths, body shapes, API URL default, and stream parsing.
- Modify `web/src/lib/apiClient.ts`: remove legacy `discoverDestination` and `generatePlan`; add canonical route methods and `streamItinerary`.
- Modify kept pages:
  - `web/src/app/discovery/[sessionId]/page.tsx`
  - `web/src/app/preferences/[sessionId]/page.tsx`
  - `web/src/app/trips/[sessionId]/page.tsx`
- Modify kept components:
  - `web/src/components/intake/HardConstraintForm.tsx`
  - `web/src/components/discovery/*.tsx`
  - `web/src/components/preferences/PreferenceForm.tsx`
  - `web/src/components/itinerary/*.tsx`
  - `web/src/components/chat/*.tsx`
- Modify `web/next.config.ts`: add `/api/:path*` rewrite to the Python API.
- Modify `web/package.json`: make `npm run dev` start FastAPI and Next.js together without adding dependencies.
- Modify `web/README.md` and `README.md`: describe the post-cutover web/API development loop.
- Delete legacy backend and UI surfaces:
  - `web/src/server/`
  - `web/src/domain/`
  - `web/src/app/api/`
  - `web/src/app/discover/`
  - `web/src/app/plan/`
  - `web/src/components/discover/`
  - `web/src/components/plan/`
  - `web/src/components/search/`
  - `web/src/hooks/usePlan.ts`
  - `web/src/lib/claude.ts`
  - `web/src/lib/googleSearch.ts`
  - `web/src/lib/planStore.ts`
  - `web/src/__tests__/lib/claude.test.ts`
  - `web/src/__tests__/lib/googleSearch.test.ts`

---

### Task 1: Move UI Types and Selection Helpers Out of `domain`

**Files:**
- Modify: `web/src/lib/types.ts`
- Create: `web/src/lib/selection.ts`
- Modify imports in kept pages and components listed in File Structure
- Test: `web/src/lib/selection.test.ts`

- [ ] **Step 1: Write the failing selection helper test**

Create `web/src/lib/selection.test.ts`:

```ts
import { describe, expect, it } from "vitest"
import {
  hasDensityWarning,
  isContinueDisabled,
  normalizeSelectedCardIds,
} from "./selection"

describe("selection helpers", () => {
  it("normalizes selected card ids without empty values or duplicates", () => {
    expect(normalizeSelectedCardIds(["card-a", "", "card-a", "card-b"])).toEqual([
      "card-a",
      "card-b",
    ])
  })

  it("blocks continuing with no selected cards", () => {
    expect(isContinueDisabled([])).toBe(true)
    expect(isContinueDisabled(["card-a"])).toBe(false)
  })

  it("warns when density is above five stops per day", () => {
    expect(hasDensityWarning(16, 3)).toBe(true)
    expect(hasDensityWarning(15, 3)).toBe(false)
  })
})
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
cd web
npm run test -- src/lib/selection.test.ts
```

Expected: FAIL because `web/src/lib/selection.ts` does not exist.

- [ ] **Step 3: Replace `web/src/lib/types.ts` with Plan 6 minimal UI types**

Use these exported types:

```ts
export interface Coordinate {
  lat: number
  lng: number
}

export type Provider = "amap" | "mapbox" | "baidu" | "google"
export type CostSignal = "free" | "low" | "medium" | "high" | "unknown"
export type Confidence = "high" | "medium" | "low"
export type BudgetBasis =
  | "per_person"
  | "per_party"
  | "per_room_per_night"
  | "per_day"
  | "per_trip"

export interface NormalizedPlace {
  id: string
  name: string
  coordinate: Coordinate | null
  address: string | null
  category: string | null
  provider: Provider
}

export interface BudgetBand {
  currency: string
  low: number
  high: number
  confidence: Confidence
  basis: BudgetBasis
}

export interface BudgetSummary {
  currency: string
  transport: BudgetBand
  stay: BudgetBand
  food: BudgetBand
  attractions: BudgetBand
  other: BudgetBand
  total: BudgetBand
  user_budget: number
  overrun_flag: boolean
}

export interface DiscoveryCard {
  id: string
  name: string
  reason: string
  category: string
  tags: string[]
  suggested_duration_minutes: number
  cost_signal: CostSignal
  cost_estimate: BudgetBand | null
  image_url: string | null
  reservation_hint: string | null
  place: NormalizedPlace | null
  enrichment_status: "complete" | "partial" | "minimal"
}

export interface AreaSummary {
  id: string
  name: string
  vibe_tags: string[]
  note: string
  center: Coordinate
}

export interface FoodSummary {
  id: string
  name: string
  category: string
  description: string
  image_url: string | null
}

export interface SourceNote {
  provider: string
  url: string | null
  note: string
}

export interface DiscoveryOutput {
  cards: DiscoveryCard[]
  food_summaries: FoodSummary[]
  area_summaries: AreaSummary[]
  budget_estimate: BudgetSummary
  source_notes: SourceNote[]
}

export interface StayOption {
  id: string
  area: AreaSummary
  fit_reason: string
  price_band: BudgetBand
  sample_hotels: Array<{
    name: string
    style: string
    price_band: BudgetBand
    place: NormalizedPlace
  }>
}

export interface StayRecommendation {
  primary: StayOption
  alternatives: StayOption[]
  user_override_id: string | null
}

export interface ValidatorIssue {
  code: string
  severity: "warning" | "error"
  scope: Record<string, unknown>
  message: string
  suggested_action: string | null
}

export interface ItinerarySegment {
  type:
    | "attraction"
    | "food"
    | "transit"
    | "rest"
    | "hotel_checkin"
    | "hotel_checkout"
    | "hotel_return"
  start_time: string
  end_time: string
  place: NormalizedPlace | null
  card_ref: string | null
  description: string
  cost_estimate: BudgetBand | null
}

export interface ItineraryDay {
  day_index: number
  date: string
  segments: ItinerarySegment[]
  notes: string[]
}

export interface Itinerary {
  id: string
  session_id: string
  days: ItineraryDay[]
  budget: BudgetSummary
  validator_issues: ValidatorIssue[]
  version: number
}

export interface HardConstraints {
  departure_city: string
  destination_city: string
  destination_country_code: string
  departure_date: string
  duration_days: number
  traveler_count: number
  total_budget: number
  currency: string
}

export interface Preference {
  area_vibe: string
  quiet_vs_lively: "quiet" | "balanced" | "lively"
  stay_type: "hotel" | "homestay" | "flexible"
  willing_to_change_hotels: boolean
  intercity_transport_preference: "rail" | "flight" | "flexible"
  early_departure_tolerance: "low" | "medium" | "high"
  transfer_tolerance: "low" | "medium" | "high"
  pay_more_to_save_time: boolean
}

export interface AdjustmentRequest {
  raw_text: string
  type: "A" | "B" | "C" | "unknown"
  confidence: number
  target_scope:
    | "day"
    | "segment"
    | "stay"
    | "transport"
    | "budget"
    | "duration"
    | "destination"
    | "traveler_count"
    | "none"
  proposed_change: string | null
}

export interface ConversationTurn {
  id: string
  raw_text: string
  classification: AdjustmentRequest | null
  created_at: string
}

export interface DiscoveryState {
  payload: DiscoveryOutput | null
  selected_card_ids: string[]
}

export interface PlanningSession {
  session_id: string
  hard_constraints: HardConstraints
  discovery_state: DiscoveryState | null
  preferences: Preference | null
  stay_recommendation: StayRecommendation | null
  transport_recommendation: unknown | null
  itinerary: Itinerary | null
  conversation_history: Array<ConversationTurn | Record<string, unknown>>
  validator_issues: ValidatorIssue[]
  parent_session_id: string | null
  snapshot_label: string | null
  status: "active" | "archived"
  created_at: string
  updated_at: string
}

export interface PlanningProgressEvent {
  stage: string
  status: "start" | "started" | "finish" | "completed" | "skipped" | "failed" | "error"
  message: string
  payload?: Record<string, unknown>
}
```

- [ ] **Step 4: Create `web/src/lib/selection.ts`**

```ts
export function isContinueDisabled(selectedCardIds: string[]): boolean {
  return normalizeSelectedCardIds(selectedCardIds).length === 0
}

export function hasDensityWarning(selectedCount: number, durationDays: number): boolean {
  return selectedCount > durationDays * 5
}

export function normalizeSelectedCardIds(selectedCardIds: string[]): string[] {
  return Array.from(new Set(selectedCardIds.filter(Boolean)))
}
```

- [ ] **Step 5: Update imports from `@/domain/*`**

Change kept UI imports:

```ts
// before
import { PlanningSession } from "@/domain/schemas"
import { normalizeSelectedCardIds } from "@/domain/selection"

// after
import type { PlanningSession } from "@/lib/types"
import { normalizeSelectedCardIds } from "@/lib/selection"
```

Apply this to all kept files under `web/src/app/{discovery,preferences,trips}/` and `web/src/components/{intake,discovery,preferences,itinerary,chat}/`.

- [ ] **Step 6: Verify the helper and existing component tests**

Run:

```bash
cd web
npm run test -- src/lib/selection.test.ts src/components/intake/HardConstraintForm.test.tsx src/components/preferences/PreferenceForm.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add web/src/lib/types.ts web/src/lib/selection.ts web/src/lib/selection.test.ts web/src/app/discovery web/src/app/preferences web/src/app/trips web/src/components/intake web/src/components/discovery web/src/components/preferences web/src/components/itinerary web/src/components/chat
git commit -m "feat(web): move ui contracts out of domain"
```

---

### Task 2: Cut `apiClient` to Canonical FastAPI Routes

**Files:**
- Modify: `web/src/lib/apiClient.ts`
- Test: `web/src/lib/apiClient.test.ts`

- [ ] **Step 1: Write failing API client tests**

Create `web/src/lib/apiClient.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from "vitest"
import {
  createSession,
  getSession,
  runDiscovery,
  runItinerary,
  savePreferences,
  submitAdjustment,
  updateSelectedCards,
  updateStayOverride,
} from "./apiClient"
import type { HardConstraints, Preference } from "./types"

const hardConstraints: HardConstraints = {
  departure_city: "北京",
  destination_city: "上海",
  destination_country_code: "CN",
  departure_date: "2026-05-10",
  duration_days: 3,
  traveler_count: 2,
  total_budget: 6000,
  currency: "CNY",
}

const preferences: Preference = {
  area_vibe: "central",
  quiet_vs_lively: "balanced",
  stay_type: "hotel",
  willing_to_change_hotels: false,
  intercity_transport_preference: "rail",
  early_departure_tolerance: "medium",
  transfer_tolerance: "medium",
  pay_more_to_save_time: false,
}

function mockJsonResponse(payload: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(payload),
  } as Response)
}

describe("apiClient", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("uses the Python API URL by default", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse({ session_id: "s1" }))

    await createSession(hardConstraints)

    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/api/sessions")
  })

  it("maps session workflow calls to canonical nested routes", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse({ session_id: "s1" }))

    await getSession("s1")
    await runDiscovery("s1")
    await updateSelectedCards("s1", ["card-a"])
    await savePreferences("s1", preferences)
    await runItinerary("s1")
    await updateStayOverride("s1", "stay-a")
    await submitAdjustment({ sessionId: "s1", message: "Make day two lighter", typeCAction: "replan" })

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "http://localhost:8000/api/sessions/s1",
      "http://localhost:8000/api/sessions/s1/discovery",
      "http://localhost:8000/api/sessions/s1/selection",
      "http://localhost:8000/api/sessions/s1/preferences",
      "http://localhost:8000/api/sessions/s1/itinerary",
      "http://localhost:8000/api/sessions/s1/stay-override",
      "http://localhost:8000/api/sessions/s1/adjustments",
    ])
  })
})
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
cd web
npm run test -- src/lib/apiClient.test.ts
```

Expected: FAIL because the current client still calls legacy same-origin routes.

- [ ] **Step 3: Replace `web/src/lib/apiClient.ts`**

Use these route functions and keep the exported `AdjustmentResponse`:

```ts
"use client"

import type {
  AdjustmentRequest,
  HardConstraints,
  PlanningProgressEvent,
  PlanningSession,
  Preference,
} from "@/lib/types"

const DEFAULT_API_URL = "http://localhost:8000"
const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL).replace(/\/$/, "")

function apiUrl(path: string): string {
  return `${API_URL}${path}`
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  })
  if (!res.ok) throw new Error(`${init?.method ?? "GET"} ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export async function createSession(body: HardConstraints): Promise<PlanningSession> {
  return fetchJson<PlanningSession>("/api/sessions", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export async function getSession(sessionId: string): Promise<PlanningSession> {
  return fetchJson<PlanningSession>(`/api/sessions/${sessionId}`, { cache: "no-store" })
}

export async function runDiscovery(sessionId: string): Promise<PlanningSession> {
  return fetchJson<PlanningSession>(`/api/sessions/${sessionId}/discovery`, { method: "POST" })
}

export async function updateSelectedCards(
  sessionId: string,
  selectedCardIds: string[]
): Promise<PlanningSession> {
  return fetchJson<PlanningSession>(`/api/sessions/${sessionId}/selection`, {
    method: "PATCH",
    body: JSON.stringify({ selected_card_ids: selectedCardIds }),
  })
}

export async function savePreferences(
  sessionId: string,
  preferences: Preference
): Promise<PlanningSession> {
  return fetchJson<PlanningSession>(`/api/sessions/${sessionId}/preferences`, {
    method: "POST",
    body: JSON.stringify({ preferences }),
  })
}

export async function runItinerary(sessionId: string): Promise<PlanningSession> {
  return fetchJson<PlanningSession>(`/api/sessions/${sessionId}/itinerary`, {
    method: "POST",
    body: JSON.stringify({}),
  })
}

export async function updateStayOverride(
  sessionId: string,
  stayOptionId: string | null
): Promise<PlanningSession> {
  return fetchJson<PlanningSession>(`/api/sessions/${sessionId}/stay-override`, {
    method: "PATCH",
    body: JSON.stringify({ stay_option_id: stayOptionId }),
  })
}

export interface AdjustmentResponse {
  session: PlanningSession
  classification: AdjustmentRequest
  message: string
  confirmation?: {
    detected_change: string
    rerun_stages: string[]
    discard_estimate: string
  } | null
}

export async function submitAdjustment(input: {
  sessionId: string
  message: string
  typeCAction?: "replan" | "save_and_start_new" | "cancel"
}): Promise<AdjustmentResponse> {
  return fetchJson<AdjustmentResponse>(`/api/sessions/${input.sessionId}/adjustments`, {
    method: "POST",
    body: JSON.stringify({
      message: input.message,
      type_c_action: input.typeCAction,
    }),
  })
}

export async function streamItinerary(
  sessionId: string,
  handlers: { onProgress?: (event: PlanningProgressEvent) => void } = {}
): Promise<PlanningSession> {
  const res = await fetch(apiUrl(`/api/sessions/${sessionId}/itinerary/stream`), {
    headers: { Accept: "text/event-stream" },
    cache: "no-store",
  })
  if (!res.ok) throw new Error(`GET /api/sessions/${sessionId}/itinerary/stream failed: ${res.status}`)
  if (!res.body) throw new Error("Itinerary stream did not include a readable body")

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split("\n\n")
    buffer = frames.pop() ?? ""
    for (const frame of frames) {
      const result = parseSseFrame(frame)
      if (!result) continue
      if (result.event === "progress") handlers.onProgress?.(result.data as PlanningProgressEvent)
      if (result.event === "complete") return (result.data as { session: PlanningSession }).session
      if (result.event === "error") throw new Error(String((result.data as { message?: string }).message ?? "Itinerary stream failed"))
    }
  }

  throw new Error("Itinerary stream ended before completion")
}

function parseSseFrame(frame: string): { event: string; data: unknown } | null {
  const event = frame
    .split("\n")
    .find((line) => line.startsWith("event: "))
    ?.slice("event: ".length)
  const data = frame
    .split("\n")
    .filter((line) => line.startsWith("data: "))
    .map((line) => line.slice("data: ".length))
    .join("\n")
  if (!event || !data) return null
  return { event, data: JSON.parse(data) as unknown }
}
```

- [ ] **Step 4: Verify the API client contract**

Run:

```bash
cd web
npm run test -- src/lib/apiClient.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/apiClient.ts web/src/lib/apiClient.test.ts
git commit -m "feat(web): target canonical fastapi routes"
```

---

### Task 3: Show Plan 6 SSE Progress in the Trip Page

**Files:**
- Modify: `web/src/app/trips/[sessionId]/page.tsx`
- Modify: `web/src/components/itinerary/PlanningProgress.tsx`

- [ ] **Step 1: Update `PlanningProgress` to render live events**

Change the component signature:

```ts
import type { PlanningProgressEvent } from "@/lib/types"

export function PlanningProgress({
  active,
  events = [],
}: {
  active: boolean
  events?: PlanningProgressEvent[]
}) {
  const latest = events.at(-1)
  const steps = [
    { id: "stay", label: "Recommending stay areas" },
    { id: "transport", label: "Analyzing transport" },
    { id: "planner", label: "Generating final itinerary" },
    { id: "validator", label: "Checking constraints" },
  ]

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">Planning progress</h2>
          {latest && <p className="mt-1 text-sm text-slate-600">{latest.message}</p>}
        </div>
        <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
          {active ? "Running" : "Idle"}
        </span>
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-4">
        {steps.map((step) => {
          const matching = events.findLast((event) => event.stage === step.id)
          const isCurrent = latest?.stage === step.id && active
          return (
            <div
              key={step.id}
              className={`rounded-md px-3 py-2 text-sm ${
                isCurrent
                  ? "bg-sky-50 text-sky-900"
                  : matching?.status === "finish"
                    ? "bg-emerald-50 text-emerald-900"
                    : "bg-slate-50 text-slate-600"
              }`}
            >
              <span className="block font-medium">{step.label}</span>
              {matching && <span className="mt-1 block text-xs capitalize">{matching.status}</span>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Use `streamItinerary` from the trip page**

In `web/src/app/trips/[sessionId]/page.tsx`, import `PlanningProgressEvent` and `streamItinerary`, add progress state, and replace `runItinerary(sessionId)`:

```ts
import type { PlanningProgressEvent, PlanningSession } from "@/lib/types"
import { getSession, streamItinerary, updateStayOverride } from "@/lib/apiClient"

const [progressEvents, setProgressEvents] = useState<PlanningProgressEvent[]>([])

const planned = await streamItinerary(sessionId, {
  onProgress: (event) => {
    if (active) setProgressEvents((events) => [...events, event])
  },
})
```

Render:

```tsx
<PlanningProgress active={planning || !session?.itinerary} events={progressEvents} />
```

- [ ] **Step 3: Verify the trip page typecheck**

Run:

```bash
cd web
npm run typecheck
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add 'web/src/app/trips/[sessionId]/page.tsx' web/src/components/itinerary/PlanningProgress.tsx
git commit -m "feat(web): display itinerary stream progress"
```

---

### Task 4: Delete Legacy Next.js Server, API Routes, and Old UI

**Files:**
- Delete the legacy paths listed in File Structure
- Modify: any import references surfaced by `rg`

- [ ] **Step 1: Confirm references before deletion**

Run:

```bash
rg -n "discoverDestination|generatePlan|@/server|@/domain|@/components/(discover|plan|search)|@/lib/(claude|googleSearch|planStore)|usePlan" web/src
```

Expected: only files planned for deletion should appear.

- [ ] **Step 2: Delete legacy files and directories**

Remove:

```bash
web/src/server/
web/src/domain/
web/src/app/api/
web/src/app/discover/
web/src/app/plan/
web/src/components/discover/
web/src/components/plan/
web/src/components/search/
web/src/hooks/usePlan.ts
web/src/lib/claude.ts
web/src/lib/googleSearch.ts
web/src/lib/planStore.ts
web/src/__tests__/lib/claude.test.ts
web/src/__tests__/lib/googleSearch.test.ts
```

- [ ] **Step 3: Verify no legacy imports remain**

Run:

```bash
rg -n "discoverDestination|generatePlan|@/server|@/domain|@/components/(discover|plan|search)|@/lib/(claude|googleSearch|planStore)|usePlan" web/src
```

Expected: no output.

- [ ] **Step 4: Run web typecheck and lint**

Run:

```bash
cd web
npm run typecheck
npm run lint
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A web/src
git commit -m "chore(web): remove legacy next server surfaces"
```

---

### Task 5: Configure Web Development Against FastAPI

**Files:**
- Modify: `web/next.config.ts`
- Modify: `web/package.json`
- Modify: `web/README.md`
- Modify: `README.md`

- [ ] **Step 1: Add the `/api/:path*` rewrite**

Modify `web/next.config.ts`:

```ts
import type { NextConfig } from "next"

const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "")

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.50.100.1", "127.0.0.1"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
```

- [ ] **Step 2: Update package scripts without new dependencies**

Modify `web/package.json` scripts:

```json
{
  "dev": "sh -c 'cd ../api && uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000 & api_pid=$!; trap \"kill $api_pid\" EXIT INT TERM; next dev'",
  "dev:web": "next dev",
  "dev:api": "cd ../api && uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000",
  "build": "next build",
  "start": "next start",
  "test": "vitest run",
  "test:watch": "vitest",
  "test:e2e": "playwright test",
  "lint": "eslint .",
  "typecheck": "tsc --noEmit"
}
```

- [ ] **Step 3: Update docs**

Update `web/README.md`:

```md
# Travel Planner Web

Next.js UI and route shell for the single-city planner. Planning logic, sessions, persistence, metrics, providers, and LangGraph orchestration live in `../api`.

## Development

```bash
cd web
npm run dev
```

The dev script starts FastAPI on `http://127.0.0.1:8000` and Next.js on `http://localhost:3000`. The browser client defaults `NEXT_PUBLIC_API_URL` to `http://localhost:8000`; set it explicitly if your API runs elsewhere.
```

Update root `README.md` so it says `web/` has no Next.js API routes or server agents after Plan 7.

- [ ] **Step 4: Verify config files**

Run:

```bash
cd web
npm run typecheck
npm run lint
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/next.config.ts web/package.json web/README.md README.md
git commit -m "chore(web): point dev shell at fastapi"
```

---

### Task 6: Full Acceptance

**Files:**
- No planned code changes unless acceptance finds a regression.

- [ ] **Step 1: Run frontend unit and static checks**

Run:

```bash
cd web
npm run test
npm run typecheck
npm run lint
npm run build
```

Expected: all PASS.

- [ ] **Step 2: Run backend regression checks**

Run:

```bash
cd api
uv run pytest -v
uv run ruff check app tests
```

Expected: all PASS.

- [ ] **Step 3: Run a real FastAPI smoke flow**

Start API:

```bash
cd api
GEMINI_API_KEY=test-gemini TAVILY_API_KEY=test-tavily E2E_FIXTURE_MODE=1 SESSION_DATA_DIR=/private/tmp/travel-planner-plan7-smoke/sessions METRICS_DATA_DIR=/private/tmp/travel-planner-plan7-smoke/metrics uv run uvicorn main:app --host 127.0.0.1 --port 8766
```

In another shell:

```bash
cd api
BASE_URL=http://127.0.0.1:8766 bash scripts/smoke_curl.sh
```

Expected: `Smoke flow passed for <session id>`.

- [ ] **Step 4: Verify frontend talks to Python routes**

Start API in fixture mode on port 8000, then run the web app:

```bash
cd api
GEMINI_API_KEY=test-gemini TAVILY_API_KEY=test-tavily E2E_FIXTURE_MODE=1 SESSION_DATA_DIR=/private/tmp/travel-planner-plan7-web/sessions METRICS_DATA_DIR=/private/tmp/travel-planner-plan7-web/metrics uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

```bash
cd web
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev:web
```

Manual browser path:

```text
/ -> submit hard constraints -> /discovery/[sessionId] -> choose at least one card -> /preferences/[sessionId] -> submit preferences -> /trips/[sessionId]
```

Expected: `/trips/[sessionId]` shows a generated itinerary and no request hits a Next.js `web/src/app/api` route because that directory no longer exists.

- [ ] **Step 5: Verify legacy directories are gone**

Run:

```bash
test ! -d web/src/server
test ! -d web/src/domain
test ! -d web/src/app/api
test ! -d web/src/app/discover
test ! -d web/src/app/plan
```

Expected: all commands exit 0.

- [ ] **Step 6: Final review and commit if acceptance required fixes**

Run:

```bash
git status --short
git diff --check origin/feature/mvp-web-app...HEAD
```

Expected: no unstaged files except intentional final fixes, and no whitespace errors.

If acceptance fixes were needed:

```bash
git add -A
git commit -m "fix(web): complete fastapi cutover acceptance"
```

---

## Self-Review

- **Spec coverage:** Plan 7 roadmap deletion, rewrite, API client cutover, dev script, minimal types, and DoD checks are covered.
- **Adjusted roadmap ambiguity:** Keeps active canonical `discovery/[sessionId]`, `intake`, `itinerary`, and `chat` UI because the current main flow imports them.
- **Placeholder scan:** No red-flag placeholders or undefined follow-up tasks remain.
- **Type consistency:** UI imports use `@/lib/types`, selection imports use `@/lib/selection`, and API client endpoints match Plan 6 route files.
