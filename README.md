# Travel Planner

Single-city travel planning MVP. The target product flow is:

```text
/ -> /discovery/[sessionId] -> /preferences/[sessionId] -> /trips/[sessionId]
```

## Architecture

- `web/`: Next.js UI and route shell only.
- `api/`: FastAPI backend that will own Pydantic schemas, sessions, LangGraph planning workflow, provider adapters, metrics, and cost logs.
- LLM/search stack: `google-genai` with Gemini 2.5 flash, plus Tavily/provider adapters.

The canonical implementation plan is:

```text
docs/superpowers/plans/2026-05-09-langgraph-single-city-mvp.md
```

## Development

Run the web UI:

```bash
cd web
npm run dev
```

Run the API:

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
