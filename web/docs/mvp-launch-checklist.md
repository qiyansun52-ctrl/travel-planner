# MVP Launch Checklist

## Environment

Create `web/.env.local` from `web/.env.example`.

Required for live provider-backed runs:

- `LLM_PROVIDER_API_KEY`: server-side LLM provider key.
- `SEARCH_PROVIDER_API_KEY`: search enrichment key.
- `MAPBOX_ACCESS_TOKEN`: global geocoding and routing.
- `AMAP_API_KEY`: China geocoding and routing.
- `WEATHER_PROVIDER_API_KEY`: weather context.

The current fixture-backed MVP flow runs without live keys. The legacy migration variables `GEMINI_API_KEY`, `TAVILY_API_KEY`, and `NEXT_PUBLIC_API_URL` may still exist for older `/discover/[destination]` and Python-backend experiments; the session-based MVP flow uses same-origin Next.js routes.

## Local Development

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
- Metrics are written to `web/.data/events.jsonl`; write failures are swallowed so planning continues.
- Session persistence uses `web/.data/sessions.json` for anonymous local MVP use.

## Known MVP Limits

- Single-city trips only.
- No real-time hotel inventory.
- No real-time ticket booking.
- Prices are estimate-grade bands, not quotes.
- Session persistence is anonymous file-backed storage.
- Budget overrun errors may remain as inline risk notes because the MVP corrective pass only reruns the planner and does not rebalance stay or transport.
