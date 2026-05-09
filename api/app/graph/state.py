"""Shared state models for the planning graph."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas import (
    AdjustmentRequest,
    DiscoveryOutput,
    Itinerary,
    PlanningSession,
    StayRecommendation,
    TransportRecommendation,
    ValidatorIssue,
)

GraphMode = Literal["discovery", "full_planning", "planner_only", "adjustment"]
ProgressStatus = Literal["started", "completed", "skipped", "failed"]
TypeCAction = Literal["replan", "save_and_start_new", "cancel"]
TypeCStage = Literal["discovery", "preferences", "itinerary"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ProgressEvent(_StrictModel):
    node: str
    status: ProgressStatus
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class TypeCConfirmation(_StrictModel):
    detected_change: str
    rerun_stages: list[TypeCStage]
    discard_estimate: str


class PlanningGraphResult(_StrictModel):
    session_id: str
    stay: StayRecommendation
    transport: TransportRecommendation
    itinerary: Itinerary
    validator_issues: list[ValidatorIssue]
    progress_events: list[ProgressEvent]


class AdjustmentGraphResult(_StrictModel):
    session_id: str
    classification: AdjustmentRequest
    message: str
    stay: StayRecommendation | None = None
    transport: TransportRecommendation | None = None
    itinerary: Itinerary | None = None
    validator_issues: list[ValidatorIssue] = Field(default_factory=list)
    confirmation: TypeCConfirmation | None = None
    reset_to_step: Literal["discovery"] | None = None
    fork_requested: bool = False
    progress_events: list[ProgressEvent] = Field(default_factory=list)


class PlanState(_StrictModel):
    session: PlanningSession
    mode: GraphMode = "full_planning"
    fixture_mode: bool = False
    planner_only_reason: str | None = None
    adjustment_text: str | None = None
    type_c_action: TypeCAction | None = None
    discovery_output: DiscoveryOutput | None = None
    stay_recommendation: StayRecommendation | None = None
    transport_recommendation: TransportRecommendation | None = None
    itinerary: Itinerary | None = None
    validator_issues: list[ValidatorIssue] = Field(default_factory=list)
    corrective_attempts: int = Field(default=0, ge=0)
    classification: AdjustmentRequest | None = None
    message: str | None = None
    confirmation: TypeCConfirmation | None = None
    reset_to_step: Literal["discovery"] | None = None
    fork_requested: bool = False
    progress_events: list[ProgressEvent] = Field(default_factory=list)

    @property
    def has_validator_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.validator_issues)


class GraphState(TypedDict, total=False):
    session: dict[str, Any]
    mode: GraphMode
    fixture_mode: bool
    planner_only_reason: str
    adjustment_text: str
    type_c_action: TypeCAction
    discovery_output: dict[str, Any]
    stay_recommendation: dict[str, Any]
    transport_recommendation: dict[str, Any]
    itinerary: dict[str, Any]
    validator_issues: list[dict[str, Any]]
    corrective_attempts: int
    classification: dict[str, Any]
    message: str
    confirmation: dict[str, Any]
    reset_to_step: Literal["discovery"]
    fork_requested: bool
    progress_events: list[dict[str, Any]]
    __extra_items__: NotRequired[Any]


def graph_input_from_state(state: PlanState) -> GraphState:
    return GraphState(**state.model_dump(mode="json"))


def validate_graph_state(raw: PlanState | GraphState | dict[str, Any]) -> PlanState:
    if isinstance(raw, PlanState):
        return raw
    return PlanState.model_validate(raw)


def state_patch(**updates: Any) -> GraphState:
    return GraphState(**{key: value for key, value in updates.items() if value is not None})


def append_progress(
    state: PlanState,
    node: str,
    status: ProgressStatus,
    payload: dict[str, Any] | None = None,
) -> PlanState:
    event = ProgressEvent(
        node=node,
        status=status,
        payload=payload or {},
        created_at=datetime.now(UTC),
    )
    return state.model_copy(update={"progress_events": [*state.progress_events, event]})
