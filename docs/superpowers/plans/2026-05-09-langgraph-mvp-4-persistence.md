# LangGraph MVP — Plan 4: Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the TypeScript session repository into Python so Plan 5 LangGraph nodes and Plan 6 FastAPI routes can persist `PlanningSession` state through one file-backed repository.

**Architecture:** Persistence is a narrow async repository layer over Pydantic `PlanningSession` objects. The file implementation stores a JSON object keyed by `session_id`, validates every loaded session with `api/app/models/schemas.py`, serializes with `model_dump(mode="json")`, and protects write mutations with a per-file `asyncio.Lock` plus atomic temp-file replacement. This plan does not add FastAPI routes, LangGraph nodes, or frontend changes.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, pytest-asyncio, standard-library `asyncio`, `pathlib`, `json`, `os.replace`, `uuid`, `datetime`. **No new dependency**.

---

## Scope

**In scope:**
- Add `api/app/persistence/` package.
- Add repository protocol, typed repository errors, and a file-backed implementation.
- Match the current TypeScript repository semantics from `web/src/server/persistence/`.
- Store sessions at `api/.data/sessions.json` by default.
- Support `SESSION_DATA_DIR` override for tests, local runs, and future route wiring.
- Copy the current development session store from `web/.data/sessions.json` into `api/tests/fixtures/sessions.json` when present.
- Test create/get/list, all session mutation methods, archived-session rules, corrupt JSON quarantine, atomic writes, and concurrent mutation stability.

**Out of scope:**
- No FastAPI session routes. Plan 6 owns route registration and HTTP behavior.
- No LangGraph state or graph nodes. Plan 5 owns graph integration.
- No frontend cookie helper migration. Plan 7 owns web cutover cleanup.
- No SQLite/Postgres adapter.
- No deletion of `web/src/server/persistence/` yet; it remains the reference implementation until Plan 7.

---

## Reference Files

**Read-only TypeScript sources:**
- `web/src/server/persistence/sessionRepository.ts`
- `web/src/server/persistence/fileSessionRepository.ts`
- `web/src/server/persistence/sessionRepository.test.ts`
- `web/.data/sessions.json`

**Python contracts already available from Plan 1:**
- `api/app/models/schemas.py`

**Roadmap anchor:**
- `docs/superpowers/plans/2026-05-09-langgraph-mvp-roadmap.md`

---

## File Structure

**Create:**
- `api/app/persistence/__init__.py` — package exports.
- `api/app/persistence/session_repository.py` — `SessionRepository` protocol and typed errors.
- `api/app/persistence/file_session_repository.py` — JSON file implementation, default path helper, default repository factory.
- `api/tests/persistence/__init__.py`
- `api/tests/persistence/test_session_repository.py`
- `api/tests/fixtures/sessions.json` — copied from `web/.data/sessions.json` when it exists.

**Modify:**
- None outside the new persistence package and tests.

**Untouched:**
- `api/app/main.py`
- `api/app/routes/{discover,plan}.py`
- `api/app/config.py`
- `web/src/server/persistence/*`

---

## Public API Decisions

`session_repository.py` exposes this protocol:

```python
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
        step: Literal["intake", "discovery"],
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
```

Error classes:
- `SessionRepositoryError`
- `SessionNotFoundError`
- `ArchivedSessionMutationError`
- `SessionStoreError`

Default path behavior:
- `SESSION_DATA_DIR=/tmp/travel-data` -> `/tmp/travel-data/sessions.json`
- no env override -> `<repo>/api/.data/sessions.json`

Mutation behavior:
- Mutations on archived sessions raise `ArchivedSessionMutationError`.
- `update_snapshot_label(...)` is allowed for archived sessions.
- `archive_and_fork(...)` marks the original as `archived` and returns a new active child session with `parent_session_id` set.
- `write_itinerary(...)` writes validator issues both to `session.itinerary.validator_issues` and `session.validator_issues`, matching the TS repository.
- `reset_to_step(...)` clears downstream fields and preserves `session_id`, matching the TS repository.

Corrupt store behavior:
- Missing file reads as an empty store.
- Invalid JSON is renamed to `sessions.json.corrupt-<timestamp>` and reads as an empty store.
- JSON that is syntactically valid but not a session object raises `SessionStoreError` so data-shape bugs are visible.

---

## Task 0 — Setup

**Files:**
- Create: `api/app/persistence/__init__.py`
- Create: `api/tests/persistence/__init__.py`

- [ ] **Step 0.1: Create package directories**

```bash
mkdir -p api/app/persistence api/tests/persistence
touch api/app/persistence/__init__.py api/tests/persistence/__init__.py
```

- [ ] **Step 0.2: Run current backend baseline**

Run:

```bash
cd api && uv run pytest -v
```

Expected: all current tests pass. At the time this plan was written the expected count after Plan 3 is `173 passed`.

- [ ] **Step 0.3: Commit scaffold**

```bash
git add api/app/persistence/__init__.py api/tests/persistence/__init__.py
git commit -m "chore(api): scaffold persistence package"
```

---

## Task 1 — Repository Contract And Errors

**Files:**
- Create: `api/app/persistence/session_repository.py`
- Modify: `api/app/persistence/__init__.py`
- Create: `api/tests/persistence/test_session_repository.py`

- [ ] **Step 1.1: Write failing contract tests**

Create `api/tests/persistence/test_session_repository.py` with this initial content:

```python
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
```

- [ ] **Step 1.2: Verify the test fails**

Run:

```bash
cd api && uv run pytest tests/persistence/test_session_repository.py -v
```

Expected: fail with `ModuleNotFoundError` or `ImportError` for `app.persistence.session_repository`.

- [ ] **Step 1.3: Implement `session_repository.py`**

Create `api/app/persistence/session_repository.py`:

```python
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
```

- [ ] **Step 1.4: Export persistence public surface**

Replace `api/app/persistence/__init__.py`:

```python
"""Persistence interfaces and implementations."""

from app.persistence.session_repository import (
    ArchivedSessionMutationError,
    ResetStep,
    SessionNotFoundError,
    SessionRepository,
    SessionRepositoryError,
    SessionStoreError,
)

__all__ = [
    "ArchivedSessionMutationError",
    "ResetStep",
    "SessionNotFoundError",
    "SessionRepository",
    "SessionRepositoryError",
    "SessionStoreError",
]
```

- [ ] **Step 1.5: Verify contract tests pass**

Run:

```bash
cd api && uv run pytest tests/persistence/test_session_repository.py -v
```

Expected: 2 passed.

- [ ] **Step 1.6: Commit contract**

```bash
git add api/app/persistence/__init__.py api/app/persistence/session_repository.py api/tests/persistence/test_session_repository.py
git commit -m "feat(api): add session repository contract"
```

---

## Task 2 — File Repository Create, Get, List, And Store I/O

**Files:**
- Create: `api/app/persistence/file_session_repository.py`
- Modify: `api/app/persistence/__init__.py`
- Modify: `api/tests/persistence/test_session_repository.py`

- [ ] **Step 2.1: Add failing tests and fixtures**

Replace the import section at the top of `api/tests/persistence/test_session_repository.py` with:

```python
import json
from pathlib import Path
from typing import get_args

import pytest

from app.models.schemas import HardConstraints, PlanningSession
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
```

Keep the two Task 1 tests, then append this below them:

```python


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
```

- [ ] **Step 2.2: Verify new tests fail**

Run:

```bash
cd api && uv run pytest tests/persistence/test_session_repository.py -v
```

Expected: fail with `ModuleNotFoundError: No module named 'app.persistence.file_session_repository'`.

- [ ] **Step 2.3: Implement initial file repository**

Create `api/app/persistence/file_session_repository.py`:

```python
"""File-backed PlanningSession repository."""
from __future__ import annotations

import asyncio
import json
import os
import time
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
        itinerary_with_issues = itinerary.model_copy(
            update={"validator_issues": validator_issues}
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
                    "hard_constraints": (
                        updated_constraints or session.hard_constraints
                    ),
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
            store[session_id] = original.model_copy(
                update={
                    "status": "archived",
                    "snapshot_label": snapshot_label,
                    "updated_at": now,
                }
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
            updated = _touch(session.model_copy(update={"snapshot_label": snapshot_label}))
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
                    f"Session key {key} does not match payload id {session.session_id}"
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
```

- [ ] **Step 2.4: Export file repository**

Replace `api/app/persistence/__init__.py`:

```python
"""Persistence interfaces and implementations."""

from app.persistence.file_session_repository import (
    FileSessionRepository,
    create_default_session_repository,
    default_session_store_path,
    get_default_session_repository,
)
from app.persistence.session_repository import (
    ArchivedSessionMutationError,
    ResetStep,
    SessionNotFoundError,
    SessionRepository,
    SessionRepositoryError,
    SessionStoreError,
)

__all__ = [
    "ArchivedSessionMutationError",
    "FileSessionRepository",
    "ResetStep",
    "SessionNotFoundError",
    "SessionRepository",
    "SessionRepositoryError",
    "SessionStoreError",
    "create_default_session_repository",
    "default_session_store_path",
    "get_default_session_repository",
]
```

- [ ] **Step 2.5: Run focused tests**

Run:

```bash
cd api && uv run pytest tests/persistence/test_session_repository.py -v
```

Expected: tests introduced so far pass.

- [ ] **Step 2.6: Commit file repository base**

```bash
git add api/app/persistence/__init__.py api/app/persistence/file_session_repository.py api/tests/persistence/test_session_repository.py
git commit -m "feat(api): add file-backed session repository"
```

---

## Task 3 — Update Methods For Discovery, Preferences, Recommendations, Itinerary, Conversation

**Files:**
- Modify: `api/tests/persistence/test_session_repository.py`
- Modify: `api/app/persistence/file_session_repository.py` only if tests reveal a gap in Task 2 implementation.

- [ ] **Step 3.1: Add failing mutation tests**

Add `from datetime import datetime, timezone` to the top import section, and extend the existing `from app.models.schemas import (...)` import so it contains these names:

```python
from app.models.schemas import (
    AreaSummary,
    BudgetBand,
    BudgetSummary,
    ConversationTurn,
    DiscoveryState,
    Itinerary,
    Preference,
    StayOption,
    StayRecommendation,
    TransportRecommendation,
    ValidatorIssue,
)
```

Then append this below the Task 2 tests:

```python


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
    repository = FileSessionRepository(tmp_path / "sessions.json")
    session = await repository.create(hard_constraints())

    await repository.update_discovery(
        session.session_id,
        DiscoveryState(payload=None, selected_card_ids=["card_1"]),
    )
    await repository.update_preferences(session.session_id, preferences())
    issue = validator_issue()
    await repository.write_itinerary(
        session.session_id,
        itinerary(session.session_id),
        [issue],
    )
    updated = await repository.append_conversation_turn(
        session.session_id,
        ConversationTurn(
            id="turn_1",
            raw_text="Make day two easier.",
            classification=None,
            created_at=datetime(2026, 5, 7, tzinfo=timezone.utc),
        ),
    )

    assert updated.discovery_state is not None
    assert updated.discovery_state.selected_card_ids == ["card_1"]
    assert updated.preferences is not None
    assert updated.itinerary is not None
    assert updated.itinerary.validator_issues == [issue]
    assert updated.validator_issues == [issue]
    assert len(updated.conversation_history) == 1


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


async def test_missing_session_mutation_raises_not_found(tmp_path: Path) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")

    with pytest.raises(SessionNotFoundError, match="missing"):
        await repository.update_preferences("missing", preferences())
```

- [ ] **Step 3.2: Run tests**

Run:

```bash
cd api && uv run pytest tests/persistence/test_session_repository.py -v
```

Expected: if Task 2 implementation already included the methods, all tests pass. If any test fails, adjust only `api/app/persistence/file_session_repository.py` to match the tested behavior.

- [ ] **Step 3.3: Commit mutation coverage**

```bash
git add api/app/persistence/file_session_repository.py api/tests/persistence/test_session_repository.py
git commit -m "test(api): cover session repository mutations"
```

---

## Task 4 — Reset, Archive/Fork, Snapshot Relabel, And Archived Mutation Rules

**Files:**
- Modify: `api/tests/persistence/test_session_repository.py`
- Modify: `api/app/persistence/file_session_repository.py` only if tests reveal a gap.

- [ ] **Step 4.1: Add failing lifecycle tests**

Append this to `api/tests/persistence/test_session_repository.py`:

```python
async def test_reset_to_step_clears_downstream_state_and_preserves_id(
    tmp_path: Path,
) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")
    session = await repository.create(hard_constraints())
    await repository.update_discovery(
        session.session_id,
        DiscoveryState(payload=None, selected_card_ids=["card_1"]),
    )
    await repository.update_preferences(session.session_id, preferences())
    await repository.write_itinerary(
        session.session_id,
        itinerary(session.session_id),
        [validator_issue()],
    )

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


async def test_archive_and_fork_archives_original_and_returns_active_child(
    tmp_path: Path,
) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")
    original = await repository.create(hard_constraints())

    fork = await repository.archive_and_fork(
        original.session_id,
        "before budget cut",
        hard_constraints(total_budget=3000),
    )
    archived = await repository.get(original.session_id)

    assert archived is not None
    assert archived.status == "archived"
    assert archived.snapshot_label == "before budget cut"
    assert fork.status == "active"
    assert fork.parent_session_id == original.session_id
    assert fork.hard_constraints.total_budget == 3000


async def test_archived_sessions_reject_mutations_except_snapshot_label(
    tmp_path: Path,
) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")
    original = await repository.create(hard_constraints())
    await repository.archive_and_fork(
        original.session_id,
        "snapshot",
        hard_constraints(),
    )

    with pytest.raises(ArchivedSessionMutationError, match="archived"):
        await repository.update_preferences(original.session_id, preferences())

    relabeled = await repository.update_snapshot_label(
        original.session_id,
        "final snapshot",
    )

    assert relabeled.status == "archived"
    assert relabeled.snapshot_label == "final snapshot"


async def test_archive_and_fork_rejects_archived_original(
    tmp_path: Path,
) -> None:
    repository = FileSessionRepository(tmp_path / "sessions.json")
    original = await repository.create(hard_constraints())
    await repository.archive_and_fork(
        original.session_id,
        "snapshot",
        hard_constraints(),
    )

    with pytest.raises(ArchivedSessionMutationError, match="archived"):
        await repository.archive_and_fork(
            original.session_id,
            "second snapshot",
            hard_constraints(total_budget=2000),
        )
```

- [ ] **Step 4.2: Run lifecycle tests**

Run:

```bash
cd api && uv run pytest tests/persistence/test_session_repository.py -v
```

Expected: all persistence tests pass.

- [ ] **Step 4.3: Commit lifecycle behavior**

```bash
git add api/app/persistence/file_session_repository.py api/tests/persistence/test_session_repository.py
git commit -m "test(api): cover session repository lifecycle rules"
```

---

## Task 5 — Concurrent Write Stability And Fixture Migration

**Files:**
- Modify: `api/tests/persistence/test_session_repository.py`
- Create: `api/tests/fixtures/sessions.json`

- [ ] **Step 5.1: Copy current development fixture**

Run:

```bash
mkdir -p api/tests/fixtures
cp web/.data/sessions.json api/tests/fixtures/sessions.json
```

Expected: `api/tests/fixtures/sessions.json` exists and contains a JSON object keyed by `session_...`.

- [ ] **Step 5.2: Add fixture and concurrency tests**

Add `import asyncio` to the top import section, then append this to `api/tests/persistence/test_session_repository.py`:

```python
FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "sessions.json"
)


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
    repository = FileSessionRepository(tmp_path / f"sessions-{run_number}.json")

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

    assert all(session is not None for session in loaded)
    assert len(await repository.list()) == 8
    json.loads((tmp_path / f"sessions-{run_number}.json").read_text())
```

- [ ] **Step 5.3: Run persistence tests**

Run:

```bash
cd api && uv run pytest tests/persistence -v
```

Expected: all persistence tests pass. The concurrent write test must complete 50 parametrized runs without corrupting JSON.

- [ ] **Step 5.4: Commit fixture and concurrency coverage**

```bash
git add api/tests/fixtures/sessions.json api/tests/persistence/test_session_repository.py
git commit -m "test(api): cover session fixture and concurrent writes"
```

---

## Task 6 — Final Verification

**Files:**
- No planned source changes unless verification reveals a bug.

- [ ] **Step 6.1: Run persistence tests**

Run:

```bash
cd api && uv run pytest tests/persistence -v
```

Expected: all persistence tests pass.

- [ ] **Step 6.2: Run full backend tests**

Run:

```bash
cd api && uv run pytest -v
```

Expected: all backend tests pass.

- [ ] **Step 6.3: Run ruff**

Run:

```bash
cd api && uv run ruff check app tests/persistence
```

Expected: `All checks passed!`

- [ ] **Step 6.4: Inspect final status**

Run:

```bash
git status --short --branch
git log --oneline -8
```

Expected: working tree is clean after the final commit; recent commits show Task 0-5 persistence commits.

---

## Definition Of Done

- [ ] `api/app/persistence/session_repository.py` defines the repository protocol and typed errors.
- [ ] `api/app/persistence/file_session_repository.py` implements create/get/list and all mutation methods needed by Plan 5/6.
- [ ] Missing store reads as an empty store.
- [ ] Invalid JSON is quarantined.
- [ ] Invalid valid-JSON store shape raises `SessionStoreError`.
- [ ] Archived sessions reject mutations except `update_snapshot_label`.
- [ ] `archive_and_fork` links child sessions through `parent_session_id`.
- [ ] `write_itinerary` stores validator issues both on the itinerary and session.
- [ ] `SESSION_DATA_DIR` controls the default store directory.
- [ ] `api/tests/fixtures/sessions.json` validates against current Pydantic schemas.
- [ ] `cd api && uv run pytest tests/persistence -v` passes.
- [ ] `cd api && uv run pytest -v` passes.
- [ ] `cd api && uv run ruff check app tests/persistence` passes.

---

## Follow-Up Notes For Plan 5

- Plan 5 graph code should depend on `SessionRepository`, not directly on `FileSessionRepository`.
- Graph tests can instantiate `FileSessionRepository(tmp_path / "sessions.json")`.
- Long-running graph execution should append progress events in graph state first; Plan 6 owns exposing those as SSE.
- Adjustment Type C `save_and_start_new` should use `archive_and_fork`.
- Adjustment Type C `replan` should use `reset_to_step`.

## Follow-Up Notes For Plan 6

- Routes should call `get_default_session_repository()` or inject a repository dependency.
- Route tests should set `SESSION_DATA_DIR` to a temp directory before constructing the test app.
- HTTP 404 should map from `SessionNotFoundError`.
- HTTP 409 should map from `ArchivedSessionMutationError`.

---

## Self-Review Checklist

- **Spec coverage:** Roadmap Plan 4 create/get/update/list/archive, JSON file default path, `SESSION_DATA_DIR`, fixture migration, and 50-run concurrent write stability are covered.
- **Placeholder scan:** This plan contains concrete file paths, commands, expected results, code snippets, and commit messages for every task.
- **Type consistency:** All repository methods use types already defined in `api/app/models/schemas.py`; method names use Python snake_case while matching the TypeScript repository behavior.
