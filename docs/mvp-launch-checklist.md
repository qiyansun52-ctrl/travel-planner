# MVP Launch Checklist

## Environment

Create `api/.env` from `api/.env.example` and `web/.env.local` from `web/.env.example`.

`api/.env` owns backend provider keys, persistence, metrics, fixture mode, CORS, and server binding:

- `GEMINI_API_KEY`: Gemini LLM key for the Python backend.
- `TAVILY_API_KEY`: Tavily search key for discovery/provider enrichment.
- `GEMINI_MODEL`: Gemini model name, normally `gemini-2.5-flash`.
- `AMAP_API_KEY`: China geocoding and routing.
- `MAPBOX_ACCESS_TOKEN`: global geocoding and routing.
- `SESSION_DATA_DIR`: session storage directory, defaults to `.data`.
- `METRICS_DATA_DIR`: metrics and cost log directory, defaults to `.data`.
- `CORS_ORIGINS`: allowed browser origins for local web clients.
- `E2E_FIXTURE_MODE`: set to `1` for offline fixture-backed flows.
- `HOST` and `PORT`: API server bind settings.

`web/.env.local` owns only the public browser API target:

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

The fixture-backed MVP flow must run without live provider keys. Unit and E2E tests should use deterministic fixture behavior for LLM/provider calls with `E2E_FIXTURE_MODE=1`.

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

Expected passing state starts from the repository root:

```bash
make launch-check
make regression
```

## API Smoke

Start the API in fixture mode:

```bash
cd api
E2E_FIXTURE_MODE=1 GEMINI_API_KEY=test-gemini TAVILY_API_KEY=test-tavily uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Run the canonical curl flow from the repository root:

```bash
BASE_URL=http://127.0.0.1:8000 bash api/scripts/smoke_curl.sh
```

Expected output starts with `Smoke flow passed for session_`.

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
