# LangGraph Single-City Travel Planning MVP

> **STATUS: ACTIVE (2026-05-09)**
> 这是后续唯一 active 实施计划。旧的 `mvp-core`、`discovery-flow`、`python-backend-foundation`、`langgraph-multi-agent-planner`、`single-city-travel-planning-mvp` 都只作为历史或参考材料。

## Goal

交付单城市旅行规划 MVP:

1. Step 1 输入硬性条件。
2. Discovery 卡片选择旅行兴趣。
3. Preferences 补充住宿与交通偏好。
4. Python + LangGraph 串联 `discovery`、`stay`、`transport`、`planner`、`validator`。
5. 通过对话进行部分重规划,Type C 根约束变更必须先给确认卡。

## Architecture

### `web/` — Next.js UI 层

- 页面、组件、路由壳、Cookie/session id 引导。
- 不保留 server-side agent、LLM、provider、planner 编排逻辑。
- 前端通过 HTTP JSON 调用 `api/`,长任务进度通过 SSE。
- 临时保留 TS domain 类型供 UI 使用;最终由 Python Pydantic JSON Schema 生成 TypeScript 类型。

### `api/` — FastAPI + LangGraph 后端

- Pydantic v2 schemas 是跨服务数据契约的单一事实源。
- 文件型 session repository 默认写入 `api/.data/sessions.json`。
- LangGraph 图拥有 discovery / stay / transport / planner / adjustment-classifier 节点。
- provider 适配器包括 Tavily、map、weather、supplier fallback。
- google-genai Gemini 2.5 flash 通过统一 LLM client 调用。
- metrics 与 cost log 写入 `api/.data/` 下的 JSONL 文件。

### Communication

- HTTP JSON:
  - `POST /api/sessions`
  - `GET /api/sessions/{session_id}`
  - `POST /api/sessions/{session_id}/discovery`
  - `PATCH /api/sessions/{session_id}/selection`
  - `POST /api/sessions/{session_id}/preferences`
  - `POST /api/sessions/{session_id}/itinerary`
  - `PATCH /api/sessions/{session_id}/stay-override`
  - `POST /api/sessions/{session_id}/adjustments`
- SSE:
  - `GET /api/sessions/{session_id}/itinerary/stream`
  - event shape: `{ "stage": string, "status": "start" | "finish" | "error", "message"?: string }`

## Replacement Map

| TS source to retire | Python target | Status |
|---|---|---|
| `web/src/domain/schemas.ts` | `api/app/models/schemas.py` | Pending |
| `web/src/domain/budget.ts` | `api/app/domain/budget.py` | Pending |
| `web/src/domain/validator.ts` | `api/app/domain/validator.py` | Pending |
| `web/src/domain/geography.ts` | `api/app/domain/geography.py` | Pending |
| `web/src/domain/selection.ts` | `api/app/domain/selection.py` | Pending |
| `web/src/server/llm/client.ts` | `api/app/llm/client.py` | Pending |
| `web/src/server/llm/retry.ts` | `api/app/llm/retry.py` | Pending |
| `web/src/server/llm/jsonRepair.ts` | `api/app/llm/json_repair.py` | Pending |
| `web/src/server/llm/costLogger.ts` | `api/app/llm/cost_logger.py` | Pending |
| `web/src/server/providers/registry.ts` | `api/app/providers/registry.py` | Pending |
| `web/src/server/providers/map/amap.ts` | `api/app/providers/map_amap.py` | Pending |
| `web/src/server/providers/map/mapbox.ts` | `api/app/providers/map_mapbox.py` | Pending |
| `web/src/server/providers/map/coordinateConversion.ts` | `api/app/providers/coord.py` | Pending |
| `web/src/server/providers/search/` | `api/app/providers/search.py` | Pending |
| `web/src/server/providers/supplier/` | `api/app/providers/supplier.py` | Pending |
| `web/src/server/providers/weather/` | `api/app/providers/weather.py` | Pending |
| `web/src/server/persistence/sessionRepository.ts` | `api/app/persistence/session_repository.py` | Pending |
| `web/src/server/persistence/fileSessionRepository.ts` | `api/app/persistence/file_session_repository.py` | Pending |
| `web/src/server/persistence/cookies.ts` | `web/src/lib/cookies.ts` | Pending |
| `web/src/server/agents/discovery.ts` | `api/app/graph/nodes/discovery.py` | Pending |
| `web/src/server/agents/stay.ts` | `api/app/graph/nodes/stay.py` | Pending |
| `web/src/server/agents/transport.ts` | `api/app/graph/nodes/transport.py` | Pending |
| `web/src/server/agents/planner.ts` | `api/app/graph/nodes/planner.py` | Pending |
| `web/src/server/agents/orchestrator.ts` | `api/app/graph/workflow.py` | Pending |
| `web/src/server/agents/adjustmentClassifier.ts` | `api/app/graph/nodes/adjustment_classifier.py` | Pending |
| `web/src/server/metrics/events.ts` | `api/app/metrics/events.py` | Pending |

## Implementation Tasks

### Task 0: Repository and Documentation Baseline

- Ensure `feature/mvp-web-app` lives in the `travel-planner` repository.
- Remove the home-level ghost git repository by moving it to backup.
- Rescue all plans from nested `Projects/travel-planner/` paths.
- Mark superseded and completed plans explicitly.
- Keep this document as the only active plan.

### Task 1: Python Schemas and Domain Utilities

- Port Zod schemas to Pydantic v2 with JSON-compatible field aliases.
- Port budget, validator, geography, and selection pure functions.
- Add pytest coverage equivalent to the existing Vitest tests.
- Export JSON Schema for later TypeScript generation.

### Task 2: Python Persistence and Session Routes

- Move session persistence from `web/.data/sessions.json` to `api/.data/sessions.json`.
- Implement file-backed repository with atomic writes.
- Add FastAPI canonical session endpoints.
- Keep archived session mutation rules explicit and tested.

### Task 3: LLM, Providers, Cost Log

- Port retry, JSON repair, LLM client, and cost logging to Python.
- Use `google-genai` with Gemini 2.5 flash.
- Write cost records to `api/.data/llm-cost.jsonl`.
- Add provider registry and deterministic fixture/fallback behavior.

### Task 4: LangGraph Workflow

- Define `PlanState` with `session_id`, `hard_constraints`, `discovery`, `preferences`, `stay`, `transport`, `itinerary`, `validator_issues`, and `progress_events`.
- Implement nodes:
  - discovery
  - stay
  - transport
  - planner
  - validator
  - adjustment classifier
- Express the corrective planner pass as conditional LangGraph edges.
- Implement Type A/B/C adjustment handling with a small subgraph or typed router.

### Task 5: SSE Progress

- Stream LangGraph node start/finish/error events as SSE.
- Add frontend progress consumption for itinerary generation and partial replanning.
- Keep final itinerary response JSON-compatible with non-stream clients.

### Task 6: Next.js Slimdown

- Rename migrated TS server files to `*.legacy.ts` with `LEGACY` comments while Python parity is being verified.
- Delete legacy TS server folders only after Python tests and web build pass.
- Remove old `/plan/[id]`, `/discover`, and Next.js server API routes once canonical pages call Python.
- Keep only UI components, route shells, and a thin cookie/session helper in `web/`.

### Task 7: Product Flow Completion

- Finish progress UI, Type C confirmation card, stay override, adjustment routing, and residual validator issue rendering.
- Ensure `/ -> /discovery/[sessionId] -> /preferences/[sessionId] -> /trips/[sessionId]` is the only canonical flow.

### Task 8: Documentation and Cleanup

- Write spec v2 at `docs/superpowers/specs/2026-05-09-travel-planner-design-v2.md`.
- Move launch checklist to `docs/mvp-launch-checklist.md`.
- Archive early MCP prototype files under `docs/archive/early-mcp-prototype/`.
- Move `travel-template.html` to `web/src/templates/travel-template.html`.

### Task 9: Regression Baseline

- Backend:
  - `cd api && uv run pytest -v`
  - `cd api && uv run ruff check .`
  - `cd api && uv run mypy app`
- Frontend:
  - `cd web && npm run typecheck`
  - `cd web && npm run lint`
  - `cd web && npm run test`
  - `cd web && npm run build`
  - `cd web && npm run test:e2e`

## Notes

- During migration, TS server code is reference implementation, not target architecture.
- A file is deleted from `web/src/server/` only after its Python target has tests.
- Fixture mode is mandatory for unit and E2E tests so CI does not depend on live LLM/provider keys.
- `api/.data/sessions.json` is MVP persistence; SQLite/Postgres should be decided in a later persistence hardening plan.
