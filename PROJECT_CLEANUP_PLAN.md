# 项目治理与回归方案 — travel-planner

**写作时间**: 2026-05-09
**前置阅读**: `PROJECT_REALITY_CHECK.md`(同目录,先看完)
**性质**: 可执行的治理方案,只规划不执行 — 每一步执行前请你确认

---

## 0. 锁定的目标(本方案的前提)

> **目标产品形态**:单城市旅行规划 MVP — Step1 入口 → discovery 卡片选择 → preferences → 四 agent(stay / transport / planner + validator)流水线 → 对话式部分重规划。
>
> **目标技术架构**:Next.js 只做 UI + 路由壳 + session 引导;**所有 agent 编排在 Python + LangGraph**。Tavily 做搜索,google-genai(Gemini 2.5 flash)做 LLM。
>
> **直接结果**:`web/src/server/agents/`、`web/src/server/llm/`、`web/src/server/providers/` 这些 TS 代码 **不是最终形态**,会被作为"参考实现"逐步移植到 Python,然后删除。

下面所有阶段都围绕这两条结论展开。

---

## 0.1 已锁定的决定(2026-05-09)

- **不再使用 git worktree**。原因:单人开发 + 单项目 + 当前没有并行 agent 任务,worktree 收益不及代价,而且这次"代码进错仓库"事故就是 worktree 误用造成的。
- 实施意味:
  - Phase 1.3 之后,`.worktrees/` 目录在主仓库根**永久消失**,不再重建。
  - 后续切分支统一走 `git checkout` / `git switch`。
  - 如果未来真要跑 agent 并行,worktree 必须放在项目目录之外(如 `~/worktrees/travel-planner-<branch>/`),且必须由主仓库的 `.git` 创建。
  - `.gitignore` 要加 `.worktrees/`(防止再次被误建)。

---

## 1. 当前要治理的真实问题(简表)

| # | 问题 | 痛点 |
|---|---|---|
| P1 | 真实代码在错误的 git 仓库(挂在 `/Users/gabriel/.git`,远端是 `never-miss-UM`) | 99% 工作没进 `travel-planner` 仓库,丢失风险 + 协作混乱 |
| P2 | 两份相互冲突的实施计划(`single-city-mvp` vs `langgraph-multi-agent`)同时存在 | 后续接手不知道按哪份做 |
| P3 | 三套并行 MVP 代码同时存在(旧双面板聊天 / 旧三段 discovery / 新单城市流程) | 视觉噪音 + 死代码 + 测试覆盖空洞 |
| P4 | Next.js 写了一整套 agents/orchestrator/llm/providers,但目标架构这些都该在 Python | 路线走错;但又不能直接扔,需要作为参考移植 |
| P5 | 嵌套幽灵目录 `Projects/travel-planner/docs/superpowers/plans/` 里有 3 份计划主仓库不可见 | 关键计划文档"消失" |
| P6 | 11 个 modified + 9 处 untracked 长期未提交 | 容易在切分支或重排时丢失 |
| P7 | spec 1.0 和 launch checklist 的描述都和当前代码不一致 | 文档可信度归零 |
| P8 | 根目录 `workflow_prompt.md` / `mcp_config.json` / `setup_mcp.sh` / `travel-template.html` 是早期 MCP 原型残留,已无代码引用 | 误导:像还在用 12306-mcp / 小红书 MCP |

---

## 2. 治理总路线(七个阶段,有强先后依赖)

```
Phase 0  备份 + 安全网          (必做,15 分钟)
   ↓
Phase 1  git 拓扑整理           (高风险,先做,1-2 小时)
   ↓
Phase 2  锁定文档与计划         (无破坏,30 分钟)
   ↓
Phase 3  把 TS agents 移植到 Python LangGraph  (主要工作量)
   ↓
Phase 4  Next.js 端瘦身         (依赖 Phase 3 完成)
   ↓
Phase 5  补齐文档 + 清理根目录原型残留
   ↓
Phase 6  按新计划继续实施 + 回归测试
```

---

## Phase 0 — 备份 + 安全网(必做)

**目的**:把当前一切状态保护起来,后面任何步骤都可回滚。

- [ ] **0.1** 在 `.worktrees/feature/mvp-web-app/` 里把所有未提交工作以一个临时 commit 保存:
  ```bash
  cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app
  git add -A
  git commit -m "wip: snapshot before cleanup"
  ```
  这个 commit 会落到 `never-miss-UM` 仓库的 `feature/mvp-web-app` 分支上。
- [ ] **0.2** push 到 GitHub 备份:
  ```bash
  git push -u origin feature/mvp-web-app
  ```
- [ ] **0.3** 在主仓库打一个 tag,记录"治理前状态":
  ```bash
  cd /Users/gabriel/Projects/travel-planner
  git tag pre-cleanup-2026-05-09
  git push origin pre-cleanup-2026-05-09
  ```
- [ ] **0.4** 把 `.worktrees/feature/mvp-web-app/` 整个目录复制一份到 `~/backup/mvp-web-app-snapshot-2026-05-09/`(物理备份,防 git 操作失误):
  ```bash
  rsync -a --exclude='node_modules' --exclude='.next' --exclude='.venv' \
    /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/ \
    ~/backup/mvp-web-app-snapshot-2026-05-09/
  ```

**验收**:GitHub 上能看到 `feature/mvp-web-app` 分支 + `pre-cleanup-2026-05-09` tag;本地有 rsync 备份。

---

## Phase 1 — git 拓扑整理(把代码搬回正确的仓库)

**目的**:让 `feature/mvp-web-app` 的所有 commit 落到 `travel-planner` 仓库的分支上,然后让 `/Users/gabriel/.git` 这个家目录级别的"幽灵仓库"消失。

### 1.1 先勘察 `never-miss-UM` 仓库到底装了什么

执行前需要弄清楚:这个仓库是不是除了 `feature/mvp-web-app` 之外还有别的不相关历史/分支?

- [ ] **1.1.1** 列出 `/Users/gabriel/.git` 的所有分支和 tag:
  ```bash
  cd /Users/gabriel
  git branch -a
  git tag
  git log --all --oneline | head -50
  ```
- [ ] **1.1.2** 看看 `feature/mvp-web-app` 的根 commit 是什么 — 是个独立的 Initial commit 还是分叉自其他分支?
  ```bash
  git log feature/mvp-web-app --oneline | tail -5
  git log feature/mvp-web-app --reverse --oneline | head -5
  ```
- [ ] **1.1.3** 决策点:
  - 如果 `never-miss-UM` 里只有 `feature/mvp-web-app` 一条线性历史 → 走方案 A(干净)
  - 如果掺了其他不相关项目 → 走方案 B(只取需要的 commit)
  - 在本文档里记录决策结论。

### 1.2 把 commit 搬到 travel-planner 仓库

#### 方案 A — 单仓库直接 fetch + rebase(线性、干净)

- [ ] **A.1** 在 travel-planner 主仓库里把 `never-miss-UM` 加为临时远程:
  ```bash
  cd /Users/gabriel/Projects/travel-planner
  git remote add nm /Users/gabriel/.git
  git fetch nm feature/mvp-web-app:incoming/mvp-web-app
  ```
- [ ] **A.2** 把 incoming 分支基于当前 main rebase 一下(因为两边没有共同祖先):
  ```bash
  git checkout incoming/mvp-web-app
  # 找到 incoming 分支最早的 commit
  EARLIEST=$(git log --reverse --pretty=%H | head -1)
  # 把 EARLIEST 之后的所有 commit 重放到 main 之上
  git rebase --onto main $EARLIEST^ incoming/mvp-web-app
  ```
  *如果没有共同祖先且 rebase 报错,改用方案 C(format-patch / am)。*
- [ ] **A.3** 给最终分支起个稳定名字:
  ```bash
  git branch -m incoming/mvp-web-app feature/mvp-web-app
  git push -u origin feature/mvp-web-app
  ```

#### 方案 B — 只取 feature 分支上"非共同祖先"的 commit

适用于 never-miss-UM 仓库还有别的杂项历史时。

- [ ] **B.1** 找到 `feature/mvp-web-app` 与其它无关分支的真正分叉点(可能是个奇怪的 root commit)。
- [ ] **B.2** 用 `git format-patch <fork-point>..feature/mvp-web-app` 导出一组 patch:
  ```bash
  cd /Users/gabriel
  git format-patch <fork-point>..feature/mvp-web-app -o /tmp/mvp-patches/
  ```
- [ ] **B.3** 在 travel-planner 仓库 `git am` 应用:
  ```bash
  cd /Users/gabriel/Projects/travel-planner
  git checkout -b feature/mvp-web-app
  git am /tmp/mvp-patches/*.patch
  ```
- [ ] **B.4** 处理冲突(`git am --resolved` 推进),然后 push。

#### 方案 C — 兜底:取工作树快照,合成一个 commit

只有在 A、B 都失败时才用。会丢失 20+ 个 feat commit 的历史脉络。

- [ ] **C.1**
  ```bash
  cd /Users/gabriel/Projects/travel-planner
  git checkout -b feature/mvp-web-app
  rsync -a --delete \
    --exclude='.git' --exclude='node_modules' --exclude='.next' --exclude='.venv' \
    --exclude='.worktrees' \
    ~/backup/mvp-web-app-snapshot-2026-05-09/ ./
  git add -A
  git commit -m "feat: import mvp-web-app from never-miss-UM (history collapsed)"
  ```

### 1.3 注销旧 worktree、删除幽灵仓库

仅在 1.2 成功且新分支已 push 后再做。

- [ ] **1.3.1** 注销 home 级别 worktree 的指针:
  ```bash
  cd /Users/gabriel
  git worktree remove --force /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app
  ```
- [ ] **1.3.2** 注销本仓库的 `fastapi-session-backend-migration` worktree(它现在只是 main 副本,占位无意义):
  ```bash
  cd /Users/gabriel/Projects/travel-planner
  git worktree remove .worktrees/fastapi-session-backend-migration
  git branch -D codex/fastapi-session-backend-migration   # 如确实不需要
  ```
- [ ] **1.3.3** 谨慎处理 `/Users/gabriel/.git` — **不要直接 rm**,先检查它是不是还有别的 worktree 或别的项目在用:
  ```bash
  ls /Users/gabriel/.git/worktrees/ 2>/dev/null
  cat /Users/gabriel/.git/config
  ```
  如果确认只是为这次 mvp-web-app 服务、且已经 1.2 成功搬走、且 GitHub 上 `never-miss-UM` 仓库你也不再需要 → 备份后删除:
  ```bash
  mv /Users/gabriel/.git ~/backup/home-ghost-git-2026-05-09
  ```
  *先 mv,不 rm。一周后确认无影响再彻底删。*
- [ ] **1.3.4** 把 `nm` 远程移除:
  ```bash
  cd /Users/gabriel/Projects/travel-planner
  git remote remove nm
  ```

**验收**:
- `cd /Users/gabriel/Projects/travel-planner && git branch -a` 看到 `main` + `feature/mvp-web-app`,后者有完整代码。
- `git worktree list` 只剩主仓库自身。
- `/Users/gabriel/.worktrees/` 不再存在(或已经备份)。
- `cd /Users/gabriel && git status` 不再像在一个 git 仓库里(因为我们把 .git mv 走了)。

---

## Phase 2 — 锁定文档与计划

**目的**:消除文档之间的相互冲突,让"按哪份做"这个问题有唯一答案。

### 2.1 抢救嵌套幽灵目录里的计划

- [ ] **2.1.1** 把 worktree 里的 `Projects/travel-planner/docs/superpowers/plans/` 下 4 份计划复制到主仓库 `docs/superpowers/plans/`:
  - `2026-04-30-travel-planner-mvp-core.md`(已存在,跳过)
  - `2026-05-04-discovery-flow.md` ✅ 抢救
  - `2026-05-06-langgraph-multi-agent-planner.md` ✅ 抢救
  - `2026-05-06-python-backend-foundation.md` ✅ 抢救
- [ ] **2.1.2** 删除嵌套目录 `Projects/travel-planner/`(这是手滑产生的)。

### 2.2 显式作废过期文档

不删,而是在文档头加 `STATUS: SUPERSEDED` 说明,标明被谁取代:

- [ ] **2.2.1** `docs/superpowers/specs/2026-04-30-travel-planner-web-app-design.md`:在文件最上方插入:
  ```
  > **STATUS: SUPERSEDED (2026-05-09)**
  > 本设计文档对应早期单体 Next.js + 双面板聊天形态,已不再代表当前产品。
  > 当前产品形态见:`docs/superpowers/plans/2026-05-09-langgraph-single-city-mvp.md`
  ```
- [ ] **2.2.2** `docs/superpowers/plans/2026-04-30-travel-planner-mvp-core.md`:同样标作废,指向新计划。
- [ ] **2.2.3** `docs/superpowers/plans/2026-05-04-discovery-flow.md`:如果其内容已被 single-city plan 覆盖,标作废;否则标"PARTIAL: 已并入 X 计划的 Task Y"。
- [ ] **2.2.4** `docs/superpowers/plans/2026-05-06-python-backend-foundation.md`:它是 LangGraph 路线的前置(scaffold FastAPI),代码已经落地一部分。标"COMPLETED — 见 commit 范围 1ab156f..6433d19"。
- [ ] **2.2.5** `docs/superpowers/plans/2026-05-07-single-city-travel-planning-mvp.md`:它的**产品流程部分**仍然有效,但**架构部分**(把 agents 放 Next.js)需要被新计划覆盖。在头部加注:
  ```
  > **PARTIAL: 产品流程章节有效;架构章节(Next.js server agents)已于 2026-05-09 改为 Python+LangGraph,见 langgraph-single-city-mvp.md**
  ```

### 2.3 写一份合并新计划

> 这一份是后续所有实施的唯一依据。

- [ ] **2.3.1** 创建 `docs/superpowers/plans/2026-05-09-langgraph-single-city-mvp.md`,以 `2026-05-07-single-city-travel-planning-mvp.md` 的产品流程章节为骨架,把架构部分换成 `2026-05-06-langgraph-multi-agent-planner.md` 的 LangGraph 形态。骨架建议:
  - **目标**:单城市旅行规划 MVP,LangGraph 多 agent 后端。
  - **架构**:
    - Next.js(`web/`):UI + 页面路由 + Cookie session id;**没有任何 server-side agent 逻辑**。
    - FastAPI(`api/`):Pydantic schemas、session repository、LangGraph 图(discovery / stay / transport / planner / adjustment-classifier 节点)、provider 适配器(Tavily / map / weather / supplier)、LLM client wrapper、metrics、cost log。
    - 通讯:HTTP JSON + 关键长任务用 SSE 推 progress。
  - **任务清单**(取并集):
    - 从 `single-city-mvp` 拉:Task 0/2/3/4/5/7-15(产品流程、schemas、validator、budget、session、UI、metrics、e2e)
    - 从 `langgraph-multi-agent` 拉:graph state、LangGraph 节点封装、SSE 适配、Pydantic schemas
    - 删去 `single-city-mvp` 的 Task 6/6.5/8/11(都是 Next.js 端 agent / LLM / provider — 由 Python 端等价物代替)
- [ ] **2.3.2** 在新计划顶部明确写一个"被替换映射表":TS 文件 → Python 等价物。这张表在 Phase 3 会一格一格打勾。

### 2.4 更新顶层 README

- [ ] **2.4.1** 把 `web/README.md` 改成:
  ```
  # Travel Planner — Web (UI 层)
  Next.js 应用,只负责 UI 和路由壳。所有规划逻辑在 `../api`(Python LangGraph)。
  开发:`cd web && npm run dev`(默认 http://localhost:3000),依赖后端跑在 :8000。
  ```
- [ ] **2.4.2** 把 `api/README.md` 改成项目主入口角色,详述 LangGraph 流程、env vars、test 命令。
- [ ] **2.4.3** 顶层 `README.md`(主仓库根)写一段总览 + 指向新计划文档。

**验收**:任何人新进项目,只读顶层 README 就知道"这是单城市旅行规划 MVP,Python LangGraph 后端,实施按 `2026-05-09-langgraph-single-city-mvp.md` 走"。

---

## Phase 3 — 把 TS agents 移植到 Python LangGraph

**目的**:把 Next.js 端已经写好的逻辑作为参考,在 Python 重写为 LangGraph 节点。

### 3.1 移植映射表

按这个对照表,从上到下做。每行做完才动下一行。

| TS 源(待删) | Python 目标(新建) | 备注 |
|---|---|---|
| `web/src/domain/schemas.ts` (Zod) | `api/app/models/schemas.py` (Pydantic v2) | Pydantic 成为单一事实源;TS 端临时保留 UI 类型,长期由 Python 通过 `model_json_schema()` 导出 + `json-schema-to-typescript` 生成 |
| `web/src/domain/budget.ts` | `api/app/domain/budget.py` | 纯函数,直译,带同价的 pytest |
| `web/src/domain/validator.ts` | `api/app/domain/validator.py` | 同上,纯确定性 |
| `web/src/domain/geography.ts` + `selection.ts` | `api/app/domain/{geography,selection}.py` | 同上 |
| `web/src/server/llm/{client,retry,jsonRepair,costLogger}.ts` | `api/app/llm/{client,retry,json_repair,cost_logger}.py` | 已有 google-genai SDK,把 retry / repair / cost log 复刻 |
| `web/src/server/providers/registry.ts` 与 `map/{amap,mapbox,coordinateConversion}.ts`、`search/`、`supplier/` | `api/app/providers/{registry,map_amap,map_mapbox,coord,search,supplier,weather}.py` | weather 之前没有,补 |
| `web/src/server/persistence/{sessionRepository,fileSessionRepository,cookies}.ts` | `api/app/persistence/{session_repository,file_session_repository}.py` + Next.js 端只剩一个 cookie helper | 文件路径从 `web/.data/sessions.json` 迁到 `api/.data/sessions.json` |
| `web/src/server/agents/discovery.ts` | LangGraph 节点 `api/app/graph/nodes/discovery.py` | 行为对齐 single-city plan 的 Task 8 |
| `web/src/server/agents/stay.ts` | `api/app/graph/nodes/stay.py` | |
| `web/src/server/agents/transport.ts` | `api/app/graph/nodes/transport.py` | |
| `web/src/server/agents/planner.ts` + `orchestrator.ts` 的 corrective pass | `api/app/graph/workflow.py`(planner 节点 + 纠正回路边) | LangGraph 用条件边表达 corrective pass,而不是写一个 orchestrator class |
| `web/src/server/agents/adjustmentClassifier.ts` | `api/app/graph/nodes/adjustment_classifier.py` + 路由到 type A/B/C 子图 | |
| `web/src/server/metrics/events.ts` | `api/app/metrics/events.py` | |

### 3.2 移植的纪律

- [ ] **3.2.1** 一个文件移植完,**对应的 TS 文件先不删** — 改名为 `*.legacy.ts` 并加 `// LEGACY: replaced by api/app/...` 注释,Phase 4 再统一删。
- [ ] **3.2.2** 每个 Python 模块都要带 pytest;不允许"先放着没测"。
- [ ] **3.2.3** Pydantic v2 的字段命名跟 TS Zod 完全一致(snake_case vs camelCase 的差异由 `Field(alias=...)` + `model_config = ConfigDict(populate_by_name=True)` 处理),保证 JSON 兼容。
- [ ] **3.2.4** LLM client 一上来就加 cost log,与 TS 端 `costLogger.ts` 同结构(label / 估算 token / duration / success / retry count),日志落 `api/.data/llm-cost.jsonl`。

### 3.3 LangGraph 设计要点(给图节点定形)

- [ ] **3.3.1** `PlanState` (TypedDict 或 Pydantic) 至少含:`session_id`、`hard_constraints`、`discovery`、`preferences`、`stay`、`transport`、`itinerary`、`validator_issues`、`progress_events: list`。
- [ ] **3.3.2** 节点拓扑:
  ```
  discovery → (用户在 UI 选 cards 后回到) → stay ┐
                                                   ├→ planner → validator
                                                transport ┘                ↓
                                                                          (有 error?)
                                                                          ↓ yes
                                                                       planner(纠正一次)→ validator → end
                                                                          ↓ no
                                                                          end
  ```
- [ ] **3.3.3** Adjustment 分类用 **独立的小图**,Type A → 直接跑 planner 节点;Type B → 跑相关 agent 节点 + planner;Type C → 不跑图,返回 confirmation 给前端。
- [ ] **3.3.4** SSE:LangGraph 的 `astream` 把每个节点开始/结束事件转成 `{stage, status}` 推到 `/api/itinerary/stream` 这类端点。

**验收**:
- `cd api && uv run pytest -v` 全绿,且测试覆盖原 TS 测试覆盖的场景(尤其是 budget thresholds、validator purity、orchestrator corrective pass 三个 happy/error 路径、adjustment 分类的高/低置信度分支)。
- `cd api && uv run uvicorn main:app --reload` 起得来,新端点 `/api/sessions`、`/api/discovery`、`/api/preferences`、`/api/itinerary`、`/api/adjustments` 都能被 curl 验证。

---

## Phase 4 — Next.js 端瘦身

**前置**:Phase 3 的对应 Python 端口已经能正常服务并通测试。

### 4.1 删除已移植的 server 代码

- [ ] **4.1.1** 删除目录:
  - `web/src/server/agents/`
  - `web/src/server/llm/`
  - `web/src/server/providers/`
  - `web/src/server/metrics/`
  - `web/src/server/persistence/`(改为只在 `web/src/lib/cookies.ts` 留一个写 cookie 的薄函数)
- [ ] **4.1.2** 删除已被新流程覆盖的旧代码:
  - `web/src/app/plan/[id]/`(旧双面板聊天)
  - `web/src/app/api/plan/`(旧 plan/generate 路由)
  - `web/src/app/discover/`(旧三段 discovery 页)
  - `web/src/app/api/discover/`
  - `web/src/components/search/SearchForm.tsx`
  - `web/src/components/plan/`(旧的 ItineraryPanel/DayCard/ActivityCard/AIChatPanel)
  - `web/src/components/discover/`(旧三段 discovery 卡片)
  - `web/src/hooks/usePlan.ts`
  - `web/src/lib/{claude,planStore,googleSearch}.ts`
  - `web/src/lib/types.ts` 里只与旧版相关的类型
- [ ] **4.1.3** 删除 `web/src/app/api/` 下所有把活路由到 Next.js server 的端点(它们的工作已搬到 Python);只保留 Next.js 必需的少量 BFF 端点(如健康检查、SSE 代理),或者全部去掉,直接前端 fetch Python。

### 4.2 把 `apiClient.ts` 改成纯 Python 后端客户端

- [ ] **4.2.1** 强制要求 `NEXT_PUBLIC_API_URL` 必填(默认 `http://localhost:8000`),没设直接抛错(不要静默回退 same-origin)。
- [ ] **4.2.2** 删掉 `discoverDestination`、`generatePlan` 这俩老方法。

### 4.3 web 配置清理

- [ ] **4.3.1** `web/next.config.ts`:如果之前为同源加过 rewrites,改为 `rewrites` 把 `/api/*` 代理到 `http://localhost:8000/api/*`,这样前端代码不用关心域名差异。
- [ ] **4.3.2** `package.json` 里的 `dev` 脚本改成同时拉起 `web` 和 `api`(可以用 `concurrently`),或者写一个 `npm run dev:all` 脚本。

**验收**:
- `cd web && npm run typecheck && npm run lint && npm run build` 全绿。
- 浏览器走 `/ → /discovery/[id] → /preferences/[id] → /trips/[id]` 全程能跑通,后端是 Python。
- `web/src/server/` 目录下只有空壳或被删干净。

---

## Phase 5 — 文档兜底 + 根目录清理

### 5.1 把 spec 1.0 重写成 spec 2.0

- [ ] **5.1.1** 新建 `docs/superpowers/specs/2026-05-09-travel-planner-design-v2.md`:
  - 产品定位(沿用旧 spec 第一章)。
  - 技术栈表(Python LangGraph + Next.js UI + Tavily + Gemini)。
  - 整体架构图(两服务,Next.js 不参与逻辑)。
  - 单城市 MVP 范围。
  - 旧版 spec 标 SUPERSEDED(已在 Phase 2 做了)。

### 5.2 更新 launch checklist

- [ ] **5.2.1** `web/docs/mvp-launch-checklist.md` 改名为 `docs/mvp-launch-checklist.md`(放主仓库 docs 下,不再藏在 web 里)。
- [ ] **5.2.2** env 表统一为 Python 端的实际 env:`GEMINI_API_KEY`、`TAVILY_API_KEY`、`AMAP_API_KEY`、`MAPBOX_ACCESS_TOKEN`、`WEATHER_PROVIDER_API_KEY`、`SESSION_DATA_DIR`(可选)。
- [ ] **5.2.3** 加上 fixture 模式说明:跑 e2e / 单测时 LLM/provider 都用确定性 fixture。

### 5.3 处理早期 MCP 原型残留

这些是初代手工 prompt 工作流的产物,现在代码完全没用:

| 文件 | 处理 |
|---|---|
| `workflow_prompt.md` | 移到 `docs/archive/early-mcp-prototype/workflow_prompt.md`,作为历史保留 |
| `mcp_config.json` | 同上,移到 `docs/archive/early-mcp-prototype/` |
| `setup_mcp.sh` | 同上 |
| `travel-template.html` | 后期会作为"导出 HTML 行程"模板复用 → 移到 `web/src/templates/travel-template.html`(Phase 6 新增导出功能时再用) |

- [ ] **5.3.1** 用 `git mv` 而不是 `mv + add`,保留历史。

---

## Phase 6 — 按新计划继续实施 + 回归基线

- [ ] **6.1** 打开 `docs/superpowers/plans/2026-05-09-langgraph-single-city-mvp.md`,从"被替换映射表"对完之后的下一个 Task 开始(预计是 Task 12 起的 UI/SSE 进度条 + Type C 确认卡 + e2e 全套)。
- [ ] **6.2** 每完成一个 Task,跑回归基线:
  ```bash
  cd web && npm run typecheck && npm run lint && npm run test && npm run build && npm run test:e2e
  cd ../api && uv run pytest -v && uv run ruff check . && uv run mypy app
  ```
- [ ] **6.3** push 到 GitHub,在 PR 描述里贴对应 Task 编号。

---

## 风险与应对

| 风险 | 触发条件 | 应对 |
|---|---|---|
| Phase 1.2 rebase 冲突无法解决 | never-miss-UM 历史和 travel-planner 历史交叉太复杂 | 退回方案 C(快照 + 单 commit),仍然能继续做事 |
| Phase 1.3 误删 `/Users/gabriel/.git` 导致家目录其他东西出问题 | home 目录意外被当成更大 git 项目使用 | 只 mv 不 rm;1 周观察期;真有问题就 mv 回来 |
| Phase 3 移植期间产品双轨(TS 和 Python 都能跑),前端调用混乱 | 移植节奏不齐 | 移植期内 `apiClient.ts` 加一个 `USE_PYTHON_BACKEND` env 开关,逐路由切换;一旦某路由 Python 端测试通过,就切过去并删 TS 路由 |
| Pydantic 与 Zod schema 漂移 | 双方手工维护 | Phase 3 完成后立刻把 Python `model_json_schema()` 导出为 JSON Schema,跑 `json-schema-to-typescript` 自动生成 TS 类型,删掉手写 TS schemas |
| LangGraph corrective pass 行为与 TS orchestrator 不一致 | LangGraph 条件边的语义和我们想象的不同 | 把 TS 端 `orchestrator.test.ts` 的所有 case 用 pytest + LangGraph 重写为黑盒 fixture 测试,作为契约 |
| google-genai SDK / LangGraph 版本不稳 | 二者都还在快速迭代 | `pyproject.toml` 锁定到具体小版本号,升级走单独 PR |
| 旧 Next.js 代码删除时漏删依赖,build 失败 | TS 端隐式引用已删模块 | Phase 4.1 之前先跑 `tsc --noEmit` 找出所有引用,边删边修 |
| 现有 11 个 modified 文件里有重要本地 patch | 任何人都不一定记得为什么改 | Phase 0.1 把它们都 commit 成 `wip:` 后再处理;真有有价值的改动,在 Phase 3/4 一次拣回 |

---

## 完成判定(Definition of Done)

整套方案做完后,以下条件全部成立才算"治理完毕":

- [ ] `cd /Users/gabriel/Projects/travel-planner && git worktree list` 只有主工作区一行。
- [ ] `git branch -a` 看到 `main` + `feature/mvp-web-app`(或已合并回 main),没有 codex/* 残留。
- [ ] `git remote -v` 只有一个 origin = `qiyansun52-ctrl/travel-planner.git`。
- [ ] `/Users/gabriel/.git` 已不存在(或已 mv 到 backup 目录,1 周观察期通过)。
- [ ] `web/src/server/` 目录被清空或已删。
- [ ] `web/src/app/{plan,discover}/` 已删,`web/src/app/api/` 只剩极少 BFF。
- [ ] `api/app/graph/` 存在,LangGraph 工作流可在 `pytest` 中端到端跑通。
- [ ] `cd web && npm run build` 与 `cd api && uv run pytest` 双绿。
- [ ] 浏览器走完整产品流(Step1 → discovery → preferences → trips → adjustment)成功。
- [ ] `docs/superpowers/specs/` 下只有一份 v2 设计是 active,其它都标 SUPERSEDED。
- [ ] `docs/superpowers/plans/` 下当前只有一份 active 计划:`2026-05-09-langgraph-single-city-mvp.md`,其它标 SUPERSEDED 或 COMPLETED。
- [ ] 顶层 README 一段话能讲清"这是什么 / 怎么跑 / 计划在哪 / 架构图"。

---

## 需要你拍板的开放点

下面这些不影响方案大方向,但会改变细节:

1. **never-miss-UM 这个 GitHub 仓库要保留还是删?** 如果保留(防止 Phase 1 失败兜底),Phase 1.3 的删幽灵仓库就要往后推。
2. **`fastapi-session-backend-migration` 分支还要不要?** 当前是 main 副本,毫无内容,默认会在 Phase 1.3.2 删掉。
3. **TS 类型最终怎么生成?** 默认方案是从 Pydantic 自动生成。如果你更偏好两边各自手写,Phase 3.2.3 那条就改。
4. **Adjustment 的 LangGraph 表达**:Type A/B/C 走子图(当前默认),还是用一个大图加条件路由?子图更易测,大图更易看全貌。
5. **进度推送通道**:SSE(plan 文档默认)还是 WebSocket?WebSocket 写起来稍重,但能做双向(比如取消当前 LLM 调用)。
6. **`api/.data/sessions.json` 的将来**:文件存储是 MVP 形态。要不要顺便定一个"真正持久化"的路径(SQLite / Postgres),写到风险/路线图里?
