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

## Production-Like Demo Guardrails

Default regression is offline and fixture-backed: it uses deterministic provider behavior and does not spend live Gemini, Tavily, or map-provider quota.

Live provider checks are explicit gates:

```bash
make production-check
make smoke-real
make ops-summary
```

`make smoke-real` uses live Gemini and map providers, so it can consume provider quota. Do not run it in CI unless the CI environment is intentionally configured with production-like keys, quota, and origins.
It also expects a running AMap MCP server with `AMAP_MCP_URL` set before the gate starts.

## API Smoke

From the repo root:

```bash
make smoke
```

`make smoke` starts FastAPI in fixture mode on port `8767`, runs `api/scripts/smoke_curl.sh`, and cleans up the server process.

## Planning Docs

The original migration roadmap is `docs/superpowers/plans/2026-05-09-langgraph-mvp-roadmap.md`. Plans 1-9 are complete. Plans 10+ are post-roadmap hardening/product polish: Plan18 is complete; Plan19 covers production-readiness guardrails; Plan20 remains product polish.
