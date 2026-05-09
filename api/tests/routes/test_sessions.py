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
