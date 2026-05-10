from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app.graph.adjustments import run_adjustment_workflow
from app.llm.fixtures import fixture_mode_enabled
from app.models.schemas import ConversationTurn
from app.routes._shared import (
    AdjustmentInput,
    AdjustmentResponse,
    conversation_turn_id,
    guard_expensive_operation,
    persist_adjustment_result,
    repository,
    require_session,
    route_error,
    safe_metric,
)

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["adjustments"])


@router.post("/adjustments", response_model=AdjustmentResponse)
async def submit_adjustment(
    session_id: str,
    body: AdjustmentInput,
) -> AdjustmentResponse:
    repo = repository()
    session = await require_session(session_id, repo)
    try:
        await guard_expensive_operation(session_id, "adjustment")
        result = await run_adjustment_workflow(
            session,
            message=body.message,
            type_c_action=body.type_c_action,
            fixture_mode=fixture_mode_enabled(),
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
