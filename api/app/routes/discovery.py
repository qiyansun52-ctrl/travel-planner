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
