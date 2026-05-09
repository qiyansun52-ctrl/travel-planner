# MVP Launch Checklist

## Environment

Create `api/.env` from `api/.env.example` and `web/.env.local` from `web/.env.example`.

Required for live provider-backed runs:

- `GEMINI_API_KEY`: Gemini LLM key for the Python backend.
- `TAVILY_API_KEY`: Tavily search key for discovery/provider enrichment.
- `AMAP_API_KEY`: China geocoding and routing.
- `MAPBOX_ACCESS_TOKEN`: global geocoding and routing.
- `WEATHER_PROVIDER_API_KEY`: weather context.
- `SESSION_DATA_DIR`: optional session storage directory, defaults to `api/.data`.

The fixture-backed MVP flow must run without live provider keys. Unit and E2E tests should use deterministic fixture behavior for LLM/provider calls.

Frontend canonical API calls should point to Python:

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## Local Development

```bash
cd api
uv sync
uv run uvicorn main:app --reload --port 8000
```

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:3000`.

## Verification

Expected passing state:

```bash
cd web
npm run test
npm run typecheck
npm run lint
npm run build
npm run test:e2e

cd ../api
uv run pytest -v
```

## Fallback Behavior

- Discovery can run in deterministic fixture mode when live LLM/provider keys are not available.
- Missing image or cost enrichment does not block rendering; cards degrade to `partial` or `minimal`.
- Metrics should be written to `api/.data/events.jsonl`; write failures are swallowed so planning continues.
- LLM cost logs should be written to `api/.data/llm-cost.jsonl`.
- Session persistence should use `api/.data/sessions.json` for anonymous local MVP use.

## Known MVP Limits

- Single-city trips only.
- No real-time hotel inventory.
- No real-time ticket booking.
- Prices are estimate-grade bands, not quotes.
- Session persistence is anonymous file-backed storage.
- Budget overrun errors may remain as inline risk notes because the MVP corrective pass only reruns the planner and does not rebalance stay or transport.
