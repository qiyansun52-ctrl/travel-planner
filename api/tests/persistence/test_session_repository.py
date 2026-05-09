from __future__ import annotations

from typing import get_args

from app.persistence import (
    ArchivedSessionMutationError,
    SessionNotFoundError,
    SessionRepositoryError,
    SessionStoreError,
)
from app.persistence.session_repository import ResetStep


def test_repository_errors_share_base_type() -> None:
    assert issubclass(SessionNotFoundError, SessionRepositoryError)
    assert issubclass(ArchivedSessionMutationError, SessionRepositoryError)
    assert issubclass(SessionStoreError, SessionRepositoryError)


def test_reset_step_literal_matches_supported_steps() -> None:
    assert set(get_args(ResetStep)) == {"intake", "discovery"}
