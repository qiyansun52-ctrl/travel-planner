# Result Page Product Expression Design

## Purpose

Upgrade the trip result page from a functional itinerary view into a story-led planning command center.

The current product already has a strong planning foundation: sessions, discovery cards, preferences, itinerary generation, budget bands, stay recommendations, transport recommendations, validator issues, and fixture-backed regression. This design focuses on making that intelligence more visible and emotionally compelling to users.

The first release should not add new providers or change the planning graph. It should reuse existing session, discovery, itinerary, budget, route, stay, transport, and validator data to create a result page that feels more like a finished travel product.

## Product Direction

The agreed direction is:

- Use a professional planning dashboard as the structural backbone.
- Add destination story and visual atmosphere so the page feels like travel, not only operations.
- Add companion-like guidance through contextual summaries and adjustment prompts without building a full chat backend in this phase.
- Prefer real discovery images for emotional impact, with graceful fallback to route/map texture or editorial text when images are missing.

The result should feel trustworthy first, inspiring second, and actionable throughout.

## User Outcome

A user who lands on the result page should be able to answer four questions quickly:

1. What kind of trip did the planner create?
2. Does this plan fit my budget, pace, route, and risk tolerance?
3. What is the story arc of the trip?
4. What exactly do I do each day, and what can I adjust?

The page should make the itinerary feel curated rather than merely generated.

## Non-Goals

- No new backend providers.
- No new image scraping service.
- No live booking, ticketing, payment, or reservation workflow.
- No full AI chat backend in this phase.
- No map-provider overhaul.
- No large schema migration unless a small derived field is clearly justified.
- No visual redesign of discovery, preferences, or intake pages in this phase.

## Page Structure

The result page uses a "Story-Led Command Center" layout.

### 1. Destination Story Hero

The top of the page should frame the plan as a trip story.

Content:

- Destination city and country.
- Trip duration and date range.
- Traveler count and budget.
- A short generated or derived trip subtitle, such as "A balanced 3-day cultural loop with light evenings."
- Tags derived from selected discovery cards, preference values, or area vibes.
- Image collage using selected discovery card images.

Image strategy:

1. Prefer `DiscoveryCard.image_url` from selected discovery cards.
2. If one image exists, use it as the dominant image and support it with color panels.
3. If multiple images exist, show a compact collage.
4. If no images exist, fall back to a route/map texture using available place coordinates.
5. If no coordinates exist, fall back to an editorial text brief with color, tags, and metrics.

The hero must not claim that photos are live or official unless the source supports it.

### 2. Decision Metrics

Immediately below the hero, show four scan-friendly metric cards.

Metrics:

- Budget Fit: compares itinerary budget total against user budget.
- Pace: summarizes day density from segment count, duration, and rest blocks.
- Route: summarizes route completeness or travel friction from route-enriched segments.
- Risks: summarizes validator warnings/errors and reservation or timing issues.

Each metric should have:

- A label.
- A plain-language status.
- A compact visual indicator.
- One sentence explaining why it matters.

Examples:

- "Within budget range" for Budget Fit.
- "Balanced pace" for Pace.
- "Some routes need confirmation" for Route.
- "2 warnings to review" for Risks.

### 3. Narrative Route

Add a section that translates the itinerary into a story arc before showing the detailed day cards.

Purpose:

- Help the user understand the logic of the plan.
- Make the result feel curated.
- Bridge emotional travel desire and operational itinerary detail.

Content:

- One card per day.
- Day label, date, and a short narrative title.
- 2-3 anchor moments from itinerary segments.
- Optional area or theme tags.
- A compact budget or pace hint.

The narrative route should be derived from existing itinerary segments and discovery card references. It should not require a new LLM call for the first release.

### 4. Day-by-Day Execution

Retain the detailed itinerary, but make it feel more like an execution plan.

Each day should show:

- Day title, date, and summary.
- Timeline segments with time, type, place, description, cost band, and route information when available.
- Validator issues scoped to that day.
- Notes and caveats.
- Clear distinction between attraction, food, transit, rest, hotel, and return blocks.

The existing `ItineraryDayCard` can be redesigned or wrapped by a richer parent component. Keep the data contract stable.

### 5. Left Rail: Trip Spine

The left rail provides orientation and keeps the user grounded.

Content:

- Destination and date range.
- Selected stay area.
- Transport summary.
- Day navigation.
- Travel tone from preferences, such as quiet/lively, stay type, transport preference, and change-hotel preference.

The left rail should remain useful but not compete with the main story hero.

### 6. Right Rail: Map, Companion Brief, Smart Adjustments

The right rail adds spatial and assistant-like support.

Content:

- Map or map placeholder using existing place coordinates.
- Companion Brief: a short contextual explanation of the plan, written as helpful guidance rather than chat.
- Smart Adjustments: suggested next actions based on existing capabilities.

Smart Adjustment examples:

- "Switch stay area" if alternatives exist.
- "Reduce pace" when validator issues or dense days are present.
- "Review budget" when overrun flag is true.
- "Confirm routes" when route enrichment is partial.

This phase should not introduce a new conversational backend. The companion brief is a frontend presentation layer over existing data.

## Data Mapping

Use existing data first.

Primary data sources:

- `PlanningSession.hard_constraints`
- `PlanningSession.discovery_state.payload.cards`
- `PlanningSession.discovery_state.selected_card_ids`
- `PlanningSession.preferences`
- `PlanningSession.stay_recommendation`
- `PlanningSession.transport_recommendation`
- `PlanningSession.itinerary`
- `Itinerary.budget`
- `Itinerary.validator_issues`
- `ItineraryDay.segments`
- `ItinerarySegment.place`
- `ItinerarySegment.cost_estimate`

Derived frontend helpers:

- `selectedDiscoveryCards(session)`
- `heroImages(session)`
- `destinationTags(session)`
- `budgetFitStatus(session)`
- `paceStatus(itinerary)`
- `routeStatus(itinerary)`
- `riskStatus(itinerary)`
- `narrativeRouteItems(session)`
- `smartAdjustmentPrompts(session)`

These helpers should live in frontend code and be covered by unit tests. They should be deterministic and fixture-friendly.

## Visual System

The design should avoid copying TripStar's dark glassmorphism wholesale. The product should feel more premium while staying practical.

Style direction:

- Light professional surface as the default.
- Rich destination hero at the top.
- Warm travel accents used sparingly.
- Cool, calm neutral grays for operational sections.
- Clear metric cards with strong hierarchy.
- Rounded corners kept moderate, aligned with existing UI.
- Images treated with fixed aspect ratios and robust fallbacks.

Typography:

- Hero title: strong but not oversized.
- Section headings: concise and scannable.
- Metric labels: small, uppercase, muted.
- Important values: larger and darker.
- Explanatory copy: short, plain language.

The UI should not rely on color alone for status; metric cards should include text labels.

## Responsive Behavior

Desktop:

- Three-column command center after the hero.
- Left rail for trip spine.
- Main column for metrics, narrative route, and day execution.
- Right rail for map and companion panels.

Tablet:

- Hero remains full width.
- Left rail collapses into a horizontal trip spine.
- Right rail panels move below metrics or below narrative route.

Mobile:

- Single-column layout.
- Hero first.
- Metrics in a two-column or stacked grid.
- Trip spine becomes a compact summary.
- Map and companion panels appear before detailed days if useful, otherwise after narrative route.
- Day-by-day cards remain the primary scroll experience.

No content should require hover to understand or operate.

## Error And Fallback States

Image fallback:

- Broken image URL falls back without layout shift.
- Missing images fall back to route texture.
- Missing routes fall back to editorial brief.

Data fallback:

- Missing itinerary returns the existing empty state.
- Missing budget hides or softens Budget Fit rather than showing incorrect numbers.
- Missing validator issues displays "No issues flagged" only if itinerary exists.
- Missing discovery cards still renders hero from constraints and itinerary data.
- Missing route data marks Route as "Needs confirmation."

Provider or fixture mode should not change page structure.

## Accessibility And Usability

Requirements:

- Headings follow a logical hierarchy.
- Metric cards have readable status text.
- Images use decorative empty alt text unless the image itself conveys unique information.
- Interactive controls have clear labels.
- Buttons use action-oriented copy.
- Layout works with keyboard navigation.
- Text contrast should meet WCAG AA for normal text.
- Mobile tap targets should be at least 44px where practical.

The page should pass a basic trunk test: users should immediately know where they are, what trip they are viewing, and what they can do next.

## Testing Strategy

Unit tests:

- Hero image selection and fallback.
- Destination tag derivation.
- Budget fit classification.
- Pace classification.
- Route status classification.
- Risk status classification.
- Narrative route item derivation.
- Smart adjustment prompt derivation.

Component tests:

- Result page renders with full fixture session.
- Result page renders with no images.
- Result page renders with missing route coordinates.
- Result page renders with budget overrun.
- Result page renders validator warnings visibly.

E2E:

- Existing MVP flow should still reach the itinerary page.
- Fixture-backed e2e should verify hero, metrics, narrative route, and day execution sections exist.
- Stay override behavior should remain functional.

## Acceptance Criteria

The redesign is complete when:

1. The result page opens with a story-led destination hero.
2. Discovery images are used when available and degrade gracefully when missing or broken.
3. Budget, pace, route, and risk metrics are visible near the top.
4. The narrative route summarizes the trip before detailed day cards.
5. Detailed day execution remains available and readable.
6. Stay switching still works.
7. Validator issues remain visible and understandable.
8. The layout works on desktop, tablet, and mobile.
9. Existing fixture-backed regression remains green.
10. No new live provider dependency is introduced.
