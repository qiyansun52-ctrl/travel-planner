# LangGraph MVP Plan 6 Routes + SSE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the legacy Python scaffold routes with canonical FastAPI session routes and node-level SSE backed by the Plan 5 LangGraph workflows.

**Architecture:** FastAPI routes own HTTP validation, repository writes, and metric logging. LangGraph remains pure: route handlers call graph runners, persist returned state through `FileSessionRepository`, and expose node progress through `StreamingResponse` using LangGraph `astream(..., stream_mode="values")`. This plan does not touch the Next.js cutover; Plan 7 will move the frontend to these canonical endpoints.

**Tech Stack:** FastAPI, Pydantic v2, LangGraph, Starlette `StreamingResponse`, pytest, httpx ASGI transport, uv, ruff.

---

## Roadmap Anchor

- Source roadmap: `docs/superpowers/plans/2026-05-09-langgraph-mvp-roadmap.md`
- Depends on: Plan 5 graph workflows in `api/app/graph/`
- Produces:
  - `POST /api/sessions`
  - `GET /api/sessions/{session_id}`
  - `POST /api/sessions/{session_id}/discovery`
  - `PATCH /api/sessions/{session_id}/selection`
  - `POST /api/sessions/{session_id}/preferences`
  - `POST /api/sessions/{session_id}/itinerary`
  - `GET /api/sessions/{session_id}/itinerary/stream`
  - `PATCH /api/sessions/{session_id}/stay-override`
  - `POST /api/sessions/{session_id}/adjustments`

## File Structure

**Create:**
- `api/app/routes/_shared.py` - repository dependency, route request models, error mapping, metric helpers, result persistence, SSE frame formatting.
- `api/app/routes/sessions.py` - create/get canonical session endpoints.
- `api/app/routes/discovery.py` - discovery execution and selection endpoints.
- `api/app/routes/preferences.py` - preference persistence endpoint.
- `api/app/routes/itinerary.py` - itinerary JSON and SSE endpoints.
- `api/app/routes/adjustments.py` - adjustment endpoint with Type A/B/C persistence.
- `api/tests/routes/__init__.py` - route test package marker matching the existing test package layout.
- `api/tests/routes/conftest.py` - isolated temp repository/metrics environment and async client fixture.
- `api/tests/routes/test_sessions.py`
- `api/tests/routes/test_discovery_preferences.py`
- `api/tests/routes/test_itinerary.py`
- `api/tests/routes/test_adjustments.py`
- `api/scripts/smoke_curl.sh`

**Modify:**
- `api/main.py` - register canonical routers and remove legacy `/api/discover` + `/api/plan/generate` routers.
- `api/README.md` - document canonical routes and smoke command.

**Delete:**
- `api/app/routes/discover.py`
- `api/app/routes/plan.py`

**Keep for now:**
- `api/app/services/gemini.py`
- `api/app/services/tavily.py`

Those service shims are still referenced by existing provider/prompt tests and will be removed in a later cleanup once Plan 7/8 finish web cutover.

## Route Contracts

All success responses use `PlanningSession.model_dump(mode="json")` via FastAPI response serialization.

Error mapping:
- Missing session: `404 {"detail": "Session not found"}`
- Archived session mutation: `409`
- Invalid route precondition: `409`
- Invalid payload: FastAPI/Pydantic `422`
- Unexpected graph/provider/LLM failure: `502` only when the exception crosses a route boundary.

Preconditions:
- `POST /api/sessions/{id}/itinerary` requires both `discovery_state` and `preferences`.
- `PATCH /api/sessions/{id}/selection` requires `discovery_state`.
- `PATCH /api/sessions/{id}/stay-override` requires existing stay + transport because it immediately replans.
- Type C without action returns confirmation and does not reset or fork.

SSE event frame:

```text
event: progress
data: {"stage":"stay","status":"finish","message":"stay completed","payload":{"primary_area":"area_central"}}

```

Final frame:

```text
event: complete
data: {"session":{...PlanningSession...}}

```

Error frame:

```text
event: error
data: {"stage":"workflow","status":"error","message":"..."}

```

---

## Task 0: Commit Plan 6 Baseline

**Files:**
- Create: `docs/superpowers/plans/2026-05-10-langgraph-mvp-6-routes-sse.md`

- [ ] **Step 0.1: Verify plan file exists**

Run:

```bash
test -f docs/superpowers/plans/2026-05-10-langgraph-mvp-6-routes-sse.md
```

Expected: exit code 0.

- [ ] **Step 0.2: Commit the plan document**

Run:

```bash
git add docs/superpowers/plans/2026-05-10-langgraph-mvp-6-routes-sse.md
git commit -m "docs: add fastapi routes and sse plan"
```

Expected: commit created.

---

## Task 1: Route Test Harness And Shared Utilities

**Files:**
- Create: `api/tests/routes/__init__.py`
- Create: `api/tests/routes/conftest.py`
- Create: `api/app/routes/_shared.py`

- [ ] **Step 1.1: Write route fixture harness**

Create `api/tests/routes/__init__.py`:

```python
"""Route test package."""
```

Create `api/tests/routes/conftest.py`:

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def isolated_route_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("METRICS_DATA_DIR", str(tmp_path / "metrics"))
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily")
    monkeypatch.setenv("E2E_FIXTURE_MODE", "1")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as async_client:
        yield async_client
```

- [ ] **Step 1.2: Verify fixture imports fail before routes exist**

Run:

```bash
cd api && uv run pytest tests/routes -q
```

Expected: FAIL because `tests/routes` has no tests yet or imports canonical route modules that do not exist.

- [ ] **Step 1.3: Implement shared route utilities**

Create `api/app/routes/_shared.py`:

```python
from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.graph.state import AdjustmentGraphResult, PlanningGraphResult, ProgressEvent
from app.metrics import MetricEventPayload, safe_append_metric_event
from app.models.schemas import (
    AdjustmentRequest,
    DiscoveryState,
    HardConstraints,
    PlanningSession,
    Preference,
)
from app.persistence import (
    ArchivedSessionMutationError,
    SessionNotFoundError,
    SessionRepository,
    SessionRepositoryError,
    SessionStoreError,
)
from app.persistence.file_session_repository import get_default_session_repository


class _RouteModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SelectionUpdate(_RouteModel):
    selected_card_ids: list[str]


class PreferenceUpdate(_RouteModel):
    preferences: Preference


class ItineraryRequest(_RouteModel):
    planner_only_reason: str | None = None


class StayOverrideUpdate(_RouteModel):
    stay_option_id: str | None = None


class AdjustmentInput(_RouteModel):
    message: str = Field(min_length=1)
    type_c_action: Literal["replan", "save_and_start_new", "cancel"] | None = None


class AdjustmentResponse(_RouteModel):
    session: PlanningSession
    classification: AdjustmentRequest
    message: str
    confirmation: object | None = None


def repository() -> SessionRepository:
    return get_default_session_repository()


async def require_session(
    session_id: str,
    repo: SessionRepository | None = None,
) -> PlanningSession:
    loaded = await (repo or repository()).get(session_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return loaded


def route_error(error: Exception) -> HTTPException:
    if isinstance(error, SessionNotFoundError):
        return HTTPException(status_code=404, detail="Session not found")
    if isinstance(error, ArchivedSessionMutationError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, SessionStoreError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, SessionRepositoryError):
        return HTTPException(status_code=500, detail=str(error))
    return HTTPException(status_code=502, detail=str(error))


def fixture_mode_enabled() -> bool:
    return os.environ.get("E2E_FIXTURE_MODE") == "1"


async def safe_metric(event: MetricEventPayload) -> None:
    await safe_append_metric_event(event)


async def persist_planning_result(
    repo: SessionRepository,
    session_id: str,
    result: PlanningGraphResult,
) -> PlanningSession:
    await repo.update_stay_recommendation(session_id, result.stay)
    await repo.update_transport_recommendation(session_id, result.transport)
    return await repo.write_itinerary(
        session_id,
        result.itinerary,
        result.validator_issues,
    )


async def persist_adjustment_result(
    repo: SessionRepository,
    session: PlanningSession,
    result: AdjustmentGraphResult,
) -> PlanningSession:
    if result.reset_to_step == "discovery":
        return await repo.reset_to_step(session.session_id, "discovery", session.hard_constraints)
    if result.fork_requested:
        return await repo.archive_and_fork(
            session.session_id,
            "Before root constraint change",
            session.hard_constraints,
        )
    if result.stay is not None:
        await repo.update_stay_recommendation(session.session_id, result.stay)
    if result.transport is not None:
        await repo.update_transport_recommendation(session.session_id, result.transport)
    if result.itinerary is not None:
        return await repo.write_itinerary(
            session.session_id,
            result.itinerary,
            result.validator_issues,
        )
    return (await repo.get(session.session_id)) or session


def conversation_turn_id() -> str:
    return f"turn_{uuid4()}"


def sse_frame(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def progress_payload(event: ProgressEvent) -> dict[str, object]:
    return {
        "stage": event.node,
        "status": "finish" if event.status == "completed" else event.status,
        "message": f"{event.node} {event.status}",
        "payload": event.payload,
    }


async def iter_progress_frames(
    progress_events: list[ProgressEvent],
) -> AsyncIterator[str]:
    for event in progress_events:
        yield sse_frame("progress", progress_payload(event))
```

- [ ] **Step 1.4: Run shared utility lint**

Run:

```bash
cd api && uv run ruff check app/routes/_shared.py tests/routes/__init__.py tests/routes/conftest.py
```

Expected: pass.

- [ ] **Step 1.5: Commit shared route harness**

Run:

```bash
git add api/app/routes/_shared.py api/tests/routes/__init__.py api/tests/routes/conftest.py
git commit -m "test(api): add route harness and shared helpers"
```

---

## Task 2: Sessions Route

**Files:**
- Create: `api/app/routes/sessions.py`
- Create: `api/tests/routes/test_sessions.py`
- Modify: `api/main.py`

- [ ] **Step 2.1: Write failing session route tests**

Create `api/tests/routes/test_sessions.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import httpx


def hard_constraints() -> dict[str, object]:
    return {
        "departure_city": "杭州",
        "destination_city": "上海",
        "destination_country_code": "CN",
        "departure_date": "2026-06-01",
        "duration_days": 3,
        "traveler_count": 2,
        "total_budget": 6000,
        "currency": "CNY",
    }


async def test_create_session_persists_and_logs_metric(
    client: httpx.AsyncClient,
    tmp_path: Path,
) -> None:
    response = await client.post("/api/sessions", json=hard_constraints())

    assert response.status_code == 201
    payload = response.json()
    assert payload["session_id"].startswith("session_")
    assert payload["hard_constraints"]["destination_city"] == "上海"
    assert payload["status"] == "active"

    metrics_path = tmp_path / "metrics" / "events.jsonl"
    events = [json.loads(line) for line in metrics_path.read_text().splitlines()]
    assert events[0]["name"] == "step1_submitted"
    assert events[0]["session_id"] == payload["session_id"]


async def test_get_session_returns_404_for_missing(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/sessions/session_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


async def test_get_session_returns_created_session(client: httpx.AsyncClient) -> None:
    created = await client.post("/api/sessions", json=hard_constraints())
    session_id = created.json()["session_id"]

    response = await client.get(f"/api/sessions/{session_id}")

    assert response.status_code == 200
    assert response.json()["session_id"] == session_id


async def test_create_session_rejects_invalid_payload(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/sessions", json={})

    assert response.status_code == 422
```

- [ ] **Step 2.2: Run tests and verify failure**

Run:

```bash
cd api && uv run pytest tests/routes/test_sessions.py -v
```

Expected: FAIL with `404 Not Found` for `/api/sessions`.

- [ ] **Step 2.3: Implement sessions route and register it**

Create `api/app/routes/sessions.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import HardConstraints, PlanningSession
from app.routes._shared import repository, require_session, route_error, safe_metric

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=PlanningSession, status_code=status.HTTP_201_CREATED)
async def create_session(hard_constraints: HardConstraints) -> PlanningSession:
    repo = repository()
    try:
        session = await repo.create(hard_constraints)
    except Exception as exc:
        raise route_error(exc) from exc

    await safe_metric(
        {
            "name": "step1_submitted",
            "session_id": session.session_id,
            "payload": {
                "destination_country_code": hard_constraints.destination_country_code,
                "duration_days": hard_constraints.duration_days,
            },
        }
    )
    return session


@router.get("/{session_id}", response_model=PlanningSession)
async def get_session(session_id: str) -> PlanningSession:
    try:
        return await require_session(session_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise route_error(exc) from exc
```

Modify `api/main.py` to include:

```python
from app.routes.sessions import router as sessions_router

app.include_router(sessions_router)
```

Do not delete legacy routers yet; delete them in Task 7 after all canonical routes are registered.

- [ ] **Step 2.4: Run session route tests**

Run:

```bash
cd api && uv run pytest tests/routes/test_sessions.py -v
cd api && uv run ruff check app/routes/sessions.py api/main.py tests/routes/test_sessions.py
```

Expected: pass.

- [ ] **Step 2.5: Commit sessions route**

Run:

```bash
git add api/app/routes/sessions.py api/main.py api/tests/routes/test_sessions.py
git commit -m "feat(api): add canonical session routes"
```

---

## Task 3: Discovery, Selection, And Preferences Routes

**Files:**
- Create: `api/app/routes/discovery.py`
- Create: `api/app/routes/preferences.py`
- Create: `api/tests/routes/test_discovery_preferences.py`
- Modify: `api/main.py`

- [ ] **Step 3.1: Write failing discovery/preference tests**

Create `api/tests/routes/test_discovery_preferences.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import httpx

from tests.routes.test_sessions import hard_constraints


def preferences() -> dict[str, object]:
    return {
        "area_vibe": "central and walkable",
        "quiet_vs_lively": "balanced",
        "stay_type": "hotel",
        "willing_to_change_hotels": False,
        "intercity_transport_preference": "rail",
        "early_departure_tolerance": "medium",
        "transfer_tolerance": "medium",
        "pay_more_to_save_time": True,
    }


async def create_session(client: httpx.AsyncClient) -> str:
    response = await client.post("/api/sessions", json=hard_constraints())
    assert response.status_code == 201
    return response.json()["session_id"]


async def test_run_discovery_is_idempotent_and_logs_metrics(
    client: httpx.AsyncClient,
    tmp_path: Path,
) -> None:
    session_id = await create_session(client)

    first = await client.post(f"/api/sessions/{session_id}/discovery")
    second = await client.post(f"/api/sessions/{session_id}/discovery")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["discovery_state"]["payload"]["cards"]
    assert second.json()["discovery_state"] == first.json()["discovery_state"]

    metrics_path = tmp_path / "metrics" / "events.jsonl"
    names = [json.loads(line)["name"] for line in metrics_path.read_text().splitlines()]
    assert "discovery_arrived" in names
    assert "discovery_enrichment_summary" in names


async def test_update_selection_dedupes_ids(client: httpx.AsyncClient) -> None:
    session_id = await create_session(client)
    await client.post(f"/api/sessions/{session_id}/discovery")

    response = await client.patch(
        f"/api/sessions/{session_id}/selection",
        json={"selected_card_ids": ["disc_waterfront", "", "disc_waterfront", "disc_museum"]},
    )

    assert response.status_code == 200
    assert response.json()["discovery_state"]["selected_card_ids"] == [
        "disc_waterfront",
        "disc_museum",
    ]


async def test_selection_requires_discovery_state(client: httpx.AsyncClient) -> None:
    session_id = await create_session(client)

    response = await client.patch(
        f"/api/sessions/{session_id}/selection",
        json={"selected_card_ids": ["disc_waterfront"]},
    )

    assert response.status_code == 409


async def test_save_preferences_persists_and_logs_metric(
    client: httpx.AsyncClient,
    tmp_path: Path,
) -> None:
    session_id = await create_session(client)

    response = await client.post(
        f"/api/sessions/{session_id}/preferences",
        json={"preferences": preferences()},
    )

    assert response.status_code == 200
    assert response.json()["preferences"]["stay_type"] == "hotel"

    metrics_path = tmp_path / "metrics" / "events.jsonl"
    names = [json.loads(line)["name"] for line in metrics_path.read_text().splitlines()]
    assert "preferences_completed" in names
```

- [ ] **Step 3.2: Run tests and verify failure**

Run:

```bash
cd api && uv run pytest tests/routes/test_discovery_preferences.py -v
```

Expected: FAIL with missing canonical discovery/preference routes.

- [ ] **Step 3.3: Implement discovery route**

Create `api/app/routes/discovery.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.domain.selection import normalize_selected_card_ids
from app.graph.nodes.discovery import run_discovery_agent
from app.models.schemas import DiscoveryState, PlanningSession
from app.routes._shared import (
    SelectionUpdate,
    fixture_mode_enabled,
    repository,
    require_session,
    route_error,
    safe_metric,
)

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["discovery"])


@router.post("/discovery", response_model=PlanningSession)
async def run_discovery(session_id: str) -> PlanningSession:
    repo = repository()
    session = await require_session(session_id, repo)
    if session.discovery_state and session.discovery_state.payload:
        return session

    try:
        payload = await run_discovery_agent(session, fixture_mode=fixture_mode_enabled())
        updated = await repo.update_discovery(
            session_id,
            DiscoveryState(payload=payload, selected_card_ids=[]),
        )
    except Exception as exc:
        raise route_error(exc) from exc

    counts = {"complete_count": 0, "partial_count": 0, "minimal_count": 0}
    for card in payload.cards:
        counts[f"{card.enrichment_status}_count"] += 1

    await safe_metric({"name": "discovery_arrived", "session_id": session_id, "payload": {}})
    await safe_metric(
        {
            "name": "discovery_enrichment_summary",
            "session_id": session_id,
            "payload": {"total_cards": len(payload.cards), **counts},
        }
    )
    return updated


@router.patch("/selection", response_model=PlanningSession)
async def update_selection(session_id: str, body: SelectionUpdate) -> PlanningSession:
    repo = repository()
    session = await require_session(session_id, repo)
    if session.discovery_state is None:
        raise HTTPException(status_code=409, detail="Discovery state not found")

    selected = normalize_selected_card_ids(body.selected_card_ids)
    try:
        updated = await repo.update_discovery(
            session_id,
            session.discovery_state.model_copy(update={"selected_card_ids": selected}),
        )
    except Exception as exc:
        raise route_error(exc) from exc

    await safe_metric(
        {
            "name": "attraction_selected",
            "session_id": session_id,
            "payload": {"selected_count": len(selected)},
        }
    )
    return updated
```

- [ ] **Step 3.4: Implement preferences route**

Create `api/app/routes/preferences.py`:

```python
from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import PlanningSession
from app.routes._shared import PreferenceUpdate, repository, route_error, safe_metric

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["preferences"])


@router.post("/preferences", response_model=PlanningSession)
async def save_preferences(session_id: str, body: PreferenceUpdate) -> PlanningSession:
    repo = repository()
    try:
        session = await repo.update_preferences(session_id, body.preferences)
    except Exception as exc:
        raise route_error(exc) from exc

    await safe_metric(
        {
            "name": "preferences_completed",
            "session_id": session_id,
            "payload": {
                "stay_type": body.preferences.stay_type,
                "intercity_transport_preference": body.preferences.intercity_transport_preference,
            },
        }
    )
    return session
```

Modify `api/main.py` to include:

```python
from app.routes.discovery import router as discovery_router
from app.routes.preferences import router as preferences_router

app.include_router(discovery_router)
app.include_router(preferences_router)
```

- [ ] **Step 3.5: Run discovery/preference tests**

Run:

```bash
cd api && uv run pytest tests/routes/test_discovery_preferences.py -v
cd api && uv run ruff check app/routes/discovery.py app/routes/preferences.py tests/routes/test_discovery_preferences.py
```

Expected: pass.

- [ ] **Step 3.6: Commit discovery/preference routes**

Run:

```bash
git add api/app/routes/discovery.py api/app/routes/preferences.py api/main.py api/tests/routes/test_discovery_preferences.py
git commit -m "feat(api): add discovery and preference routes"
```

---

## Task 4: Itinerary JSON Route And Node-Level SSE

**Files:**
- Create: `api/app/routes/itinerary.py`
- Create: `api/tests/routes/test_itinerary.py`
- Modify: `api/main.py`

- [ ] **Step 4.1: Write failing itinerary tests**

Create `api/tests/routes/test_itinerary.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import httpx

from tests.routes.test_discovery_preferences import create_session, preferences


async def prepared_session(client: httpx.AsyncClient) -> str:
    session_id = await create_session(client)
    await client.post(f"/api/sessions/{session_id}/discovery")
    await client.patch(
        f"/api/sessions/{session_id}/selection",
        json={"selected_card_ids": ["disc_waterfront"]},
    )
    await client.post(
        f"/api/sessions/{session_id}/preferences",
        json={"preferences": preferences()},
    )
    return session_id


async def test_itinerary_route_runs_graph_persists_result_and_logs_metrics(
    client: httpx.AsyncClient,
    tmp_path: Path,
) -> None:
    session_id = await prepared_session(client)

    response = await client.post(f"/api/sessions/{session_id}/itinerary", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["stay_recommendation"]["primary"]["id"] == "stay_primary"
    assert payload["transport_recommendation"]["arrival"]["mode"] == "rail"
    assert payload["itinerary"]["version"] == 1
    assert payload["validator_issues"] == payload["itinerary"]["validator_issues"]

    metrics_path = tmp_path / "metrics" / "events.jsonl"
    names = [json.loads(line)["name"] for line in metrics_path.read_text().splitlines()]
    assert "itinerary_finalized" in names


async def test_itinerary_route_requires_discovery_and_preferences(
    client: httpx.AsyncClient,
) -> None:
    session_id = await create_session(client)

    response = await client.post(f"/api/sessions/{session_id}/itinerary", json={})

    assert response.status_code == 409


async def test_stay_override_replans_existing_itinerary(
    client: httpx.AsyncClient,
) -> None:
    session_id = await prepared_session(client)
    first = await client.post(f"/api/sessions/{session_id}/itinerary", json={})
    stay_id = first.json()["stay_recommendation"]["primary"]["id"]

    response = await client.patch(
        f"/api/sessions/{session_id}/stay-override",
        json={"stay_option_id": stay_id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["stay_recommendation"]["user_override_id"] == stay_id
    assert payload["itinerary"]["version"] == 2


async def test_itinerary_stream_emits_progress_and_complete_events(
    client: httpx.AsyncClient,
) -> None:
    session_id = await prepared_session(client)

    async with client.stream(
        "GET",
        f"/api/sessions/{session_id}/itinerary/stream",
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = await response.aread()

    text = body.decode()
    assert "event: progress" in text
    assert '"stage": "stay"' in text
    assert '"stage": "planner"' in text
    assert "event: complete" in text

    loaded = await client.get(f"/api/sessions/{session_id}")
    assert loaded.json()["itinerary"]["version"] == 1
```

- [ ] **Step 4.2: Run tests and verify failure**

Run:

```bash
cd api && uv run pytest tests/routes/test_itinerary.py -v
```

Expected: FAIL with missing itinerary routes.

- [ ] **Step 4.3: Implement itinerary route**

Create `api/app/routes/itinerary.py`:

```python
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.graph.state import PlanState, graph_input_from_state, validate_graph_state
from app.graph.workflow import (
    create_planner_only_graph,
    create_planning_graph,
    run_full_planning_workflow,
    run_planner_only_workflow,
)
from app.models.schemas import PlanningSession
from app.routes._shared import (
    ItineraryRequest,
    StayOverrideUpdate,
    persist_planning_result,
    progress_payload,
    repository,
    require_session,
    route_error,
    safe_metric,
    sse_frame,
)

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["itinerary"])


def _assert_itinerary_ready(session: PlanningSession) -> None:
    if session.discovery_state is None or session.preferences is None:
        raise HTTPException(
            status_code=409,
            detail="Discovery and preferences are required before itinerary generation",
        )


async def _run_planning(session: PlanningSession, reason: str | None):
    if reason and session.stay_recommendation and session.transport_recommendation:
        return await run_planner_only_workflow(session, reason=reason)
    return await run_full_planning_workflow(session)


@router.post("/itinerary", response_model=PlanningSession)
async def run_itinerary(session_id: str, body: ItineraryRequest) -> PlanningSession:
    repo = repository()
    session = await require_session(session_id, repo)
    _assert_itinerary_ready(session)
    try:
        result = await _run_planning(session, body.planner_only_reason)
        updated = await persist_planning_result(repo, session_id, result)
    except Exception as exc:
        raise route_error(exc) from exc

    await _log_itinerary_metrics(session_id, result.itinerary.version, result.validator_issues)
    return updated


@router.patch("/stay-override", response_model=PlanningSession)
async def update_stay_override(
    session_id: str,
    body: StayOverrideUpdate,
) -> PlanningSession:
    repo = repository()
    try:
        with_override = await repo.update_stay_override(session_id, body.stay_option_id)
        result = await run_planner_only_workflow(with_override, reason="stay_override")
        updated = await persist_planning_result(repo, session_id, result)
    except Exception as exc:
        raise route_error(exc) from exc

    await safe_metric(
        {
            "name": "stay_override_set",
            "session_id": session_id,
            "payload": {"override_set": body.stay_option_id is not None},
        }
    )
    return updated


@router.get("/itinerary/stream")
async def stream_itinerary(session_id: str) -> StreamingResponse:
    return StreamingResponse(
        _stream_itinerary_events(session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


async def _stream_itinerary_events(session_id: str) -> AsyncIterator[str]:
    repo = repository()
    try:
        session = await require_session(session_id, repo)
        _assert_itinerary_ready(session)
        yield sse_frame(
            "progress",
            {"stage": "workflow", "status": "start", "message": "itinerary started"},
        )
        result = None
        async for item in _stream_planning_values(session):
            if isinstance(item, str):
                yield item
            else:
                result = item
        if result is None:
            raise RuntimeError("Planning stream ended without a result")
        updated = await persist_planning_result(repo, session_id, result)
        await _log_itinerary_metrics(
            session_id,
            result.itinerary.version,
            result.validator_issues,
        )
        yield sse_frame("complete", {"session": updated.model_dump(mode="json")})
    except Exception as exc:
        yield sse_frame(
            "error",
            {"stage": "workflow", "status": "error", "message": str(exc)},
        )


async def _stream_planning_values(session: PlanningSession):
    from app.graph.state import PlanningGraphResult

    graph = create_planning_graph()
    seen_progress = 0
    last_state = None
    async for value in graph.astream(
        graph_input_from_state(PlanState(session=session, mode="full_planning")),
        stream_mode="values",
    ):
        parsed = validate_graph_state(value)
        for event in parsed.progress_events[seen_progress:]:
            seen_progress += 1
            yield sse_frame("progress", progress_payload(event))
        last_state = value

    if last_state is None:
        raise RuntimeError("Planning graph produced no state")
    parsed = validate_graph_state(last_state)
    if parsed.stay_recommendation is None or parsed.transport_recommendation is None or parsed.itinerary is None:
        raise RuntimeError("Planning graph finished without a complete result")
    yield PlanningGraphResult(
        session_id=session.session_id,
        stay=parsed.stay_recommendation,
        transport=parsed.transport_recommendation,
        itinerary=parsed.itinerary.model_copy(update={"validator_issues": parsed.validator_issues}),
        validator_issues=parsed.validator_issues,
        progress_events=parsed.progress_events,
    )


async def _log_itinerary_metrics(session_id: str, version: int, validator_issues) -> None:
    await safe_metric(
        {
            "name": "itinerary_finalized",
            "session_id": session_id,
            "payload": {"version": version},
        }
    )
    residual_errors = [issue for issue in validator_issues if issue.severity == "error"]
    if residual_errors:
        await safe_metric(
            {
                "name": "validator_error_finalized",
                "session_id": session_id,
                "payload": {"codes": [issue.code for issue in residual_errors]},
            }
        )
```

Before final implementation, remove unused imports if ruff reports them.

Modify `api/main.py` to include:

```python
from app.routes.itinerary import router as itinerary_router

app.include_router(itinerary_router)
```

- [ ] **Step 4.4: Run itinerary tests**

Run:

```bash
cd api && uv run pytest tests/routes/test_itinerary.py -v
cd api && uv run ruff check app/routes/itinerary.py tests/routes/test_itinerary.py
```

Expected: pass.

- [ ] **Step 4.5: Commit itinerary routes**

Run:

```bash
git add api/app/routes/itinerary.py api/main.py api/tests/routes/test_itinerary.py
git commit -m "feat(api): add itinerary routes and sse progress"
```

---

## Task 5: Adjustment Route

**Files:**
- Create: `api/app/routes/adjustments.py`
- Create: `api/tests/routes/test_adjustments.py`
- Modify: `api/main.py`

- [ ] **Step 5.1: Write failing adjustment route tests**

Create `api/tests/routes/test_adjustments.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import httpx

from tests.routes.test_itinerary import prepared_session


async def planned_session(client: httpx.AsyncClient) -> str:
    session_id = await prepared_session(client)
    response = await client.post(f"/api/sessions/{session_id}/itinerary", json={})
    assert response.status_code == 200
    return session_id


async def test_type_a_adjustment_persists_new_itinerary(
    client: httpx.AsyncClient,
    tmp_path: Path,
) -> None:
    session_id = await planned_session(client)

    response = await client.post(
        f"/api/sessions/{session_id}/adjustments",
        json={"message": "Update the itinerary for day two."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["classification"]["type"] == "A"
    assert payload["message"] == "Itinerary updated."
    assert payload["session"]["itinerary"]["version"] == 2

    metrics_path = tmp_path / "metrics" / "events.jsonl"
    names = [json.loads(line)["name"] for line in metrics_path.read_text().splitlines()]
    assert "adjustment_classified" in names


async def test_low_confidence_adjustment_returns_clarification(
    client: httpx.AsyncClient,
) -> None:
    session_id = await planned_session(client)

    response = await client.post(
        f"/api/sessions/{session_id}/adjustments",
        json={"message": "ok"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["classification"]["type"] == "unknown"
    assert payload["session"]["conversation_history"][-1]["raw_text"] == "ok"
    assert "clarify" in payload["message"]


async def test_type_c_without_action_returns_confirmation_without_reset(
    client: httpx.AsyncClient,
) -> None:
    session_id = await planned_session(client)

    response = await client.post(
        f"/api/sessions/{session_id}/adjustments",
        json={"message": "预算改成 3000"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["classification"]["type"] == "C"
    assert payload["confirmation"]["rerun_stages"] == ["discovery", "preferences", "itinerary"]
    assert payload["session"]["itinerary"] is not None


async def test_type_c_replan_resets_session_to_discovery(
    client: httpx.AsyncClient,
) -> None:
    session_id = await planned_session(client)

    response = await client.post(
        f"/api/sessions/{session_id}/adjustments",
        json={"message": "预算改成 3000", "type_c_action": "replan"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Session reset to discovery."
    assert payload["session"]["discovery_state"] is None
    assert payload["session"]["itinerary"] is None
```

- [ ] **Step 5.2: Run tests and verify failure**

Run:

```bash
cd api && uv run pytest tests/routes/test_adjustments.py -v
```

Expected: FAIL with missing adjustment route.

- [ ] **Step 5.3: Implement adjustment route**

Create `api/app/routes/adjustments.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app.graph.adjustments import run_adjustment_workflow
from app.models.schemas import ConversationTurn
from app.routes._shared import (
    AdjustmentInput,
    AdjustmentResponse,
    conversation_turn_id,
    persist_adjustment_result,
    repository,
    require_session,
    route_error,
    safe_metric,
)

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["adjustments"])


@router.post("/adjustments", response_model=AdjustmentResponse)
async def submit_adjustment(session_id: str, body: AdjustmentInput) -> AdjustmentResponse:
    repo = repository()
    session = await require_session(session_id, repo)
    try:
        result = await run_adjustment_workflow(
            session,
            message=body.message,
            type_c_action=body.type_c_action,
        )
        await repo.append_conversation_turn(
            session_id,
            ConversationTurn(
                id=conversation_turn_id(),
                raw_text=body.message,
                classification=result.classification,
                created_at=datetime.now(UTC),
            ),
        )
        await safe_metric(
            {
                "name": "adjustment_classified",
                "session_id": session_id,
                "payload": {
                    "type": result.classification.type,
                    "confidence": result.classification.confidence,
                },
            }
        )
        if result.classification.type == "C" and body.type_c_action is not None:
            await safe_metric(
                {
                    "name": "type_c_action_taken",
                    "session_id": session_id,
                    "payload": {"action": body.type_c_action},
                }
            )
        updated = await persist_adjustment_result(repo, session, result)
    except Exception as exc:
        raise route_error(exc) from exc

    return AdjustmentResponse(
        session=updated,
        classification=result.classification,
        message=result.message,
        confirmation=result.confirmation,
    )
```

Modify `api/main.py` to include:

```python
from app.routes.adjustments import router as adjustments_router

app.include_router(adjustments_router)
```

- [ ] **Step 5.4: Run adjustment tests**

Run:

```bash
cd api && uv run pytest tests/routes/test_adjustments.py -v
cd api && uv run ruff check app/routes/adjustments.py tests/routes/test_adjustments.py
```

Expected: pass.

- [ ] **Step 5.5: Commit adjustment route**

Run:

```bash
git add api/app/routes/adjustments.py api/main.py api/tests/routes/test_adjustments.py
git commit -m "feat(api): add adjustment route"
```

---

## Task 6: Remove Legacy Routes And Add Smoke Script

**Files:**
- Delete: `api/app/routes/discover.py`
- Delete: `api/app/routes/plan.py`
- Modify: `api/main.py`
- Modify: `api/README.md`
- Create: `api/scripts/smoke_curl.sh`

- [ ] **Step 6.1: Remove legacy router imports**

Modify `api/main.py` so it registers only canonical routers:

```python
from app.routes.adjustments import router as adjustments_router
from app.routes.discovery import router as discovery_router
from app.routes.itinerary import router as itinerary_router
from app.routes.preferences import router as preferences_router
from app.routes.sessions import router as sessions_router

app.include_router(sessions_router)
app.include_router(discovery_router)
app.include_router(preferences_router)
app.include_router(itinerary_router)
app.include_router(adjustments_router)
```

Delete:

```bash
rm api/app/routes/discover.py api/app/routes/plan.py
```

- [ ] **Step 6.2: Add smoke curl script**

Create `api/scripts/smoke_curl.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

SESSION_JSON="$(curl -fsS -X POST "$BASE_URL/api/sessions" \
  -H 'Content-Type: application/json' \
  -d '{"departure_city":"杭州","destination_city":"上海","destination_country_code":"CN","departure_date":"2026-06-01","duration_days":3,"traveler_count":2,"total_budget":6000,"currency":"CNY"}')"

SESSION_ID="$(python -c 'import json,sys; print(json.load(sys.stdin)["session_id"])' <<<"$SESSION_JSON")"

curl -fsS -X POST "$BASE_URL/api/sessions/$SESSION_ID/discovery" >/dev/null
curl -fsS -X PATCH "$BASE_URL/api/sessions/$SESSION_ID/selection" \
  -H 'Content-Type: application/json' \
  -d '{"selected_card_ids":["disc_waterfront"]}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/sessions/$SESSION_ID/preferences" \
  -H 'Content-Type: application/json' \
  -d '{"preferences":{"area_vibe":"central and walkable","quiet_vs_lively":"balanced","stay_type":"hotel","willing_to_change_hotels":false,"intercity_transport_preference":"rail","early_departure_tolerance":"medium","transfer_tolerance":"medium","pay_more_to_save_time":true}}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/sessions/$SESSION_ID/itinerary" \
  -H 'Content-Type: application/json' \
  -d '{}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/sessions/$SESSION_ID/adjustments" \
  -H 'Content-Type: application/json' \
  -d '{"message":"Update the itinerary for day two."}' >/dev/null

echo "Smoke flow passed for $SESSION_ID"
```

- [ ] **Step 6.3: Update README route list**

Update `api/README.md` so it lists canonical session endpoints and marks `/api/discover` and `/api/plan/generate` as removed legacy endpoints.

- [ ] **Step 6.4: Run route suite**

Run:

```bash
cd api && uv run pytest tests/routes -v
cd api && uv run ruff check app/routes tests/routes
```

Expected: pass.

- [ ] **Step 6.5: Commit legacy route removal**

Run:

```bash
git add api/main.py api/app/routes api/tests/routes api/scripts/smoke_curl.sh api/README.md
git add -u api/app/routes
git commit -m "chore(api): remove legacy route scaffold"
```

---

## Task 7: Final Verification And Acceptance

**Files:**
- All Plan 6 files.

- [ ] **Step 7.1: Run full API route and graph verification**

Run:

```bash
cd api && uv run pytest tests/routes tests/graph -v
cd api && uv run pytest -v
cd api && uv run ruff check app tests
git diff --check origin/feature/mvp-web-app...HEAD
```

Expected:
- route + graph tests pass.
- full API tests pass.
- ruff reports no issues.
- diff check prints nothing and exits 0.

- [ ] **Step 7.2: Optional smoke script check**

Run the API in one terminal:

```bash
cd api && E2E_FIXTURE_MODE=1 uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Run smoke script in another terminal:

```bash
cd api && BASE_URL=http://127.0.0.1:8000 bash scripts/smoke_curl.sh
```

Expected:

```text
Smoke flow passed for session_...
```

If the environment cannot run a background server in the current session, record that limitation and rely on ASGI route tests.

- [ ] **Step 7.3: Acceptance review checklist**

Verify:
- Canonical route tests cover happy paths, 4xx preconditions, metrics, and SSE frame format.
- `api/main.py` exposes canonical routers only.
- Legacy `/api/discover` and `/api/plan/generate` route modules are gone.
- No graph node mutates the repository.
- Route handlers persist graph outputs through `SessionRepository`.
- SSE emits `progress`, `complete`, and `error` frame shapes.
- Worktree is clean after commits.

- [ ] **Step 7.4: Final commit only if acceptance fixes are needed**

If Step 7 reveals fixes, commit them with:

```bash
git add api docs/superpowers/plans/2026-05-10-langgraph-mvp-6-routes-sse.md
git commit -m "fix(api): harden canonical route acceptance"
```

---

## Risks And Guardrails

- `uv run` may need access to the user-level uv cache. If sandboxed execution fails with cache permission errors, rerun the same command with approved escalation.
- Do not remove `api/app/services/tavily.py` in this plan; provider tests still import its compatibility shim.
- Do not update Next.js API client in this plan; that is Plan 7.
- Do not add token-level LLM streaming; Plan 6 streams node progress only.
- Keep route tests in fixture mode so no live Tavily/Gemini keys are required.

## Self-Review

- **Spec coverage:** Covers Plan 6 canonical FastAPI routes, repository persistence, metrics, SSE frame format, legacy route removal, and smoke script.
- **Placeholder scan:** No placeholder red flags remain.
- **Type consistency:** Request/response model names in route tasks match `_shared.py`; route paths consistently use `/api/sessions/{session_id}/...`.
- **Scope check:** Web cutover, generated TypeScript types, and E2E browser flow remain Plan 7-9.
