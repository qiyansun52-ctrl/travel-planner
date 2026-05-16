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


def _install_operation_budget(monkeypatch, limits: dict[str, int]) -> None:
    from app.ops.operation_budget import SessionOperationBudget
    from app.routes import _shared

    monkeypatch.setattr(
        _shared,
        "_OPERATION_BUDGET",
        SessionOperationBudget(default_limits=limits),
    )


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


async def test_run_discovery_returns_concurrent_success_when_late_request_fails(
    client: httpx.AsyncClient,
    monkeypatch,
) -> None:
    import app.routes.discovery as discovery_route
    from app.models.schemas import DiscoveryState

    session_id = await create_session(client)
    original_run_discovery_agent = discovery_route.run_discovery_agent

    async def late_loser(session, **_: object):
        payload = await original_run_discovery_agent(session, fixture_mode=True)
        await discovery_route.repository().update_discovery(
            session.session_id,
            DiscoveryState(payload=payload, selected_card_ids=[]),
        )
        raise RuntimeError("late loser")

    monkeypatch.setattr(discovery_route, "run_discovery_agent", late_loser)

    response = await client.post(f"/api/sessions/{session_id}/discovery")

    assert response.status_code == 200
    assert response.json()["discovery_state"]["payload"]["cards"]


async def test_discovery_budget_applies_to_generation_not_cached_request(
    client: httpx.AsyncClient,
    monkeypatch,
) -> None:
    import app.routes.discovery as discovery_route

    _install_operation_budget(
        monkeypatch,
        {"discovery": 1, "itinerary": 4, "adjustment": 8},
    )
    session_id = await create_session(client)

    first = await client.post(f"/api/sessions/{session_id}/discovery")
    second = await client.post(f"/api/sessions/{session_id}/discovery")
    await discovery_route.repository().reset_to_step(session_id, "discovery")
    third = await client.post(f"/api/sessions/{session_id}/discovery")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["discovery_state"] == first.json()["discovery_state"]
    assert third.status_code == 429
    assert "Operation budget exceeded for discovery" in third.json()["detail"]


async def test_update_selection_dedupes_ids(client: httpx.AsyncClient) -> None:
    session_id = await create_session(client)
    await client.post(f"/api/sessions/{session_id}/discovery")

    response = await client.patch(
        f"/api/sessions/{session_id}/selection",
        json={
            "selected_card_ids": [
                "disc_waterfront",
                "",
                "disc_waterfront",
                "disc_museum",
            ]
        },
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
