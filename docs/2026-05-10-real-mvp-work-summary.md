# 2026-05-10 Real MVP Work Summary

## TL;DR

今天的主线是把项目从“fixture-backed MVP”推进到“真实 provider 可用 MVP”。

结论：

- 本地真实 Gemini 调用跑通。
- 本地真实 Tavily adapter smoke 跑通。
- 真实 API smoke 跑通：sessions -> discovery -> selection -> preferences -> itinerary -> adjustments。
- 真实浏览器流程跑通：首页 -> discovery -> preferences -> trips -> adjustment。
- 离线发布门禁跑通：`make regression` 全绿。
- 当前主流程会先用 Tavily 搜索 grounding，再把搜索摘要交给 Gemini discovery agent 生成结构化结果。
- Plan15 已把 AMap/Mapbox provider registry 接入 discovery card place enrichment；本机地图 key 为空时会自动跳过并保留 LLM place。
- Plan16 已新增最近行程恢复入口：首页会列出最近 active sessions，并可继续回 discovery/preferences/trips。
- Plan17 已完成 Mapbox 真实 smoke 和 place quality gate：Mapbox 路线可用，但中国 POI 搜索会返回城市级结果，系统现在会拒绝这种低质量匹配，避免假坐标污染 discovery cards。

当前分支：`feature/mvp-web-app`

当前状态：真实 provider 稳定性修复已提交；Plan14/Plan15 已把 Tavily grounding 和地图 place enrichment 接入 discovery 主流程；Plan16 已补上最近行程恢复入口；Plan17 已补上地图结果质量门槛，并通过完整 regression。

## 今天你完成了什么

### 1. 完成了真实 provider 配置

你在本地配置了：

- `api/.env`
- `web/.env.local`

关键状态：

- `GEMINI_API_KEY` 已设置。
- `TAVILY_API_KEY` 已设置。
- `MAPBOX_ACCESS_TOKEN` 已设置。
- `E2E_FIXTURE_MODE=0` 用于真实模式。
- `.env` 文件被 git ignore，不会被提交。

注意：今天密钥曾经被贴进聊天里。安全上应视为已泄露，后续建议轮换。

### 2. 跑了真实 Gemini smoke

命令形态：

```bash
cd api
set -a
source .env
set +a
uv run python scripts/smoke_llm.py
```

结果：

```text
[smoke] OK city=Shanghai country=CN
```

说明 Gemini key、模型、SDK、结构化响应最小链路可用。

### 3. 跑了真实 Tavily adapter smoke

单独调用 Tavily provider adapter，结果：

```text
tavily_ok count=8
first_url_set=True
```

说明 Tavily key 和 adapter 可用。Plan14 进一步把 Tavily 搜索结果接进 discovery prompt，并把 Tavily 来源合并进 `source_notes`。

### 3.5 接入地图地点 enrichment

Plan15 已把 `TravelDataProviderRegistry.search_places()` 接进 discovery agent：

- 有 `AMAP_API_KEY` 或 `MAPBOX_ACCESS_TOKEN` 时，会为每张 discovery card 用目的地 + card name 做一次受限 place search。
- 搜到真实 `NormalizedPlace` 时，会替换 LLM 生成或缺失的 `card.place`。
- 地图 provider 缺 key、失败或无结果时，不阻断 discovery，会保留 LLM place 并继续。
- 本机当前 `MAPBOX_ACCESS_TOKEN` 已配置；真实 route smoke 已通过，固定上海坐标可返回非零步行/驾车路线。
- Mapbox 对中国 POI 的搜索会把东方明珠、外滩等查询退回到城市级 `Shanghai`。Plan17 已增加 discovery 侧的质量门槛：最多取 3 个候选，只接受有坐标且名称/地址能匹配 card name 的候选，否则保留原 card place。

### 4. 修掉真实模式暴露的问题

真实验收不是只跑脚本，今天真的抓到了几个产品级问题：

- `api/.env` 里的共享变量会导致 API 启动失败。
- LLM 返回 JSON 的顶层结构不稳定，导致 discovery 502。
- Gemini SDK 原生 `response_schema` 不接受部分 Pydantic JSON Schema 字段。
- React dev/StrictMode 下 discovery 页面会重复触发真实 LLM 请求，一个成功、一个失败时前端会显示 502。
- `smoke_curl.sh` 之前硬编码 fixture card id，真实 discovery 生成动态 card id 时不适用。
- 本地真实 `.env` 会污染 pytest，让 fixture 测试偷偷走真实 LLM。

对应修复：

- `api/app/config.py`：加载 `api/.env` 到进程环境，并忽略非 Settings 管辖的共享 env 键。
- `api/app/llm/client.py`：给 Gemini 传 schema，注入 JSON Schema prompt，净化 provider schema，对 JSON/schema 校验失败重试。
- `api/app/routes/discovery.py`：并发 discovery late loser 失败时，重读 session 并返回已成功写入的 discovery。
- `web/src/app/discovery/[sessionId]/page.tsx`：同一个 session 的 discovery load promise 去重，避免 StrictMode 重复调用。
- `api/scripts/smoke_curl.sh`：从真实 discovery 响应中抽取 card id，而不是硬编码 fixture id。
- `api/tests/conftest.py`：pytest 默认隔离真实 provider 环境变量。
- `api/app/graph/nodes/discovery.py`：拒绝明显错配或城市级的地图 enrichment 结果，避免错误坐标进入 discovery cards。

### 5. 跑通完整真实流程

真实 API smoke 跑通：

```text
Smoke flow passed for session_...
```

真实浏览器流程跑通：

- 首页提交 hard constraints。
- Discovery 页面生成真实上海卡片。
- 选择 3 个 card。
- Preferences 页面提交偏好。
- Trips 页面生成 3 天行程。
- Adjustment 输入请求并提交。
- 页面返回 `Itinerary updated.`

### 6. 跑通完整离线 regression

最终验证：

```bash
make regression
```

结果摘要：

- launch readiness passed
- type generation/typecheck passed
- web lint passed
- web unit tests: `12 passed`
- web build passed
- API pytest: `351 passed, 1 warning`
- API ruff passed
- fixture smoke passed
- Playwright e2e: `5 passed`

### 7. 补上最近行程恢复

Plan16 新增了本地持久化的恢复入口：

- `GET /api/sessions` 返回最近 active sessions，支持 `limit` 和 `include_archived`。
- 首页会拉取最近行程并展示目的地、日期、预算和当前状态。
- Resume 会根据 session 状态跳到 discovery、preferences 或 trips。
- Recent trips focused e2e 和完整 regression 均已通过。

## Agent 跑通了吗

### 已跑通

- Discovery LLM agent：跑通真实 Gemini，并通过 schema 约束和重试提升稳定性。
- Full planning workflow：跑通 sessions -> discovery -> preferences -> itinerary。
- Adjustment workflow：跑通真实浏览器里的 adjustment 提交，页面显示已更新。
- Fixture agents/workflow：完整 regression 和 e2e 仍然通过。

### 进一步跑通

- Tavily search provider：adapter 已真实跑通，key 可用；Plan14 已把 Tavily grounding 接入 discovery 主流程。
- Map place enrichment：Plan15 已接入 discovery 主流程；有 AMap/Mapbox key 时会用 provider registry 为 discovery cards 解析真实 `NormalizedPlace`，失败时保留 LLM place 并继续。Plan17 已加入质量门槛，避免 Mapbox 中国 POI 覆盖不足时把景点误补成城市中心点。
- Recent trips / resume：Plan16 已新增 `GET /api/sessions` 和首页最近行程入口，用户可以回到首页继续最近的本地行程。

### 还没有产品化

- AMap / Mapbox：Mapbox key 已配置且路线 smoke 通过；中国 POI 精度仍建议后续配置 AMap key 做主 provider。当前完成的是主流程接线、graceful fallback 和低质量结果拒绝。
- 图片：`example.com` 占位图片已在 discovery normalization 中过滤；后续还需要真实图片/provider 或更完整的图片策略。
- 生产环境：还没有部署、监控、限流、成本保护、用户数据隔离。

## 当前已有功能

### Web 功能

- 首页 hard constraints 表单。
- 中英文切换。
- Discovery 卡片展示和选择。
- Food context 和 area impressions。
- Discovery budget 展示。
- Preferences 表单。
- Trips 页面展示 stay area、budget、daily itinerary。
- Adjustment 输入和提交。
- Progress panel。
- 最近行程恢复入口。

### API 功能

- `POST /api/sessions`
- `GET /api/sessions`
- `GET /api/sessions/{session_id}`
- `POST /api/sessions/{session_id}/discovery`
- `PATCH /api/sessions/{session_id}/selection`
- `POST /api/sessions/{session_id}/preferences`
- `POST /api/sessions/{session_id}/itinerary`
- `GET /api/sessions/{session_id}/itinerary/stream`
- `POST /api/sessions/{session_id}/adjustments`
- `GET /health`

### Agent / Graph 功能

- Discovery agent。
- Discovery Tavily grounding。
- Discovery map place enrichment。
- Stay recommendation node。
- Transport recommendation node。
- Planner node。
- Validator node。
- Adjustment classifier。
- Type A itinerary adjustment。
- Type B stay/transport adjustment。
- Type C major-change confirmation/reset/fork path。

### 工程功能

- Pydantic domain schemas。
- TypeScript generated types。
- File-based session persistence。
- Metrics JSONL logging。
- LLM cost logging。
- Fixture mode。
- Real provider mode。
- API smoke script。
- Fixture smoke runner。
- Full regression Make target。
- Playwright e2e。

## 下一步建议

### 明天第一件事

1. 轮换今天暴露过的 Gemini/Tavily key。
2. 更新本地 `api/.env`。
3. 重新跑：

```bash
cd api
set -a
source .env
set +a
uv run python scripts/smoke_llm.py
```

然后跑真实 API smoke。

### 当前真实模式修复

以下范围已经提交：

- config/env loading
- LLM structured schema hardening
- discovery concurrency idempotency
- real smoke script dynamic card selection
- web discovery StrictMode dedupe
- tests for all of the above

commit message：

```text
fix: harden real provider MVP flow
```

### 下一阶段 Plan 建议

Plan14 已完成：

```text
Plan14: Tavily-Backed Discovery Grounding
```

目标：

- Discovery 前先调用 Tavily 搜索目的地亮点、交通、食物、区域信息。
- 把 Tavily result 摘要喂给 Gemini discovery agent。
- `source_notes` 里保留真实 Tavily 来源。
- 避免模型凭空生成 `example.com` 图片 URL。
- 为 Tavily 失败设计 graceful fallback。
- 加 fixture 和真实 smoke 验收。

Plan15 也已完成主流程接线：

```text
Plan15: Map Place Enrichment
```

已完成：

- Discovery card 通过 provider registry 解析真实 `NormalizedPlace`。
- 缺地图 key 或 provider 失败时 graceful fallback。
- 最新完整 regression 全绿。

Plan16 已补上：

```text
Plan16: Session Resume
```

已完成：

- `GET /api/sessions` 最近 active sessions。
- 首页 Recent trips。
- Recent trips Playwright e2e，并纳入完整 regression。

Plan17 已补上：

```text
Plan17: Mapbox Place Quality
```

已完成：

- 验证 `MAPBOX_ACCESS_TOKEN` 已被后端环境读取。
- 真实 Mapbox route smoke 通过：上海固定坐标之间可返回非零距离和时间。
- 确认 Mapbox 中国 POI 搜索会返回城市级结果，这是数据覆盖问题，不是 token 问题。
- Discovery enrichment 改为最多取 3 个候选，并拒绝无坐标、城市级或名称不匹配的候选。
- 新增回归测试覆盖“拒绝泛化城市结果”和“跳过第一个坏候选、选后续匹配候选”。
- 最新完整 regression 全绿：API `351 passed`、web unit `12 passed`、Playwright `5 passed`。

之后建议继续做：

- Plan18: route-duration enrichment，把可用坐标之间的 Mapbox 路线时间接入 planner/validator。
- Plan19: production readiness，包括部署、限流、日志、成本控制、错误监控。
- Plan20: product polish，包括真实图片、加载体验、中文 UI 完整化。

## 当前风险

- 密钥已在聊天里暴露过，必须轮换。
- Tavily 已进入主 discovery graph，但搜索摘要到 itinerary 质量仍需要真实多城市样本持续观察。
- 地图 enrichment 已接入，Mapbox route 已真实验收；中国 POI 搜索精度不足，后续建议配置 AMap key 或接入更强 POI provider。
- 真实 Gemini 输出仍需要长期观察，虽然今天已经加了 schema、净化和重试。
- 当前 session persistence 是本地文件，不适合多人生产使用。
- 最近行程恢复是匿名本地恢复，不是账号级跨设备同步。
- 没有认证、限流、额度保护。
- 没有线上监控和错误告警。

## 结束时状态

- 没有 dev server 残留。
- 本地 `.env` 不会被提交。
- 真实 provider 稳定性修复已提交。
- 完整 regression 已通过，包括 Plan17 后的最新一轮：API `351 passed`、web unit `12 passed`、Playwright `5 passed`。
- 真实 Gemini/Tavily 验收已通过；Plan15 后的真实 API smoke 也已通过。Mapbox key 已配置，路线真实 smoke 通过；中国 POI 搜索覆盖不足已通过质量门槛做防护。
- 项目现在可以被称为“真实可用 MVP”，但还不是“可长期给真实用户使用的生产产品”。
