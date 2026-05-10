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


def _install_operation_budget(monkeypatch, limits: dict[str, int]) -> None:
    from app.ops.operation_budget import SessionOperationBudget
    from app.routes import _shared

    monkeypatch.setattr(
        _shared,
        "_OPERATION_BUDGET",
        SessionOperationBudget(default_limits=limits),
    )


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


async def test_adjustment_budget_returns_429_after_limit(
    client: httpx.AsyncClient,
    monkeypatch,
) -> None:
    _install_operation_budget(
        monkeypatch,
        {"discovery": 3, "itinerary": 4, "adjustment": 1},
    )
    session_id = await planned_session(client)

    first = await client.post(
        f"/api/sessions/{session_id}/adjustments",
        json={"message": "把第二天下午安排轻松一点"},
    )
    second = await client.post(
        f"/api/sessions/{session_id}/adjustments",
        json={"message": "再轻松一点"},
    )

    assert first.status_code == 200
    assert second.status_code == 429


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
    assert payload["confirmation"]["rerun_stages"] == [
        "discovery",
        "preferences",
        "itinerary",
    ]
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
