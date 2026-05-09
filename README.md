# Travel Planner

Single-city travel planning MVP. The target product flow is:

```text
/ -> /discovery/[sessionId] -> /preferences/[sessionId] -> /trips/[sessionId]
```

## Architecture

- `web/`: Next.js UI and route shell only.
- `api/`: FastAPI backend that owns Pydantic schemas, sessions, LangGraph planning workflow, provider adapters, metrics, and cost logs.
- LLM/search stack: `google-genai` with Gemini 2.5 flash, plus Tavily/provider adapters.

After Plan 7, `web/src/app/api/`, `web/src/server/`, and `web/src/domain/` are gone. The browser client calls the Python API routes directly, with `NEXT_PUBLIC_API_URL` defaulting to `http://localhost:8000`.

The canonical implementation plan is:

```text
docs/superpowers/plans/2026-05-09-langgraph-single-city-mvp.md
```

## Development

Run both services from the web workspace:

```bash
cd web
npm run dev
```

Run either service by itself:

```bash
cd web
npm run dev:web
npm run dev:api
```

Or run the API directly:

```bash
cd api
uv run uvicorn main:app --reload --port 8000
```

## Verification

```bash
cd web
npm run typecheck
npm run lint
npm run test
npm run build

cd ../api
uv run pytest -v
```
