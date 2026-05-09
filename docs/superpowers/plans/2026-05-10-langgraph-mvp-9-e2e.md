# LangGraph MVP Plan 9 E2E Regression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a deterministic offline regression suite covering happy path, budget overrun, and Type B adjustment.

**Architecture:** Playwright drives the real Next.js UI against FastAPI running in `E2E_FIXTURE_MODE=1`. API fixtures live in explicit modules so route, graph, and browser tests share the same offline assumptions. A root `make regression` target runs the whole local CI gate.

**Tech Stack:** Playwright, Next.js dev server, FastAPI fixture mode, pytest/httpx ASGI integration tests, GNU Make.

---

## Context Notes

- Existing coverage already includes `web/playwright.config.ts`, `web/e2e/home.spec.ts`, and `web/e2e/mvp-flow.spec.ts`.
- Plan9 still needs two additional browser paths: budget overrun and Type B adjustment.
- `E2E_FIXTURE_MODE=1` is already honored by the discovery route; this plan adds explicit fixture modules and documents the mode.
- `make regression` may need normal local process privileges because Next/Turbopack and Playwright start local servers.

## File Structure

- Create `api/app/llm/fixtures.py`: central fixture-mode helper and dummy provider key constants for offline runs.
- Create `api/app/providers/fixtures.py`: deterministic provider fixture helpers for source notes and normalized places.
- Modify `api/app/routes/_shared.py`: use the shared `fixture_mode_enabled()`.
- Modify `api/app/graph/nodes/discovery.py`: use provider fixture helpers for fixture source notes and places.
- Create `api/tests/integration/test_full_workflow.py`: route-level full workflow with fixture mode, including Type B adjustment.
- Create `web/e2e/helpers/mvpFlow.ts`: reusable browser flow helper.
- Modify `web/e2e/mvp-flow.spec.ts`: use the helper.
- Create `web/e2e/budget-overrun.spec.ts`: low budget path asserts warnings and final budget issue.
- Create `web/e2e/type-b-adjustment.spec.ts`: stay adjustment path asserts Type B update.
- Create `web/e2e/fixtures/README.md`: explain that browser fixtures are served by the Python fixture backend.
- Modify `Makefile`: add `regression`.
- Modify `web/README.md`: document offline fixture/e2e/regression commands.

---

### Task 1: Centralize Fixture Helpers

**Files:**
- Create: `api/app/llm/fixtures.py`
- Create: `api/app/providers/fixtures.py`
- Modify: `api/app/routes/_shared.py`
- Modify: `api/app/graph/nodes/discovery.py`
- Test: `api/tests/integration/test_full_workflow.py`

- [ ] **Step 1: Add API integration test skeleton**

Create `api/tests/integration/test_full_workflow.py`:

```python
from __future__ import annotations

import importlib

import httpx
import pytest


@pytest.fixture(autouse=True)
def fixture_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily")
    monkeypatch.setenv("E2E_FIXTURE_MODE", "1")
    monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("METRICS_DATA_DIR", str(tmp_path / "metrics"))
    import app.config as config

    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.fixture
async def client():
    import main

    importlib.reload(main)
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as api:
        yield api


async def create_planned_session(client: httpx.AsyncClient, *, total_budget: int = 6000) -> str:
    created = await client.post(
        "/api/sessions",
        json={
            "departure_city": "北京",
            "destination_city": "上海",
            "destination_country_code": "CN",
            "departure_date": "2026-05-10",
            "duration_days": 3,
            "traveler_count": 2,
            "total_budget": total_budget,
            "currency": "CNY",
        },
    )
    assert created.status_code == 201
    session_id = created.json()["session_id"]

    discovery = await client.post(f"/api/sessions/{session_id}/discovery")
    assert discovery.status_code == 200
    selected = [card["id"] for card in discovery.json()["discovery_state"]["payload"]["cards"][:3]]
    selection = await client.patch(
        f"/api/sessions/{session_id}/selection",
        json={"selected_card_ids": selected},
    )
    assert selection.status_code == 200
    preferences = await client.post(
        f"/api/sessions/{session_id}/preferences",
        json={
            "preferences": {
                "area_vibe": "central, walkable, good food nearby",
                "quiet_vs_lively": "balanced",
                "stay_type": "hotel",
                "willing_to_change_hotels": False,
                "intercity_transport_preference": "rail",
                "early_departure_tolerance": "medium",
                "transfer_tolerance": "medium",
                "pay_more_to_save_time": False,
            }
        },
    )
    assert preferences.status_code == 200
    itinerary = await client.post(f"/api/sessions/{session_id}/itinerary", json={})
    assert itinerary.status_code == 200
    assert itinerary.json()["itinerary"]["days"]
    return session_id


async def test_fixture_full_workflow_happy_path(client: httpx.AsyncClient) -> None:
    session_id = await create_planned_session(client)

    loaded = await client.get(f"/api/sessions/{session_id}")

    assert loaded.status_code == 200
    assert loaded.json()["itinerary"]["budget"]["total"]["high"] > 0


async def test_fixture_workflow_surfaces_budget_overrun(client: httpx.AsyncClient) -> None:
    session_id = await create_planned_session(client, total_budget=500)

    loaded = await client.get(f"/api/sessions/{session_id}")

    assert loaded.status_code == 200
    assert any(
        issue["code"] == "budget_overrun"
        for issue in loaded.json()["itinerary"]["validator_issues"]
    )


async def test_fixture_workflow_type_b_stay_adjustment(client: httpx.AsyncClient) -> None:
    session_id = await create_planned_session(client)

    adjusted = await client.post(
        f"/api/sessions/{session_id}/adjustments",
        json={"message": "酒店换到更安静的区域"},
    )

    assert adjusted.status_code == 200
    body = adjusted.json()
    assert body["classification"]["type"] == "B"
    assert body["classification"]["target_scope"] == "stay"
    assert body["message"] == "Itinerary updated."
```

- [ ] **Step 2: Run the focused integration test to verify current baseline**

Run:

```bash
cd api
uv run pytest tests/integration/test_full_workflow.py -v
```

Expected: PASS or fail only for fixture-module imports not yet added. If it passes, keep it as regression coverage.

- [ ] **Step 3: Add `api/app/llm/fixtures.py`**

```python
from __future__ import annotations

import os

FIXTURE_GEMINI_API_KEY = "test-gemini"
FIXTURE_TAVILY_API_KEY = "test-tavily"


def fixture_mode_enabled() -> bool:
    return os.environ.get("E2E_FIXTURE_MODE") == "1"
```

- [ ] **Step 4: Add `api/app/providers/fixtures.py`**

```python
from __future__ import annotations

from app.models.schemas import Coordinate, NormalizedPlace, SourceNote


def fixture_provider_for_country(country_code: str) -> str:
    return "amap" if country_code == "CN" else "mapbox"


def fixture_place(id_suffix: str, name: str, provider: str) -> NormalizedPlace:
    offset = len(id_suffix) / 1000
    return NormalizedPlace(
        id=f"place_{id_suffix}",
        name=name,
        coordinate=Coordinate(lat=31.23 + offset, lng=121.47 + offset),
        address=name,
        category="poi",
        provider=provider,
    )


def fixture_source_note() -> SourceNote:
    return SourceNote(
        provider="fixture",
        url=None,
        note="Fixture-backed MVP discovery; live enrichment uses configured providers.",
    )
```

- [ ] **Step 5: Wire helpers into existing code**

In `api/app/routes/_shared.py`:

```python
from app.llm.fixtures import fixture_mode_enabled
```

Remove the local `fixture_mode_enabled()` definition.

In `api/app/graph/nodes/discovery.py`, import:

```python
from app.providers.fixtures import (
    fixture_place,
    fixture_provider_for_country,
    fixture_source_note,
)
```

Use:

```python
provider = fixture_provider_for_country(constraints.destination_country_code)
place=fixture_place("waterfront", f"{city} waterfront", provider)
source_notes=[fixture_source_note()]
```

Remove the private `_place()` helper after replacing all calls.

- [ ] **Step 6: Verify API fixture coverage**

Run:

```bash
cd api
uv run pytest tests/integration/test_full_workflow.py tests/routes tests/graph -v
uv run ruff check app tests scripts
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add api/app/llm/fixtures.py api/app/providers/fixtures.py api/app/routes/_shared.py api/app/graph/nodes/discovery.py api/tests/integration/test_full_workflow.py
git commit -m "feat(api): add fixture-backed integration baseline"
```

---

### Task 2: Add Browser Critical Paths

**Files:**
- Create: `web/e2e/helpers/mvpFlow.ts`
- Modify: `web/e2e/mvp-flow.spec.ts`
- Create: `web/e2e/budget-overrun.spec.ts`
- Create: `web/e2e/type-b-adjustment.spec.ts`
- Create: `web/e2e/fixtures/README.md`

- [ ] **Step 1: Extract browser flow helper**

Create `web/e2e/helpers/mvpFlow.ts`:

```ts
import { expect, type Page } from "@playwright/test"

export async function startFixtureTrip(page: Page, totalBudget = "6000") {
  await page.goto("/")
  await page.getByLabel("Departure city").fill("北京")
  await page.getByLabel("Destination city").fill("上海")
  await page.getByLabel("Departure date").fill("2026-05-10")
  await page.getByLabel("Trip duration").fill("3")
  await page.getByLabel("Traveler count").fill("2")
  await page.getByLabel("Total trip budget").fill(totalBudget)
  await page.getByRole("button", { name: "Start discovering ideas" }).click()
  await expect(page).toHaveURL(/\/discovery\/session_/)
  await expect(page.getByRole("heading", { name: /Choose what feels worth it/ })).toBeVisible()
}

export async function selectDiscoveryCards(page: Page) {
  await page.getByRole("button", { name: /Select .* waterfront walk/ }).click()
  await page.getByRole("button", { name: /Select .* old town lanes/ }).click()
  await page.getByRole("button", { name: /Select .* city museum/ }).click()
  await page.getByRole("button", { name: "Continue to preferences" }).click()
  await expect(page).toHaveURL(/\/preferences\/session_/)
}

export async function submitPreferences(page: Page) {
  await page.getByLabel("Area vibe").fill("central, walkable, good food nearby")
  await page.getByLabel("Stay type").selectOption("homestay")
  await page.getByRole("button", { name: "Generate itinerary" }).click()
  await expect(page).toHaveURL(/\/trips\/session_/)
  await expect(page.getByRole("heading", { name: /Your .* itinerary/ })).toBeVisible()
  await expect(page.getByText("Final budget")).toBeVisible()
}

export async function completeFixtureTrip(page: Page, totalBudget = "6000") {
  await startFixtureTrip(page, totalBudget)
  await selectDiscoveryCards(page)
  await submitPreferences(page)
}
```

- [ ] **Step 2: Refactor happy path spec**

Change `web/e2e/mvp-flow.spec.ts`:

```ts
import { expect, test } from "@playwright/test"
import { completeFixtureTrip } from "./helpers/mvpFlow"

test("completes the fixture-backed MVP flow", async ({ page }) => {
  await completeFixtureTrip(page)

  await page.getByLabel("Adjustment request").fill("把第二天下午改轻松一点")
  await page.getByRole("button", { name: "Send adjustment" }).click()
  await expect(page.getByText(/Itinerary updated/)).toBeVisible()
})
```

- [ ] **Step 3: Add budget overrun spec**

Create `web/e2e/budget-overrun.spec.ts`:

```ts
import { expect, test } from "@playwright/test"
import { selectDiscoveryCards, startFixtureTrip, submitPreferences } from "./helpers/mvpFlow"

test("surfaces budget overrun in fixture mode", async ({ page }) => {
  await startFixtureTrip(page, "500")
  await expect(page.getByText(/Budget warning/)).toBeVisible()
  await selectDiscoveryCards(page)
  await submitPreferences(page)
  await expect(page.getByText(/budget_overrun/).first()).toBeVisible()
})
```

- [ ] **Step 4: Add Type B adjustment spec**

Create `web/e2e/type-b-adjustment.spec.ts`:

```ts
import { expect, test } from "@playwright/test"
import { completeFixtureTrip } from "./helpers/mvpFlow"

test("replans after a Type B stay adjustment", async ({ page }) => {
  await completeFixtureTrip(page)

  await page.getByLabel("Adjustment request").fill("酒店换到更安静的区域")
  await page.getByRole("button", { name: "Send adjustment" }).click()

  await expect(page.getByText(/Itinerary updated/)).toBeVisible()
  await expect(page.getByText("Stay area")).toBeVisible()
})
```

- [ ] **Step 5: Document fixture source**

Create `web/e2e/fixtures/README.md`:

```md
# E2E Fixtures

Playwright does not mock browser network responses directly. It starts the real FastAPI app with `E2E_FIXTURE_MODE=1`, and the Python backend serves deterministic fixture data from `api/app/*/fixtures.py`.
```

- [ ] **Step 6: Verify browser paths**

Run:

```bash
cd web
npm run test:e2e
```

Expected: four specs pass: home, happy, budget overrun, Type B adjustment.

- [ ] **Step 7: Commit**

```bash
git add web/e2e
git commit -m "test(web): add fixture e2e critical paths"
```

---

### Task 3: Add Regression Gate and Docs

**Files:**
- Modify: `Makefile`
- Modify: `web/README.md`

- [ ] **Step 1: Add root regression target**

Modify `Makefile`:

```makefile
.PHONY: gen-types check-types regression

gen-types:
	cd web && npm run gen:types

check-types:
	cd web && npm run check:types

regression:
	cd web && npm run check:types
	cd web && npm run lint
	cd web && npm run test
	cd web && npm run build
	cd api && uv run pytest -v
	cd api && uv run ruff check app tests scripts
	cd web && npm run test:e2e
```

- [ ] **Step 2: Document offline regression**

Add to `web/README.md`:

```md
## Offline Regression

```bash
make regression
```

The regression target runs generated-type drift checks, frontend lint/unit/build/e2e, and backend pytest/ruff. Playwright starts FastAPI with `E2E_FIXTURE_MODE=1`, dummy provider keys, temp session storage, and CORS configured for `127.0.0.1:3000`.
```

- [ ] **Step 3: Verify full regression**

Run:

```bash
make regression
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add Makefile web/README.md
git commit -m "chore: add regression gate"
```

---

### Task 4: Full Acceptance

**Files:**
- No planned code changes unless acceptance finds a regression.

- [ ] **Step 1: Verify clean generated types**

Run:

```bash
cd web
npm run gen:types
git diff --exit-code api/dist/schema.json web/src/lib/generated/types.ts
```

Expected: no diff.

- [ ] **Step 2: Verify final state**

Run:

```bash
git status --short
git diff --check origin/feature/mvp-web-app...HEAD
```

Expected: clean working tree and no whitespace errors.

If acceptance fixes were needed:

```bash
git add -A
git commit -m "fix(e2e): complete regression acceptance"
```

---

## Self-Review

- **Spec coverage:** Adds three browser critical paths, explicit fixture modules, API integration workflow coverage, root regression gate, and fixture-mode docs.
- **Existing work reused:** Keeps current Playwright config and happy path, extracting helper code instead of rewriting the flow.
- **Placeholder scan:** No red-flag placeholders or undefined follow-up tasks remain.
- **Type consistency:** E2E helpers use Playwright `Page`; API integration tests call canonical Plan6 routes.
