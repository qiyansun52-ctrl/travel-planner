from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import get_args

import pytest

from app.models.schemas import (
    AreaSummary,
    BudgetBand,
    BudgetSummary,
    ConversationTurn,
    DiscoveryState,
    HardConstraints,
    Itinerary,
    PlanningSession,
    Preference,
    StayOption,
    StayRecommendation,
    TransportRecommendation,
    ValidatorIssue,
)
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

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "sessions.json"
)


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


async def test_invalid_conversation_turn_is_rejected_before_persistence(
    tmp_path: Path,
) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")
    session = await repository.create(hard_constraints())

    with pytest.raises(SessionStoreError):
        await repository.append_conversation_turn(
            session.session_id,
            {"id": "", "raw_text": 123},  # type: ignore[arg-type]
        )

    loaded = await repository.get(session.session_id)
    assert loaded is not None
    assert loaded.conversation_history == []


async def test_invalid_model_copy_conversation_turn_is_rejected_before_persistence(
    tmp_path: Path,
) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")
    session = await repository.create(hard_constraints())
    turn = ConversationTurn(
        id="turn_1",
        raw_text="Please make the trip quieter",
        classification=None,
        created_at=datetime.now(timezone.utc),
    ).model_copy(update={"raw_text": 123})

    with pytest.raises(SessionStoreError):
        await repository.append_conversation_turn(session.session_id, turn)

    loaded = await repository.get(session.session_id)
    assert loaded is not None
    assert loaded.conversation_history == []


async def test_invalid_model_copy_hard_constraints_are_rejected_before_fork_persistence(
    tmp_path: Path,
) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")
    original = await repository.create(hard_constraints())
    invalid_constraints = hard_constraints().model_copy(
        update={"duration_days": "many"}
    )

    with pytest.raises(SessionStoreError):
        await repository.archive_and_fork(
            original.session_id,
            "before invalid duration",
            invalid_constraints,
        )

    sessions = await repository.list(include_archived=True)
    assert [session.session_id for session in sessions] == [original.session_id]
    assert sessions[0].status == "active"


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


def budget_band(basis: str = "per_trip") -> BudgetBand:
    return BudgetBand(
        currency="CNY",
        low=100,
        high=200,
        confidence="medium",
        basis=basis,
    )


def preferences() -> Preference:
    return Preference(
        area_vibe="central and walkable",
        quiet_vs_lively="balanced",
        stay_type="hotel",
        willing_to_change_hotels=False,
        intercity_transport_preference="rail",
        early_departure_tolerance="medium",
        transfer_tolerance="low",
        pay_more_to_save_time=True,
    )


def stay_recommendation() -> StayRecommendation:
    area = AreaSummary(
        id="area_1",
        name="People Square",
        vibe_tags=["central"],
        note="Central base",
        center={"lat": 31.23, "lng": 121.47},
    )
    option = StayOption(
        id="stay_primary",
        area=area,
        fit_reason="Short transfers",
        price_band=budget_band(),
        sample_hotels=[],
    )
    return StayRecommendation(
        primary=option,
        alternatives=[],
        user_override_id=None,
    )


def transport_recommendation() -> TransportRecommendation:
    band = budget_band()
    return TransportRecommendation(
        arrival={
            "mode": "rail",
            "duration_minutes": 300,
            "cost_band": band,
            "note": None,
        },
        departure={
            "mode": "rail",
            "duration_minutes": 300,
            "cost_band": band,
            "note": None,
        },
        intracity={
            "primary_mode": "transit",
            "daily_cost_band": budget_band("per_day"),
            "note": None,
        },
        tradeoffs=[],
    )


def validator_issue() -> ValidatorIssue:
    return ValidatorIssue(
        code="DAY_OVERLOADED",
        severity="warning",
        scope={"type": "day", "day_index": 1},
        message="Day 1 may feel dense.",
        suggested_action="Move one stop.",
    )


def itinerary(session_id: str) -> Itinerary:
    band = budget_band()
    return Itinerary(
        id="itinerary_1",
        session_id=session_id,
        days=[],
        budget=BudgetSummary(
            currency="CNY",
            transport=band,
            stay=band,
            food=band,
            attractions=band,
            other=band,
            total=band,
            user_budget=5000,
            overrun_flag=False,
        ),
        validator_issues=[],
        version=1,
    )


async def test_updates_discovery_preferences_itinerary_and_conversation(
    tmp_path: Path,
) -> None:
    store_path = tmp_path / "sessions.json"
    repository = FileSessionRepository(store_path)
    session = await repository.create(hard_constraints())
    expected_preferences = preferences()
    expected_itinerary = itinerary(session.session_id)
    issue = validator_issue()
    turn = ConversationTurn(
        id="turn_1",
        raw_text="Make day two easier.",
        classification=None,
        created_at=datetime(2026, 5, 7, tzinfo=timezone.utc),
    )

    await repository.update_discovery(
        session.session_id,
        DiscoveryState(payload=None, selected_card_ids=["card_1"]),
    )
    await repository.update_preferences(session.session_id, expected_preferences)
    await repository.write_itinerary(
        session.session_id,
        expected_itinerary,
        [issue],
    )
    await repository.append_conversation_turn(
        session.session_id,
        turn,
    )

    loaded = await FileSessionRepository(store_path).get(session.session_id)

    assert loaded is not None
    assert loaded.discovery_state is not None
    assert loaded.discovery_state.selected_card_ids == ["card_1"]
    assert loaded.preferences == expected_preferences
    assert loaded.itinerary is not None
    assert loaded.itinerary.id == "itinerary_1"
    assert loaded.itinerary.session_id == session.session_id
    assert loaded.itinerary.validator_issues == [issue]
    assert loaded.validator_issues == [issue]
    assert loaded.conversation_history == [turn]


async def test_last_write_wins_for_repeated_discovery_updates(
    tmp_path: Path,
) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")
    session = await repository.create(hard_constraints())

    await repository.update_discovery(
        session.session_id,
        DiscoveryState(payload=None, selected_card_ids=["old_card"]),
    )
    updated = await repository.update_discovery(
        session.session_id,
        DiscoveryState(payload=None, selected_card_ids=["new_card"]),
    )

    assert updated.discovery_state is not None
    assert updated.discovery_state.selected_card_ids == ["new_card"]


async def test_writes_stay_transport_and_stay_override(
    tmp_path: Path,
) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")
    session = await repository.create(hard_constraints())

    await repository.update_stay_recommendation(
        session.session_id,
        stay_recommendation(),
    )
    await repository.update_transport_recommendation(
        session.session_id,
        transport_recommendation(),
    )
    updated = await repository.update_stay_override(
        session.session_id,
        "stay_primary",
    )

    assert updated.stay_recommendation is not None
    assert updated.stay_recommendation.user_override_id == "stay_primary"
    assert updated.transport_recommendation is not None
    assert updated.transport_recommendation.arrival.mode == "rail"


async def test_stay_override_requires_stay_recommendation(
    tmp_path: Path,
) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")
    session = await repository.create(hard_constraints())

    with pytest.raises(SessionStoreError, match="no stay recommendation"):
        await repository.update_stay_override(session.session_id, "stay_primary")


async def test_reset_to_step_clears_downstream_state_and_preserves_id(
    tmp_path: Path,
) -> None:
    store_path = tmp_path / "sessions.json"
    repository = FileSessionRepository(store_path)
    session = await repository.create(hard_constraints())
    issue = validator_issue()
    turn = ConversationTurn(
        id="turn_1",
        raw_text="Keep the quieter hotel note.",
        classification=None,
        created_at=datetime(2026, 5, 7, tzinfo=timezone.utc),
    )

    await repository.update_discovery(
        session.session_id,
        DiscoveryState(payload=None, selected_card_ids=["card_1"]),
    )
    await repository.update_preferences(session.session_id, preferences())
    await repository.update_stay_recommendation(
        session.session_id,
        stay_recommendation(),
    )
    await repository.update_transport_recommendation(
        session.session_id,
        transport_recommendation(),
    )
    await repository.write_itinerary(
        session.session_id,
        itinerary(session.session_id),
        [issue],
    )
    await repository.append_conversation_turn(session.session_id, turn)

    reset = await repository.reset_to_step(
        session.session_id,
        "discovery",
        hard_constraints(total_budget=4500),
    )

    assert reset.session_id == session.session_id
    assert reset.hard_constraints.total_budget == 4500
    assert reset.discovery_state is None
    assert reset.preferences is None
    assert reset.stay_recommendation is None
    assert reset.transport_recommendation is None
    assert reset.itinerary is None
    assert reset.validator_issues == []
    assert reset.conversation_history == [turn]

    loaded = await FileSessionRepository(store_path).get(session.session_id)

    assert loaded is not None
    assert loaded.session_id == session.session_id
    assert loaded.hard_constraints.total_budget == 4500
    assert loaded.discovery_state is None
    assert loaded.preferences is None
    assert loaded.stay_recommendation is None
    assert loaded.transport_recommendation is None
    assert loaded.itinerary is None
    assert loaded.validator_issues == []
    assert loaded.conversation_history == [turn]


async def test_archive_and_fork_archives_original_and_returns_active_child(
    tmp_path: Path,
) -> None:
    store_path = tmp_path / "sessions.json"
    repository = FileSessionRepository(store_path)
    original = await repository.create(hard_constraints())

    fork = await repository.archive_and_fork(
        original.session_id,
        "before budget cut",
        hard_constraints(total_budget=3000),
    )
    reloaded_repository = FileSessionRepository(store_path)
    archived = await reloaded_repository.get(original.session_id)
    loaded_fork = await reloaded_repository.get(fork.session_id)

    assert archived is not None
    assert archived.session_id == original.session_id
    assert archived.status == "archived"
    assert archived.snapshot_label == "before budget cut"
    assert loaded_fork is not None
    assert loaded_fork.status == "active"
    assert loaded_fork.parent_session_id == original.session_id
    assert loaded_fork.hard_constraints.total_budget == 3000
    assert loaded_fork.session_id != original.session_id


async def test_archived_sessions_reject_mutations_except_snapshot_label(
    tmp_path: Path,
) -> None:
    store_path = tmp_path / "sessions.json"
    repository = FileSessionRepository(store_path)
    original = await repository.create(hard_constraints())
    await repository.archive_and_fork(
        original.session_id,
        "snapshot",
        hard_constraints(total_budget=3000),
    )

    with pytest.raises(ArchivedSessionMutationError, match="archived"):
        await repository.update_discovery(
            original.session_id,
            DiscoveryState(payload=None, selected_card_ids=["card_1"]),
        )
    with pytest.raises(ArchivedSessionMutationError, match="archived"):
        await repository.update_preferences(original.session_id, preferences())
    with pytest.raises(ArchivedSessionMutationError, match="archived"):
        await repository.update_stay_recommendation(
            original.session_id,
            stay_recommendation(),
        )
    with pytest.raises(ArchivedSessionMutationError, match="archived"):
        await repository.update_transport_recommendation(
            original.session_id,
            transport_recommendation(),
        )
    with pytest.raises(ArchivedSessionMutationError, match="archived"):
        await repository.write_itinerary(
            original.session_id,
            itinerary(original.session_id),
            [validator_issue()],
        )
    with pytest.raises(ArchivedSessionMutationError, match="archived"):
        await repository.append_conversation_turn(
            original.session_id,
            ConversationTurn(
                id="turn_1",
                raw_text="Can we make this cheaper?",
                classification=None,
                created_at=datetime(2026, 5, 7, tzinfo=timezone.utc),
            ),
        )
    with pytest.raises(ArchivedSessionMutationError, match="archived"):
        await repository.update_stay_override(
            original.session_id,
            "stay_primary",
        )
    with pytest.raises(ArchivedSessionMutationError, match="archived"):
        await repository.reset_to_step(original.session_id, "intake")

    relabeled = await repository.update_snapshot_label(
        original.session_id,
        "final snapshot",
    )

    assert relabeled.status == "archived"
    assert relabeled.snapshot_label == "final snapshot"

    loaded = await FileSessionRepository(store_path).get(original.session_id)

    assert loaded is not None
    assert loaded.status == "archived"
    assert loaded.snapshot_label == "final snapshot"


async def test_archive_and_fork_rejects_archived_original(
    tmp_path: Path,
) -> None:
    store_path = tmp_path / "sessions.json"
    repository = FileSessionRepository(store_path)
    original = await repository.create(hard_constraints())
    fork = await repository.archive_and_fork(
        original.session_id,
        "snapshot",
        hard_constraints(total_budget=3000),
    )

    with pytest.raises(ArchivedSessionMutationError, match="archived"):
        await repository.archive_and_fork(
            original.session_id,
            "second snapshot",
            hard_constraints(total_budget=2000),
        )

    reloaded_repository = FileSessionRepository(store_path)
    sessions = await reloaded_repository.list(include_archived=True)
    session_ids = {session.session_id for session in sessions}
    archived_original = await reloaded_repository.get(original.session_id)
    loaded_fork = await reloaded_repository.get(fork.session_id)

    assert len(sessions) == 2
    assert session_ids == {original.session_id, fork.session_id}
    assert archived_original is not None
    assert archived_original.status == "archived"
    assert archived_original.snapshot_label == "snapshot"
    assert loaded_fork is not None
    assert loaded_fork.status == "active"
    assert loaded_fork.parent_session_id == original.session_id
    assert loaded_fork.hard_constraints.total_budget == 3000


async def test_missing_session_mutation_raises_not_found(tmp_path: Path) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")

    with pytest.raises(SessionNotFoundError, match="missing"):
        await repository.update_preferences("missing", preferences())


def test_copied_web_session_fixture_validates_against_pydantic() -> None:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert isinstance(raw, dict)
    assert raw
    for session_id, payload in raw.items():
        session = PlanningSession.model_validate(payload)
        assert session.session_id == session_id


@pytest.mark.parametrize("run_number", range(50))
async def test_concurrent_writes_keep_store_readable(
    tmp_path: Path,
    run_number: int,
) -> None:
    store_path = tmp_path / f"sessions-{run_number}.json"
    repository = FileSessionRepository(store_path)

    sessions = await asyncio.gather(
        *[repository.create(hard_constraints()) for _ in range(8)]
    )
    await asyncio.gather(
        *[
            repository.update_discovery(
                session.session_id,
                DiscoveryState(
                    payload=None,
                    selected_card_ids=[f"card_{index}"],
                ),
            )
            for index, session in enumerate(sessions)
        ]
    )

    loaded = await asyncio.gather(
        *[repository.get(session.session_id) for session in sessions]
    )

    for index, session in enumerate(loaded):
        assert session is not None
        assert session.discovery_state is not None
        assert session.discovery_state.selected_card_ids == [f"card_{index}"]

    assert len(await repository.list()) == 8
    json.loads(store_path.read_text(encoding="utf-8"))
