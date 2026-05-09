# LangGraph MVP Plan 12 Roadmap Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the original Plan 1-9 roadmap as completed, align current handoff docs with Plan 10/11, and make launch readiness catch stale roadmap/status drift.

**Architecture:** Keep product code unchanged. Treat roadmap/README files as release artifacts and extend `scripts/check_launch_readiness.py` with lightweight file-content and path assertions so stale "active roadmap" or old `npm run regression` guidance cannot re-enter unnoticed.

**Tech Stack:** Markdown, Python stdlib launch checker, GNU Make regression gate.

---

## Context Notes

- Plan 1-9 are complete and Plan 10/11 added post-roadmap launch readiness and fixture API smoke gates.
- The root roadmap still says `STATUS: ACTIVE (2026-05-09)` and leaves the final Definition of Done unchecked.
- Root/API/Web README files still have small handoff drift: root README only names Plan 10, API README points to an older plan, and Web README omits the API smoke step from regression details.
- This plan does not change runtime behavior; it only closes documentation and checker gaps.

## File Structure

- Create `docs/superpowers/plans/2026-05-10-langgraph-mvp-12-roadmap-closure.md`: this plan, committed before implementation.
- Modify `docs/superpowers/plans/2026-05-09-langgraph-mvp-roadmap.md`: mark status and route-level Definition of Done as complete with current `make regression` evidence.
- Modify `README.md`: replace the stale Plan 10-only note with current post-roadmap hardening status.
- Modify `api/README.md`: point to the canonical roadmap/post-roadmap plans instead of the older single-city MVP plan.
- Modify `web/README.md`: mention fixture-backed API smoke in the offline regression description and align the API URL default wording.
- Modify `scripts/check_launch_readiness.py`: assert roadmap closure, current docs, and important structural DoD paths.

---

### Task 0: Commit Plan

**Files:**
- Create: `docs/superpowers/plans/2026-05-10-langgraph-mvp-12-roadmap-closure.md`

- [x] **Step 1: Commit this plan before implementation**

```bash
git add docs/superpowers/plans/2026-05-10-langgraph-mvp-12-roadmap-closure.md
git commit -m "docs: add roadmap closure plan"
```

Expected: a docs-only commit containing this plan.

---

### Task 1: Close Roadmap and Handoff Docs

**Files:**
- Modify: `docs/superpowers/plans/2026-05-09-langgraph-mvp-roadmap.md`
- Modify: `README.md`
- Modify: `api/README.md`
- Modify: `web/README.md`

- [x] **Step 1: Update roadmap status**

In `docs/superpowers/plans/2026-05-09-langgraph-mvp-roadmap.md`, replace the opening status block with:

```md
> **STATUS: COMPLETED (2026-05-10)**
>
> Plan 1-9 are complete. Post-roadmap hardening continues in Plan 10 (launch readiness), Plan 11 (fixture API smoke gate), and Plan 12 (roadmap closure).
```

- [x] **Step 2: Update Plan 9 command wording**

Replace the Plan 9 DoD command reference:

```md
**DoD**:`npm run regression` 在 CI(本地模拟)跑完无错;Playwright trace 三条路径全绿;有 README 段落说明怎么开 fixture 模式跑离线 e2e。
```

with:

```md
**DoD**:`make regression` 在本地 CI gate 跑完无错;Playwright critical paths 全绿;README 说明了 fixture 模式、API smoke 和离线回归。
```

- [x] **Step 3: Mark roadmap Definition of Done complete**

Replace the final Definition of Done checklist with:

```md
## Definition of Done(整套路线图)

- [x] Plan 1-9 全部 DoD 通过(Plan 10/11 后 `make regression` 验收通过)
- [x] `web/src/server/` 不存在
- [x] `api/app/graph/` 存在,LangGraph 工作流可在 pytest 中端到端跑通
- [x] `cd web && npm run build` 与 `cd api && uv run pytest` 双绿
- [x] 浏览器关键路径通过 Playwright fixture 模式跑完整流程
- [x] `make regression` 跑通(包含 launch-check、类型漂移、API smoke、pytest、ruff、Playwright fixture e2e)
- [x] 顶层 README 更新"如何启动 / 如何跑回归"段落
```

- [x] **Step 4: Update root README planning note**

Replace the root `## Planning Docs` paragraph with:

```md
The original migration roadmap is `docs/superpowers/plans/2026-05-09-langgraph-mvp-roadmap.md`. Plan 1-9 are complete; Plan 10-12 are post-roadmap hardening passes for launch readiness, fixture smoke automation, and roadmap closure.
```

- [x] **Step 5: Update API README planning note**

Replace the final API README planning sentence with:

```md
The canonical migration roadmap is `../docs/superpowers/plans/2026-05-09-langgraph-mvp-roadmap.md`; post-roadmap hardening plans live beside it as Plan 10+.
```

- [x] **Step 6: Update Web README regression wording**

In `web/README.md`, replace:

```md
The regression target runs generated-type drift checks, frontend lint/unit/build/e2e,
and backend pytest/ruff. Playwright starts FastAPI with `E2E_FIXTURE_MODE=1`, dummy
provider keys, temp session storage, and CORS configured for `127.0.0.1:3000`.
```

with:

```md
The regression target runs launch docs/env checks, generated-type drift checks,
frontend lint/unit/build/e2e, backend pytest/ruff, and fixture-backed API smoke.
Playwright starts FastAPI with `E2E_FIXTURE_MODE=1`, dummy provider keys, temp
session storage, and CORS configured for `127.0.0.1:3000`.
```

Also replace:

```md
The dev script starts FastAPI on `http://127.0.0.1:8000` and Next.js on `http://localhost:3000`. The browser client defaults `NEXT_PUBLIC_API_URL` to `http://localhost:8000`; set it explicitly if your API runs elsewhere.
```

with:

```md
The dev script starts FastAPI on `http://127.0.0.1:8000` and Next.js on `http://localhost:3000`. Keep `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` unless your API runs elsewhere.
```

- [x] **Step 7: Commit docs**

```bash
git add docs/superpowers/plans/2026-05-09-langgraph-mvp-roadmap.md README.md api/README.md web/README.md docs/superpowers/plans/2026-05-10-langgraph-mvp-12-roadmap-closure.md
git commit -m "docs: close MVP roadmap status"
```

---

### Task 2: Add Roadmap Closure Checks

**Files:**
- Modify: `scripts/check_launch_readiness.py`

- [x] **Step 1: Add path assertion helpers**

Add these helpers below `require_not_contains`:

```python
def require_path_exists(path: Path, failures: list[str], *, reason: str) -> None:
    if not path.exists():
        failures.append(f"{path}: missing ({reason})")


def require_path_not_exists(path: Path, failures: list[str], *, reason: str) -> None:
    if path.exists():
        failures.append(f"{path}: should not exist ({reason})")
```

- [x] **Step 2: Add roadmap/doc assertions**

Inside `check_docs`, define:

```python
    roadmap = ROOT / "docs/superpowers/plans/2026-05-09-langgraph-mvp-roadmap.md"
```

Then add these assertions near the existing docs checks:

```python
    require_contains(
        root_readme,
        "Plan 1-9 are complete; Plan 10-12 are post-roadmap hardening passes",
        failures,
        reason="root planning status",
    )
    require_not_contains(
        root_readme,
        "Plan 10 is the launch-readiness pass after Plan 9",
        failures,
        reason="stale planning status",
    )
    require_contains(
        api_readme,
        "post-roadmap hardening plans live beside it as Plan 10+",
        failures,
        reason="API planning status",
    )
    require_not_contains(
        api_readme,
        "2026-05-09-langgraph-single-city-mvp.md",
        failures,
        reason="old implementation plan pointer",
    )
    require_contains(
        web_readme,
        "fixture-backed API smoke",
        failures,
        reason="web regression docs",
    )
```

- [x] **Step 3: Add roadmap DoD assertions**

Add these assertions near the end of `check_docs`:

```python
    require_contains(
        roadmap,
        "**STATUS: COMPLETED (2026-05-10)**",
        failures,
        reason="roadmap closure status",
    )
    require_contains(
        roadmap,
        "- [x] Plan 1-9 全部 DoD 通过",
        failures,
        reason="roadmap DoD closure",
    )
    require_contains(
        roadmap,
        "`make regression` 跑通",
        failures,
        reason="current regression command",
    )
    require_not_contains(
        roadmap,
        "`npm run regression` 跑通",
        failures,
        reason="stale regression command",
    )
    require_path_not_exists(
        ROOT / "web/src/server",
        failures,
        reason="Plan 7 cutover removed server code",
    )
    require_path_exists(
        ROOT / "api/app/graph",
        failures,
        reason="LangGraph workflow package",
    )
```

- [x] **Step 4: Verify checker fails before docs commit only if docs are incomplete**

Run:

```bash
make launch-check
```

Expected after Task 1 + Task 2: `Launch readiness checks passed.`

- [x] **Step 5: Commit checker**

```bash
git add scripts/check_launch_readiness.py
git commit -m "chore: check roadmap closure status"
```

---

### Task 3: Full Acceptance

**Files:**
- No planned file changes unless verification finds drift.

- [x] **Step 1: Run full regression**

```bash
make regression
```

Expected: launch checker, generated type drift, frontend lint/unit/build/e2e, backend pytest/ruff, and API smoke all pass.

- [x] **Step 2: Verify repository state**

```bash
git status --short --branch
git diff --check origin/feature/mvp-web-app...HEAD
```

Expected: clean working tree and no whitespace errors.

- [x] **Step 3: Commit acceptance notes if the plan checklist changed**

```bash
git add docs/superpowers/plans/2026-05-10-langgraph-mvp-12-roadmap-closure.md
git commit -m "docs: record roadmap closure acceptance"
```

Expected: only checklist status changes are committed.

---

## Self-Review

- **Spec coverage:** Closes roadmap status, README handoff drift, Web regression wording, API plan pointer, and launch-check coverage for all of those.
- **No product scope creep:** No runtime API, graph, persistence, provider, or UI behavior changes.
- **Placeholder scan:** No placeholders remain.
- **Verification:** Requires `make launch-check` and `make regression` before acceptance.
