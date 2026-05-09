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
