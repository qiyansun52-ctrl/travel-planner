# Session Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users resume recent active trips from the home page using the existing file-backed session persistence.

**Architecture:** Add a read-only sessions list endpoint backed by the existing repository, expose it through the web API client, and render a compact recent trips section in the current `HomeStart` page. Resume routing uses the existing discovery/preferences/trips pages instead of adding a new dashboard.

**Tech Stack:** FastAPI, Pydantic response models, file-backed session repository, Next.js App Router client components, Vitest, Playwright, existing `make regression` gate.

---

## File Map

- Modify `api/app/routes/sessions.py`: add `GET /api/sessions` with `limit` and `include_archived`.
- Modify `api/tests/routes/test_sessions.py`: add list endpoint tests for sorting, archived filtering, archived inclusion, and limit validation.
- Modify `web/src/lib/apiClient.ts`: add `listSessions(limit = 5)`.
- Modify `web/src/lib/apiClient.test.ts`: assert list sessions URL mapping.
- Create `web/src/components/intake/RecentTrips.tsx`: render recent active trips and compute resume href.
- Modify `web/src/components/intake/HomeStart.tsx`: fetch recent sessions and render `RecentTrips`.
- Create `web/e2e/recent-trips.spec.ts`: verify a fixture trip appears on home and can be resumed.
- Modify `docs/2026-05-10-real-mvp-work-summary.md`: record Plan16 status.
- Create this plan at `docs/superpowers/plans/2026-05-10-langgraph-mvp-16-session-resume.md`.

---

### Task 1: Add Sessions List API

**Files:**
- Modify: `api/app/routes/sessions.py`
- Modify: `api/tests/routes/test_sessions.py`

- [x] **Step 1: Add failing route tests**

Add tests to `api/tests/routes/test_sessions.py`:

```python
async def test_list_sessions_returns_recent_active_sessions(
    client: httpx.AsyncClient,
) -> None:
    first = await client.post("/api/sessions", json=hard_constraints())
    second = await client.post(
        "/api/sessions",
        json={**hard_constraints(), "destination_city": "北京"},
    )

    response = await client.get("/api/sessions")

    assert response.status_code == 200
    payload = response.json()
    assert [session["session_id"] for session in payload] == [
        second.json()["session_id"],
        first.json()["session_id"],
    ]
    assert all(session["status"] == "active" for session in payload)
```

Add:

```python
async def test_list_sessions_respects_limit(client: httpx.AsyncClient) -> None:
    for index in range(3):
        await client.post(
            "/api/sessions",
            json={**hard_constraints(), "destination_city": f"上海{index}"},
        )

    response = await client.get("/api/sessions?limit=2")

    assert response.status_code == 200
    assert len(response.json()) == 2
```

Add:

```python
async def test_list_sessions_filters_archived_by_default(
    client: httpx.AsyncClient,
) -> None:
    created = await client.post("/api/sessions", json=hard_constraints())
    session_id = created.json()["session_id"]
    await client.post(
        f"/api/sessions/{session_id}/adjustments",
        json={"message": "Change destination to Tokyo", "type_c_action": "save_and_start_new"},
    )

    active_only = await client.get("/api/sessions")
    with_archived = await client.get("/api/sessions?include_archived=true")

    assert active_only.status_code == 200
    assert all(session["status"] == "active" for session in active_only.json())
    assert any(session["status"] == "archived" for session in with_archived.json())
```

Add:

```python
async def test_list_sessions_rejects_invalid_limit(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/sessions?limit=0")

    assert response.status_code == 422
```

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
cd api
uv run pytest tests/routes/test_sessions.py::test_list_sessions_returns_recent_active_sessions tests/routes/test_sessions.py::test_list_sessions_respects_limit tests/routes/test_sessions.py::test_list_sessions_filters_archived_by_default tests/routes/test_sessions.py::test_list_sessions_rejects_invalid_limit -q
```

Expected: FAIL because `GET /api/sessions` does not exist yet.

- [x] **Step 3: Implement list route**

In `api/app/routes/sessions.py`, import `Query` and add this route before `/{session_id}`:

```python
@router.get("", response_model=list[PlanningSession])
async def list_sessions(
    limit: int = Query(default=5, ge=1, le=20),
    include_archived: bool = False,
) -> list[PlanningSession]:
    repo = repository()
    try:
        sessions = await repo.list(include_archived=include_archived)
    except Exception as exc:
        raise route_error(exc) from exc
    return sessions[:limit]
```

- [x] **Step 4: Run route tests**

Run the same `uv run pytest ... -q` command.

Expected: PASS.

---

### Task 2: Add Web Resume UI

**Files:**
- Modify: `web/src/lib/apiClient.ts`
- Modify: `web/src/lib/apiClient.test.ts`
- Create: `web/src/components/intake/RecentTrips.tsx`
- Modify: `web/src/components/intake/HomeStart.tsx`

- [x] **Step 1: Add API client function and unit assertion**

Add to `apiClient.ts`:

```ts
export async function listSessions(limit = 5): Promise<PlanningSession[]> {
  return fetchJson<PlanningSession[]>(`/api/sessions?limit=${limit}`, {
    cache: "no-store",
  })
}
```

Update `apiClient.test.ts` imports to include `listSessions`, call it before `getSession("s1")`, and add the expected URL:

```ts
"http://127.0.0.1:8000/api/sessions?limit=5",
```

- [x] **Step 2: Create `RecentTrips` component**

Create `web/src/components/intake/RecentTrips.tsx`:

```tsx
"use client"

import Link from "next/link"
import type { PlanningSession } from "@/lib/types"
import type { IntakeLanguage } from "./HardConstraintForm"

const copy = {
  en: {
    title: "Recent trips",
    resume: "Resume",
    itineraryReady: "Itinerary ready",
    preferencesReady: "Ready to plan",
    discoveryReady: "Discovery ready",
    justStarted: "Just started",
    updated: "Updated",
  },
  zh: {
    title: "最近行程",
    resume: "继续",
    itineraryReady: "行程已生成",
    preferencesReady: "可生成行程",
    discoveryReady: "已完成发现",
    justStarted: "刚开始",
    updated: "更新于",
  },
} satisfies Record<IntakeLanguage, Record<string, string>>

export function RecentTrips({
  sessions,
  language,
}: {
  sessions: PlanningSession[]
  language: IntakeLanguage
}) {
  if (sessions.length === 0) return null
  const text = copy[language]

  return (
    <section aria-labelledby="recent-trips-title" className="w-full max-w-5xl">
      <div className="mb-3 flex items-center justify-between">
        <h2 id="recent-trips-title" className="text-sm font-semibold text-slate-900">
          {text.title}
        </h2>
      </div>
      <div className="grid gap-2">
        {sessions.map((session) => (
          <article
            key={session.session_id}
            className="grid gap-3 rounded-md border border-slate-200 bg-white px-4 py-3 shadow-sm sm:grid-cols-[1fr_auto] sm:items-center"
          >
            <div className="min-w-0">
              <h3 className="truncate text-sm font-semibold text-slate-950">
                {session.hard_constraints.destination_city}
              </h3>
              <p className="mt-1 text-sm text-slate-600">
                {session.hard_constraints.departure_date} · {session.hard_constraints.duration_days} days · {session.hard_constraints.currency} {session.hard_constraints.total_budget}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {tripStatus(session, text)} · {text.updated} {formatUpdatedAt(session.updated_at)}
              </p>
            </div>
            <Link
              href={resumeHref(session)}
              className="inline-flex h-9 items-center justify-center rounded-md bg-slate-950 px-3 text-sm font-semibold text-white hover:bg-slate-800"
            >
              {text.resume}
            </Link>
          </article>
        ))}
      </div>
    </section>
  )
}

export function resumeHref(session: PlanningSession): string {
  if (session.itinerary || session.preferences) {
    return `/trips/${session.session_id}`
  }
  if ((session.discovery_state?.selected_card_ids?.length ?? 0) > 0) {
    return `/preferences/${session.session_id}`
  }
  return `/discovery/${session.session_id}`
}

function tripStatus(session: PlanningSession, text: Record<string, string>): string {
  if (session.itinerary) return text.itineraryReady
  if (session.preferences) return text.preferencesReady
  if (session.discovery_state?.payload) return text.discoveryReady
  return text.justStarted
}

function formatUpdatedAt(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value))
}
```

- [x] **Step 3: Render recent trips in `HomeStart`**

Update imports:

```tsx
import { useEffect, useState } from "react"
import { listSessions } from "@/lib/apiClient"
import type { PlanningSession } from "@/lib/types"
import { RecentTrips } from "./RecentTrips"
```

Inside `HomeStart`, add:

```tsx
  const [recentSessions, setRecentSessions] = useState<PlanningSession[]>([])

  useEffect(() => {
    let active = true
    listSessions()
      .then((sessions) => {
        if (active) setRecentSessions(sessions)
      })
      .catch(() => {
        if (active) setRecentSessions([])
      })
    return () => {
      active = false
    }
  }, [])
```

Render before the form:

```tsx
      <RecentTrips sessions={recentSessions} language={language} />
```

- [x] **Step 4: Run web unit tests**

Run:

```bash
cd web
npm run test
```

Expected: PASS.

---

### Task 3: E2E, Docs, Regression, Commit

**Files:**
- Create: `web/e2e/recent-trips.spec.ts`
- Modify: `docs/2026-05-10-real-mvp-work-summary.md`
- Modify: this plan file

- [x] **Step 1: Add Playwright recent trips test**

Create `web/e2e/recent-trips.spec.ts`:

```ts
import { expect, test } from "@playwright/test"
import { startFixtureTrip } from "./helpers/mvpFlow"

test("resumes a recent fixture trip from the home page", async ({ page }) => {
  await startFixtureTrip(page)
  await page.goto("/")

  await expect(page.getByRole("heading", { name: "Recent trips" })).toBeVisible()
  await expect(page.getByText("上海").first()).toBeVisible()
  await page.getByRole("link", { name: "Resume" }).first().click()

  await expect(page).toHaveURL(/\/discovery\/session_/, { timeout: 15_000 })
  await expect(page.getByRole("heading", { name: /Choose what feels worth it/ })).toBeVisible({
    timeout: 15_000,
  })
})
```

- [x] **Step 2: Run focused tests**

Run:

```bash
cd api
uv run pytest tests/routes/test_sessions.py -q
cd ../web
npm run test
npm run test:e2e -- recent-trips.spec.ts
```

Expected: PASS.

- [x] **Step 3: Update summary document**

Add Plan16 to `docs/2026-05-10-real-mvp-work-summary.md`:

```markdown
- Recent trips / resume：Plan16 已新增 `GET /api/sessions` 和首页最近行程入口，用户可以回到首页继续最近的本地行程。
```

- [x] **Step 4: Run full regression and guards**

Run:

```bash
make regression
git diff --check
rg -n 'AI''zaSy|tvly''-' --glob '!api/.env' --glob '!web/.env.local' --glob '!node_modules' --glob '!.git'
```

Expected: all pass; secret grep returns no matches.

- [x] **Step 5: Commit**

Run:

```bash
git add api/app/routes/sessions.py api/tests/routes/test_sessions.py web/src/lib/apiClient.ts web/src/lib/apiClient.test.ts web/src/components/intake/HomeStart.tsx web/src/components/intake/RecentTrips.tsx web/e2e/recent-trips.spec.ts docs/2026-05-10-real-mvp-work-summary.md docs/superpowers/plans/2026-05-10-langgraph-mvp-16-session-resume.md
git commit -m "feat: add recent trip resume"
```

---

## Self-Review

- Spec coverage: The plan implements the approved session resume design through API, client, UI, e2e, docs, and regression.
- Placeholder scan: No TBD/TODO placeholders are present.
- Type consistency: Uses existing generated `PlanningSession` and existing route/page behavior.
