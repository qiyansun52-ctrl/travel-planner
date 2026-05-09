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
AMAP_API_KEY=...
MAPBOX_ACCESS_TOKEN=...
WEATHER_PROVIDER_API_KEY=...
SESSION_DATA_DIR=.data
```

Provider keys besides Gemini/Tavily are optional during fixture-backed development.

## Run

```bash
uv run uvicorn main:app --reload --port 8000
```

Server listens on `http://localhost:8000`. Health check: `http://localhost:8000/health`.

## Current Endpoints

- `GET /health`
- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `POST /api/sessions/{session_id}/discovery`
- `PATCH /api/sessions/{session_id}/selection`
- `POST /api/sessions/{session_id}/preferences`
- `POST /api/sessions/{session_id}/itinerary`
- `GET /api/sessions/{session_id}/itinerary/stream`
- `PATCH /api/sessions/{session_id}/stay-override`
- `POST /api/sessions/{session_id}/adjustments`

Legacy scaffold endpoints `/api/discover` and `/api/plan/generate` have been removed from the Python app. The remaining Next.js endpoints are compatibility surfaces until the web cutover plan points the UI directly at these canonical FastAPI routes.

## Smoke Test

Start the API in fixture mode:

```bash
E2E_FIXTURE_MODE=1 uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Run the canonical curl flow:

```bash
BASE_URL=http://127.0.0.1:8000 bash scripts/smoke_curl.sh
```

Expected output:

```text
Smoke flow passed for session_...
```

Set `PYTHON_BIN=/path/to/python` when your shell does not expose `python3`.

## Tests

```bash
uv run pytest -v
```

The active implementation plan is `../docs/superpowers/plans/2026-05-09-langgraph-single-city-mvp.md`.
