> **STATUS: SUPERSEDED (2026-05-09)**
> 本文档从已注销的 `fastapi-session-backend-migration` worktree 抢救而来,作为历史参考保留。
> 其“先做 FastAPI session 边界、LangGraph 延后”的路线已被 Python + LangGraph 单城市 MVP 合并计划取代。
> 当前唯一 active 计划见:`docs/superpowers/plans/2026-05-09-langgraph-single-city-mvp.md`

# FastAPI Frontend/Backend Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement task-by-task.

**Goal:** Make FastAPI the only backend for the canonical session-based single-city MVP while keeping the current user-visible flow behavior unchanged.

**Architecture:** Next.js remains a frontend-only app for `/` -> `/discovery/[sessionId]` -> `/preferences/[sessionId]` -> `/trips/[sessionId]`. FastAPI owns sessions, discovery, preferences, itinerary generation, stay override, adjustment routing, file persistence, metrics, and deterministic fixture behavior. LangGraph and live supplier/provider integration are explicitly deferred until this backend boundary is stable.

**Tech Stack:** Next.js 16, React 19, TypeScript, FastAPI, Pydantic 2, pytest, Vitest, Playwright, file-backed JSON persistence.

## Summary

- Canonical product flow becomes fully cross-service: Next pages call FastAPI through `NEXT_PUBLIC_API_URL`.
- Existing Next API Routes remain temporarily as legacy code, but no canonical page uses them.
- Python backend ports the current TypeScript session flow behavior first: same session shape, same fixture discovery, same deterministic stay/transport/planner, same validator semantics.
- Legacy `/discover/[destination]` -> `/plan/[id]` and old `/api/discover`/`/api/plan/generate` are not deleted in this pass.

## Key API Changes

FastAPI becomes the owner of these canonical endpoints:

```text
POST   /api/sessions
GET    /api/sessions/{session_id}
POST   /api/sessions/{session_id}/discovery
PATCH  /api/sessions/{session_id}/selection
POST   /api/sessions/{session_id}/preferences
POST   /api/sessions/{session_id}/itinerary
PATCH  /api/sessions/{session_id}/stay-override
POST   /api/sessions/{session_id}/adjustments
GET    /health
```

Request/response defaults:

- All canonical session payloads use the current `web/src/domain/schemas.ts` snake_case field names.
- `POST /api/sessions` returns the full `PlanningSession`; frontend uses `session_id` from the response URL path, not a cross-origin cookie.
- `POST /api/sessions/{session_id}/discovery` returns the updated `PlanningSession`.
- `PATCH /selection` body: `{ "selected_card_ids": string[] }`.
- `POST /preferences` body is the `Preference` object directly.
- `POST /itinerary` body may include `{ "planner_only_reason": string | null }`.
- `PATCH /stay-override` body: `{ "stay_option_id": string | null }`.
- `POST /adjustments` body: `{ "message": string, "type_c_action"?: "replan" | "save_and_start_new" | "cancel" }`.

## Implementation Tasks

### Task 1: Add Python Session Domain Models

**Files:**

- Create `api/app/domain/schemas.py`
- Create `api/tests/test_session_schemas.py`

**Steps:**

- Port the canonical Zod models from `web/src/domain/schemas.ts` into Pydantic models: `HardConstraints`, `DiscoveryCard`, `DiscoveryOutput`, `Preference`, `StayRecommendation`, `TransportRecommendation`, `Itinerary`, `ValidatorIssue`, `PlanningSession`.
- Preserve enum values exactly, including `hotel_checkin`, `hotel_checkout`, `hotel_return`, `active`, `archived`, `A`/`B`/`C`/`unknown`.
- Add tests proving valid fixture payloads parse and invalid renamed fields fail.
- Run `cd api && uv run pytest tests/test_session_schemas.py -v`.
- Commit: `feat(api): add canonical session schemas`.

### Task 2: Port Budget, Selection, Validator Utilities

**Files:**

- Create `api/app/domain/budget.py`
- Create `api/app/domain/selection.py`
- Create `api/app/domain/validator.py`
- Create matching pytest files under `api/tests/`

**Steps:**

- Port `calculateDailyAttractionSlot`, `classifyAttractionCostSignal`, `normalizeSelectedCardIds`, `isContinueDisabled`, `hasDensityWarning`, and `validateItinerary`.
- Keep validator thresholds identical: budget high `> 115%`, more than 5 attraction stops, more than 8 attraction hours, transit `> 40%` active attraction time, reservation window/duration checks.
- Add pytest coverage matching the current Vitest cases.
- Run `cd api && uv run pytest tests/test_budget.py tests/test_selection.py tests/test_validator.py -v`.
- Commit: `feat(api): port session domain utilities`.

### Task 3: Add File-Backed Python Session Repository

**Files:**

- Create `api/app/persistence/session_repository.py`
- Create `api/tests/test_session_repository.py`
- Modify `api/app/config.py`

**Steps:**

- Add optional `data_dir: str = ".data"` to settings.
- Implement file store at `api/.data/sessions.json` by default.
- Implement repository methods matching current TypeScript behavior: create, get, update discovery, update preferences, update stay, update transport, write itinerary, append conversation, update stay override, reset to discovery, archive and fork, update snapshot label.
- Use atomic temp-file write + rename.
- Reject mutations on archived sessions except snapshot relabel.
- Add tests for create/read/update, reset, archive/fork, stay override, corrupt JSON quarantine.
- Run `cd api && uv run pytest tests/test_session_repository.py -v`.
- Commit: `feat(api): add file-backed planning session repository`.

### Task 4: Port Deterministic Agents and Orchestrator

**Files:**

- Create `api/app/agents/discovery.py`
- Create `api/app/agents/stay.py`
- Create `api/app/agents/transport.py`
- Create `api/app/agents/planner.py`
- Create `api/app/agents/adjustment_classifier.py`
- Create `api/app/agents/orchestrator.py`
- Create matching pytest files under `api/tests/`

**Steps:**

- Port current behavior from `web/src/server/agents/*` exactly before improving intelligence.
- `discovery` returns fixture output when `E2E_FIXTURE_MODE=1` or no live LLM key is configured.
- `stay` uses discovery area summaries and returns one primary plus two alternatives.
- `transport` uses `intercity_transport_preference`, choosing rail unless flight is explicitly selected.
- `planner` builds deterministic day-by-day itinerary from selected discovery cards and active stay area.
- `orchestrator` runs stay + transport + planner + validator, then one corrective planner pass only for validator errors.
- `adjustment_classifier` keeps the current regex-based `A`/`B`/`C` behavior.
- Add pytest coverage for fixture discovery, stay/transport outputs, planner versioning, corrective pass, `A`/`B`/`C` classification.
- Run `cd api && uv run pytest tests/test_agents_*.py -v`.
- Commit: `feat(api): port deterministic planning agents`.

### Task 5: Add FastAPI Canonical Session Routes

**Files:**

- Create `api/app/routes/sessions.py`
- Modify `api/main.py`
- Create `api/tests/test_session_routes.py`

**Steps:**

- Include the new router in `api/main.py`.
- Implement the eight canonical endpoints listed above.
- Route behavior must match current Next API semantics:
  - create session logs `step1_submitted`;
  - discovery is idempotent if payload already exists;
  - selection deduplicates ids;
  - preferences validates payload;
  - itinerary writes stay, transport, itinerary, validator issues;
  - stay override reruns planner-only;
  - adjustments append conversation before reruns;
  - Type C without action returns confirmation and does not rerun agents.
- Add route tests with FastAPI test client using a temp data dir and fixture mode.
- Run `cd api && uv run pytest tests/test_session_routes.py -v`.
- Commit: `feat(api): expose session planning routes`.

### Task 6: Move Canonical Frontend API Calls to FastAPI

**Files:**

- Modify `web/src/lib/apiClient.ts`
- Add/modify `web/src/lib/apiClient.test.ts`
- Modify `web/.env.example`

**Steps:**

- Require `NEXT_PUBLIC_API_URL` for canonical session functions: `createSession`, `getSession`, `runDiscovery`, `updateSelectedCards`, `savePreferences`, `runItinerary`, `updateStayOverride`, `submitAdjustment`.
- Keep `discoverDestination` and `generatePlan` as legacy helpers for old flow.
- Change canonical endpoint paths to the FastAPI REST paths:
  - `/api/sessions/{sessionId}/discovery`, `/selection`, `/preferences`, `/itinerary`, `/stay-override`, `/adjustments`.
- Add `.env.example` value comment or placeholder for `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`.
- Add Vitest tests that mock fetch and assert canonical functions call FastAPI URLs.
- Run `cd web && npm run test -- src/lib/apiClient.test.ts`.
- Commit: `feat(web): route canonical session flow through FastAPI`.

### Task 7: Update E2E Dev Orchestration

**Files:**

- Modify `web/playwright.config.ts`
- Modify `web/e2e/mvp-flow.spec.ts` only if route expectations changed

**Steps:**

- Configure Playwright to start both services:
  - FastAPI: `cd ../api && E2E_FIXTURE_MODE=1 uv run uvicorn main:app --host 127.0.0.1 --port 8000`
  - Next: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev`
- Keep browser base URL as `http://127.0.0.1:3000`.
- Verify the existing canonical E2E still completes the full flow.
- Run `cd web && npm run test:e2e`.
- Commit: `test: run MVP E2E against FastAPI backend`.

### Task 8: Mark Legacy Surface Explicitly

**Files:**

- Modify `web/README.md`
- Modify `web/docs/mvp-launch-checklist.md`
- Optionally modify root `README.md`

**Steps:**

- Document canonical flow as FastAPI-backed.
- Mark `/discover/[destination]`, `/plan/[id]`, `/api/discover`, and `/api/plan/generate` as legacy compatibility surfaces.
- State that LangGraph, live supplier inventory, and provider-backed routing are deferred.
- Do not delete old routes in this pass.
- Run no codegen or formatter; just run `cd web && npm run lint`.
- Commit: `docs: mark FastAPI session flow as canonical`.

### Task 9: Full Verification and Guardrails

**Files:**

- No planned source changes unless tests reveal a bug

**Steps:**

- Run backend tests: `cd api && uv run pytest -v`.
- Run frontend tests: `cd web && npm run test`.
- Run typecheck: `cd web && npm run typecheck`.
- Run lint: `cd web && npm run lint`.
- Run build: `cd web && npm run build`.
- Run E2E: `cd web && npm run test:e2e`.
- Confirm `git status --short` contains only intentional tracked changes and generated ignored files are not staged.
- Commit any verification-only fixes separately with narrow messages.

## Test Plan

- Unit: Pydantic schemas reject renamed/mistyped fields and preserve current enum contracts.
- Unit: Python budget/selection/validator outputs match current TypeScript behavior.
- Unit: Python repository supports create, update, reset, archive/fork, and archived write protection.
- Unit: Python agents reproduce current deterministic fixture/session behavior.
- Route: FastAPI session endpoints return updated `PlanningSession` for every canonical step.
- Frontend: `apiClient` canonical methods require and use `NEXT_PUBLIC_API_URL`.
- E2E: full canonical flow works through FastAPI: intake, discovery, selection, preferences, itinerary, adjustment.
- Regression: legacy old-flow helpers remain available but are not used by the canonical E2E.

## Assumptions and Defaults

- Canonical product is single-city, discovery-first, session-based.
- FastAPI is the only future backend for canonical flow.
- Phase 1 preserves current behavior; it does not add LangGraph or real supplier booking.
- Cross-origin cookies are not required for Phase 1 because `session_id` is carried in route URLs and API paths.
- Existing Next API Routes are retained temporarily to reduce deletion risk.
- Python session models manually mirror TypeScript Zod models for now; schema generation is deferred.
- Fixture mode must run without live provider keys.
