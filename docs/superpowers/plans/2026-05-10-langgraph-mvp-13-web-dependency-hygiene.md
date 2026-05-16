# LangGraph MVP Plan 13 Web Dependency Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove stale backend-era dependencies from the Next.js UI package, delete unused Jest config, align the web default API origin with local docs, and prevent those dependencies from drifting back.

**Architecture:** Keep product behavior unchanged. The web package remains a pure UI shell using Vitest and Playwright; Python owns LLM/provider/schema logic. Dependency removal is performed through npm so `package.json` and `package-lock.json` stay consistent, then `scripts/check_launch_readiness.py` asserts that forbidden backend dependencies and stale Jest config are absent.

**Tech Stack:** npm, Next.js, Vitest, Playwright, Python stdlib launch checker.

---

## Context Notes

- After Plan 7 cutover, `web/src/server/` is gone and the browser talks directly to FastAPI.
- `web/package.json` still lists unused backend-era runtime dependencies: `@anthropic-ai/sdk`, `@google/generative-ai`, and `zod`.
- Web tests now use Vitest, but `jest`, `ts-jest`, `jest-environment-jsdom`, `@types/jest`, and `web/jest.config.ts` remain.
- Docs and `.env.example` use `http://127.0.0.1:8000`, while `web/src/lib/apiClient.ts` and `web/next.config.ts` still default to `http://localhost:8000`.

## File Structure

- Create `docs/superpowers/plans/2026-05-10-langgraph-mvp-13-web-dependency-hygiene.md`: this plan, committed before implementation.
- Modify `web/package.json`: remove unused runtime/dev dependencies.
- Modify `web/package-lock.json`: let npm update lock metadata.
- Delete `web/jest.config.ts`: obsolete after Vitest migration.
- Modify `web/src/lib/apiClient.ts`: default API URL becomes `http://127.0.0.1:8000`.
- Modify `web/src/lib/apiClient.test.ts`: update default URL expectations.
- Modify `web/next.config.ts`: default rewrite target becomes `http://127.0.0.1:8000`.
- Modify `scripts/check_launch_readiness.py`: parse `web/package.json` and assert forbidden web dependencies/config are absent.

---

### Task 0: Commit Plan

**Files:**
- Create: `docs/superpowers/plans/2026-05-10-langgraph-mvp-13-web-dependency-hygiene.md`

- [x] **Step 1: Commit this plan before implementation**

```bash
git add docs/superpowers/plans/2026-05-10-langgraph-mvp-13-web-dependency-hygiene.md
git commit -m "docs: add web dependency hygiene plan"
```

Expected: a docs-only commit containing this plan.

---

### Task 1: Remove Stale Web Dependencies

**Files:**
- Modify: `web/package.json`
- Modify: `web/package-lock.json`
- Delete: `web/jest.config.ts`

- [x] **Step 1: Confirm no source imports rely on removed packages**

Run:

```bash
rg -n "from ['\"](zod|@anthropic-ai/sdk|@google/generative-ai)|require\\(['\"](zod|@anthropic-ai/sdk|@google/generative-ai)" web/src web/e2e web/*.ts web/*.mjs
```

Expected: no output.

- [x] **Step 2: Remove stale npm packages**

Run from `web/`:

```bash
npm uninstall @anthropic-ai/sdk @google/generative-ai zod jest @types/jest jest-environment-jsdom ts-jest
```

Expected: `web/package.json` no longer contains those package names and `web/package-lock.json` is updated.

- [x] **Step 3: Delete obsolete Jest config**

Delete `web/jest.config.ts`.

- [x] **Step 4: Verify remaining test stack is Vitest**

Run:

```bash
rg -n "jest|ts-jest|jest-environment-jsdom|@types/jest" web/package.json web/jest.config.ts web/src web/vitest.config.ts
```

Expected: either no output or only `@testing-library/jest-dom/vitest`, which is still required by Vitest setup.

- [x] **Step 5: Run focused web checks**

Run from `web/`:

```bash
npm run test
npm run build
```

Expected: Vitest and Next build pass after dependency removal.

- [x] **Step 6: Commit dependency cleanup**

```bash
git add web/package.json web/package-lock.json web/jest.config.ts
git commit -m "chore(web): remove stale backend dependencies"
```

---

### Task 2: Align Default Web API Origin

**Files:**
- Modify: `web/src/lib/apiClient.ts`
- Modify: `web/src/lib/apiClient.test.ts`
- Modify: `web/next.config.ts`

- [x] **Step 1: Update API client default**

In `web/src/lib/apiClient.ts`, replace:

```ts
const DEFAULT_API_URL = "http://localhost:8000"
```

with:

```ts
const DEFAULT_API_URL = "http://127.0.0.1:8000"
```

- [x] **Step 2: Update Next rewrite default**

In `web/next.config.ts`, replace:

```ts
const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "")
```

with:

```ts
const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "")
```

- [x] **Step 3: Update API client tests**

Replace every expected `http://localhost:8000/...` in `web/src/lib/apiClient.test.ts` with `http://127.0.0.1:8000/...`.

- [x] **Step 4: Run API client tests**

Run from `web/`:

```bash
npm run test -- src/lib/apiClient.test.ts
```

Expected: API client tests pass with the new default origin.

- [x] **Step 5: Commit default origin alignment**

```bash
git add web/src/lib/apiClient.ts web/src/lib/apiClient.test.ts web/next.config.ts
git commit -m "fix(web): align default API origin"
```

---

### Task 3: Add Launch Checks and Acceptance

**Files:**
- Modify: `scripts/check_launch_readiness.py`
- Modify: `docs/superpowers/plans/2026-05-10-langgraph-mvp-13-web-dependency-hygiene.md`

- [x] **Step 1: Import JSON support**

Add this import near the top of `scripts/check_launch_readiness.py`:

```python
import json
```

- [x] **Step 2: Add forbidden web package set**

Add this constant below `WEB_ENV_FORBIDDEN`:

```python
WEB_PACKAGE_FORBIDDEN = {
    "@anthropic-ai/sdk",
    "@google/generative-ai",
    "zod",
    "jest",
    "@types/jest",
    "jest-environment-jsdom",
    "ts-jest",
}
```

- [x] **Step 3: Add package checker**

Add this function after `check_env_examples`:

```python
def check_web_package(failures: list[str]) -> None:
    package_json = json.loads((ROOT / "web/package.json").read_text())
    package_names = set(package_json.get("dependencies", {})) | set(
        package_json.get("devDependencies", {})
    )
    forbidden = sorted(WEB_PACKAGE_FORBIDDEN & package_names)
    if forbidden:
        failures.append(
            "web/package.json contains stale backend/test dependencies: "
            + ", ".join(forbidden)
        )
```

Call `check_web_package(failures)` from `main()` between env and docs checks.

- [x] **Step 4: Add docs/config assertions**

Inside `check_docs`, add:

```python
    require_path_not_exists(
        ROOT / "web/jest.config.ts",
        failures,
        reason="Vitest is the canonical web unit test runner",
    )
    require_contains(
        ROOT / "web/src/lib/apiClient.ts",
        'const DEFAULT_API_URL = "http://127.0.0.1:8000"',
        failures,
        reason="web API default origin",
    )
    require_contains(
        ROOT / "web/next.config.ts",
        "http://127.0.0.1:8000",
        failures,
        reason="Next rewrite default origin",
    )
```

- [x] **Step 5: Run launch checker**

Run:

```bash
make launch-check
```

Expected: `Launch readiness checks passed.`

- [x] **Step 6: Run full regression**

Run:

```bash
make regression
```

Expected: launch checker, generated type drift, frontend lint/unit/build/e2e, backend pytest/ruff, and API smoke all pass.

- [x] **Step 7: Verify repository state**

Run:

```bash
git status --short --branch
git diff --check origin/feature/mvp-web-app...HEAD
```

Expected: clean working tree except the Plan13 acceptance checklist before the final commit; no whitespace errors.

- [x] **Step 8: Commit checker and acceptance**

```bash
git add scripts/check_launch_readiness.py docs/superpowers/plans/2026-05-10-langgraph-mvp-13-web-dependency-hygiene.md
git commit -m "chore: guard web dependency hygiene"
```

---

## Self-Review

- **Spec coverage:** Removes stale web backend/Jest dependencies, deletes obsolete Jest config, aligns API defaults, and adds launch-check guards.
- **No product scope creep:** Does not change routes, UI copy, backend graph behavior, provider behavior, or API schemas.
- **Placeholder scan:** No placeholder steps remain.
- **Verification:** Requires focused web checks, `make launch-check`, and full `make regression`.
