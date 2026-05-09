"""File-backed PlanningSession repository."""
from __future__ import annotations

import asyncio
import json
import os
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping
from uuid import uuid4

from pydantic import ValidationError

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
from app.persistence.session_repository import (
    ArchivedSessionMutationError,
    ResetStep,
    SessionNotFoundError,
    SessionStoreError,
)

SessionStore = dict[str, PlanningSession]

_LOCKS: dict[Path, asyncio.Lock] = {}
_LOCKS_GUARD = asyncio.Lock()


class FileSessionRepository:
    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    async def create(self, hard_constraints: HardConstraints) -> PlanningSession:
        async with await self._lock():
            store = await self._read_store()
            now = _utc_now()
            session = PlanningSession(
                session_id=f"session_{uuid4()}",
                hard_constraints=hard_constraints,
                discovery_state=None,
                preferences=None,
                stay_recommendation=None,
                transport_recommendation=None,
                itinerary=None,
                conversation_history=[],
                validator_issues=[],
                parent_session_id=None,
                snapshot_label=None,
                status="active",
                created_at=now,
                updated_at=now,
            )
            store[session.session_id] = session
            await self._write_store(store)
            return session

    async def get(self, session_id: str) -> PlanningSession | None:
        store = await self._read_store()
        return store.get(session_id)

    async def list(
        self, *, include_archived: bool = False
    ) -> list[PlanningSession]:
        store = await self._read_store()
        sessions = list(store.values())
        if not include_archived:
            sessions = [
                session for session in sessions if session.status != "archived"
            ]
        return sorted(sessions, key=lambda session: session.updated_at, reverse=True)

    async def update_discovery(
        self, session_id: str, discovery_state: DiscoveryState
    ) -> PlanningSession:
        return await self._update_active(
            session_id,
            lambda session: session.model_copy(
                update={"discovery_state": discovery_state}
            ),
        )

    async def update_preferences(
        self, session_id: str, preferences: Preference
    ) -> PlanningSession:
        return await self._update_active(
            session_id,
            lambda session: session.model_copy(update={"preferences": preferences}),
        )

    async def update_stay_recommendation(
        self, session_id: str, stay_recommendation: StayRecommendation
    ) -> PlanningSession:
        return await self._update_active(
            session_id,
            lambda session: session.model_copy(
                update={"stay_recommendation": stay_recommendation}
            ),
        )

    async def update_transport_recommendation(
        self,
        session_id: str,
        transport_recommendation: TransportRecommendation,
    ) -> PlanningSession:
        return await self._update_active(
            session_id,
            lambda session: session.model_copy(
                update={"transport_recommendation": transport_recommendation}
            ),
        )

    async def write_itinerary(
        self,
        session_id: str,
        itinerary: Itinerary,
        validator_issues: list[ValidatorIssue],
    ) -> PlanningSession:
        itinerary_with_issues = _validate_itinerary_for_write(
            itinerary.model_copy(update={"validator_issues": validator_issues})
        )
        return await self._update_active(
            session_id,
            lambda session: session.model_copy(
                update={
                    "itinerary": itinerary_with_issues,
                    "validator_issues": validator_issues,
                }
            ),
        )

    async def append_conversation_turn(
        self, session_id: str, turn: ConversationTurn
    ) -> PlanningSession:
        return await self._update_active(
            session_id,
            lambda session: session.model_copy(
                update={
                    "conversation_history": [
                        *session.conversation_history,
                        turn,
                    ]
                }
            ),
        )

    async def update_stay_override(
        self, session_id: str, stay_option_id: str | None
    ) -> PlanningSession:
        def updater(session: PlanningSession) -> PlanningSession:
            if session.stay_recommendation is None:
                raise SessionStoreError(
                    f"Session {session_id} has no stay recommendation"
                )
            return session.model_copy(
                update={
                    "stay_recommendation": session.stay_recommendation.model_copy(
                        update={"user_override_id": stay_option_id}
                    )
                }
            )

        return await self._update_active(session_id, updater)

    async def reset_to_step(
        self,
        session_id: str,
        step: ResetStep,
        updated_constraints: HardConstraints | None = None,
    ) -> PlanningSession:
        if step not in ("intake", "discovery"):
            raise SessionStoreError(f"Unsupported reset step: {step}")
        return await self._update_active(
            session_id,
            lambda session: session.model_copy(
                update={
                    "hard_constraints": updated_constraints
                    or session.hard_constraints,
                    "discovery_state": None,
                    "preferences": None,
                    "stay_recommendation": None,
                    "transport_recommendation": None,
                    "itinerary": None,
                    "validator_issues": [],
                }
            ),
        )

    async def archive_and_fork(
        self,
        session_id: str,
        snapshot_label: str,
        new_hard_constraints: HardConstraints,
    ) -> PlanningSession:
        async with await self._lock():
            store = await self._read_store()
            original = _require_session(store, session_id)
            _assert_active(original)
            now = _utc_now()
            store[session_id] = _validate_session_for_write(
                original.model_copy(
                    update={
                        "status": "archived",
                        "snapshot_label": snapshot_label,
                        "updated_at": now,
                    }
                )
            )
            fork = PlanningSession(
                session_id=f"session_{uuid4()}",
                hard_constraints=new_hard_constraints,
                discovery_state=None,
                preferences=None,
                stay_recommendation=None,
                transport_recommendation=None,
                itinerary=None,
                conversation_history=[],
                validator_issues=[],
                parent_session_id=session_id,
                snapshot_label=None,
                status="active",
                created_at=now,
                updated_at=now,
            )
            store[fork.session_id] = fork
            await self._write_store(store)
            return fork

    async def update_snapshot_label(
        self, session_id: str, snapshot_label: str
    ) -> PlanningSession:
        async with await self._lock():
            store = await self._read_store()
            session = _require_session(store, session_id)
            updated = _touch(
                session.model_copy(update={"snapshot_label": snapshot_label})
            )
            updated = _validate_session_for_write(updated)
            store[session_id] = updated
            await self._write_store(store)
            return updated

    async def _update_active(
        self,
        session_id: str,
        updater: Callable[[PlanningSession], PlanningSession],
    ) -> PlanningSession:
        async with await self._lock():
            store = await self._read_store()
            session = _require_session(store, session_id)
            _assert_active(session)
            updated = _touch(updater(session))
            updated = _validate_session_for_write(updated)
            store[session_id] = updated
            await self._write_store(store)
            return updated

    async def _read_store(self) -> SessionStore:
        try:
            content = await asyncio.to_thread(
                self._file_path.read_text,
                encoding="utf-8",
            )
        except FileNotFoundError:
            return {}

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            await self._quarantine_corrupt_store()
            return {}

        if not isinstance(parsed, dict):
            raise SessionStoreError("Session store must be a JSON object")

        store: SessionStore = {}
        for key, payload in parsed.items():
            if not isinstance(key, str):
                raise SessionStoreError("Session store keys must be strings")
            try:
                session = PlanningSession.model_validate(payload)
            except ValidationError as exc:
                raise SessionStoreError(
                    f"Session {key} is not a valid PlanningSession"
                ) from exc
            if session.session_id != key:
                raise SessionStoreError(
                    f"Session key {key} does not match payload id "
                    f"{session.session_id}"
                )
            store[key] = session
        return store

    async def _write_store(self, store: SessionStore) -> None:
        serializable = {
            session_id: session.model_dump(mode="json")
            for session_id, session in store.items()
        }
        await asyncio.to_thread(self._write_json_atomically, serializable)

    def _write_json_atomically(self, serializable: dict[str, object]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._file_path.with_name(
            f"{self._file_path.name}.{os.getpid()}.{uuid4()}.tmp"
        )
        try:
            temp_path.write_text(
                f"{json.dumps(serializable, ensure_ascii=False, indent=2)}\n",
                encoding="utf-8",
            )
            os.replace(temp_path, self._file_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    async def _quarantine_corrupt_store(self) -> None:
        corrupt_path = self._file_path.with_name(
            f"{self._file_path.name}.corrupt-{int(time.time() * 1000)}"
        )
        try:
            await asyncio.to_thread(os.replace, self._file_path, corrupt_path)
        except FileNotFoundError:
            return

    async def _lock(self) -> asyncio.Lock:
        path = self._file_path.resolve()
        async with _LOCKS_GUARD:
            lock = _LOCKS.get(path)
            if lock is None:
                lock = asyncio.Lock()
                _LOCKS[path] = lock
            return lock


def default_session_store_path(
    env: Mapping[str, str] | None = None,
) -> Path:
    source = env if env is not None else os.environ
    data_dir = source.get("SESSION_DATA_DIR")
    if data_dir:
        return Path(data_dir) / "sessions.json"
    return Path(__file__).resolve().parents[2] / ".data" / "sessions.json"


_DEFAULT_REPOSITORIES: dict[Path, FileSessionRepository] = {}


def create_default_session_repository(
    env: Mapping[str, str] | None = None,
) -> FileSessionRepository:
    return FileSessionRepository(default_session_store_path(env))


def get_default_session_repository(
    env: Mapping[str, str] | None = None,
) -> FileSessionRepository:
    path = default_session_store_path(env).resolve()
    repository = _DEFAULT_REPOSITORIES.get(path)
    if repository is None:
        repository = FileSessionRepository(path)
        _DEFAULT_REPOSITORIES[path] = repository
    return repository


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _touch(session: PlanningSession) -> PlanningSession:
    return session.model_copy(update={"updated_at": _utc_now()})


def _validate_session_for_write(session: PlanningSession) -> PlanningSession:
    try:
        return PlanningSession.model_validate(_dump_for_validation(session))
    except ValidationError as exc:
        raise SessionStoreError("Mutated session is not a valid PlanningSession") from exc


def _validate_itinerary_for_write(itinerary: Itinerary) -> Itinerary:
    try:
        return Itinerary.model_validate(_dump_for_validation(itinerary))
    except ValidationError as exc:
        raise SessionStoreError("Mutated itinerary is not a valid Itinerary") from exc


def _dump_for_validation(session: PlanningSession | Itinerary) -> dict[str, object]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return session.model_dump(mode="json")


def _require_session(store: SessionStore, session_id: str) -> PlanningSession:
    session = store.get(session_id)
    if session is None:
        raise SessionNotFoundError(f"Session {session_id} not found")
    return session


def _assert_active(session: PlanningSession) -> None:
    if session.status == "archived":
        raise ArchivedSessionMutationError(
            f"Session {session.session_id} is archived"
        )
