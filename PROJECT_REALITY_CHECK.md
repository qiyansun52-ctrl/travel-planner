# 项目现状摸底报告 — travel-planner

**审查时间**: 2026-05-09
**审查范围**: `/Users/gabriel/Projects/travel-planner` 及其下挂的所有 worktree
**性质**: 只读审查,未修改任何代码或文档(仅写入此报告)

---

## 关键提醒(请先看这一段)

这个目录下其实并存着 **两个互不相干的 git 仓库**,而你大部分实际代码工作都"散落"在不属于本仓库的那一边:

| 位置 | git 仓库 | 远程 origin | 当前内容 |
|---|---|---|---|
| `/Users/gabriel/Projects/travel-planner` (本仓库) | `.git/` 在本目录 | `qiyansun52-ctrl/travel-planner.git` | 早期 HTML 模板 + 3 份规划文档,只有 1 次 commit (`40ab94c Initial commit`) |
| `.worktrees/fastapi-session-backend-migration/` | 本仓库的 worktree(已注册) | 同上 | 与 main **完全相同**,分支 `codex/fastapi-session-backend-migration` 还没动过任何文件 |
| `.worktrees/feature/mvp-web-app/` | **另一个仓库**:`/Users/gabriel/.git` | `qiyansun52-ctrl/never-miss-UM.git` | Next.js + FastAPI 完整 MVP 代码,20 多次 commit,大量未提交改动 |

> 也就是说:你过去这一两周写的几乎所有代码(`web/` Next.js 应用、`api/` FastAPI 后端)其实都被提交到了 **`never-miss-UM` 这个仓库**,而不是 `travel-planner` 仓库。`/Users/gabriel/` 整个家目录被当作了一个 git 工作区,然后用 worktree 挂到了本项目下。这极有可能是一次手滑(在家目录里 `git init` 过)留下的遗产。

判断对错由你来,但下面所有"代码现状"都是基于 `.worktrees/feature/mvp-web-app/` 里的真实代码读出来的。

---

## A. 项目当前实际状态(按代码事实)

### A.1 顶层结构(本仓库本身)

```
travel-planner/
├── travel-template.html        # 23KB 静态 HTML 旅行规划模板(原型,2026-04-25)
├── workflow_prompt.md          # 早期"提示词工作流"说明:用 Claude + 12306/小红书/高德 MCP 串行规划
├── mcp_config.json             # MCP 服务器配置(12306-mcp / xhs-mcp / amap-mcp)
├── setup_mcp.sh                # MCP 安装脚本
├── docs/superpowers/
│   ├── specs/2026-04-30-travel-planner-web-app-design.md   # 产品/技术总体设计(中文)
│   └── plans/
│       ├── 2026-04-30-travel-planner-mvp-core.md            # 旧版"双面板聊天"MVP 实施计划
│       └── 2026-05-07-single-city-travel-planning-mvp.md    # 当前主流计划:单城市垂直切片 MVP
└── .worktrees/                 # 见上
```

本仓库自身只是个"骨架仓库",历史只有一个 Initial commit。

### A.2 `.worktrees/feature/mvp-web-app/` 里真实在跑什么

这是 **真正的项目**。当前分支 `feature/mvp-web-app`,commit 头部:
```
9bf06a8 feat: add LLM client wrapper with retry and structured output
c9b238a feat: add travel data provider abstraction
e02bfbe feat: add anonymous session persistence
82d5c45 feat: add itinerary validator
70c215b feat: add budget band and cost signal utilities
9641df3 feat: add normalized travel planning schemas
656e914 feat: align web scaffold tooling
…
38eb094 feat(web): switch to apiClient targeting Python backend
6433d19 feat(api): add discover and plan routes + FastAPI entry point
…
```

提交历史明显分两段(从下往上):
1. **早期 Next.js 单体架构**(2026-04-30 ~ 2026-05-04 左右):做完了 Claude 直接生成 plan + 双面板聊天 MVP,加上一个 3-section 的 discovery 流程。
2. **架构调整,拆出 Python FastAPI 后端**(`feat(api): scaffold Python FastAPI project with uv` 之后):把搜索换成 Tavily,LLM 换成 google-genai/Gemini 2.5 flash,FastAPI 镜像 Next.js 路由。
3. **再次重构,引入 single-city MVP 的 schema/validator/budget/orchestrator 等基础设施**(最近 7-8 个 commit):基本就是 `2026-05-07-single-city-travel-planning-mvp.md` 计划中 Task 0 ~ Task 6.5 的内容。

工作树状态:
- **11 个文件 modified 未提交**(README、首页、apiClient、e2e、session repo 等)
- **9 处新增未追踪**:`web/docs/mvp-launch-checklist.md`、`e2e/mvp-flow.spec.ts`、4 个新 API 路由(`adjustments/`、`discovery/`、`itinerary/`、`preferences/`、`stay-override/`、`selection/`)、新页面 `discovery/`、`preferences/`,以及 2 份新计划文档
- 还有一个**奇怪的嵌套目录** `Projects/travel-planner/docs/superpowers/plans/`(在 worktree 内部),里面有 4 份计划文档 — 看上去是某次在 home 目录下当 cwd 跑命令导致 plans 被写错位置

### A.3 当前应用真实形态

代码读出来,目前实际是个 **双服务架构**(虽然两边的代码都还在):

**前端**:`web/` — Next.js 16.2 + React 19 + TS + Tailwind 4 + Vitest + Playwright

`web/src/app/` 实际页面:
- `/` → `HomeStart` → `HardConstraintForm`(Step 1 硬性条件入口,中英双语切换,提交 `POST /api/sessions` 然后跳 `/discovery/[sessionId]`)
- `/discovery/[sessionId]/page.tsx` ✅ 存在
- `/preferences/[sessionId]/page.tsx` ✅ 存在
- `/trips/[sessionId]/page.tsx` ✅ 存在
- 还残留:`/discover/`(旧版三段式发现页)、`/plan/[id]/`(更老的双面板聊天版)

`web/src/app/api/` 路由:
- `sessions/route.ts`、`sessions/[sessionId]/route.ts`、`sessions/[sessionId]/selection/`、`sessions/[sessionId]/stay-override/`
- `discovery/route.ts`、`preferences/route.ts`、`itinerary/route.ts`、`adjustments/route.ts`
- 旧路由仍在:`discover/route.ts`、`plan/generate/route.ts`

`web/src/domain/` 已实现:`schemas.ts`(Zod)、`budget.ts`、`validator.ts`、`selection.ts`、`geography.ts`,均带测试。

`web/src/server/` 已实现:
- `agents/`:`discovery.ts`、`stay.ts`、`transport.ts`、`planner.ts`、`adjustmentClassifier.ts`、`orchestrator.ts`(含 `runFullPlanning` / `runPlannerOnly` 双入口和纠正回路)
- `llm/`:`client.ts`、`retry.ts`、`jsonRepair.ts`、`costLogger.ts`
- `providers/`:`registry.ts`、`map/{amap,mapbox,coordinateConversion}.ts`、`search/`、`supplier/`(注意没有 `weather/` 目录)
- `persistence/`:`sessionRepository.ts`、`fileSessionRepository.ts`、`cookies.ts`(文件落到 `web/.data/sessions.json`)
- `metrics/events.ts`

**Python 后端**:`api/` — FastAPI + uv,Python 3.12

`api/main.py` 暴露:
- `GET /health`
- `GET /api/discover?destination=...`(`app/routes/discover.py`)
- `POST /api/plan/generate`(`app/routes/plan.py`)

依赖 `app/services/{gemini,tavily}.py`(google-genai 直接调 gemini-2.5-flash + Tavily 搜索)。
模型在 `app/models/{attraction,plan,preferences}.py`,提示词在 `app/prompts/{discover,plan}.py`,**没有**任何 sessions / discovery-flow / orchestrator 的概念 — 它只镜像了"老版本"的两个端点。
有 5 个 pytest 测试文件覆盖 prompts、模型序列化、Tavily query builder。

**两边的关系**:`web/src/lib/apiClient.ts` 用 `NEXT_PUBLIC_API_URL` 决定是否打到 Python 后端;但 `createSession`、`runDiscovery`、`runItinerary`、`updateSelectedCards` 等 **都直接打到同源的 Next.js 路由,不经过 Python 后端**。也就是说:Python 后端在新流程里 **暂时不在主路径上**,只服务于老版本的 `/discover` 和 `/plan/generate`。

---

## B. 文档与代码不一致的地方

| 文档 | 文档中说 | 代码实际 | 性质 |
|---|---|---|---|
| `docs/superpowers/specs/2026-04-30-…design.md` §二 技术栈 | 单体 Next.js,Claude API,**没有** Python 后端 | 已存在 FastAPI + Gemini + Tavily 的并行架构 | 设计文档已过期,后续两次架构调整都没回写 |
| 同上 §四 页面设计 | 4 个页面:`/`、`/plan/[id]`、`/compare`、`/profile` | 实际是 `/`、`/discovery/[id]`、`/preferences/[id]`、`/trips/[id]`,旧 `/plan/[id]` 仍残留;**没有** `/compare` 和 `/profile` | 设计 1.0 与当前 MVP 不一致,见下面计划演化 |
| `docs/superpowers/plans/2026-04-30-travel-planner-mvp-core.md` | 第一版 MVP:首页 + 双面板聊天 + Claude 流式 + localStorage | 这一版代码确实存在(`/plan/[id]`、`usePlan.ts`、`planStore.ts`、`SearchForm.tsx`),但**已不在主流程上** | 实施计划已被新计划替代,代码未清理 |
| `docs/superpowers/plans/2026-05-07-single-city-travel-planning-mvp.md` | 16 个 Task,从 schemas 到 metrics 到 e2e 全覆盖 | Task 0 ~ Task 11 大致已落地;Task 12+(progress UI 完整版、adjustment routing UI、metrics 完整接入、e2e 全套)状态混合 — 文件大都在,有些是占位 | 当前主计划,代码追上了大概 60-70% |
| `web/docs/mvp-launch-checklist.md`(未提交) | 5 个环境变量(`LLM_PROVIDER_API_KEY`、`SEARCH_PROVIDER_API_KEY`、`MAPBOX_ACCESS_TOKEN`、`AMAP_API_KEY`、`WEATHER_PROVIDER_API_KEY`),并提"fixture-backed mode 不需要 key" | `web/src/server/providers/` 下 **没有 `weather/` 目录**;Python 后端用的是 `GEMINI_API_KEY` / `TAVILY_API_KEY`,不在该清单里 | 文档面向新计划写的,但跨服务的 env 还没统一 |
| `api/README.md` | "FastAPI 后端镜像 Next.js `/api/*` 路由 during the multi-agent migration" | 只镜像了 `/discover` 和 `/plan/generate`,新流程的 sessions/discovery/preferences/itinerary/adjustments 都没镜像 | 文档措辞暗示已经在迁移,但实际只完成了第一步骨架 |
| 根目录 `workflow_prompt.md` + `travel-template.html` + `mcp_config.json` | 早期 MCP-based 的 Claude 提示词工作流 | 当前代码完全没用这套(没有任何 MCP 调用),Tavily/Gemini 取代之 | 是早期原型残留,未被任何代码引用 |

---

## C. 文档之间的冲突

1. **MVP 形态前后两版**
   - `2026-04-30-travel-planner-mvp-core.md`:首页 + AI 双面板聊天,Claude 一次性出 JSON,localStorage 保存。
   - `2026-05-07-single-city-travel-planning-mvp.md`:Step1 入口 → discovery 卡片选择 → preferences → 四 agent 流水线 → 调整分类与部分重规划。
   - 两者的 **页面、数据流、状态存储、agent 边界全部不同**,但都以"MVP"自称。新计划没有显式说"作废旧计划",代码里两套页面也都还在。

2. **后端形态前后两版**
   - 设计文档说"Next.js 一体化,Claude API"。
   - `2026-05-06-python-backend-foundation.md`(在嵌套的 `Projects/...` 路径里)说"两服务架构,FastAPI 取代 Next.js API"。
   - `2026-05-06-langgraph-multi-agent-planner.md` 说"Python 后端跑 LangGraph 多 agent 流"。
   - `2026-05-07-single-city-travel-planning-mvp.md` 又把 agent 编排放在 **Next.js 服务端** (`web/src/server/agents/`),没提 LangGraph,也没提 Python 后端。
   - 现在代码里:Next.js 自己跑 agent,Python 那边用的是裸 google-genai + 旧端点。这意味着 LangGraph 路线在 schema/validator/orchestrator 出现之前就已经被悄悄换掉了。

3. **嵌套路径的"幽灵计划"**
   - `.worktrees/feature/mvp-web-app/Projects/travel-planner/docs/superpowers/plans/` 这个嵌套目录里有 4 份计划,其中 `2026-05-04-discovery-flow.md` 在主仓库 `docs/superpowers/plans/` 下 **不存在**。
   - 说明这条独立的"discovery flow"实施轨迹只活在 worktree 的错误路径下,其他人(或未来的你)按本仓库 `docs/` 找会漏掉。

---

## D. 关键不确定 / 需要你拍板的问题

1. **两个 git 仓库的关系**:你是希望 MVP 工作真的留在 `never-miss-UM` 仓库,还是当初就该把它做进 `travel-planner` 仓库?如果是后者,这是个不小的整理活(把 `feature/mvp-web-app` 的提交搬到当前仓库,删掉 home 目录下意外创建的那个 `.git`)。
2. **Python 后端的去留**:新流程已经把 agent / orchestrator / providers 都做在 Next.js server 里,Python 后端暂时是"老路径专用"。是要继续把 Python 那边补齐(按 LangGraph 计划走)还是让 Python 退场只留 Next.js?计划 2026-05-06 与 2026-05-07 之间有路线分叉。
3. **旧 MVP 代码(`/plan/[id]`、`SearchForm`、`usePlan.ts`、`planStore.ts`)**:已不在主流程上,留作备用?还是属于"还没来得及删"的死代码?
4. **当前正在做哪一步**:从 commit 节奏看,你最近在 `2026-05-07-single-city-travel-planning-mvp.md` 的 Task 6.5(LLM 客户端)那一带停下了,但工作区里又出现了 4 个新 API 路由 + 2 个新页面 + e2e + launch checklist — 是已经 **跳到了更后面的 Task 12-16**,还是这些是以前调试时半成品?
5. **嵌套的 `Projects/travel-planner/docs/...`**:是手滑写错路径,还是有意要把 plans 留在 worktree 里?现在主仓库的 `docs/superpowers/plans/` 缺少 `2026-05-04-discovery-flow.md`、`2026-05-06-python-backend-foundation.md`、`2026-05-06-langgraph-multi-agent-planner.md` 这 3 份。

---

## E. 这个项目的目标 — 候选解读(请你选)

下列每条都基于具体证据,但代码 + 文档之间还没有一个唯一答案:

### 候选 1:把模糊旅行想法转成清晰行程的 AI 一站式工具
- 证据:`specs/…design.md` §一"产品定位";`workflow_prompt.md` 围绕同样意图;`travel-template.html` 是产物形式之一。
- 特征:用户用自然语言描述期待,AI 拉数据 + 出 3-5 个选项 + 可对话调整。
- 代码对应:旧 `SearchForm` + `/plan/[id]` 这一版最贴这个定位。

### 候选 2:**单城市垂直切片**的旅行规划 MVP(更近期)
- 证据:`2026-05-07-single-city-travel-planning-mvp.md` 整份;`HomeStart` 文案"Plan a single-city trip / 规划一趟单城市旅行";discovery → preferences → itinerary 四 agent 流水线;orchestrator 的 corrective pass 结构。
- 特征:先卡死硬性条件 → 探索阶段(发现卡片) → 偏好 → 四 agent(stay / transport / planner + validator)生成行程 → 对话式部分重规划。
- 代码对应:目前主路径上的代码全部对应这一版。

### 候选 3:**Python + LangGraph 多 agent 后端**的实验项目
- 证据:`2026-05-06-langgraph-multi-agent-planner.md`;`api/` 整套 FastAPI + Gemini;commit `feat(api): scaffold Python FastAPI project with uv` 等。
- 特征:Next.js 只做 UI,所有 agent 编排放 Python,LangGraph 跑 transport / stay / planner 三节点,SSE 推进度回前端。
- 代码对应:Python 后端骨架已搭,但 LangGraph、graph state、SSE 都还没动 — 这条路看起来在 schema/validator 那一波重构里被中止了。

> 我倾向于**目前真实在做的是候选 2**,候选 1 是早期定位的延续,候选 3 是中途被换掉的方向。但这个判断由你确认。

---

## 审查元信息

- 范围:本项目根目录、两个 worktree 的代码与文档全部扫过。
- **未深读的盲区**:
  - `web/src/server/agents/{discovery,stay,transport,planner,adjustmentClassifier}.ts` 只看了 orchestrator,具体 prompt / LLM 调用形态没逐一展开。
  - `api/app/services/{gemini,tavily}.py` 只看了 README 和路由声明,内部异步实现没读细节。
  - 所有 `*.test.ts(x)` 与 `tests/test_*.py` 没看,只确认它们存在。
  - 11 个 modified 文件的具体 diff 没逐一读,只看了文件名。
- 代码即事实,文档为声明 — 当冲突,以代码为准并已显式标注。
- 未给出"建议"或"应该怎么做"。决策权归你。
