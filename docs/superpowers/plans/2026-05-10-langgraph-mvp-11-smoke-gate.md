# LangGraph MVP Plan 11 API Smoke Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the documented fixture-mode API smoke flow into a repeatable local gate that starts FastAPI, runs the canonical curl flow, and cleans up.

**Architecture:** Keep `api/scripts/smoke_curl.sh` as the pure request script. Add a wrapper script that owns process orchestration, fixture env, temporary persistence directories, readiness polling, and cleanup, then expose it as `make smoke` and include it in `make regression`.

**Tech Stack:** Bash, curl, uvicorn, GNU Make, existing FastAPI fixture mode.

---

## Context Notes

- Plan10 aligned launch docs and added `make launch-check`.
- The launch checklist still has a manual two-terminal smoke procedure; this plan makes that procedure one command.
- Use a non-default smoke port so this gate does not collide with a normal dev API on port `8000`.
- Keep the wrapper under `api/scripts/` because it is API-specific and calls the existing API smoke script.

## File Structure

- Modify `docs/superpowers/plans/2026-05-10-langgraph-mvp-11-smoke-gate.md`: this plan, committed before implementation.
- Create `api/scripts/run_fixture_smoke.sh`: starts FastAPI in fixture mode on `127.0.0.1:${SMOKE_PORT:-8767}`, waits for `/health`, runs `scripts/smoke_curl.sh`, then kills the server.
- Modify `Makefile`: add `smoke` target and run it in `regression` before Playwright e2e.
- Modify `scripts/check_launch_readiness.py`: require the new `smoke` target and smoke docs.
- Modify `README.md`: replace the two-terminal API smoke instructions with `make smoke`.
- Modify `api/README.md`: document `bash scripts/run_fixture_smoke.sh`.
- Modify `docs/mvp-launch-checklist.md`: document `make smoke`.
- Modify `docs/superpowers/plans/2026-05-10-langgraph-mvp-10-launch-readiness.md`: keep the prior launch plan's checker examples aligned with the new smoke target.

---

### Task 0: Commit Plan

**Files:**
- Modify: `docs/superpowers/plans/2026-05-10-langgraph-mvp-11-smoke-gate.md`

- [ ] **Step 1: Commit this implementation plan before code changes**

```bash
git add docs/superpowers/plans/2026-05-10-langgraph-mvp-11-smoke-gate.md
git commit -m "docs: add fixture smoke gate plan"
```

Expected: a docs-only commit containing this plan.

---

### Task 1: Add Fixture Smoke Runner

**Files:**
- Create: `api/scripts/run_fixture_smoke.sh`

- [ ] **Step 1: Create the smoke runner**

Create `api/scripts/run_fixture_smoke.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

SMOKE_HOST="${SMOKE_HOST:-127.0.0.1}"
SMOKE_PORT="${SMOKE_PORT:-8767}"
BASE_URL="${BASE_URL:-http://${SMOKE_HOST}:${SMOKE_PORT}}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ -n "${SMOKE_TMP_DIR:-}" ]]; then
  TMP_ROOT="$SMOKE_TMP_DIR"
  CLEAN_TMP=0
else
  TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/travel-planner-smoke.XXXXXX")"
  CLEAN_TMP=1
fi

SESSION_DATA_DIR="${SESSION_DATA_DIR:-$TMP_ROOT/sessions}"
METRICS_DATA_DIR="${METRICS_DATA_DIR:-$TMP_ROOT/metrics}"
LOG_FILE="$TMP_ROOT/uvicorn.log"

mkdir -p "$SESSION_DATA_DIR" "$METRICS_DATA_DIR"

api_pid=""
cleanup() {
  if [[ -n "$api_pid" ]]; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi
  if [[ "$CLEAN_TMP" == "1" ]]; then
    rm -rf "$TMP_ROOT"
  fi
}
trap cleanup EXIT INT TERM

cd "$API_DIR"
GEMINI_API_KEY="${GEMINI_API_KEY:-test-gemini}" \
TAVILY_API_KEY="${TAVILY_API_KEY:-test-tavily}" \
E2E_FIXTURE_MODE=1 \
SESSION_DATA_DIR="$SESSION_DATA_DIR" \
METRICS_DATA_DIR="$METRICS_DATA_DIR" \
uv run uvicorn main:app --host "$SMOKE_HOST" --port "$SMOKE_PORT" >"$LOG_FILE" 2>&1 &
api_pid=$!

ready=0
for _ in $(seq 1 60); do
  if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  if ! kill -0 "$api_pid" 2>/dev/null; then
    break
  fi
  sleep 0.5
done

if [[ "$ready" != "1" ]]; then
  echo "Smoke API did not become ready at $BASE_URL" >&2
  cat "$LOG_FILE" >&2 || true
  exit 1
fi

BASE_URL="$BASE_URL" PYTHON_BIN="$PYTHON_BIN" bash scripts/smoke_curl.sh
```

- [ ] **Step 2: Run the new runner**

Run:

```bash
cd api
bash scripts/run_fixture_smoke.sh
```

Expected: output starts with `Smoke flow passed for session_`.

- [ ] **Step 3: Verify temporary files are not written into `api/.data` by default**

Run:

```bash
git status --short api/.data
```

Expected: no output.

---

### Task 2: Wire Smoke Gate Into Make and Docs

**Files:**
- Modify: `Makefile`
- Modify: `scripts/check_launch_readiness.py`
- Modify: `README.md`
- Modify: `api/README.md`
- Modify: `docs/mvp-launch-checklist.md`
- Modify: `docs/superpowers/plans/2026-05-10-langgraph-mvp-10-launch-readiness.md`

- [ ] **Step 1: Add Makefile target**

Update `Makefile`:

```makefile
.PHONY: gen-types check-types launch-check smoke regression

gen-types:
	cd web && npm run gen:types

check-types:
	cd web && npm run check:types

launch-check:
	python3 scripts/check_launch_readiness.py

smoke:
	cd api && bash scripts/run_fixture_smoke.sh

regression:
	python3 scripts/check_launch_readiness.py
	cd web && npm run check:types
	git diff --exit-code api/dist/schema.json web/src/lib/generated/types.ts
	cd web && npm run lint
	cd web && npm run test
	cd web && npm run build
	cd api && uv run pytest -v
	cd api && uv run ruff check app tests scripts
	cd api && bash scripts/run_fixture_smoke.sh
	cd web && npm run test:e2e
```

- [ ] **Step 2: Strengthen launch readiness checker**

In `scripts/check_launch_readiness.py`, add checks:

```python
    require_contains(makefile, "smoke:", failures, reason="API smoke target")
    require_contains(
        makefile,
        "cd api && bash scripts/run_fixture_smoke.sh",
        failures,
        reason="API smoke target",
    )
    require_contains(root_readme, "make smoke", failures, reason="root API smoke")
    require_contains(
        api_readme,
        "bash scripts/run_fixture_smoke.sh",
        failures,
        reason="API smoke runner",
    )
    require_contains(
        launch_checklist,
        "make smoke",
        failures,
        reason="launch smoke gate",
    )
```

Place the `makefile` checks near the existing Makefile checks, and the doc checks near the existing README/checklist assertions.

- [ ] **Step 3: Update root README**

Replace the two-terminal smoke section in `README.md` with:

````md
## API Smoke

From the repo root:

```bash
make smoke
```

`make smoke` starts FastAPI in fixture mode on port `8767`, runs `api/scripts/smoke_curl.sh`, and cleans up the server process.
````

- [ ] **Step 4: Update API README**

Replace the smoke test section in `api/README.md` with:

````md
## Smoke Test

From `api/`, run the fixture-backed smoke gate:

```bash
bash scripts/run_fixture_smoke.sh
```

The runner starts FastAPI on `127.0.0.1:${SMOKE_PORT:-8767}`, uses temporary session and metrics directories, runs `scripts/smoke_curl.sh`, and cleans up the server process.
````

- [ ] **Step 5: Update launch checklist**

In `docs/mvp-launch-checklist.md`, replace the manual two-terminal API smoke instructions with:

````md
## API Smoke

From the repository root:

```bash
make smoke
```

Expected output starts with `Smoke flow passed for session_`.
````

- [ ] **Step 6: Update Plan10 checker examples**

Update `docs/superpowers/plans/2026-05-10-langgraph-mvp-10-launch-readiness.md` so its checker and README examples mention `make smoke` and `bash scripts/run_fixture_smoke.sh` instead of only direct `smoke_curl.sh` commands.

- [ ] **Step 7: Verify launch checker**

Run:

```bash
make launch-check
```

Expected: `Launch readiness checks passed.`

- [ ] **Step 8: Verify smoke gate through Makefile**

Run:

```bash
make smoke
```

Expected: output starts with `Smoke flow passed for session_`.

- [ ] **Step 9: Commit**

```bash
git add Makefile api/scripts/run_fixture_smoke.sh scripts/check_launch_readiness.py README.md api/README.md docs/mvp-launch-checklist.md docs/superpowers/plans/2026-05-10-langgraph-mvp-10-launch-readiness.md
git commit -m "chore: add fixture smoke gate"
```

---

### Task 3: Full Regression and Acceptance

**Files:**
- No planned file changes unless verification finds a regression.

- [ ] **Step 1: Run full regression**

Run:

```bash
make regression
```

Expected:

- launch readiness checker passes.
- generated type drift check is clean.
- frontend lint/unit/build pass.
- backend pytest and ruff pass.
- fixture API smoke prints `Smoke flow passed for session_`.
- Playwright e2e passes.

- [ ] **Step 2: Verify repository state**

Run:

```bash
git status --short
git diff --check origin/feature/mvp-web-app...HEAD
```

Expected: clean working tree and no whitespace errors.

- [ ] **Step 3: Commit acceptance fixes only if needed**

If verification required changes:

```bash
git add -A
git commit -m "fix: complete smoke gate acceptance"
```

---

## Self-Review

- **Spec coverage:** Converts manual fixture API smoke into `make smoke` and includes it in `make regression`.
- **No product scope creep:** Does not add new routes, providers, UI, persistence, or deployment behavior.
- **Placeholder scan:** No placeholder implementation steps remain.
- **Cleanup:** Smoke runner uses temp session/metrics directories and cleans up the uvicorn process.
