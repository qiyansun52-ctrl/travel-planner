# Single-City Travel Planning MVP Design

## Goal

Build a travel planning MVP that does two jobs well:

1. Spark travel inspiration with a strong destination discovery experience.
2. Turn the user's selected interests into a realistic, adjustable single-city trip plan.

The MVP should feel like a travel advisor, not a one-shot itinerary generator. Users should start with a small set of hard constraints, explore what is worth doing in a city, and only then move into stay, transport, and final itinerary planning.

## Product Positioning

This product is not just a planner for users who already know exactly what they want. It is a two-stage assistant:

- Stage 1 helps the user discover what is worth doing in a city.
- Stage 2 helps the user turn those choices into a concrete, budget-aware plan.

The key interaction principle is progressive narrowing:

- first define the trip boundaries,
- then choose what to do,
- then decide where to stay and how to move,
- then generate and refine the final plan through conversation.

## Scope

### In Scope for MVP

- Single-city trip planning.
- China cities and international cities supported in the same product flow.
- A discovery page with:
  - attraction and experience cards,
  - representative food summaries,
  - area impressions,
  - rough cost signals,
  - image, coordinate, and reservation hints where available.
- A budget awareness system that warns early without automatically changing the plan.
- Four-agent planning pipeline:
  - `discovery`
  - `stay`
  - `transport`
  - `planner`
- A non-agent validation layer for obvious issues.
- Conversational partial replanning after the first full itinerary is generated.
- Semi-real planning quality:
  - recommended hotel areas,
  - sample hotel references,
  - transport suggestions and price bands,
  - realistic but non-booking-grade budget estimates.

### Explicitly Out of Scope for MVP

- Multi-city trip planning.
- Real-time hotel inventory and real-time ticket booking.
- Fully accurate supplier pricing.
- Automatic budget re-optimization without user approval.
- A mandatory restaurant selection step during discovery.
- Committing to a single provider for all countries and all use cases.

## Product Strategy

The MVP target is level `B`: semi-real planning.

That means the product should feel credible and useful in real travel planning, but it does not yet promise real-time bookable inventory. The architecture should still be prepared for a later upgrade to level `C`, where hotels, transport, and availability become live supplier-backed data.

The product should therefore optimize for:

- strong discovery quality,
- believable location and routing context,
- budget transparency,
- adjustable plans,
- provider abstraction from day one.

## Core User Flow

### Step 1: Hard-Constraint Intake

The first screen collects only the minimum information needed to start discovery:

- departure city,
- destination city,
- departure date,
- trip duration,
- number of travelers,
- total trip budget.

The CTA should frame the next step as exploration rather than final generation, for example:

- "Start discovering ideas"
- "See how this city can be explored"

This screen should not ask for:

- hotel style preferences,
- transport mode preferences,
- detailed food preferences,
- detailed daily pace preferences.

Those belong later, after the user has chosen what they want to do.

### Step 2: Discovery

After the first form is submitted, the system runs `discovery` and produces a city exploration page. This page should include three blocks:

1. Attraction and experience cards as the primary content.
2. Representative local food summaries as secondary content.
3. Area impressions and city-style signals as planning context.

The main user action here is selecting attractions and experiences they care about.

The user should not be required at this step to select:

- specific hotels,
- transport cards,
- specific restaurants.

### Discovery Exit Gate

The transition from discovery to stay and transport preferences must be an explicit user action, not an automatic trigger. The discovery page should present a persistent "Continue to preferences" CTA that is enabled once the user has selected at least one attraction.

Selection rules:

- minimum: 1 attraction required to advance.
- soft warning threshold: `duration_days * 5`; selecting beyond this shows a non-blocking warning that the trip may feel too dense.
- no hard maximum. Density problems at the itinerary level are caught later by the validator's `DAY_OVERLOADED` check, not at the discovery exit gate. The discovery selection is treated as the user's interest pool, not a final daily schedule.

Edge case behavior:

- if the user advances with very few selections, the planner should treat unfilled time as flexible space rather than padding it with low-confidence additions.
- if the user advances with many selections, planner and validator should surface density warnings during itinerary generation rather than silently dropping selections.

### Step 3: Early Budget Awareness

The discovery page should already show rough budget awareness, because waiting until the final itinerary to reveal a budget problem creates a poor experience.

Each attraction card should show a coarse cost signal such as:

- free,
- low,
- medium,
- high.

The page should also show a trip-level budget estimate band composed of:

- attraction estimate,
- stay estimate,
- transport estimate,
- food estimate,
- total estimate band.

This estimate is explicitly a range, not a precise quote.

### Step 4: Stay and Transport Preferences

After the user selects attractions, the product collects the next level of planning preferences:

- stay preferences:
  - area vibe,
  - quiet vs lively,
  - hotel vs homestay preference,
  - willingness to change hotels.
- transport preferences:
  - train vs flight vs flexible,
  - early departure tolerance,
  - transfer tolerance,
  - willingness to spend more to save time.

These preferences are then passed into `stay` and `transport`.

### Step 5: Final Itinerary Generation

The system runs:

1. `stay`
2. `transport`
3. `planner`

The final itinerary should include:

- day-by-day structure,
- movement logic,
- budget breakdown,
- context-aware food placement,
- reminders such as reservation or weather notes.

The generation experience should expose progress to the user instead of blocking silently. The user should see stage-level updates such as:

- discovering city highlights,
- recommending stay areas,
- analyzing transport,
- generating final itinerary.

### Step 6: Conversational Partial Replanning

After the first itinerary is generated, the user should be able to adjust the plan in natural language.

Examples:

- "Make the second afternoon more relaxed."
- "Reduce the budget a bit."
- "I want to stay closer to the attractions."
- "Remove one touristy stop and make it more local."

These requests are not generic chat. They are routed into partial replanning logic.

### Step 7: Session Continuity

The trip should remain available after initial generation so the user can come back and continue refining it.

For MVP, persistence does not need to be multi-user account-grade, but it should be strong enough that:

- the generated trip can be reopened,
- later conversational adjustments operate on the latest saved result,
- the user does not lose the plan just because one page refresh happens at the wrong time.

## Discovery Experience Design

### Attraction Cards

Each attraction or experience card should ideally contain:

- name,
- one-line reason to care,
- category,
- suggested visit duration,
- rough per-person cost signal,
- image,
- reservation requirement hint where relevant,
- map coordinate,
- tags such as:
  - landmark,
  - museum,
  - night view,
  - family-friendly,
  - citywalk,
  - local culture.

The product should prefer showing information that helps the user decide interest quickly, not encyclopedic detail.

### Food Summaries

The discovery page should include representative food summaries, but not specific restaurants yet.

Examples:

- local noodle style,
- signature dumplings,
- famous street snacks,
- regional cuisine profile.

This keeps discovery inspirational while avoiding premature restaurant decisions before stay area and movement logic are known.

### Area Impressions

The discovery page should also include lightweight area impressions, such as:

- good for nightlife,
- good for relaxed walking,
- good for families,
- central but busy,
- scenic but farther from core sights.

These area signals are not final stay recommendations. They are context that later helps `stay`.

### Cost Signal Calibration

The four cost levels (`free`, `low`, `medium`, `high`) need a stable reference, otherwise they become decoration.

The reference is the per-person per-day attraction budget:

```text
daily_attraction_slot = (total_budget * attraction_share) / (duration_days * traveler_count)
```

`attraction_share` defaults to `0.15` in MVP and can be tuned per destination later.

Bucket assignment:

- `free`: `0`
- `low`: cost is less than or equal to `30%` of `daily_attraction_slot`
- `medium`: cost is more than `30%` and less than or equal to `80%` of `daily_attraction_slot`
- `high`: cost is more than `80%` of `daily_attraction_slot`

Implications:

- the same attraction may be `low` for one user and `medium` for another, which is intentional. The signal is decision-relevant, not absolute.
- when raw cost data is missing, the bucket should be returned as `unknown` rather than guessed.
- the bucket calculation lives in a shared utility, not inside the LLM prompt, so it stays consistent across agents.

## Budget Strategy

### Principle

Budget should become visible early, but should not become falsely precise too early.

### Discovery-Stage Budget

The discovery-stage budget is a guidance layer, not a quote. It should be expressed as a band such as:

- user budget: `5000`
- current estimated range: `4200-5600`

### Overspend Policy

If the estimated range approaches or exceeds the user's budget, the system should:

- warn,
- explain that the current mix is becoming expensive,
- leave the decision to the user.

The system should not automatically:

- remove attractions,
- downgrade the stay,
- change transport,
- regenerate a cheaper version.

Budget optimization should happen later only if the user asks for it through conversation.

### Final-Stage Budget

By the time the final itinerary is produced, the budget should be refined into:

- transport,
- stay,
- food,
- attractions,
- other,
- total.

This remains estimate-grade in MVP, but more grounded than the discovery-stage band.

## Agent Architecture

### `discovery`

Responsibilities:

- gather and summarize city-level inspiration,
- produce structured attraction and experience choices,
- provide representative food summaries,
- provide area impressions,
- enrich cards with image, coordinate, reservation hints, and rough cost data where possible.

Non-responsibilities:

- no final itinerary,
- no final hotel choice,
- no final transport route,
- no specific restaurant list.

### `stay`

Responsibilities:

- recommend suitable stay areas based on:
  - selected attractions,
  - budget,
  - traveler count,
  - duration,
  - stay preferences,
- provide sample hotel references and price bands,
- explain why each area fits the trip.

Non-responsibilities:

- no full itinerary generation,
- no detailed daily scheduling.

### `transport`

Responsibilities:

- recommend arrival and departure strategy,
- recommend in-city movement strategy,
- estimate transport cost bands,
- surface transport constraints and tradeoffs.

Non-responsibilities:

- no final stay choice,
- no minute-by-minute itinerary ownership.

### `planner`

Responsibilities:

- merge the structured outputs of `discovery`, `stay`, and `transport`,
- create the final day-by-day plan,
- place food suggestions into the daily trip context,
- handle most post-generation natural-language adjustments.

### `validator`

`validator` should not be an LLM agent.

It should be a programmatic layer that checks for:

- obvious overspend,
- obviously overloaded days,
- obviously wasteful routing,
- obviously unrealistic timing.

Its job is to detect and surface issues, not to become a fifth planning brain.

### Validator Interface

The validator runs after planner completes a draft itinerary and before the itinerary is finalized to the user. It outputs a structured list of issues, not a rewritten plan.

Issue shape:

- `code`: stable issue identifier, such as `BUDGET_OVERRUN`, `DAY_OVERLOADED`, `WASTEFUL_ROUTING`, or `TIMING_UNREALISTIC`.
- `severity`: `warning` or `error`.
- `scope`: trip-level, day-level, or segment-level reference.
- `message`: human-readable explanation.
- `suggested_action`: optional one-line hint.

Concrete thresholds for MVP:

- `BUDGET_OVERRUN`: estimated total exceeds user budget by more than `15%`.
- `DAY_OVERLOADED`: a single day contains more than 8 active hours of attractions, or more than 5 distinct attraction stops.
- `WASTEFUL_ROUTING`: a single day's total movement time exceeds `40%` of its active hours.
- `TIMING_UNREALISTIC`: any reservation-required attraction is placed outside its known operating window, or visit duration is shorter than `50%` of the suggested duration.

Consumption rules:

- error issues do not block finalization. They trigger a single corrective pass: the planner receives the issue list and reruns once.
- after the corrective pass, the itinerary is finalized regardless of whether errors remain. Any residual error issues are attached to the itinerary and rendered inline in red on the affected day or segment, with the issue's message and `suggested_action` shown as a risk note.
- warning issues never trigger a corrective pass. They are passed straight through to the UI and shown next to the relevant day or segment.
- the validator is stateless across sessions and never modifies itinerary data. It only emits issues.

## Adjustment Routing

Post-generation conversation should be classified into three categories.

### Type A: Light itinerary adjustments

Examples:

- "Make the second afternoon easier."
- "Do not start so early on day one."

Handling:

- route only to `planner`.

### Type B: Stay or transport preference changes

Examples:

- "Stay somewhere closer to the attractions."
- "Do not take a flight."
- "Make the hotel cheaper."

Handling:

- rerun `stay` and/or `transport`,
- then rerun `planner`.

### Type C: Root constraint changes

Examples:

- "Change from 3 days to 4 days."
- "Budget is now 3000."
- "Switch destination from Shanghai to Chengdu."
- "We are 4 people instead of 2."

Handling:

- treat as replanning,
- push the user back into earlier confirmation steps rather than silently rewriting everything inside the chat surface.

### Type C Replanning UX

When adjustment classification returns Type C, the chat surface must explicitly hand off to a confirmation flow rather than reply with a new itinerary.

The chat reply renders a confirmation card showing:

- what root constraint the user appears to have changed,
- what stages will need to rerun (`discovery`, `stay`, `transport`, `planner`),
- an estimate of how much of the current plan will be discarded.

The user picks one of three actions:

- `Replan`: discard the current itinerary and return to the matching earlier step. Use Step 1 if hard constraints changed; use Step 2 if duration or budget changed in a way that invalidates discovery.
- `Save and start new`: keep the current itinerary as a snapshot and begin a new planning session with the new constraints.
- `Cancel`: discard the proposed change and keep the current itinerary unchanged.

Only after the user picks `Replan` or `Save and start new` does any agent rerun.

If classification confidence is low, the system should ask a clarifying question instead of guessing the change scope.

## Provider Architecture

### Design Principle

Provider choices should not be baked directly into agent logic. The product needs a provider abstraction layer so it can evolve from `B` to `C` without rewriting planning logic.

### `SearchProvider`

Used mainly by `discovery`.

Responsibilities:

- web search,
- article and guide sourcing,
- discovery research inputs.

The system should continue using stable search APIs as the main production path rather than brittle browser-driven scraping as the primary engine.

### `MapProvider`

Responsibilities:

- geocoding,
- reverse geocoding,
- POI search,
- routing,
- travel-time reasoning,
- map-friendly spatial context.

Provider decision for MVP:

- global and non-China cities: `Mapbox`
- China cities: `AMap`

Planned future additions:

- China fallback: `Baidu`
- global fallback or enrichment path: `Google`

The routing layer should choose providers by geography first, and fall back by health or capability second.

Coordinate system normalization:

- AMap and Baidu return coordinates in non-WGS84 systems, GCJ02 and BD09 respectively. Raw provider coordinates must never leak into `NormalizedPlace`.
- Every provider adapter is responsible for converting to WGS84 before producing a `NormalizedPlace`.
- When raw provider payloads need to be retained for debugging or for re-sending to the same provider, store them in a separate `raw_payload` field outside `NormalizedPlace`. Never reuse `NormalizedPlace.coordinate` as a passthrough.
- Inside the system, all coordinate arithmetic, distance calculation, and map rendering assumes WGS84.

### `WeatherProvider`

Responsibilities:

- location/date weather summary,
- forecast context for discovery and final planning.

Weather should influence:

- discovery messaging,
- packing and reservation hints,
- final daily suggestions.

### `SupplierProvider`

This is a future-facing abstraction. In MVP it may only provide sample references or normalized estimate inputs.

Later it should split into:

- `HotelProvider`
- `TransportProvider`

This allows the system to graduate from B-level planning into C-level live inventory and quote logic without changing the core user flow.

## Progress and Persistence

### Progress UX

Long-running planning steps should not feel opaque. The system should expose progress at meaningful milestones rather than showing a generic spinner the whole time.

The minimum useful stages are:

- discovery in progress,
- stay recommendation in progress,
- transport recommendation in progress,
- final itinerary composition in progress.

The product does not need to expose every internal micro-step. It should expose just enough stage visibility to make the system feel active and understandable.

### Persistence

Generated plans and later adjustments should be stored in a way that survives normal usage.

For MVP, acceptable persistence can still be lightweight, but the architecture should move away from treating browser-only local state as the sole source of truth. The important design principle is:

- latest itinerary state should be restorable,
- conversational edits should update the stored canonical result,
- future account-backed persistence should be easy to add.

### MVP Persistence Plan

The MVP storage target is server-side, anonymous, and session-scoped.

Storage shape:

- one record per planning session,
- keyed by an opaque `session_id` issued on first hard-constraint submission,
- the `session_id` is held by the client in a long-lived cookie or local key, and is the only thing the browser is allowed to be the source of.

Record fields:

- `session_id`: string, primary key.
- `hard_constraints`: object, the Step 1 form payload.
- `discovery_state`: object, attraction selections and discovery payload references.
- `preferences`: object, the Step 4 form payload.
- `itinerary`: object, latest canonical itinerary.
- `conversation_history`: array, ordered adjustment turns and their classified types.
- `validator_issues`: array, latest validator output.
- `parent_session_id`: string or null. Set when this session was created via `Save and start new` from another session; null otherwise.
- `snapshot_label`: string or null. User-supplied or auto-generated label for archived sessions, such as `3-day version` or `before budget cut`; null on active sessions.
- `status`: `active` or `archived`. Archived sessions are read-only snapshots, not eligible for further agent runs.
- `created_at`, `updated_at`: timestamps.

Write rules:

- every successful agent run writes a new canonical itinerary.
- every conversational adjustment, regardless of Type A/B/C, appends to `conversation_history` before any agent rerun.
- writes are last-write-wins; no conflict resolution in MVP.
- `Save and start new` creates a new record with the current itinerary copied verbatim, sets the original record's status to `archived`, and links the new record's `parent_session_id` to the archived one.
- archived records are never written to except for `snapshot_label` edits.

Account migration path:

- when account login lands later, sessions are claimed by associating `session_id` with a `user_id`; no record reshape is required.

## China and International Coverage

The product should support China and international cities in the same planning flow from MVP onward.

This does not mean identical providers are used everywhere. It means the user experience should feel unified even if provider routing differs behind the scenes.

The planning system should therefore normalize outputs across providers so agents consume:

- a common place shape,
- a common route shape,
- a common weather shape,
- a common budget shape.

The user should not need to care which provider served the answer.

## Reliability and Fallback Principles

### Discovery

If some enrichment signals fail, the product should still render discovery content.

Examples:

- no image available,
- no reservation hint available,
- no stable cost signal available.

The core attraction card should survive partial enrichment failure.

### Map and Routing

If the primary provider fails:

- retry if appropriate,
- then use the fallback provider where available,
- keep the normalized output contract stable.

### Budget

If some budget components are weakly known:

- widen the estimate band rather than inventing false precision.

### Conversation

If a user request implies root changes, do not quietly reinterpret it as a local adjustment. Escalate it clearly as replanning.

## Schema Definitions

The internal system should gradually move toward these normalized layers. The key architecture rule remains: LLM prompts may vary, providers may vary, but these normalized product-facing shapes should remain stable.

The shapes below are MVP v1 contracts. Field names and types are stable; agents and providers may add fields but must not rename or retype them.

### `NormalizedPlace`

Provider-agnostic shape for any geographic point.

- `id`: string. Provider-prefixed stable id, such as `amap:B0FFG...`.
- `name`: string. Display name.
- `coordinate`: `{ lat: number, lng: number } | null`. Always WGS84 once inside the system; null if geocoding failed and enrichment is incomplete. See `MapProvider` for the conversion rule.
- `address`: string or null. Formatted address if available.
- `category`: string or null. Normalized category tag.
- `provider`: `amap`, `mapbox`, `baidu`, or `google`. Which provider supplied this record.

### `NormalizedRoute`

Provider-agnostic shape for any A-to-B movement.

- `from`: `NormalizedPlace`. Origin point.
- `to`: `NormalizedPlace`. Destination point.
- `mode`: `walk`, `transit`, `drive`, `rail`, or `flight`. Movement mode.
- `duration_minutes`: number. Estimated travel time.
- `distance_meters`: number. Estimated distance.
- `cost_estimate`: `BudgetBand` or null. Estimated cost band, null if unknown.
- `provider`: provider enum. Which provider supplied this record.

### `BudgetBand`

Reusable shape for any cost expressed as a range.

- `currency`: string. ISO 4217 code.
- `low`: number. Lower bound.
- `high`: number. Upper bound.
- `confidence`: `high`, `medium`, or `low`. How trusted the band is.
- `basis`: `per_person`, `per_party`, `per_room_per_night`, `per_day`, or `per_trip`. Pricing unit; consumers must convert before summing.

### `DiscoveryCard`

Output of `discovery` for a single attraction or experience.

- `id`: string. Stable card id within the session.
- `name`: string. Display name.
- `reason`: string. One-line reason to care.
- `category`: string. High-level category.
- `tags`: string array. Display tags.
- `suggested_duration_minutes`: number. Recommended visit length.
- `cost_signal`: `free`, `low`, `medium`, `high`, or `unknown`.
- `cost_estimate`: `BudgetBand` or null.
- `image_url`: string or null. Primary image.
- `reservation_hint`: string or null.
- `place`: `NormalizedPlace` or null. Geographic anchor; null if the place could not be resolved by any provider.
- `enrichment_status`: `complete`, `partial`, or `minimal`. `complete` means all fields are present; `partial` means optional fields are missing, such as image, reservation, or cost; `minimal` means place or core enrichment failed and the card renders with name and reason only.

### `AreaSummary`

Lightweight area impression on the discovery page.

- `id`: string. Stable area id.
- `name`: string. Display name.
- `vibe_tags`: string array. Descriptors such as nightlife, walkable, or family.
- `note`: string. One-line summary.
- `center`: `{ lat: number, lng: number }`. Approximate center point in WGS84.

### `StayRecommendation`

Output of `stay`.

- `primary`: `StayOption`. The default stay area used by planner unless user overrides.
- `alternatives`: `StayOption[]`. Other viable areas, ranked by fit.
- `user_override_id`: string or null. Id of the `StayOption` the user explicitly picked, if any; planner uses this when set, otherwise `primary`.

`StayOption`:

- `id`: string. Stable option id.
- `area`: `AreaSummary`. Recommended area.
- `fit_reason`: string. Why this area fits.
- `price_band`: `BudgetBand`. Nightly price band with `basis: per_room_per_night`.
- `sample_hotels`: `SampleHotel[]`.

`SampleHotel`:

- `name`: string.
- `style`: string, such as `boutique`, `business`, or `homestay`.
- `price_band`: `BudgetBand`.
- `place`: `NormalizedPlace`.

### `TransportRecommendation`

Output of `transport`.

- `arrival`: `TransportLeg`. Arrival strategy.
- `departure`: `TransportLeg`. Departure strategy.
- `intracity`: `IntracityStrategy`. In-city movement strategy.
- `tradeoffs`: string array. Short notes on cost, time, and comfort tradeoffs.

`TransportLeg`:

- `mode`: `rail`, `flight`, `drive`, `bus`, or `mixed`.
- `duration_minutes`: number.
- `cost_band`: `BudgetBand`.
- `note`: string or null.

`IntracityStrategy`:

- `primary_mode`: `walk`, `transit`, `taxi`, or `mixed`.
- `daily_cost_band`: `BudgetBand`.
- `note`: string or null.

### `Itinerary`

Output of `planner`.

- `id`: string. Itinerary id.
- `session_id`: string. Owning session.
- `days`: `ItineraryDay[]`. Ordered day list.
- `budget`: `BudgetSummary`. Final budget breakdown.
- `validator_issues`: `ValidatorIssue[]`. Issues attached at finalization time.
- `version`: number. Increments on each canonical write.

`ItineraryDay`:

- `day_index`: number, 1-based.
- `date`: ISO date string.
- `segments`: `ItinerarySegment[]`. Ordered events of the day.
- `notes`: string array. Daily reminders such as weather or reservation notes.

`ItinerarySegment`:

- `type`: `attraction`, `food`, `transit`, `rest`, `hotel_checkin`, `hotel_checkout`, or `hotel_return`. `hotel_return` covers mid-day or end-of-day returns to the hotel that are not check-in or check-out.
- `start_time`: string, `HH:mm`.
- `end_time`: string, `HH:mm`.
- `place`: `NormalizedPlace` or null.
- `card_ref`: string or null. References `DiscoveryCard.id` when applicable.
- `description`: string.
- `cost_estimate`: `BudgetBand` or null.

### `BudgetSummary`

Final breakdown shown to the user.

- `currency`: string.
- `transport`: `BudgetBand`.
- `stay`: `BudgetBand`.
- `food`: `BudgetBand`.
- `attractions`: `BudgetBand`.
- `other`: `BudgetBand`.
- `total`: `BudgetBand`.
- `user_budget`: number. Step 1 input.
- `overrun_flag`: boolean. True if `total.high` exceeds `user_budget * 1.15`.

### `AdjustmentRequest`

Output of the adjustment classifier.

- `raw_text`: string. Original user message.
- `type`: `A`, `B`, `C`, or `unknown`.
- `confidence`: number from `0` to `1`.
- `target_scope`: `day`, `segment`, `stay`, `transport`, `budget`, `duration`, `destination`, `traveler_count`, or `none`.
- `proposed_change`: string or null. Short structured description of what the user appears to want.

### `ValidatorIssue`

Already defined in `Validator Interface`; included here for completeness.

- `code`: string.
- `severity`: `warning` or `error`.
- `scope`: object referencing trip, day, or segment id.
- `message`: string.
- `suggested_action`: string or null.

## MVP Success Criteria

The MVP is successful if a user can:

1. enter trip hard constraints,
2. receive an engaging discovery page,
3. select attractions with early budget awareness,
4. provide stay and transport preferences,
5. receive a credible full itinerary,
6. see budget warnings without forced automatic plan changes,
7. ask for partial replanning in natural language,
8. get a revised result without restarting the whole experience for every small change.

## Observable Success Metrics

The criteria above are qualitative. The following are quantitative proxies tracked from day one to make "is this MVP working?" answerable.

Funnel metrics:

- `discovery_arrival_rate`: percent of Step 1 submissions that reach the discovery page within 30 seconds.
- `attraction_selection_rate`: percent of users on the discovery page who select at least 3 attractions before leaving.
- `preferences_completion_rate`: percent of users who complete Step 4 after entering it.
- `itinerary_delivery_rate`: percent of Step 4 completions that produce a finalized itinerary within 90 seconds.
- `full_flow_completion_rate`: percent of Step 1 submissions that result in a finalized itinerary.

Quality metrics:

- `validator_error_rate`: percent of generated itineraries that contain at least one error-severity validator issue at finalization.
- `adjustment_acceptance_rate`: percent of post-generation adjustments where the user does not immediately ask for another change to the same scope.
- `type_c_escalation_rate`: percent of adjustment turns classified as Type C; high values suggest Step 1 intake is missing constraints users actually care about.
- `replan_loop_count`: median number of adjustment turns before the user stops adjusting.

Reliability metrics:

- `provider_fallback_rate`: percent of map calls that fall through to a secondary provider.
- `enrichment_partial_rate`: percent of discovery cards rendered with at least one missing enrichment field.

These metrics do not replace qualitative judgment, but they make regressions visible.

## Follow-On Work

This design intentionally leaves clean upgrade paths for:

- multi-city planning,
- live hotel and transport inventory,
- stronger provider fallback,
- more detailed restaurant planning,
- shareable or persistent planning sessions,
- richer route visualization.

These are not required for the MVP, but the MVP should avoid architectural decisions that make them expensive later.
