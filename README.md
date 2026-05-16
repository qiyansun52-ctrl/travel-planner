# Travel Planner

> A single-city AI travel planning product that turns constraints into discovery cards, preferences, a grounded itinerary, and conversational adjustments.
>
> AI 单城市旅行规划产品：从硬约束出发，生成发现卡片、偏好选择、完整行程和对话式调整。

![status](https://img.shields.io/badge/status-MVP%20product-teal)
![stack](https://img.shields.io/badge/stack-Next.js%20%2B%20FastAPI%20%2B%20LangGraph-blue)
![tests](https://img.shields.io/badge/tests-Vitest%20%2B%20Playwright-green)

## Product Flow

```text
/ -> /discovery/[sessionId] -> /preferences/[sessionId] -> /trips/[sessionId]
```

1. **Intake** - collect destination, dates, travelers, budget, and core constraints.
2. **Discovery** - present grounded cards for attractions, food, neighborhoods, and activities.
3. **Preferences** - capture stay, transport, pace, and budget tradeoffs.
4. **Trips** - generate a story-led itinerary with budget validation and chat adjustments.

## Highlights

- **Grounded discovery cards** with provider-enriched places, images, cost signals, and source notes.
- **LangGraph planning workflow** for stay, transport, daily itinerary, validation, and adjustment routing.
- **Premium web UI** across intake, discovery, planning progress, trip result, and preferences.
- **Conversational refinement** for itinerary changes, including Type A/B/C adjustment handling.
- **Fixture-backed regression mode** so CI and local smoke tests do not spend live provider quota.
- **Production-readiness guardrails** for environment checks, generated type drift, provider smoke, and ops summaries.

## Architecture

- `web/` - Next.js UI and route shell. The browser calls the Python API through `NEXT_PUBLIC_API_URL`.
- `api/` - FastAPI backend with Pydantic schemas, sessions, LangGraph workflow, provider adapters, metrics, and cost logs.
- `docs/` - product specs, implementation plans, and archived prototype material.

The legacy `web/src/app/api/`, `web/src/server/`, and `web/src/domain/` TypeScript backend paths are intentionally gone.

## Tech Stack

**Frontend**
- Next.js 16
- React 19
- TypeScript
- Tailwind CSS v4
- Vitest + Testing Library
- Playwright

**Backend**
- FastAPI
- LangGraph
- Pydantic
- `google-genai` with Gemini 2.5 Flash
- Tavily and map-provider adapters
- File-backed fixture/session storage for local regression

## Environment

```bash
cp api/.env.example api/.env
cp web/.env.example web/.env.local
```

Fixture-backed local regression uses dummy keys and `E2E_FIXTURE_MODE=1`.
Live provider-backed runs need real keys in `api/.env`.

## Development

Run both services from the web workspace:

```bash
cd web
npm run dev
```

Open `http://localhost:3000`.

Run the API by itself:

```bash
cd api
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Verification

From `web/`:

```bash
npm run typecheck
npm run test
npm run test:e2e
npm run build
```

From the repo root:

```bash
make launch-check
make smoke
make regression
```

`make regression` runs launch docs/env checks, generated-type drift checks, frontend lint/unit/build/e2e, backend pytest, backend ruff, and fixture-backed API smoke.

## Production-Like Demo Guardrails

Default regression is offline and fixture-backed. It uses deterministic provider behavior and does not spend live Gemini, Tavily, or map-provider quota.

Live provider checks are explicit gates:

```bash
make production-check
make smoke-real
make ops-summary
```

`make smoke-real` can consume provider quota. Do not run it in CI unless the environment is intentionally configured with production-like keys, quota, and origins. It also expects a running AMap MCP server with `AMAP_MCP_URL` set before the gate starts.

## Legacy MCP Prototype

This repository began as a Claude + MCP manual workflow using rail, map, and lifestyle-social tools to render a printable HTML itinerary. Those early files were archived under `docs/archive/early-mcp-prototype/`, and the current product has moved to the FastAPI + LangGraph + Next.js app described above.

## Planning Docs

The original migration roadmap is `docs/superpowers/plans/2026-05-09-langgraph-mvp-roadmap.md`.
Plans 1-9 are complete. Later plans cover launch readiness, fixture smoke, grounding, map enrichment, session resume, production guardrails, result-page expression, and product completion.

## License

Personal project. Please open an issue if you want to reuse the code or template.
