# Development Environment

## Requirements

- Node.js LTS.
- npm, using the committed `package-lock.json`.
- FastAPI backend running on `http://127.0.0.1:8000`.

## Environment Variables

Create `web/.env.local` from `web/.env.example`:

```bash
cp .env.example .env.local
```

The only frontend-owned variable is the public API target:

```dotenv
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## Backend Provider Keys

Provider keys live in `../api/.env`, not in `web/.env.local`.

## Minimum Runnable Mode

Fixture-backed unit tests and end-to-end tests run without live provider keys. Playwright starts FastAPI with `E2E_FIXTURE_MODE=1`, dummy provider keys, and temporary session storage.

## Local Files

These files and folders are local-only and must not be committed:

- `web/.env.local`
- `web/test-results/`
- `web/playwright-report/`
