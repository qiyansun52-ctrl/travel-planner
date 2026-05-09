# Travel Planner Web

Next.js UI and route shell for the single-city planner. Planning logic, sessions, persistence, metrics, providers, and LangGraph orchestration live in `../api`.

## Development

```bash
cd web
npm install
npm run dev
```

The dev script starts FastAPI on `http://127.0.0.1:8000` and Next.js on `http://localhost:3000`. The browser client defaults `NEXT_PUBLIC_API_URL` to `http://localhost:8000`; set it explicitly if your API runs elsewhere.

Run either side by itself:

```bash
npm run dev:web
npm run dev:api
```

## Test

```bash
npm run typecheck
npm run lint
npm run test
npm run build
npm run test:e2e
```

`npm run test:e2e` starts both services in fixture mode with dummy provider keys.

## Canonical Flow

```text
/ -> /discovery/[sessionId] -> /preferences/[sessionId] -> /trips/[sessionId]
```

There are no Next.js API routes or server-side planning agents after Plan 7; the UI talks to the Python API directly.
