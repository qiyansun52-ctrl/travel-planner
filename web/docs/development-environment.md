# Development Environment

## Requirements

- Node.js LTS.
- npm, using the committed `package-lock.json`.
- Local project data is written under `web/.data/`.

## Environment Variables

Create `web/.env.local` from `web/.env.example` and fill in provider keys:

```bash
LLM_PROVIDER_API_KEY=
SEARCH_PROVIDER_API_KEY=
MAPBOX_ACCESS_TOKEN=
AMAP_API_KEY=
WEATHER_PROVIDER_API_KEY=
```

## Provider Keys

- `LLM_PROVIDER_API_KEY`: key for the configured LLM provider used by server-side agents.
- `SEARCH_PROVIDER_API_KEY`: key for discovery research/search enrichment.
- `MAPBOX_ACCESS_TOKEN`: token for global map, geocoding, and routing coverage.
- `AMAP_API_KEY`: key for China map, geocoding, and routing coverage.
- `WEATHER_PROVIDER_API_KEY`: key for forecast and trip weather context.

## Minimum Runnable Mode

Fixture-backed unit tests and end-to-end tests must be able to run without live provider keys. Live discovery and itinerary generation require the provider keys above because those flows call external search, map, weather, and LLM services.

## Local Files

These files and folders are local-only and must not be committed:

- `web/.env.local`
- `web/.data/`
- `web/test-results/`
- `web/playwright-report/`
