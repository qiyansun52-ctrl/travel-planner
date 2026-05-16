from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

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


@router.get("/{session_id}", response_model=PlanningSession)
async def get_session(session_id: str) -> PlanningSession:
    try:
        return await require_session(session_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise route_error(exc) from exc
