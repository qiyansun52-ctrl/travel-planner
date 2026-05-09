"""Type C root-constraint adjustment routing."""

from __future__ import annotations

from app.graph.state import AdjustmentGraphResult, TypeCAction, TypeCConfirmation
from app.models.schemas import AdjustmentRequest, PlanningSession


async def run_type_c_adjustment(
    session: PlanningSession,
    classification: AdjustmentRequest,
    *,
    action: TypeCAction | None = None,
) -> AdjustmentGraphResult:
    if action is None:
        return AdjustmentGraphResult(
            session_id=session.session_id,
            classification=classification,
            message="This changes core trip constraints.",
            confirmation=TypeCConfirmation(
                detected_change=classification.proposed_change or classification.raw_text,
                rerun_stages=["discovery", "preferences", "itinerary"],
                discard_estimate="Most downstream planning state will be refreshed.",
            ),
        )

    if action == "cancel":
        return AdjustmentGraphResult(
            session_id=session.session_id,
            classification=classification,
            message="Root change cancelled.",
        )

    if action == "save_and_start_new":
        return AdjustmentGraphResult(
            session_id=session.session_id,
            classification=classification,
            message="New session requested.",
            fork_requested=True,
        )

    return AdjustmentGraphResult(
        session_id=session.session_id,
        classification=classification,
        message="Session reset to discovery.",
        reset_to_step="discovery",
    )
