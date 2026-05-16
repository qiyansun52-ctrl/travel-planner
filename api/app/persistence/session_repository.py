"""Session repository contract for PlanningSession persistence."""
from __future__ import annotations

from typing import Literal, Protocol

from app.models.schemas import (
    ConversationTurn,
    DiscoveryState,
    HardConstraints,
    Itinerary,
    PlanningSession,
    Preference,
    StayRecommendation,
    TransportRecommendation,
    ValidatorIssue,
)

ResetStep = Literal["intake", "discovery"]


class SessionRepositoryError(RuntimeError):
    """Base error for session repository failures."""


class SessionNotFoundError(SessionRepositoryError):
    """Raised when a session id is not present in the store."""


class ArchivedSessionMutationError(SessionRepositoryError):
    """Raised when a mutation targets an archived session."""


class SessionStoreError(SessionRepositoryError):
    """Raised when the session store has an invalid shape."""


class SessionRepository(Protocol):
    async def create(self, hard_constraints: HardConstraints) -> PlanningSession: ...

    async def get(self, session_id: str) -> PlanningSession | None: ...

    async def list(
        self, *, include_archived: bool = False
    ) -> list[PlanningSession]: ...

    async def update_discovery(
        self, session_id: str, discovery_state: DiscoveryState
    ) -> PlanningSession: ...

    async def update_preferences(
        self, session_id: str, preferences: Preference
    ) -> PlanningSession: ...

    async def update_stay_recommendation(
        self, session_id: str, stay_recommendation: StayRecommendation
    ) -> PlanningSession: ...

    async def update_transport_recommendation(
        self,
        session_id: str,
        transport_recommendation: TransportRecommendation,
    ) -> PlanningSession: ...

    async def write_itinerary(
        self,
        session_id: str,
        itinerary: Itinerary,
        validator_issues: list[ValidatorIssue],
    ) -> PlanningSession: ...

    async def append_conversation_turn(
        self, session_id: str, turn: ConversationTurn
    ) -> PlanningSession: ...

    async def update_stay_override(
        self, session_id: str, stay_option_id: str | None
    ) -> PlanningSession: ...

    async def reset_to_step(
        self,
        session_id: str,
        step: ResetStep,
        updated_constraints: HardConstraints | None = None,
    ) -> PlanningSession: ...

    async def archive_and_fork(
        self,
        session_id: str,
        snapshot_label: str,
        new_hard_constraints: HardConstraints,
    ) -> PlanningSession: ...

    async def update_snapshot_label(
        self, session_id: str, snapshot_label: str
    ) -> PlanningSession: ...
