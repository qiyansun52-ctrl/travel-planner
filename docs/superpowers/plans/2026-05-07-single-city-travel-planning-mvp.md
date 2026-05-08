# Single-City Travel Planning MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-city travel planning MVP that starts with hard constraints, produces an engaging destination discovery page, collects stay and transport preferences, generates a realistic budget-aware itinerary, and supports conversational partial replanning.

**Architecture:** Build a Next.js App Router web app with a thin UI layer, typed domain contracts, server-side anonymous session storage, provider adapters, and an orchestrated four-agent planning pipeline. Keep all product-facing data in normalized TypeScript/Zod schemas so the UI, validator, persistence, and future live suppliers do not depend on any one provider or prompt shape.

**Tech Stack:** Next.js App Router, React, TypeScript, Tailwind CSS, Zod, Vitest, React Testing Library, Playwright, server-side session repository, provider adapter interfaces, LLM JSON-mode style outputs validated by schemas.

---

## Product Decisions Locked By This Plan

- The first usable MVP is a **vertical slice**, not a broad demo: Step 1 intake -> discovery -> preferences -> itinerary -> adjustment.
- Discovery is the primary inspiration surface. Hotels, restaurants, and transport are not selected during discovery.
- Budget is visible from discovery onward, but remains estimate-grade and band-based.
- `validator` is deterministic TypeScript, not an LLM agent.
- Post-generation chat is routed through adjustment classification before any agent reruns.
- Persistence is server-side and session-scoped. The browser stores only an opaque `session_id`.
- Provider choices sit behind interfaces from day one. UI and agents consume normalized shapes only.
- Existing `travel-template.html` remains useful as a later export template, but it is not part of the first core planning loop.

---

## Recommended Milestones

1. **Foundation:** scaffold app, shared schemas, budget utilities, validator tests.
2. **Session Backbone:** anonymous server-side planning session repository and APIs.
3. **Infrastructure:** provider abstraction, LLM client wrapper, retry, JSON repair, and cost logging.
4. **Discovery Slice:** Step 1 intake, discovery agent, discovery page, selection gate, discovery budget estimate.
5. **Planning Slice:** preferences page, stay agent, transport agent, planner agent, stage progress, final itinerary page.
6. **Adjustment Slice:** classifier, Type A/B/C routing, partial replanning, confirmation card for root changes.
7. **Reliability Slice:** provider fallbacks, residual validator issue rendering, metrics events, Playwright coverage.

Each milestone should leave the app runnable and testable.

---

## File Map

```text
web/
├── .env.example
├── package.json
├── next.config.ts
├── tailwind.config.ts
├── vitest.config.ts
├── playwright.config.ts
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── discovery/[sessionId]/page.tsx
│   │   ├── preferences/[sessionId]/page.tsx
│   │   ├── trips/[sessionId]/page.tsx
│   │   └── api/
│   │       ├── sessions/route.ts
│   │       ├── sessions/[sessionId]/route.ts
│   │       ├── sessions/[sessionId]/stay-override/route.ts
│   │       ├── discovery/route.ts
│   │       ├── preferences/route.ts
│   │       ├── itinerary/route.ts
│   │       └── adjustments/route.ts
│   ├── components/
│   │   ├── intake/HardConstraintForm.tsx
│   │   ├── discovery/DiscoveryBoard.tsx
│   │   ├── discovery/DiscoveryCardGrid.tsx
│   │   ├── discovery/DiscoveryCard.tsx
│   │   ├── discovery/FoodSummaryList.tsx
│   │   ├── discovery/AreaImpressionList.tsx
│   │   ├── discovery/BudgetBandPanel.tsx
│   │   ├── preferences/PreferenceForm.tsx
│   │   ├── itinerary/PlanningProgress.tsx
│   │   ├── itinerary/ItineraryView.tsx
│   │   ├── itinerary/ItineraryDayCard.tsx
│   │   ├── itinerary/StayAreaSwitcher.tsx
│   │   ├── itinerary/ValidatorIssueNote.tsx
│   │   ├── chat/AdjustmentPanel.tsx
│   │   ├── chat/TypeCConfirmationCard.tsx
│   │   └── ui/
│   ├── domain/
│   │   ├── schemas.ts
│   │   ├── budget.ts
│   │   ├── dates.ts
│   │   ├── geography.ts
│   │   ├── selection.ts
│   │   └── validator.ts
│   ├── server/
│   │   ├── agents/
│   │   │   ├── types.ts
│   │   │   ├── prompts.ts
│   │   │   ├── discovery.ts
│   │   │   ├── stay.ts
│   │   │   ├── transport.ts
│   │   │   ├── planner.ts
│   │   │   ├── adjustmentClassifier.ts
│   │   │   └── orchestrator.ts
│   │   ├── llm/
│   │   │   ├── client.ts
│   │   │   ├── retry.ts
│   │   │   ├── jsonRepair.ts
│   │   │   └── costLogger.ts
│   │   ├── persistence/
│   │   │   ├── sessionRepository.ts
│   │   │   ├── fileSessionRepository.ts
│   │   │   └── cookies.ts
│   │   ├── providers/
│   │   │   ├── types.ts
│   │   │   ├── registry.ts
│   │   │   ├── search/
│   │   │   ├── map/
│   │   │   │   ├── amap.ts
│   │   │   │   ├── mapbox.ts
│   │   │   │   └── coordinateConversion.ts
│   │   │   ├── weather/
│   │   │   └── supplier/
│   │   └── metrics/events.ts
│   └── test/
│       ├── fixtures/
│       └── setup.ts
└── e2e/
    ├── discovery-flow.spec.ts
    ├── itinerary-flow.spec.ts
    └── adjustment-flow.spec.ts
```

`ui/` is for shared UI primitives such as `Button`, `Input`, `Card`, and `Textarea`. Add primitives only when a task needs them so the component layer does not grow before the product flow proves what it needs.

---

## Task 0: Prepare Development Environment

**Files:**
- Create: `web/.env.example`
- Create: `web/docs/development-environment.md`
- Modify: `.gitignore`

- [ ] Document the minimum local requirements:
  - Node.js LTS version.
  - Package manager used by the scaffolded app.
  - Required API keys and where to obtain them: LLM provider, search provider, Mapbox, AMap, weather provider.
  - Local-only data directory: `web/.data/`.
- [ ] Add ignored local files and folders:
  - `web/.env.local`
  - `web/.data/`
  - `web/test-results/`
  - `web/playwright-report/`
- [ ] Create a `web/.env.example` template with these exact variable names and empty values:

```bash
LLM_PROVIDER_API_KEY=
SEARCH_PROVIDER_API_KEY=
MAPBOX_ACCESS_TOKEN=
AMAP_API_KEY=
WEATHER_PROVIDER_API_KEY=
```

- [ ] Add a short "minimum runnable mode" note: fixture-backed tests and E2E can run without live provider keys; live discovery and planning require keys.
- [ ] Commit as `docs: add development environment checklist`.

**Acceptance Criteria:**
- A new engineer knows which keys are needed before starting Task 1.
- Local generated session, metrics, and LLM cost files cannot be accidentally committed.

---

## Task 1: Scaffold The Web App

**Files:**
- Create: `web/`
- Create: `web/src/app/layout.tsx`
- Create: `web/src/app/page.tsx`
- Create: `web/src/test/setup.ts`

- [ ] Create a Next.js App Router project under `web/` with TypeScript and Tailwind.
- [ ] Add Vitest, React Testing Library, Playwright, Zod, and a small class-name helper if the UI components need one.
- [ ] Configure path alias `@/* -> src/*`.
- [ ] Add scripts:
  - `dev`: start local app
  - `test`: run Vitest
  - `test:e2e`: run Playwright
  - `lint`: run framework linting
  - `typecheck`: run `tsc --noEmit`
- [ ] Replace the default page with a placeholder shell at `/`. The real intake form lands in Task 7.
- [ ] Run `npm run test`, `npm run typecheck`, and `npm run lint`.
- [ ] Commit as `feat: scaffold travel planner web app`.

**Acceptance Criteria:**
- `web/` starts locally.
- Tests and typecheck have runnable scripts from day one.

---

## Task 2: Add Normalized Domain Schemas

**Files:**
- Create: `web/src/domain/schemas.ts`
- Test: `web/src/domain/schemas.test.ts`

- [ ] Define Zod schemas and exported TypeScript types for:
  - `Coordinate`
  - `NormalizedPlace` with `coordinate: Coordinate | null` and a code comment that coordinates are always WGS84 once inside the system.
  - `NormalizedRoute`
  - `BudgetBand` with required `basis: per_person | per_party | per_room_per_night | per_day | per_trip`.
  - `DiscoveryCard` with `place: NormalizedPlace | null` and `enrichment_status: complete | partial | minimal`.
  - `AreaSummary`
  - `StayOption`
  - `StayRecommendation` as `{ primary: StayOption, alternatives: StayOption[], user_override_id: string | null }`.
  - `SampleHotel`
  - `TransportRecommendation`
  - `TransportLeg`
  - `IntracityStrategy`
  - `FoodSummary` as `{ id, name, category, description, image_url: string | null }`.
  - `SourceNote` as `{ provider, url: string | null, note }`.
  - `DiscoveryOutput` as `{ cards, food_summaries, area_summaries, budget_estimate, source_notes }`.
  - `Itinerary`
  - `ItineraryDay`
  - `ItinerarySegment` with the extended enum `attraction | food | transit | rest | hotel_checkin | hotel_checkout | hotel_return`.
  - `BudgetSummary` with `overrun_flag: boolean`.
  - `AdjustmentRequest`
  - `ValidatorIssue`
  - `PlanningSession` with `parent_session_id: string | null`, `snapshot_label: string | null`, and `status: active | archived`.
- [ ] Match the field names and enum values from the MVP document exactly.
- [ ] Add `HardConstraintsSchema` with:
  - `departure_city`
  - `destination_city`
  - `destination_country_code` as ISO 3166-1 alpha-2, resolved at intake in Task 7.
  - `departure_date`
  - `duration_days`
  - `traveler_count`
  - `total_budget`
  - `currency`
- [ ] Add `PreferenceSchema` with stay and transport preference fields from Step 4.
- [ ] Add parsing tests that prove valid fixture payloads pass and renamed or mistyped fields fail.
- [ ] Add explicit tests for:
  - `BudgetBand.basis` is required.
  - `DiscoveryCard.place` accepts `null`.
  - `StayRecommendation.user_override_id` accepts `null`.
  - `ItinerarySegment.type` rejects values outside the extended enum.
- [ ] Commit as `feat: add normalized travel planning schemas`.

**Acceptance Criteria:**
- All agent outputs, API payloads, persisted session records, and UI props can import from one schema source.
- Invalid enum values such as `hotel` for `NormalizedPlace.provider` fail fast.
- No later agent task defines ad-hoc product schemas.

---

## Task 3: Add Budget Utilities

**Files:**
- Create: `web/src/domain/budget.ts`
- Test: `web/src/domain/budget.test.ts`

- [ ] Export `DEFAULT_ATTRACTION_SHARE = 0.15` as the single source of truth.
- [ ] Implement `calculateDailyAttractionSlot(totalBudget, durationDays, travelerCount, attractionShare?)`.
- [ ] Implement `classifyAttractionCostSignal(costEstimate, hardConstraints, attractionShare?)`.
- [ ] Return `unknown` when raw cost data is missing.
- [ ] Implement `toPerTripBand(band, context)` for supported bases:
  - `per_person`
  - `per_party`
  - `per_room_per_night`
  - `per_day`
  - `per_trip`
- [ ] Require conversion context to include `traveler_count`, `duration_days`, and `room_count`. If `room_count` is not explicit, estimate it from traveler count in the caller before conversion.
- [ ] Reject conversions that lack required context fields.
- [ ] Implement `sumBudgetBands(currency, bands)` with low/high summation and confidence degradation to the lowest confidence present.
- [ ] Require all input bands to already use `per_trip` basis; reject mixed-basis inputs.
- [ ] Add tests for the exact thresholds:
  - `free`: cost is `0`
  - `low`: cost is `<= 30%` of daily attraction slot
  - `medium`: cost is `> 30%` and `<= 80%`
  - `high`: cost is `> 80%`
- [ ] Add tests for basis conversion:
  - `per_room_per_night` -> `per_trip` requires `room_count` and `duration_days`.
  - `per_person` -> `per_trip` requires `traveler_count`.
  - Mixed-basis sum fails.
- [ ] Commit as `feat: add budget band and cost signal utilities`.

**Acceptance Criteria:**
- Cost signal behavior is deterministic and does not depend on an LLM prompt.
- The same attraction can classify differently for different budgets.
- Budget aggregation cannot silently mix `per_person` and `per_trip` bands.

---

## Task 4: Add Deterministic Validator

**Files:**
- Create: `web/src/domain/validator.ts`
- Test: `web/src/domain/validator.test.ts`

- [ ] Implement `validateItinerary(itinerary, context)` returning `ValidatorIssue[]`.
- [ ] Implement `BUDGET_OVERRUN`: error when `budget.total.high > user_budget * 1.15`.
- [ ] Implement `DAY_OVERLOADED`: warning when a day has more than 8 attraction active hours or more than 5 attraction stops.
- [ ] Implement `WASTEFUL_ROUTING`: warning when a day's transit movement time exceeds 40% of active attraction hours.
- [ ] Implement `TIMING_UNREALISTIC`: error when a reservation-required attraction is outside a known operating window, or segment duration is under 50% of the discovery card suggested duration.
- [ ] Ensure the validator is pure: never mutates itinerary input, never reads global state, and never tracks corrective pass count.
- [ ] Keep corrective-loop pass count in the orchestrator from Task 11, not in the validator.
- [ ] Add tests with fixture itineraries for each issue code and one no-issue itinerary.
- [ ] Add a purity test proving two calls with the same input return identical results.
- [ ] Commit as `feat: add itinerary validator`.

**Acceptance Criteria:**
- Validator output is issue-only and contains stable `code`, `severity`, `scope`, `message`, and `suggested_action`.
- Calling `validateItinerary` twice on the same input returns identical results.

---

## Task 5: Add Server-Side Session Persistence

**Files:**
- Create: `web/src/server/persistence/sessionRepository.ts`
- Create: `web/src/server/persistence/fileSessionRepository.ts`
- Create: `web/src/server/persistence/cookies.ts`
- Create: `web/src/app/api/sessions/route.ts`
- Create: `web/src/app/api/sessions/[sessionId]/route.ts`
- Test: `web/src/server/persistence/sessionRepository.test.ts`

- [ ] Define `SessionRepository` methods:
  - `create(hardConstraints) -> Promise<PlanningSession>`.
  - `get(sessionId) -> Promise<PlanningSession | null>`.
  - `updateDiscovery(sessionId, discoveryState) -> Promise<PlanningSession>`.
  - `updatePreferences(sessionId, preferences) -> Promise<PlanningSession>`.
  - `writeItinerary(sessionId, itinerary, validatorIssues) -> Promise<PlanningSession>`.
  - `appendConversationTurn(sessionId, turn) -> Promise<PlanningSession>`.
  - `updateStayOverride(sessionId, stayOptionId | null) -> Promise<PlanningSession>` to set `StayRecommendation.user_override_id`.
  - `resetToStep(sessionId, step: "intake" | "discovery", updatedConstraints?) -> Promise<PlanningSession>` to keep the session id and clear downstream state from the chosen step onward.
  - `archiveAndFork(sessionId, snapshotLabel, newHardConstraints) -> Promise<PlanningSession>` to archive the original session and return a new active linked session with `parent_session_id` set.
  - `updateSnapshotLabel(sessionId, snapshotLabel) -> Promise<PlanningSession>`.
- [ ] Implement a file-backed repository at `web/.data/sessions.json` for local MVP use.
- [ ] Keep `session_id` opaque and generated server-side.
- [ ] Set a long-lived client cookie named `travel_session_id` after first hard-constraint submission.
- [ ] Reject agent write attempts to archived sessions, except snapshot label edits.
- [ ] Add route handlers:
  - `POST /api/sessions`: create session from hard constraints.
  - `GET /api/sessions/[sessionId]`: return session state.
- [ ] Add tests for:
  - create.
  - write.
  - last-write-wins update behavior.
  - `resetToStep` clears downstream state.
  - `archiveAndFork` creates a linked new session.
  - archived session rejects mutation except snapshot label edits.
- [ ] Commit as `feat: add anonymous session persistence`.

**Acceptance Criteria:**
- Refreshing a page can restore the latest session from server state.
- Browser state is not the canonical source of trip data.
- Type C `Replan` and `Save and start new` map to distinct repository methods with different state outcomes.

---

## Task 6: Add Provider Abstraction Layer

**Files:**
- Create: `web/src/server/providers/types.ts`
- Create: `web/src/server/providers/registry.ts`
- Create: `web/src/server/providers/map/coordinateConversion.ts`
- Create: `web/src/server/providers/map/amap.ts`
- Create: `web/src/server/providers/map/mapbox.ts`
- Create: `web/src/server/providers/search/index.ts`
- Create: `web/src/server/providers/weather/index.ts`
- Create: `web/src/server/providers/supplier/index.ts`
- Create: `web/src/domain/geography.ts`
- Test: `web/src/server/providers/map/coordinateConversion.test.ts`
- Test: `web/src/server/providers/registry.test.ts`

- [ ] Define interfaces:
  - `SearchProvider`
  - `MapProvider`
  - `WeatherProvider`
  - `SupplierProvider`
- [ ] Define provider methods around normalized outputs, not raw vendor payloads.
- [ ] Implement `isChinaDestination(countryCode: string)` in `web/src/domain/geography.ts` as a strict `CN` match.
- [ ] Do not use city-name string matching for geography routing.
- [ ] Read `countryCode` from `HardConstraints.destination_country_code`, which is resolved during intake in Task 7.
- [ ] Implement provider routing:
  - China map primary: AMap.
  - International map primary: Mapbox.
  - Fallback selection by adapter health result.
- [ ] Define MVP fallback behavior explicitly:
  - attempt the primary provider once.
  - treat timeout, network failure, unhealthy health result, auth failure, or invalid normalized payload as a provider failure.
  - if a fallback provider exists, attempt the fallback once.
  - if fallback also fails, return a typed provider error to the caller; do not invent data.
  - no hidden provider retry loop in MVP. More advanced retries can be added behind the same provider interface later.
- [ ] Implement GCJ02 -> WGS84 conversion for AMap outputs before creating `NormalizedPlace`.
- [ ] Ensure provider adapters convert all coordinates to WGS84 before producing `NormalizedPlace`.
- [ ] Ensure raw provider payloads, if retained for debugging, live only under `raw_payload` fields that are never consumed by agents or UI.
- [ ] Add tests that AMap adapter never returns GCJ02 coordinates as normalized coordinates.
- [ ] Add registry tests for:
  - primary provider timeout triggers fallback.
  - primary provider invalid normalized payload triggers fallback.
  - fallback failure returns a typed provider error.
- [ ] Add deterministic fixture providers for tests only.
- [ ] Commit as `feat: add travel data provider abstraction`.

**Acceptance Criteria:**
- No UI or agent file imports a concrete provider adapter directly.
- Coordinate math and map rendering only see WGS84.
- Provider routing depends on country code, never on city-name string matching.
- Provider fallback behavior is deterministic and testable.

---

## Task 6.5: Build LLM Client Wrapper

**Files:**
- Create: `web/src/server/llm/client.ts`
- Create: `web/src/server/llm/retry.ts`
- Create: `web/src/server/llm/jsonRepair.ts`
- Create: `web/src/server/llm/costLogger.ts`
- Test: `web/src/server/llm/client.test.ts`
- Test: `web/src/server/llm/jsonRepair.test.ts`

- [ ] Implement `callLLM({ system, user, schema, label, timeoutMs? })`.
- [ ] Return parsed output validated against the provided Zod schema.
- [ ] Retry up to 2 times on transient network errors with exponential backoff.
- [ ] Apply one structured JSON repair pass when initial parsing fails:
  - strip leading and trailing non-JSON text.
  - fix common trailing comma issues.
  - re-validate against the provided schema.
- [ ] Throw after all retries and repair attempts fail; never return silent fallback content.
- [ ] Apply a default 30 second timeout, configurable per call.
- [ ] Log every call to `web/.data/llm-cost.jsonl` with:
  - `label`
  - prompt token count estimate
  - completion token count estimate
  - duration
  - success or failure
  - retry count
- [ ] Ensure cost logging never throws or blocks the LLM call.
- [ ] Centralize LLM provider key configuration here so agents never read environment variables directly.
- [ ] Add tests for:
  - schema validation success path.
  - JSON repair recovers malformed output.
  - retry on transient failure.
  - timeout enforcement.
  - cost log entry shape.
- [ ] Commit as `feat: add LLM client wrapper with retry and structured output`.

**Acceptance Criteria:**
- Every agent in Tasks 8, 11, and 13 calls LLMs exclusively through this wrapper.
- LLM costs and failure rates are observable from `web/.data/llm-cost.jsonl`.
- Invalid JSON from the LLM does not propagate to downstream code.

---

## Task 7: Build Hard-Constraint Intake

**Files:**
- Create: `web/src/components/intake/HardConstraintForm.tsx`
- Modify: `web/src/app/page.tsx`
- Test: `web/src/components/intake/HardConstraintForm.test.tsx`
- E2E: `web/e2e/discovery-flow.spec.ts`

- [ ] Render only the Step 1 fields:
  - departure city
  - destination city, using an autocomplete-style picker that resolves to a known city and ISO country code.
  - departure date
  - trip duration
  - traveler count
  - total trip budget
- [ ] Persist both `destination_city` and `destination_country_code` from the selected destination entry.
- [ ] Do not ask for hotel style, transport preference, food preference, or daily pace.
- [ ] Label the submit CTA as `Start discovering ideas` or an equivalent exploration-oriented phrase.
- [ ] On submit, call `POST /api/sessions` and navigate to `/discovery/[sessionId]`.
- [ ] Set the `travel_session_id` cookie server-side in the route handler with:
  - `HttpOnly`
  - `Secure` in production
  - `SameSite=Lax`
  - `Path=/`
  - 90 day expiry
- [ ] Add client-side and server-side validation for positive duration, traveler count, and budget.
- [ ] Server-side validation must also verify `destination_country_code` is a valid ISO 3166-1 alpha-2 code.
- [ ] If city autocomplete cannot resolve a country code, block submission with a clear error instead of guessing.
- [ ] Track `step1_submitted` metric.
- [ ] Ensure the first screen is a real travel intake screen, not a marketing page or placeholder.
- [ ] Commit as `feat: add hard constraint intake`.

**Acceptance Criteria:**
- Step 1 has no premature preference questions.
- A valid submission creates a persisted session and moves to discovery.
- Every persisted session has a non-null `destination_country_code`.

---

## Task 8: Build Discovery Agent And API

**Files:**
- Create: `web/src/server/agents/types.ts`
- Create: `web/src/server/agents/prompts.ts`
- Create: `web/src/server/agents/discovery.ts`
- Create: `web/src/app/api/discovery/route.ts`
- Test: `web/src/server/agents/discovery.test.ts`

- [ ] Implement `runDiscoveryAgent(session)` returning `DiscoveryOutput` from Task 2.
- [ ] In the discovery prompt, prohibit final itinerary, final hotel choice, final transport route, and specific restaurant selection.
- [ ] Call the LLM exclusively through `callLLM` from Task 6.5.
- [ ] Parse and validate LLM output against `DiscoveryOutputSchema`.
- [ ] Enrich each card through providers where possible:
  - image
  - coordinate
  - reservation hint
  - rough cost estimate
- [ ] Run `classifyAttractionCostSignal` after enrichment.
- [ ] Compute `enrichment_status` per card:
  - `complete`: `place`, `image_url`, and `cost_estimate` all present.
  - `partial`: `place` present, but `image_url` or `cost_estimate` missing.
  - `minimal`: `place` is `null`.
- [ ] Do not include `reservation_hint` in `enrichment_status` calculation. It is optional because many valid attractions require no reservation.
- [ ] Persist discovery payload and initial empty selection to `discovery_state`.
- [ ] Return stage progress events or simple status values consumable by the UI.
- [ ] Add tests proving missing image or coordinate still produces renderable cards with `partial` or `minimal` status.
- [ ] Commit as `feat: add discovery agent and API`.

**Acceptance Criteria:**
- Discovery content can render even with partial enrichment failure.
- Cost signals are calculated by shared utility, not by prompt text.
- Output validates against `DiscoveryOutputSchema` before persistence.

---

## Task 9: Build Discovery UI And Exit Gate

**Files:**
- Create: `web/src/app/discovery/[sessionId]/page.tsx`
- Create: `web/src/components/discovery/DiscoveryBoard.tsx`
- Create: `web/src/components/discovery/DiscoveryCardGrid.tsx`
- Create: `web/src/components/discovery/DiscoveryCard.tsx`
- Create: `web/src/components/discovery/FoodSummaryList.tsx`
- Create: `web/src/components/discovery/AreaImpressionList.tsx`
- Create: `web/src/components/discovery/BudgetBandPanel.tsx`
- Create: `web/src/domain/selection.ts`
- Test: `web/src/domain/selection.test.ts`
- Test: `web/src/components/discovery/DiscoveryBoard.test.tsx`

- [ ] Render attraction and experience cards as the primary content.
- [ ] Render representative food summaries as secondary content.
- [ ] Render area impressions as planning context.
- [ ] Let users select and unselect attraction cards.
- [ ] Disable `Continue to preferences` until at least one card is selected.
- [ ] Show non-blocking density warning when selected count exceeds `duration_days * 5`.
- [ ] Do not hard-limit selected attractions.
- [ ] Update `discovery_state.selected_card_ids` server-side whenever selection changes.
- [ ] Render enrichment statuses differently:
  - `complete`: full card layout with image and cost signal.
  - `partial`: full card layout with image placeholder or missing-cost note.
  - `minimal`: text-only card with name, reason, and tags.
- [ ] Show discovery-stage budget estimate band with attraction, stay, transport, food, and total ranges.
- [ ] Show budget warning when estimated high range approaches or exceeds user budget.
- [ ] Commit as `feat: add discovery selection experience`.

**Acceptance Criteria:**
- The user explicitly advances from discovery to preferences.
- Few selections are allowed and many selections are warned about but not blocked.
- Cards in any enrichment status render without errors.

---

## Task 10: Build Stay And Transport Preferences

**Files:**
- Create: `web/src/app/preferences/[sessionId]/page.tsx`
- Create: `web/src/components/preferences/PreferenceForm.tsx`
- Create: `web/src/app/api/preferences/route.ts`
- Test: `web/src/components/preferences/PreferenceForm.test.tsx`

- [ ] Render stay fields:
  - area vibe
  - quiet vs lively
  - hotel vs homestay
  - willingness to change hotels
- [ ] Render transport fields:
  - train vs flight vs flexible
  - early departure tolerance
  - transfer tolerance
  - willingness to spend more to save time
- [ ] Persist preferences to the session.
- [ ] Navigate to `/trips/[sessionId]` and start final planning.
- [ ] Track `preferences_completed`.
- [ ] Commit as `feat: add stay and transport preferences`.

**Acceptance Criteria:**
- Preferences are collected only after discovery selection.
- Preference payload is available to stay and transport agents.

---

## Task 11: Add Stay, Transport, And Planner Agents

**Files:**
- Create: `web/src/server/agents/stay.ts`
- Create: `web/src/server/agents/transport.ts`
- Create: `web/src/server/agents/planner.ts`
- Create: `web/src/server/agents/orchestrator.ts`
- Create: `web/src/app/api/itinerary/route.ts`
- Test: `web/src/server/agents/orchestrator.test.ts`

- [ ] Implement `runStayAgent(session)` returning `StayRecommendation` with one `primary` and 2-3 `alternatives`.
- [ ] Implement `runTransportAgent(session)` returning `TransportRecommendation`.
- [ ] Implement `runPlannerAgent(session, stay, transport, validatorIssues?)` returning `Itinerary`.
- [ ] Implement orchestrator entrypoints:
  - `runFullPlanning(session)`: runs stay, transport, planner, validator, and possible corrective planner pass.
  - `runPlannerOnly(session, reason)`: reuses existing stay and transport outputs, then runs planner, validator, and possible corrective planner pass. Used by stay override, Type A adjustments, and the planner phase after Type B agent reruns.
- [ ] Planner consumes the active stay option:
  - if `stay.user_override_id` is set and matches an option in `[primary, ...alternatives]`, use that option.
  - otherwise use `primary`.
- [ ] Ensure planner uses selected discovery cards as interest pool, not a mandatory schedule.
- [ ] If there are very few selections, instruct planner to leave flexible/rest space instead of inventing low-confidence additions.
- [ ] If there are many selections, planner may prioritize but must surface density tradeoffs and preserve omitted interests as notes.
- [ ] Implement orchestrator with this explicit corrective-pass state machine:
  - first planner call passes `validatorIssues = undefined`.
  - run validator.
  - if no error issues exist, finalize with the validator output attached.
  - if error issues exist, filter to `severity === "error"` and run planner exactly one more time with only those error issues as corrective context.
  - run validator again.
  - finalize regardless of remaining errors, attaching the second validator output to `Itinerary.validator_issues`.
- [ ] Warning issues never trigger corrective pass and are not sent as corrective context. Attach warnings from the final validator run to the itinerary; do not carry stale first-pass warnings forward after a corrective rerun.
- [ ] Keep corrective-pass count in the orchestrator only. Planner is stateless and receives full context every call.
- [ ] Corrective pass only reruns planner, not stay or transport. Budget overrun errors that cannot be solved by planner reshuffling remain as residual errors and surface inline in the UI; this is an explicit MVP tradeoff.
- [ ] Attach residual issues to `Itinerary.validator_issues`.
- [ ] Persist the canonical itinerary and validator issues.
- [ ] Increment `Itinerary.version` on each canonical write.
- [ ] Track `itinerary_finalized` and `validator_error_finalized` metrics.
- [ ] Add orchestrator tests for:
  - no-error happy path: 1 planner call.
  - error then resolved: 2 planner calls, second validator returns 0 error issues, final itinerary has no residual errors.
  - error persists: 2 planner calls, second validator returns at least 1 error issue, and those issues appear in final `Itinerary.validator_issues`.
  - warning-only: 1 planner call, no rerun.
  - planner-only path: `runPlannerOnly` uses the same corrective-pass rules without rerunning stay or transport.
- [ ] Commit as `feat: add final planning agent pipeline`.

**Acceptance Criteria:**
- Final itinerary includes day structure, movement logic, budget breakdown, contextual food placement, reservation notes, and weather notes when available.
- Warnings never trigger corrective reruns.
- Errors trigger at most one corrective pass and no infinite loop.
- Planner has no internal pass counter.
- Stay override, Type A adjustment, and the planner phase after Type B reruns use orchestrator planner-only reruns, not direct planner calls.

---

## Task 12: Build Planning Progress And Itinerary UI

**Files:**
- Create: `web/src/app/trips/[sessionId]/page.tsx`
- Create: `web/src/app/api/sessions/[sessionId]/stay-override/route.ts`
- Create: `web/src/components/itinerary/PlanningProgress.tsx`
- Create: `web/src/components/itinerary/ItineraryView.tsx`
- Create: `web/src/components/itinerary/ItineraryDayCard.tsx`
- Create: `web/src/components/itinerary/StayAreaSwitcher.tsx`
- Create: `web/src/components/itinerary/ValidatorIssueNote.tsx`
- Test: `web/src/components/itinerary/ItineraryView.test.tsx`
- Test: `web/src/components/itinerary/StayAreaSwitcher.test.tsx`
- E2E: `web/e2e/itinerary-flow.spec.ts`

- [ ] Show stage-level progress:
  - discovering city highlights
  - recommending stay areas
  - analyzing transport
  - generating final itinerary
- [ ] Render itinerary by day with ordered segments.
- [ ] Render segment types:
  - attraction
  - food
  - transit
  - rest
  - hotel_checkin
  - hotel_checkout
  - hotel_return
- [ ] Render final budget summary by transport, stay, food, attractions, other, and total.
- [ ] Render warning validator issues inline next to affected day or segment.
- [ ] Render residual error issues inline in red with message and suggested action.
- [ ] Render `StayAreaSwitcher` showing the active stay area with a `Change area` affordance.
- [ ] `StayAreaSwitcher` opens a panel listing `primary` and alternatives, with primary highlighted as default.
- [ ] When the user selects an option, call `PATCH /api/sessions/[sessionId]/stay-override` to write `user_override_id` through `SessionRepository.updateStayOverride`.
- [ ] After stay override changes, trigger `runPlannerOnly(session, "stay_override")`. Do not rerun stay or transport because stay options have not changed.
- [ ] Add `Reset to recommended`, which sets `user_override_id` back to `null` and triggers `runPlannerOnly(session, "stay_override_reset")`.
- [ ] Add reload behavior that fetches latest session itinerary instead of regenerating.
- [ ] Commit as `feat: add itinerary progress and result UI`.

**Acceptance Criteria:**
- A user sees meaningful progress during long-running work.
- Refreshing a completed trip reopens the saved itinerary.
- Switching stay area updates the itinerary without restarting the full flow.

---

## Task 13: Add Adjustment Classification And Routing

**Files:**
- Create: `web/src/server/agents/adjustmentClassifier.ts`
- Create: `web/src/app/api/adjustments/route.ts`
- Create: `web/src/components/chat/AdjustmentPanel.tsx`
- Create: `web/src/components/chat/TypeCConfirmationCard.tsx`
- Test: `web/src/server/agents/adjustmentClassifier.test.ts`
- E2E: `web/e2e/adjustment-flow.spec.ts`

- [ ] Classify post-generation chat into:
  - Type A: planner-only light itinerary adjustment
  - Type B: stay and/or transport preference change, then planner
  - Type C: root constraint change requiring confirmation flow
  - unknown: clarifying question
- [ ] Append every adjustment turn to `conversation_history` before reruns.
- [ ] For Type A, call `runPlannerOnly(session, "type_a_adjustment")` with current stay and transport outputs.
- [ ] For Type B, rerun only the relevant agent or agents:
  - stay-related scope: rerun stay, then call `runPlannerOnly(session, "type_b_stay")`.
  - transport-related scope: rerun transport, then call `runPlannerOnly(session, "type_b_transport")`.
  - both scopes: rerun both, then call `runPlannerOnly(session, "type_b_stay_transport")`.
- [ ] When stay reruns, write the new `StayRecommendation` and reset `user_override_id` to `null`. Rationale: the user explicitly asked for a different kind of stay, so the previous manual override is no longer meaningful.
- [ ] When transport reruns alone and stay does not rerun, preserve the existing `user_override_id`.
- [ ] For Type C, render a confirmation card and do not rerun agents.
- [ ] Type C card must show:
  - detected root constraint change
  - stages that need to rerun
  - estimate of how much current plan will be discarded
  - `Replan`: calls `SessionRepository.resetToStep(...)` with the target step and updated constraints, preserves the session id, then redirects to that step.
  - `Save and start new`: calls `SessionRepository.archiveAndFork(...)`, redirects to the new session, and leaves the old session browseable but read-only.
  - `Cancel`: discards the proposed change, runs no agent, and records the cancellation in conversation history.
- [ ] If confidence is low, return a clarifying question instead of guessing.
- [ ] Track `adjustment_classified` metric with resolved type and confidence.
- [ ] Commit as `feat: add conversational partial replanning`.

**Acceptance Criteria:**
- Small changes do not restart the full product flow.
- Root changes are never silently interpreted as local itinerary edits.
- After stay rerun, `user_override_id` is `null`.
- After transport-only rerun, existing `user_override_id` is preserved.
- Each Type C action maps to a distinct repository call with a verifiable session-state outcome.

---

## Task 14: Add Metrics Events

**Files:**
- Create: `web/src/server/metrics/events.ts`
- Modify: API routes from Tasks 7-13
- Test: `web/src/server/metrics/events.test.ts`

- [ ] Define event names:
  - `step1_submitted`
  - `discovery_arrived`
  - `discovery_enrichment_summary` emitted once per discovery completion with `{ total_cards, complete_count, partial_count, minimal_count }`.
  - `attraction_selected`
  - `preferences_completed`
  - `itinerary_finalized`
  - `validator_error_finalized` emitted when itinerary finalizes with residual errors and error codes.
  - `adjustment_classified` with resolved type and confidence.
  - `type_c_action_taken` with `{ action: "replan" | "save_and_start_new" | "cancel" }`.
  - `provider_fallback_used` with provider name and reason.
  - `stay_override_set` with whether override was set or cleared.
- [ ] Store events in a simple server-side JSONL file under `web/.data/events.jsonl` for MVP.
- [ ] Compute funnel and quality metrics from events in a helper function.
- [ ] Ensure event logging failure never breaks planning.
- [ ] Commit as `feat: add MVP metrics events`.

**Acceptance Criteria:**
- Observable success metrics can be calculated without adding an analytics vendor.
- Planning still works if metric writes fail.
- Discovery enrichment is observable as a single aggregate event per session.

---

## Task 15: Add End-To-End Quality Pass

**Files:**
- Modify: `web/e2e/discovery-flow.spec.ts`
- Modify: `web/e2e/itinerary-flow.spec.ts`
- Modify: `web/e2e/adjustment-flow.spec.ts`
- Create: `web/src/test/fixtures/sampleSession.ts`

- [ ] Add fixture-backed agent mode for E2E tests using deterministic responses, with LLM calls stubbed at the Task 6.5 wrapper boundary.
- [ ] Test full flow:
  - submit hard constraints
  - reach discovery
  - select at least 3 attractions
  - continue to preferences
  - complete preferences
  - receive itinerary
- [ ] Test density warning when selection count exceeds `duration_days * 5`.
- [ ] Test budget warning display.
- [ ] Test Type A adjustment changes only itinerary content.
- [ ] Test Type B adjustment reruns stay and clears `user_override_id`.
- [ ] Test Type B transport-only adjustment reruns transport and preserves existing `user_override_id`.
- [ ] Test stay area switch from itinerary UI: switching to an alternative updates active stay and triggers planner-only rerun.
- [ ] Test Reset to recommended clears `user_override_id` and triggers planner-only rerun.
- [ ] Test Type C `Replan`: confirmation card -> click Replan -> user is sent back to the matching step -> session id is preserved -> downstream state is cleared.
- [ ] Test Type C `Save and start new`: confirmation card -> click Save and start new -> new session is created with `parent_session_id` set -> original session is archived -> old session is reachable but rejects writes.
- [ ] Test Type C `Cancel`: confirmation card -> click Cancel -> no state change -> conversation history records the cancellation.
- [ ] Run:
  - `npm run test`
  - `npm run typecheck`
  - `npm run lint`
  - `npm run test:e2e`
- [ ] Commit as `test: cover core travel planning flow`.

**Acceptance Criteria:**
- The MVP success criteria are covered by automated tests at utility, API, and browser-flow levels.
- All three Type C branches are tested end-to-end.

---

## Task 16: Prepare MVP Launch Checklist

**Files:**
- Create: `web/docs/mvp-launch-checklist.md`
- Modify: `README.md`

- [ ] Document required environment variables:
  - LLM provider key
  - search provider key
  - Mapbox token
  - AMap key
  - weather provider key
- [ ] Document local development commands.
- [ ] Document test commands and expected passing state.
- [ ] Document fallback behavior when enrichment providers fail.
- [ ] Document current known MVP limits:
  - single-city only
  - no real-time hotel inventory
  - no real-time ticket booking
  - estimate-grade prices
  - anonymous session persistence
  - budget overrun errors may persist as inline risk notes because the MVP corrective pass does not rebalance stay or transport.
- [ ] Commit as `docs: add MVP launch checklist`.

**Acceptance Criteria:**
- Another engineer can run, test, and demo the MVP without reading the original product document first.

---

## Implementation Order

Execute tasks in this order:

1. Task 0
2. Task 1
3. Task 2
4. Task 3
5. Task 4
6. Task 5
7. Task 6
8. Task 6.5
9. Task 7
10. Task 8
11. Task 9
12. Task 10
13. Task 11
14. Task 12
15. Task 13
16. Task 14
17. Task 15
18. Task 16

Do not start UI-heavy work before Tasks 2-6.5 are complete. The schemas, budget utility, validator, session repository, provider abstraction, and LLM client are the spine of the product.

---

## Risk Register

| Risk | Mitigation |
| --- | --- |
| Discovery quality is weak without enough provider data | Use provider adapters for enrichment and mark weak cards as `partial` or `minimal` instead of hiding them. |
| LLM returns invalid JSON or renamed fields | Validate every agent output with Zod through the Task 6.5 wrapper, with one structured repair pass before failing the stage. |
| Budget estimates feel falsely precise | Always show `BudgetBand` ranges and confidence, never single exact quote totals except user-entered budget. |
| Budget overrun errors cannot be auto-resolved by planner alone | Surface as inline residual error in UI with explicit risk note; document as an MVP limit. |
| International and China map data diverge | Normalize provider outputs immediately and keep WGS84 as the only internal coordinate system. |
| City-name string matching fails for routing | Resolve `destination_country_code` at intake and route providers only from country code. |
| Chat replanning becomes unpredictable | Classify every adjustment before running agents and block Type C changes behind confirmation. |
| Stay override drifts after stay rerun | On Type B stay rerun, repository explicitly clears `user_override_id`; cover this with E2E. |
| LLM cost spikes during development | Route all LLM calls through the Task 6.5 wrapper and log cost metadata per call. |
| Server-side file persistence is not production-grade for serverless deployment | Keep all storage behind `SessionRepository` so a Postgres or Supabase adapter can replace file storage without changing product code. |

---

## Self-Review

- **Spec coverage:** The plan maps Step 1 through Step 7, discovery cost signals, budget bands with basis, four agents, non-agent validator, provider abstraction, China/international map normalization, persistence with snapshot/fork, progress UX, metrics, adjustment routing including all three Type C actions, and stay area override.
- **Scope control:** Multi-city, real-time booking, live hotel inventory, mandatory restaurant choice, and automatic budget optimization are excluded from implementation tasks.
- **Type consistency:** All product-facing contracts flow through `web/src/domain/schemas.ts`; agents validate LLM output through the Task 6.5 wrapper, and provider adapters normalize directly into the same schemas before persistence or UI rendering.
- **Execution shape:** The tasks build from deterministic foundations toward UI and LLM behavior, reducing rework when prompts or providers change.
- **State machine clarity:** Corrective-pass counter, stay override lifecycle, and Type C action mapping are each owned by one named module or route path, with no shared mutable state.
