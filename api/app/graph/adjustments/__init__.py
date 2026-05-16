"""Adjustment graph routing."""

from __future__ import annotations

from app.graph.adjustments.type_a import run_type_a_adjustment
from app.graph.adjustments.type_b import run_type_b_adjustment
from app.graph.adjustments.type_c import run_type_c_adjustment
from app.graph.nodes.adjustment_classifier import classify_adjustment
from app.graph.state import AdjustmentGraphResult, TypeCAction
from app.models.schemas import PlanningSession

CLARIFICATION_MESSAGE = (
    "Can you clarify whether this changes the itinerary, stay, transport, or core trip "
    "constraints?"
)


async def run_adjustment_workflow(
    session: PlanningSession,
    *,
    message: str,
    type_c_action: TypeCAction | None = None,
    fixture_mode: bool = False,
) -> AdjustmentGraphResult:
    classification = classify_adjustment(message)

    if classification.type == "unknown" or classification.confidence < 0.55:
        return AdjustmentGraphResult(
            session_id=session.session_id,
            classification=classification,
            message=CLARIFICATION_MESSAGE,
        )

    if classification.type == "A":
        return await run_type_a_adjustment(
            session,
            classification,
            fixture_mode=fixture_mode,
        )
    if classification.type == "B":
        return await run_type_b_adjustment(
            session,
            classification,
            fixture_mode=fixture_mode,
        )

    return await run_type_c_adjustment(
        session,
        classification,
        action=type_c_action,
    )


__all__ = [
    "run_adjustment_workflow",
    "run_type_a_adjustment",
    "run_type_b_adjustment",
    "run_type_c_adjustment",
]
