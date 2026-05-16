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
