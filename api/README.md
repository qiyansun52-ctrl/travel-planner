# Travel Planner API

FastAPI backend for the single-city travel planner. This service is the target owner of schemas, sessions, LangGraph workflow orchestration, provider adapters, metrics, and LLM cost logs.

## Target Flow

```text
discovery -> stay + transport -> planner -> validator
                                      ^          |
                                      | error    |
                                      +----------+
```

Adjustment requests are classified separately:

- Type A: planner-only partial replan.
- Type B: rerun the relevant agent(s), then planner.
- Type C: return a confirmation for root constraint changes before rerunning anything.

## Setup

Requires Python 3.12 and `uv`.

```bash
cd api
cp .env.example .env
uv sync
```

Environment variables:

```text
GEMINI_API_KEY=...
TAVILY_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
ENVIRONMENT=development
AMAP_API_KEY=...
MAPBOX_ACCESS_TOKEN=...
AMAP_MCP_URL=...
SESSION_DATA_DIR=.data
METRICS_DATA_DIR=.data
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
E2E_FIXTURE_MODE=0
RATE_LIMIT_ENABLED=1
RATE_LIMIT_MAX_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
MAX_DISCOVERY_RUNS_PER_SESSION=3
MAX_ITINERARY_RUNS_PER_SESSION=4
MAX_ADJUSTMENTS_PER_SESSION=8
HOST=0.0.0.0
PORT=8000
```

Provider keys besides Gemini/Tavily are optional during fixture-backed development.

- `ENVIRONMENT`: `development`, `test`, or `production`; `production` enables strict readiness checks.
- `AMAP_MCP_URL`: URL for a running AMap MCP server; required before running `make smoke-real`.
- `SESSION_DATA_DIR`: session storage directory. In production mode it must be an explicit non-`.data` path.
- `METRICS_DATA_DIR`: metrics and LLM cost log directory. In production mode it must be an explicit non-`.data` path.
- `RATE_LIMIT_ENABLED`: enables the in-process request limiter. It must stay enabled in production.
- `RATE_LIMIT_MAX_REQUESTS`: maximum requests allowed per rate-limit window.
- `RATE_LIMIT_WINDOW_SECONDS`: rate-limit window size in seconds.
- `MAX_DISCOVERY_RUNS_PER_SESSION`: per-session budget for discovery runs that may call paid providers.
- `MAX_ITINERARY_RUNS_PER_SESSION`: per-session budget for itinerary generation runs that may call paid providers.
- `MAX_ADJUSTMENTS_PER_SESSION`: per-session budget for adjustment requests that may call paid providers.

## Run

```bash
uv run uvicorn main:app --reload --port 8000
```

Server listens on `http://localhost:8000`. Health check: `http://localhost:8000/health`.

## Current Endpoints

- `GET /health`
- `POST /api/sessions`
- `GET /api/sessions`
- `GET /api/sessions/{session_id}`
- `POST /api/sessions/{session_id}/discovery`
- `PATCH /api/sessions/{session_id}/selection`
- `POST /api/sessions/{session_id}/preferences`
- `POST /api/sessions/{session_id}/itinerary`
- `GET /api/sessions/{session_id}/itinerary/stream`
- `PATCH /api/sessions/{session_id}/stay-override`
- `POST /api/sessions/{session_id}/adjustments`

Legacy scaffold endpoints `/api/discover` and `/api/plan/generate` have been removed from the Python app. There are no Next.js API routes in the canonical product flow after the web cutover; the browser calls these FastAPI routes directly.

## Smoke Test

From `api/`, run the fixture-backed smoke gate:

```bash
bash scripts/run_fixture_smoke.sh
```

The runner starts FastAPI on `127.0.0.1:${SMOKE_PORT:-8767}`, uses temporary session and metrics directories, runs `scripts/smoke_curl.sh`, and cleans up the server process.

Set `PYTHON_BIN=/path/to/python` when your shell does not expose `python3`.

From the repository root, `make smoke-real` runs live provider smoke checks. Start the AMap MCP server first and set `AMAP_MCP_URL`; this gate can consume live Gemini and map-provider quota.

## Ops Summary

```bash
uv run python scripts/ops_summary.py
```

This summarizes local metrics and LLM cost logs without printing secrets.

## Tests

```bash
uv run pytest -v
uv run ruff check app tests scripts
```

From the repository root, `make regression` runs the full web + API gate.

The canonical migration roadmap is `../docs/superpowers/plans/2026-05-09-langgraph-mvp-roadmap.md`; post-roadmap hardening plans live beside it as Plan 10+.
