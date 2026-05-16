from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import httpx
import pytest

from app.config import get_settings
from app.llm.fixtures import FIXTURE_GEMINI_API_KEY, FIXTURE_TAVILY_API_KEY


@pytest.fixture(autouse=True)
def fixture_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("GEMINI_API_KEY", FIXTURE_GEMINI_API_KEY)
    monkeypatch.setenv("TAVILY_API_KEY", FIXTURE_TAVILY_API_KEY)
    monkeypatch.setenv("E2E_FIXTURE_MODE", "1")
    monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("METRICS_DATA_DIR", str(tmp_path / "metrics"))
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


def hard_constraints(total_budget: float = 6000) -> dict[str, object]:
    return {
        "departure_city": "杭州",
        "destination_city": "上海",
        "destination_country_code": "CN",
        "departure_date": "2026-06-01",
        "duration_days": 3,
        "traveler_count": 2,
        "total_budget": total_budget,
        "currency": "CNY",
    }


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


async def run_full_workflow(
    client: httpx.AsyncClient,
    *,
    total_budget: float = 6000,
) -> dict[str, object]:
    created = await client.post("/api/sessions", json=hard_constraints(total_budget))
    assert created.status_code == 201
    session_id = created.json()["session_id"]

    discovery = await client.post(f"/api/sessions/{session_id}/discovery")
    assert discovery.status_code == 200
    card_ids = [
        card["id"]
        for card in discovery.json()["discovery_state"]["payload"]["cards"]
        if card["place"] is not None
    ][:3]

    selection = await client.patch(
        f"/api/sessions/{session_id}/selection",
        json={"selected_card_ids": card_ids},
    )
    assert selection.status_code == 200

    saved_preferences = await client.post(
        f"/api/sessions/{session_id}/preferences",
        json={"preferences": preferences()},
    )
    assert saved_preferences.status_code == 200

    itinerary = await client.post(f"/api/sessions/{session_id}/itinerary", json={})
    assert itinerary.status_code == 200
    return itinerary.json()


async def test_fixture_full_workflow_happy_path(client: httpx.AsyncClient) -> None:
    payload = await run_full_workflow(client)

    assert payload["discovery_state"]["payload"]["source_notes"] == [
        {
            "provider": "fixture",
            "url": None,
            "note": "Fixture-backed MVP discovery; live enrichment uses configured providers.",
        }
    ]
    assert payload["stay_recommendation"]["primary"]["id"] == "stay_primary"
    assert payload["transport_recommendation"]["arrival"]["mode"] == "rail"
    assert payload["itinerary"]["version"] == 1
    assert payload["validator_issues"] == payload["itinerary"]["validator_issues"]


async def test_fixture_full_workflow_reports_budget_overrun(
    client: httpx.AsyncClient,
) -> None:
    payload = await run_full_workflow(client, total_budget=500)

    assert any(
        issue["code"] == "BUDGET_OVERRUN"
        for issue in payload["itinerary"]["validator_issues"]
    )


async def test_fixture_full_workflow_type_b_stay_adjustment(
    client: httpx.AsyncClient,
) -> None:
    payload = await run_full_workflow(client)
    session_id = payload["session_id"]

    response = await client.post(
        f"/api/sessions/{session_id}/adjustments",
        json={"message": "酒店换到更安静的区域"},
    )

    assert response.status_code == 200
    adjusted = response.json()
    assert adjusted["classification"]["type"] == "B"
    assert adjusted["classification"]["target_scope"] == "stay"
    assert adjusted["message"] == "Itinerary updated."
    assert adjusted["session"]["stay_recommendation"]["user_override_id"] == "stay_alt_quiet"
    assert (
        adjusted["session"]["itinerary"]["days"][0]["segments"][0]["place"]["name"]
        == "上海 quieter residential edge"
    )
