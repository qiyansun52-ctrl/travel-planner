# LangGraph MVP Plan 10 Launch Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the migrated MVP easy to run, verify, and hand off by aligning environment examples, launch docs, and root verification gates.

**Architecture:** Keep product code unchanged unless verification exposes a real defect. Add a small root launch-readiness checker that validates docs and env examples, then wire it into `make regression` so future Plan 1-9 drift is caught automatically.

**Tech Stack:** Python stdlib script, GNU Make, Markdown docs, existing FastAPI/Next.js regression commands.

---

## Context Notes

- The original roadmap ends at Plan 9. Plan 10 is the post-roadmap launch readiness pass before pushing or demoing.
- Current canonical runtime is Python FastAPI plus Next.js UI shell; there are no Next.js API routes or server agents left.
- `make regression` already runs generated type checks, frontend lint/unit/build/e2e, backend pytest, backend ruff, and generated output drift checks.
- `web/.env.example` currently still lists provider secrets that belong in `api/.env.example`.
- `api/README.md` still contains stale language about remaining Next.js compatibility endpoints.

## File Structure

- Create `scripts/check_launch_readiness.py`: root validation script for env examples, docs, Makefile, and stale text.
- Modify `Makefile`: add `launch-check` and run it inside `regression`.
- Modify `api/.env.example`: include backend-owned live provider, persistence, metric, fixture, and server env keys.
- Modify `web/.env.example`: keep only frontend-owned public API URL.
- Modify `README.md`: add setup, regression, smoke, and fixture-mode launch instructions.
- Modify `api/README.md`: remove stale Next.js compatibility language and add current regression/lint instructions.
- Modify `web/README.md`: add `.env.local` guidance that matches the web-only env surface.
- Modify `web/docs/development-environment.md`: remove stale frontend provider-key setup.
- Modify `docs/mvp-launch-checklist.md`: align verification and known env setup with Plan 9/10.

---

### Task 1: Add Launch Readiness Checker

**Files:**
- Create: `scripts/check_launch_readiness.py`
- Modify: `Makefile`

- [ ] **Step 1: Create the checker script**

Create `scripts/check_launch_readiness.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

API_ENV_REQUIRED = {
    "GEMINI_API_KEY",
    "TAVILY_API_KEY",
    "GEMINI_MODEL",
    "AMAP_API_KEY",
    "MAPBOX_ACCESS_TOKEN",
    "SESSION_DATA_DIR",
    "METRICS_DATA_DIR",
    "CORS_ORIGINS",
    "E2E_FIXTURE_MODE",
    "HOST",
    "PORT",
}

WEB_ENV_REQUIRED = {"NEXT_PUBLIC_API_URL"}

WEB_ENV_FORBIDDEN = {
    "GEMINI_API_KEY",
    "TAVILY_API_KEY",
    "LLM_PROVIDER_API_KEY",
    "SEARCH_PROVIDER_API_KEY",
    "AMAP_API_KEY",
    "MAPBOX_ACCESS_TOKEN",
    "WEATHER_PROVIDER_API_KEY",
}


def parse_env_keys(path: Path, failures: list[str]) -> set[str]:
    keys: set[str] = set()
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            failures.append(f"{path}: line {line_number} must be KEY=value")
            continue
        keys.add(stripped.split("=", 1)[0])
    return keys


def require_contains(
    path: Path,
    needle: str,
    failures: list[str],
    *,
    reason: str,
) -> None:
    text = path.read_text()
    if needle not in text:
        failures.append(f"{path}: missing {needle!r} ({reason})")


def require_not_contains(
    path: Path,
    needle: str,
    failures: list[str],
    *,
    reason: str,
) -> None:
    text = path.read_text()
    if needle in text:
        failures.append(f"{path}: remove stale {needle!r} ({reason})")


def check_env_examples(failures: list[str]) -> None:
    api_keys = parse_env_keys(ROOT / "api/.env.example", failures)
    web_keys = parse_env_keys(ROOT / "web/.env.example", failures)

    missing_api = sorted(API_ENV_REQUIRED - api_keys)
    if missing_api:
        failures.append(f"api/.env.example missing keys: {', '.join(missing_api)}")

    missing_web = sorted(WEB_ENV_REQUIRED - web_keys)
    if missing_web:
        failures.append(f"web/.env.example missing keys: {', '.join(missing_web)}")

    forbidden_web = sorted(WEB_ENV_FORBIDDEN & web_keys)
    if forbidden_web:
        failures.append(
            "web/.env.example contains backend-only secrets: "
            + ", ".join(forbidden_web)
        )


def check_docs(failures: list[str]) -> None:
    root_readme = ROOT / "README.md"
    api_readme = ROOT / "api/README.md"
    web_readme = ROOT / "web/README.md"
    web_dev_doc = ROOT / "web/docs/development-environment.md"
    launch_checklist = ROOT / "docs/mvp-launch-checklist.md"
    makefile = ROOT / "Makefile"

    require_contains(root_readme, "api/.env.example", failures, reason="root setup")
    require_contains(root_readme, "web/.env.example", failures, reason="root setup")
    require_contains(root_readme, "make regression", failures, reason="root verification")
    require_contains(root_readme, "api/scripts/smoke_curl.sh", failures, reason="API smoke")

    require_contains(api_readme, "There are no Next.js API routes", failures, reason="cutover")
    require_not_contains(
        api_readme,
        "remaining Next.js endpoints are compatibility surfaces",
        failures,
        reason="Plan 7 cutover is complete",
    )

    require_contains(
        web_readme,
        "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000",
        failures,
        reason="web env",
    )
    require_contains(web_readme, "cd ..\nmake regression", failures, reason="root Makefile")
    require_contains(
        web_dev_doc,
        "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000",
        failures,
        reason="web development env",
    )
    for key in sorted(WEB_ENV_FORBIDDEN):
        require_not_contains(
            web_dev_doc,
            key,
            failures,
            reason="backend-only env does not belong in web docs",
        )

    require_contains(launch_checklist, "make regression", failures, reason="launch gate")
    require_contains(
        launch_checklist,
        "api/scripts/smoke_curl.sh",
        failures,
        reason="root API smoke",
    )
    require_not_contains(
        launch_checklist,
        "WEATHER_PROVIDER_API_KEY",
        failures,
        reason="weather provider is an explicit MVP unavailable fallback",
    )
    require_contains(
        launch_checklist,
        "E2E_FIXTURE_MODE=1",
        failures,
        reason="offline flow",
    )
    require_contains(
        launch_checklist,
        "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000",
        failures,
        reason="frontend API target",
    )

    require_contains(makefile, "launch-check:", failures, reason="launch gate target")
    require_contains(
        makefile,
        "git diff --exit-code api/dist/schema.json web/src/lib/generated/types.ts",
        failures,
        reason="generated drift gate",
    )


def main() -> int:
    failures: list[str] = []
    check_env_examples(failures)
    check_docs(failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("Launch readiness checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Wire the checker into Makefile**

Update `Makefile` to include `launch-check` and run it at the start of `regression`:

```makefile
.PHONY: gen-types check-types launch-check regression

gen-types:
	cd web && npm run gen:types

check-types:
	cd web && npm run check:types

launch-check:
	python3 scripts/check_launch_readiness.py

regression:
	python3 scripts/check_launch_readiness.py
	cd web && npm run check:types
	git diff --exit-code api/dist/schema.json web/src/lib/generated/types.ts
	cd web && npm run lint
	cd web && npm run test
	cd web && npm run build
	cd api && uv run pytest -v
	cd api && uv run ruff check app tests scripts
	cd web && npm run test:e2e
```

- [ ] **Step 3: Run the checker to verify current docs/env drift is caught**

Run:

```bash
make launch-check
```

Expected before Task 2: FAIL with missing/stale launch readiness messages.

- [ ] **Step 4: Commit only if Task 2 will be separate**

Do not commit a failing checker by itself unless the implementation worker intentionally splits the work. Prefer committing Task 1 and Task 2 together after the checker passes.

---

### Task 2: Align Env Examples and Launch Docs

**Files:**
- Modify: `api/.env.example`
- Modify: `web/.env.example`
- Modify: `README.md`
- Modify: `api/README.md`
- Modify: `web/README.md`
- Modify: `docs/mvp-launch-checklist.md`

- [ ] **Step 1: Replace API env example with backend-owned keys**

Set `api/.env.example` to:

```dotenv
GEMINI_API_KEY=
TAVILY_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
AMAP_API_KEY=
MAPBOX_ACCESS_TOKEN=
SESSION_DATA_DIR=.data
METRICS_DATA_DIR=.data
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
E2E_FIXTURE_MODE=0
HOST=0.0.0.0
PORT=8000
```

- [ ] **Step 2: Replace web env example with frontend-owned key**

Set `web/.env.example` to:

```dotenv
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

- [ ] **Step 3: Update root README**

Rewrite `README.md` so it includes these sections and commands:

````md
# Travel Planner

Single-city travel planning MVP. The target product flow is:

```text
/ -> /discovery/[sessionId] -> /preferences/[sessionId] -> /trips/[sessionId]
```

## Architecture

- `web/`: Next.js UI and route shell only.
- `api/`: FastAPI backend that owns Pydantic schemas, sessions, LangGraph planning workflow, provider adapters, metrics, and cost logs.
- LLM/search stack: `google-genai` with Gemini 2.5 flash, plus Tavily/provider adapters.

`web/src/app/api/`, `web/src/server/`, and `web/src/domain/` are gone. The browser client calls the Python API routes directly through `NEXT_PUBLIC_API_URL`.

## Environment

```bash
cp api/.env.example api/.env
cp web/.env.example web/.env.local
```

Live provider-backed runs need real keys in `api/.env`. Fixture-backed regression uses dummy keys and `E2E_FIXTURE_MODE=1`.

## Development

Run both services from the web workspace:

```bash
cd web
npm run dev
```

Open `http://localhost:3000`.

Run the API by itself:

```bash
cd api
uv run uvicorn main:app --reload --port 8000
```

## Verification

From the repo root:

```bash
make launch-check
make regression
```

`make regression` runs launch docs/env checks, generated-type drift checks, frontend lint/unit/build/e2e, backend pytest, and backend ruff.

## API Smoke

In one terminal:

```bash
cd api
E2E_FIXTURE_MODE=1 GEMINI_API_KEY=test-gemini TAVILY_API_KEY=test-tavily uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

In another terminal, from the repository root:

```bash
BASE_URL=http://127.0.0.1:8000 bash api/scripts/smoke_curl.sh
```

Expected output starts with `Smoke flow passed for session_`.

## Planning Docs

The active migration roadmap is `docs/superpowers/plans/2026-05-09-langgraph-mvp-roadmap.md`; Plan 10 is the launch-readiness pass after Plan 9.
````

- [ ] **Step 4: Update API README stale cutover language**

In `api/README.md`, replace the stale paragraph:

```md
Legacy scaffold endpoints `/api/discover` and `/api/plan/generate` have been removed from the Python app. The remaining Next.js endpoints are compatibility surfaces until the web cutover plan points the UI directly at these canonical FastAPI routes.
```

with:

```md
Legacy scaffold endpoints `/api/discover` and `/api/plan/generate` have been removed from the Python app. There are no Next.js API routes in the canonical product flow after the web cutover; the browser calls these FastAPI routes directly.
```

Also update the Tests section to:

````md
## Tests

```bash
uv run pytest -v
uv run ruff check app tests scripts
```

From the repository root, `make regression` runs the full web + API gate.
````

- [ ] **Step 5: Update web README env guidance**

In `web/README.md`, add this under `## Development` before the install/dev commands:

````md
Create the local frontend env file:

```bash
cp .env.example .env.local
```

`NEXT_PUBLIC_API_URL` should point at the FastAPI service, normally `http://127.0.0.1:8000`.
````

- [ ] **Step 6: Update launch checklist**

Update `docs/mvp-launch-checklist.md` so:

- Environment setup says `api/.env` owns provider keys and `web/.env.local` owns only `NEXT_PUBLIC_API_URL`.
- Verification section starts with:

```bash
make launch-check
make regression
```

- API smoke section includes `BASE_URL=http://127.0.0.1:8000 bash api/scripts/smoke_curl.sh`.
- Offline fixture note explicitly names `E2E_FIXTURE_MODE=1`.

- [ ] **Step 7: Verify launch checker passes**

Run:

```bash
make launch-check
```

Expected: `Launch readiness checks passed.`

- [ ] **Step 8: Commit**

```bash
git add Makefile scripts/check_launch_readiness.py api/.env.example web/.env.example README.md api/README.md web/README.md docs/mvp-launch-checklist.md
git commit -m "docs: add launch readiness gate"
```

---

### Task 3: Full Regression and Acceptance

**Files:**
- No planned file changes unless verification finds a regression.

- [ ] **Step 1: Run full regression**

Run from repo root:

```bash
make regression
```

Expected:

- launch readiness checker passes.
- generated type drift check is clean.
- frontend lint/unit/build/e2e pass.
- backend pytest and ruff pass.

- [ ] **Step 2: Verify generated outputs remain clean**

Run:

```bash
git diff --exit-code api/dist/schema.json web/src/lib/generated/types.ts
```

Expected: no diff.

- [ ] **Step 3: Verify repository state**

Run:

```bash
git status --short
git diff --check origin/feature/mvp-web-app...HEAD
```

Expected: clean working tree and no whitespace errors.

- [ ] **Step 4: Commit acceptance fixes only if needed**

If verification required changes:

```bash
git add -A
git commit -m "fix: complete launch readiness acceptance"
```

---

## Self-Review

- **Spec coverage:** Covers post-roadmap launch readiness gaps: env examples, stale docs, root verification discovery, smoke instructions, and regression drift checks.
- **No product scope creep:** Does not add booking, live inventory, auth, deployment, SQLite, or new UI flows.
- **Placeholder scan:** No placeholder implementation steps remain.
- **Type consistency:** Script uses only Python stdlib and validates exact current env/doc surfaces.
