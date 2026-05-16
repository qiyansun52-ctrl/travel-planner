from __future__ import annotations

import json
from pathlib import Path

import httpx

from app.models.schemas import HardConstraints
from app.routes._shared import repository


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


async def test_list_sessions_respects_limit(client: httpx.AsyncClient) -> None:
    for index in range(3):
        await client.post(
            "/api/sessions",
            json={**hard_constraints(), "destination_city": f"上海{index}"},
        )

    response = await client.get("/api/sessions?limit=2")

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_sessions_filters_archived_by_default(
    client: httpx.AsyncClient,
) -> None:
    created = await client.post("/api/sessions", json=hard_constraints())
    session_id = created.json()["session_id"]
    await repository().archive_and_fork(
        session_id,
        "Before destination change",
        HardConstraints.model_validate(hard_constraints()),
    )

    active_only = await client.get("/api/sessions")
    with_archived = await client.get("/api/sessions?include_archived=true")

    assert active_only.status_code == 200
    assert all(session["status"] == "active" for session in active_only.json())
    assert any(session["status"] == "archived" for session in with_archived.json())


async def test_list_sessions_rejects_invalid_limit(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/sessions?limit=0")

    assert response.status_code == 422
