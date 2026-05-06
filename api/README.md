# Travel Planner API (Python Backend)

FastAPI backend for the travel planner. Mirrors the Next.js `/api/*` routes
during the multi-agent migration.

## Setup

Requires Python 3.12 and [uv](https://github.com/astral-sh/uv).

```bash
cd api
cp .env.example .env
# Edit .env — fill in GEMINI_API_KEY and TAVILY_API_KEY
uv sync
```

## Run

```bash
uv run uvicorn main:app --reload --port 8000
```

Server listens on http://localhost:8000. Health check: http://localhost:8000/health.

## Endpoints

- `GET /health` — liveness check
- `GET /api/discover?destination=...` — three-section attraction cards
- `POST /api/plan/generate` — new plan generation OR chat adjustment

## Tests

```bash
uv run pytest -v
```
