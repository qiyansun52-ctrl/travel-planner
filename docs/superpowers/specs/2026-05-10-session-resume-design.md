# Session Resume Design

## Goal

Make the local MVP feel persistent instead of throwaway by letting a user resume recent active trips from the home screen.

## Recommended Approach

Use the existing file-backed session repository as the source of truth and add a small read-only list path:

- `GET /api/sessions?limit=5` returns recent active sessions sorted by `updated_at`.
- `web/src/lib/apiClient.ts` exposes `listSessions()`.
- `HomeStart` loads recent sessions on mount and renders a compact "Recent trips" section below the intake copy and above the hard-constraint form.

This is better than a localStorage-only shortcut because it works with the existing backend persistence, survives browser storage clears, and aligns with the current anonymous local-MVP model. It is also smaller than building a full trips dashboard with search, archive, labels, and auth.

## User Experience

The home page stays focused on starting a new trip. If recent active sessions exist, it shows a quiet list with destination, dates, budget, last updated time, and a single "Resume" link per trip.

Resume target is deterministic:

- If `session.itinerary` exists, go to `/trips/{session_id}`.
- Else if `session.preferences` exists, go to `/trips/{session_id}` so the itinerary stream can run.
- Else if discovery has selected card IDs, go to `/preferences/{session_id}`.
- Else go to `/discovery/{session_id}` so discovery can either load existing cards or run.

If the list request fails, the home page hides the recent section and still allows a new trip to start.

## API Contract

`GET /api/sessions` accepts:

- `limit`: integer, default `5`, minimum `1`, maximum `20`.
- `include_archived`: boolean, default `false`.

Response model is `list[PlanningSession]`.

The endpoint is read-only and does not emit metrics.

## Components

- `api/app/routes/sessions.py`: add the list route before `/{session_id}` so FastAPI does not treat query access as a session id.
- `api/tests/routes/test_sessions.py`: verify sorting, default archived filtering, optional archived inclusion, and limit clamping/validation.
- `web/src/lib/apiClient.ts`: add `listSessions(limit = 5)`.
- `web/src/components/intake/RecentTrips.tsx`: render recent sessions and compute resume href.
- `web/src/components/intake/HomeStart.tsx`: load sessions and pass copy by language.
- `web/src/lib/apiClient.test.ts`: verify URL mapping.
- `web/e2e/recent-trips.spec.ts`: create a fixture trip, navigate home, and resume it from the recent list.

## Error Handling

- API repository errors use existing `route_error()`.
- The web client treats recent-list failure as non-blocking and renders the intake form normally.
- Empty lists render nothing, avoiding visual clutter for first-time users.

## Testing

- API route pytest for `GET /api/sessions`.
- API client unit test for `listSessions`.
- Component behavior is covered by Playwright through the real fixture-backed backend.
- Full `make regression` remains the release gate.

## Non-Goals

- No auth or multi-user isolation.
- No archive/delete UI.
- No server-side rendered dashboard.
- No migration away from file-backed persistence.

## Self-Review

- Placeholder scan: no placeholder language.
- Internal consistency: resume routing matches existing page behavior.
- Scope: one API list endpoint plus one home-page section; no broader account system.
- Ambiguity: archived sessions are excluded by default and only included via explicit query.
