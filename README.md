# Travel Planner

Single-city travel planning MVP. The target product flow is:

```text
/ -> /discovery/[sessionId] -> /preferences/[sessionId] -> /trips/[sessionId]
```

## Architecture

- `web/`: Next.js UI and route shell only.
- `api/`: FastAPI backend that owns Pydantic schemas, sessions, LangGraph planning workflow, provider adapters, metrics, and cost logs.
- LLM/search stack: `google-genai` with Gemini 2.5 flash, plus Tavily/provider adapters.

`web/src/app/api/`, `web/src/server/`, and `web/src/domain/` are gone. The browser client calls the Python API routes directly through `NEXT_PUBLIC_API_URL`.

## Environment

```bash
cp api/.env.example api/.env
cp web/.env.example web/.env.local
```

Live provider-backed runs need real keys in `api/.env`. Fixture-backed regression uses dummy keys and `E2E_FIXTURE_MODE=1`.

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
uv run uvicorn main:app --reload --port 8000
```

## Verification

From the repo root:

```bash
make launch-check
make smoke
make regression
```

`make regression` runs launch docs/env checks, generated-type drift checks, frontend lint/unit/build/e2e, backend pytest, backend ruff, and fixture-backed API smoke.

## API Smoke

From the repo root:

```bash
make smoke
```

`make smoke` starts FastAPI in fixture mode on port `8767`, runs `api/scripts/smoke_curl.sh`, and cleans up the server process.

## Planning Docs

The original migration roadmap is `docs/superpowers/plans/2026-05-09-langgraph-mvp-roadmap.md`. Plan 1-9 are complete; Plan 10-13 are post-roadmap hardening passes for launch readiness, fixture smoke automation, roadmap closure, and web dependency hygiene.
