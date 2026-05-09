# Travel Planner Design v2

> **STATUS: ACTIVE (2026-05-09)**

## Product Positioning

Travel Planner turns a rough single-city travel idea into a structured, adjustable itinerary. The product helps users progressively narrow the trip: first hard constraints, then discovery choices, then stay and transport preferences, then a budget-aware itinerary that can be partially replanned through chat.

The MVP is not a booking engine. It targets semi-real planning quality: credible areas, travel times, budget bands, and itinerary structure, without promising real-time hotel or ticket inventory.

## MVP Scope

In scope:

- Single-city trips.
- Step 1 hard-constraint intake.
- Discovery cards for experiences, food summaries, area impressions, cost signals, and reservation hints.
- Preferences for stay and intercity/local transport.
- Four-agent planning pipeline plus deterministic validator.
- Conversational partial replanning with Type A/B/C adjustment classification.
- File-backed anonymous sessions for local MVP use.

Out of scope:

- Multi-city trip planning.
- Real-time booking.
- Guaranteed supplier pricing.
- Automatic root constraint changes without confirmation.
- Fully persistent user accounts.

## Technical Stack

| Layer | Technology |
|---|---|
| UI | Next.js App Router, React, TypeScript, Tailwind |
| Backend | FastAPI, Python 3.12, Pydantic v2 |
| Agent orchestration | LangGraph |
| LLM | `google-genai`, Gemini 2.5 flash |
| Search/provider enrichment | Tavily, map/weather/supplier adapters |
| Persistence | File-backed session JSON for MVP |
| Verification | Vitest, Playwright, pytest |

## Architecture

```text
┌────────────────────────────┐
│ web/ Next.js               │
│ UI, pages, route shell     │
│ session id in browser      │
└─────────────┬──────────────┘
              │ HTTP JSON + SSE
              ▼
┌────────────────────────────┐
│ api/ FastAPI               │
│ Pydantic contracts         │
│ session repository         │
│ LangGraph workflow         │
│ metrics + cost logs        │
└─────────────┬──────────────┘
              │ adapters
              ▼
┌────────────────────────────┐
│ Gemini / Tavily / maps     │
│ weather / supplier future  │
└────────────────────────────┘
```

Next.js must not own server-side agent orchestration in the target architecture. During migration, existing TypeScript server code is reference implementation only.

## Canonical User Flow

1. `/`: user submits hard constraints.
2. `/discovery/[sessionId]`: backend generates discovery cards; user selects interests.
3. `/preferences/[sessionId]`: user confirms stay and transport preferences.
4. `/trips/[sessionId]`: backend runs stay, transport, planner, validator, and one corrective planner pass if needed.
5. Adjustment panel: backend classifies the request and reruns only the necessary graph branch.

## Data Ownership

- Pydantic schemas in `api/` are the source of truth.
- TypeScript UI types should eventually be generated from Python JSON Schema.
- Session data lives in `api/.data/sessions.json` for the MVP.
- LLM cost records live in `api/.data/llm-cost.jsonl`.
- Metrics events live in `api/.data/events.jsonl`.

## Active Plan

Implementation follows:

```text
docs/superpowers/plans/2026-05-09-langgraph-single-city-mvp.md
```
