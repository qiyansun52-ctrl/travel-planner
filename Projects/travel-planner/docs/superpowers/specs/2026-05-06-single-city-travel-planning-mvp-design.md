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

## Data and Interface Boundaries

The internal system should gradually move toward these normalized layers:

- discovery card model,
- area summary model,
- stay recommendation model,
- transport recommendation model,
- itinerary model,
- budget summary model,
- provider-normalized place and route models,
- adjustment request classification model.

The key architecture rule is:

LLM prompts may vary, providers may vary, but these normalized product-facing shapes should remain stable.

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

## Follow-On Work

This design intentionally leaves clean upgrade paths for:

- multi-city planning,
- live hotel and transport inventory,
- stronger provider fallback,
- more detailed restaurant planning,
- shareable or persistent planning sessions,
- richer route visualization.

These are not required for the MVP, but the MVP should avoid architectural decisions that make them expensive later.
