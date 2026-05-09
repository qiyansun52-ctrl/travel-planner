from __future__ import annotations

import json
from pathlib import Path
from typing import get_args

import pytest

from app.models.schemas import HardConstraints
from app.persistence import (
    ArchivedSessionMutationError,
    SessionNotFoundError,
    SessionRepositoryError,
    SessionStoreError,
)
from app.persistence.file_session_repository import (
    FileSessionRepository,
    default_session_store_path,
)
from app.persistence.session_repository import ResetStep


def test_repository_errors_share_base_type() -> None:
    assert issubclass(SessionNotFoundError, SessionRepositoryError)
    assert issubclass(ArchivedSessionMutationError, SessionRepositoryError)
    assert issubclass(SessionStoreError, SessionRepositoryError)


def test_reset_step_literal_matches_supported_steps() -> None:
    assert set(get_args(ResetStep)) == {"intake", "discovery"}


def hard_constraints(total_budget: float = 5000) -> HardConstraints:
    return HardConstraints(
        departure_city="Beijing",
        destination_city="Shanghai",
        destination_country_code="CN",
        departure_date="2026-05-10",
        duration_days=3,
        traveler_count=2,
        total_budget=total_budget,
        currency="CNY",
    )


async def test_creates_and_retrieves_active_session(tmp_path: Path) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")

    session = await repository.create(hard_constraints())
    loaded = await repository.get(session.session_id)

    assert session.session_id.startswith("session_")
    assert session.status == "active"
    assert session.discovery_state is None
    assert session.preferences is None
    assert loaded == session


async def test_persists_sessions_as_json_object(tmp_path: Path) -> None:
    store_path = tmp_path / "nested" / "sessions.json"
    repository = FileSessionRepository(store_path)

    session = await repository.create(hard_constraints())

    raw = json.loads(store_path.read_text())
    assert list(raw) == [session.session_id]
    assert raw[session.session_id]["hard_constraints"]["destination_city"] == "Shanghai"
    assert raw[session.session_id]["created_at"].endswith("Z")


async def test_invalid_preference_mutation_is_rejected_before_persistence(
    tmp_path: Path,
) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")
    session = await repository.create(hard_constraints())

    with pytest.raises(SessionStoreError):
        await repository.update_preferences(
            session.session_id,
            {"quiet_vs_lively": "ultra-loud"},  # type: ignore[arg-type]
        )

    loaded = await repository.get(session.session_id)
    assert loaded is not None
    assert loaded.preferences is None


async def test_missing_store_reads_as_empty(tmp_path: Path) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")

    assert await repository.get("missing") is None
    assert await repository.list() == []


async def test_list_filters_archived_sessions_by_default(tmp_path: Path) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")
    active = await repository.create(hard_constraints())
    fork = await repository.archive_and_fork(
        active.session_id,
        "before budget change",
        hard_constraints(total_budget=3000),
    )

    active_only = await repository.list()
    all_sessions = await repository.list(include_archived=True)

    assert [session.session_id for session in active_only] == [fork.session_id]
    assert {session.session_id for session in all_sessions} == {
        active.session_id,
        fork.session_id,
    }


async def test_corrupt_json_is_quarantined_and_restarts_empty(
    tmp_path: Path,
) -> None:
    store_path = tmp_path / "sessions.json"
    store_path.write_text("{", encoding="utf-8")
    repository = FileSessionRepository(store_path)

    assert await repository.list() == []

    corrupt_files = list(tmp_path.glob("sessions.json.corrupt-*"))
    assert len(corrupt_files) == 1
    assert corrupt_files[0].read_text(encoding="utf-8") == "{"


async def test_valid_json_with_invalid_store_shape_raises(
    tmp_path: Path,
) -> None:
    store_path = tmp_path / "sessions.json"
    store_path.write_text("[]", encoding="utf-8")
    repository = FileSessionRepository(store_path)

    with pytest.raises(SessionStoreError, match="object"):
        await repository.list()


def test_default_session_store_path_uses_env_override(tmp_path: Path) -> None:
    path = default_session_store_path({"SESSION_DATA_DIR": str(tmp_path)})

    assert path == tmp_path / "sessions.json"


def test_default_session_store_path_points_to_api_data_dir_without_env() -> None:
    path = default_session_store_path({})

    assert path.name == "sessions.json"
    assert path.parent.name == ".data"
    assert path.parent.parent.name == "api"
