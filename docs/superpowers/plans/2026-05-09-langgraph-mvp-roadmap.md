# LangGraph MVP — Execution Roadmap (Phase 3 → 4 → 6)

> **STATUS: COMPLETED (2026-05-10)**
>
> Plan 1-9 are complete. Post-roadmap hardening continues in Plan 10 (launch readiness), Plan 11 (fixture API smoke gate), and Plan 12 (roadmap closure).

## Goal

把 `web/src/server/`(~2630 行 TS)+ `web/src/domain/`(~1307 行 TS)的全部业务逻辑,作为参考实现移植到 Python + LangGraph 后端;然后一次性删除 Next.js 端的 server 代码,把前端切到 Python 后端。

## Architecture

- **Big-bang 切换**:Plan 1-6 全部完成、Python 端能 curl 通完整流程之后,Plan 7 才动 Next.js 端。期间前端始终使用现有 TS 路由,不做双轨。
- **TDD 纪律**:每份子计划都先写 pytest,再写实现。Pydantic 与 Zod 字段名严格一致(snake_case),JSON 兼容。
- **不使用 worktree**:所有工作在 `feature/mvp-web-app` 分支主仓库直接进行。

## Tech Stack

- 后端:FastAPI + Pydantic v2 + LangGraph + google-genai (Gemini 2.5 flash) + Tavily + httpx
- 前端:Next.js(只做 UI 和路由壳)
- 持久化:JSON 文件(`api/.data/sessions.json`),MVP 后再考虑 SQLite
- 流式:SSE(`StreamingResponse`)
- 测试:pytest + pytest-asyncio + pytest-httpx;前端 e2e 用 Playwright(Plan 9)

---

## 子计划清单与依赖

```
Plan 1: Domain Layer ─────────┐
                              ├─→ Plan 5: LangGraph Workflow ─┐
Plan 2: LLM Wrapper ──────────┤                                ├─→ Plan 6: FastAPI Routes + SSE ─┐
                              │                                │                                 │
Plan 3: Provider Adapters ────┤                                │                                 │
                              │                                │                                 │
Plan 4: Persistence ──────────┘                                │                                 │
                                                                │                                 │
                                                                └─────────── CHECKPOINT ──────────┤
                                                                       (curl 全流程通过)         │
                                                                                                 ↓
                                                                                    Plan 7: Web Slimming + Cutover
                                                                                                 │
                                                                                                 ↓
                                                                                    Plan 8: Pydantic→TS 类型自动生成
                                                                                                 │
                                                                                                 ↓
                                                                                    Plan 9: E2E 回归基线 + Fixture 模式
```

Plan 1-4 互相独立,理论可并行,但单人开发推荐顺序做。Plan 5 依赖 1+2+3+4 全部就绪。Plan 6 依赖 5。Plan 7 依赖 6 通过 curl 验证。

---

## Plan 1 — Domain Layer(纯逻辑层)

**文件**:`docs/superpowers/plans/2026-05-09-langgraph-mvp-1-domain.md`

**新建**:
- `api/app/models/schemas.py` — Pydantic v2 等价于 `web/src/domain/schemas.ts`(全部 entity)
- `api/app/domain/budget.py` — 等价于 `web/src/domain/budget.ts`
- `api/app/domain/validator.py` — 等价于 `web/src/domain/validator.ts`
- `api/app/domain/geography.py` + `selection.py` — 等价于同名 ts
- `api/tests/domain/` — 五个 pytest 文件,场景一一对齐 TS 测试

**删除**:`api/app/models/{plan,preferences,attraction}.py`(早期 scaffold,被 schemas.py 取代)+ 相关旧测试。

**DoD**:`cd api && uv run pytest tests/domain -v` 全绿,覆盖原 TS 测试覆盖的全部 case;`uv run ruff check app/` 通过。

---

## Plan 2 — LLM Wrapper

**文件**:`docs/superpowers/plans/2026-05-09-langgraph-mvp-2-llm.md`

**新建**:
- `api/app/llm/client.py` — google-genai 异步 wrapper,签名:`async def generate_structured[T](prompt: str, schema: type[T], *, label: str, ...) -> T`
- `api/app/llm/retry.py` — 等价于 TS retry.ts(指数退避 + jitter,最多 3 次)
- `api/app/llm/json_repair.py` — 等价于 TS jsonRepair.ts(去 markdown 围栏、修剪 trailing commas 等)
- `api/app/llm/cost_logger.py` — 等价于 TS costLogger.ts,落 `api/.data/llm-cost.jsonl`
- `api/tests/llm/` — 用 pytest fixture 模拟 LLM 响应,验证 retry / json_repair / cost log 行为

**删除**:`api/app/services/gemini.py`(被 llm/client.py 取代);`api/app/services/__init__.py` 调整。

**DoD**:`cd api && uv run pytest tests/llm -v` 全绿;set 一个真实 GEMINI_API_KEY 跑一次烟测脚本(`scripts/smoke_llm.py`),返回结构化对象。

---

## Plan 3 — Provider Adapters

**文件**:`docs/superpowers/plans/2026-05-09-langgraph-mvp-3-providers.md`

**新建**:
- `api/app/providers/types.py` — Protocol/ABC 等价于 `web/src/server/providers/types.ts`
- `api/app/providers/registry.py` — 等价于 registry.ts,环境变量 → provider 实例
- `api/app/providers/search/tavily.py` — 沿用现有 `services/tavily.py` 但适配新签名
- `api/app/providers/map/{amap,mapbox,coord}.py` — 等价于 TS 同名
- `api/app/providers/supplier.py` + `weather.py` — 同上,weather 是新增
- `api/tests/providers/` — 用 pytest-httpx 录制响应,所有 provider 都有契约测试

**删除**:`api/app/services/tavily.py`(并入 providers/search/tavily.py)。

**DoD**:`cd api && uv run pytest tests/providers -v` 全绿;registry 在缺 env 时给出明确错误。

---

## Plan 4 — Persistence(Session Repository)

**文件**:`docs/superpowers/plans/2026-05-09-langgraph-mvp-4-persistence.md`

**新建**:
- `api/app/persistence/session_repository.py` — Protocol(create / get / update / list / archive)
- `api/app/persistence/file_session_repository.py` — JSON 文件实现,等价于 TS fileSessionRepository.ts
- `api/.data/sessions.json` 路径,默认值 + `SESSION_DATA_DIR` env override
- `api/tests/persistence/` — 包含并发写入 / 读改写 / archive 三大场景

**搬运**:把开发态 `web/.data/sessions.json`(如有)迁到 `api/.data/sessions.json`,作为 fixture 保留一份在 `api/tests/fixtures/`。

**DoD**:`cd api && uv run pytest tests/persistence -v` 全绿;并发写测试稳定通过 50 次循环。

---

## Plan 5 — LangGraph Workflow

**文件**:`docs/superpowers/plans/2026-05-09-langgraph-mvp-5-graph.md`

**新建**:
- `api/app/graph/state.py` — `PlanState`(Pydantic 模型,字段在 spec v2 列出)
- `api/app/graph/nodes/discovery.py` / `stay.py` / `transport.py` / `planner.py` / `validator.py` / `adjustment_classifier.py`
- `api/app/graph/workflow.py` — 主图 + 纠正回路条件边
- `api/app/graph/adjustments/{type_a,type_b,type_c}.py` — 三个独立小图
- `api/app/metrics/events.py` — 等价于 events.ts
- `api/tests/graph/` — 黑盒 fixture 测试,把 TS orchestrator.test.ts 全部 case 转写过来

**新增依赖**:`langgraph>=0.2.0` 加入 pyproject.toml。

**DoD**:`cd api && uv run pytest tests/graph -v` 全绿,覆盖:happy path / validator 触发纠正回路 / 纠正后仍 fail 走 end / Type A/B/C 分类高低置信度分支。

---

## Plan 6 — FastAPI Routes + SSE

**文件**:`docs/superpowers/plans/2026-05-09-langgraph-mvp-6-routes.md`

**新建**:
- `api/app/routes/sessions.py` — `POST /api/sessions`, `GET /api/sessions/{id}`
- `api/app/routes/discovery.py` — `POST /api/discovery/{session_id}` 触发 discovery 节点;`POST /api/discovery/{session_id}/select` 提交选 cards
- `api/app/routes/preferences.py` — `PUT /api/preferences/{session_id}`
- `api/app/routes/itinerary.py` — `POST /api/itinerary/{session_id}` 触发流水线;`GET /api/itinerary/{session_id}/stream` 走 SSE 推 progress
- `api/app/routes/adjustments.py` — `POST /api/adjustments/{session_id}` 走 adjustment_classifier 子图
- `api/tests/routes/` — TestClient + httpx-asgi,覆盖 happy / 4xx / SSE 帧格式
- `api/scripts/smoke_curl.sh` — 走 sessions → discovery → preferences → itinerary → adjustments 完整 curl 流程

**删除**:`api/app/routes/{discover,plan}.py`(老 scaffold);`main.py` 路由注册同步更新。

**DoD**:
- `cd api && uv run pytest tests/routes -v` 全绿
- `cd api && bash scripts/smoke_curl.sh` 一遍跑通
- **CHECKPOINT**:本 Plan 完成后开始 Plan 7

---

## Plan 7 — Web Slimming + Cutover(Big-Bang)

**文件**:`docs/superpowers/plans/2026-05-09-langgraph-mvp-7-web-cutover.md`

**删除目录**:
- `web/src/server/` 整个删
- `web/src/domain/` 整个删(被 Pydantic 取代,过渡期前端先用 `any`/手写 minimal type,Plan 8 自动生成补回)
- `web/src/app/{plan,discover,discovery}/` 整个删(旧版三套 UI,被新版 `discovery/[sessionId]`、`preferences/[sessionId]`、`trips/[sessionId]` 替代)
- `web/src/app/api/{adjustments,discover,discovery,itinerary,plan,preferences,sessions}/` — 全删,不保留 BFF;前端直接 fetch Python
- `web/src/components/{plan,discover,chat,search,intake,itinerary}/` — 旧版组件全删
- `web/src/lib/{claude,planStore,googleSearch}.ts` 全删
- `web/src/hooks/usePlan.ts` 全删
- `web/src/__tests__/lib/{claude,googleSearch}.test.ts` 全删

**改写**:
- `web/src/lib/apiClient.ts` — 强制 `NEXT_PUBLIC_API_URL` 必填,默认 `http://localhost:8000`,删 `discoverDestination` / `generatePlan`,新增匹配 Plan 6 的方法
- `web/next.config.ts` — `rewrites` 把 `/api/*` 代理到 Python
- `web/package.json` — `dev` 脚本改用 `concurrently` 同时拉 web + api
- `web/src/lib/types.ts` — 留一份过渡 minimal types,Plan 8 替换为生成

**保留**:
- `web/src/components/{ui,preferences,discovery}/` — 实际新版组件
- `web/src/app/{layout,page}.tsx`、`web/src/app/{preferences,trips}/` — 新版页面

**DoD**:
- `cd web && npm run typecheck && npm run lint && npm run build` 全绿
- 浏览器手动走完 `/ → /discovery/[id] → /preferences/[id] → /trips/[id]`,后端是 Python(同时启动 `cd api && uv run uvicorn main:app --reload`)
- `web/src/server/` 不存在

---

## Plan 8 — Pydantic → TypeScript 类型自动生成

**文件**:`docs/superpowers/plans/2026-05-09-langgraph-mvp-8-types.md`

**新建**:
- `api/scripts/export_schema.py` — 跑 `model.model_json_schema()` 把 schemas.py 全部模型导出到 `api/dist/schema.json`
- `web/scripts/generate-types.mjs` — 调 `json-schema-to-typescript` 把 schema.json 编译到 `web/src/lib/generated/types.ts`
- `web/package.json` — 新增 `npm run gen:types` 脚本
- `Makefile` 或 `package.json` 顶层 — `npm run gen:types && npm run typecheck` 作为 pre-commit gate

**删除**:`web/src/lib/types.ts` 中所有可被自动生成替代的部分。

**DoD**:删完 web 端手写 schema 后 `npm run typecheck` 仍全绿;改 Pydantic 跑 `npm run gen:types` 自动反映到前端。

---

## Plan 9 — E2E 回归基线 + Fixture 模式

**文件**:`docs/superpowers/plans/2026-05-09-langgraph-mvp-9-e2e.md`

**新建**:
- `web/playwright.config.ts` + `web/e2e/` — 三条 critical path:happy / 预算超支 / Type B adjustment
- `api/app/llm/fixtures.py` + `api/app/providers/fixtures.py` — 录制响应模式,`E2E_FIXTURE_MODE=1` 时不走真 API
- `api/tests/integration/test_full_workflow.py` — pytest 端跑完整 graph(用 fixture)
- `web/e2e/fixtures/` — Playwright 用的 mocked Python 后端响应

**新增脚本**:
- `web/package.json`:`test:e2e` = `playwright test`
- `Makefile`:跑全套(typecheck + lint + unit + pytest + ruff + API smoke + e2e)

**DoD**:`make regression` 在本地 CI gate 跑完无错;Playwright critical paths 全绿;README 说明了 fixture 模式、API smoke 和离线回归。

---

## 风险与应对

| 风险 | 触发条件 | 应对 |
|---|---|---|
| Pydantic v2 strict mode 与 Zod `.strict()` 行为差异 | Plan 1 schema 拒收/接收的字段不一致 | 每个 schema 写 `extra="forbid"` + `populate_by_name=True`,跑跨 ts/py 的同 fixture 比对测试 |
| google-genai 流式 API 与 LangGraph astream 节奏不一致 | Plan 5 SSE 推帧时 LLM 还没结束 | 节点级别先用 sync 接口跑通,SSE 在节点之间推,不试图把 LLM token 流也透传 |
| Plan 7 删完 TS 后 Next.js build 漏检引用 | 隐式 import / 动态 import | Plan 7 第一步先 `tsc --noEmit` + `eslint --no-eslintrc` 找出所有引用,边删边修 |
| `api/.data/sessions.json` 在并发请求下竞态 | Plan 4 file repo 没加锁 | Plan 4 必须用 `aiofiles` + `asyncio.Lock`(单进程)或 `fcntl.flock`(跨进程);测试要并发写 50 次 |
| LangGraph 升级破坏图定义 | langgraph 还在快速迭代 | pyproject.toml 钉死小版本号(如 `>=0.2.0,<0.3.0`),升级单独走 PR |
| Plan 7 期间 Pydantic→TS 还没自动生成,前端 `any` 一片 | Plan 8 还在 Plan 7 之后 | Plan 7 临时手写 minimal `web/src/lib/types.ts`,Plan 8 立刻补回,中间不留长尾 |

## Definition of Done(整套路线图)

- [x] Plan 1-9 全部 DoD 通过(Plan 10/11 后 `make regression` 验收通过)
- [x] `web/src/server/` 不存在
- [x] `api/app/graph/` 存在,LangGraph 工作流可在 pytest 中端到端跑通
- [x] `cd web && npm run build` 与 `cd api && uv run pytest` 双绿
- [x] 浏览器关键路径通过 Playwright fixture 模式跑完整流程
- [x] `make regression` 跑通(包含 launch-check、类型漂移、API smoke、pytest、ruff、Playwright fixture e2e)
- [x] 顶层 README 更新"如何启动 / 如何跑回归"段落

## 节奏估算(单人,每天 4-6 工时)

| Plan | 估算工作量 | 累计 |
|---|---|---|
| Plan 1 | 1.5 天 | 1.5 |
| Plan 2 | 1 天 | 2.5 |
| Plan 3 | 2 天 | 4.5 |
| Plan 4 | 0.5 天 | 5 |
| Plan 5 | 3 天(最重) | 8 |
| Plan 6 | 1.5 天 | 9.5 |
| **CHECKPOINT** | 0.5 天验证 | 10 |
| Plan 7 | 1 天 | 11 |
| Plan 8 | 0.5 天 | 11.5 |
| Plan 9 | 1.5 天 | 13 |

**总计:~13 工作日(2.5 周)**。Plan 5 是技术风险最高的,如果 LangGraph 学习曲线超预期,整体可能拉到 3 周。
