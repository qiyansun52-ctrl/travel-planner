# Production Readiness Guardrails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the smallest production-readiness layer that lets the real-provider MVP be safely demoed to real users: env safety checks, request throttling, per-session expensive-operation budgets, local ops summaries, and real smoke gates.

**Architecture:** Keep the current FastAPI + file-backed MVP architecture. Add lightweight `app.ops` modules that sit at the API boundary and do not change graph/provider contracts. Production checks fail early, rate limits protect HTTP ingress, operation budgets protect costly graph entry points, and scripts summarize local JSONL logs without exposing secrets over public API routes.

**Tech Stack:** FastAPI middleware, Pydantic settings, pytest/httpx route tests, existing JSONL metrics/cost logs, Makefile gates, shell smoke scripts.

---

## Scope

Plan19 is a production-readiness pass, not a product expansion. It intentionally does not add authentication, a hosted database, a public dashboard, payments, booking, or a multi-user admin surface. Those belong after this guardrail pass.

Plan19 should make these true:

1. Production mode fails fast when fixture mode, placeholder secrets, or unsafe CORS are configured.
2. HTTP routes have a small in-memory rate limiter suitable for one-process MVP demos.
3. Expensive session operations have per-session budgets so repeated clicks cannot burn unlimited LLM/provider quota.
4. Local metrics and LLM cost logs can be summarized from a CLI without opening raw JSONL files.
5. Real-provider smoke scripts are explicit opt-in and never print secrets.
6. `make regression` remains offline and deterministic; live-provider checks are separate.

---

## File Structure

- Modify: `api/app/config.py`
  - Add production-readiness and guardrail settings.
- Create: `api/app/ops/__init__.py`
  - Export ops helpers.
- Create: `api/app/ops/readiness.py`
  - Validate production env safety and return redacted env status.
- Create: `api/app/ops/rate_limit.py`
  - Add small in-memory sliding-window limiter and FastAPI middleware.
- Create: `api/app/ops/operation_budget.py`
  - Add per-session budget guard for expensive operations.
- Create: `api/app/ops/summary.py`
  - Summarize metrics and LLM cost logs.
- Modify: `api/main.py`
  - Run production readiness checks at startup and install rate-limit middleware.
- Modify: `api/app/routes/_shared.py`
  - Add `guard_expensive_operation(...)` helper.
- Modify: `api/app/routes/discovery.py`
  - Guard discovery generation.
- Modify: `api/app/routes/itinerary.py`
  - Guard itinerary generation, stream generation, and stay override replans.
- Modify: `api/app/routes/adjustments.py`
  - Guard adjustment replans.
- Create: `api/tests/ops/test_readiness.py`
- Create: `api/tests/ops/test_rate_limit.py`
- Create: `api/tests/ops/test_operation_budget.py`
- Create: `api/tests/ops/test_summary.py`
- Modify: `api/tests/routes/test_discovery_preferences.py`
- Modify: `api/tests/routes/test_itinerary.py`
- Modify: `api/tests/routes/test_adjustments.py`
- Modify: `api/tests/test_config.py`
- Modify: `api/.env.example`
- Modify: `docs/mvp-launch-checklist.md`
- Modify: `api/README.md`
- Modify: `README.md`
- Modify: `scripts/check_launch_readiness.py`
- Create: `api/scripts/ops_summary.py`
- Create: `api/scripts/check_production_readiness.py`
- Modify: `Makefile`

---

### Task 1: Add Production Readiness Settings and Checks

**Files:**
- Modify: `api/app/config.py`
- Create: `api/app/ops/__init__.py`
- Create: `api/app/ops/readiness.py`
- Create: `api/tests/ops/test_readiness.py`
- Modify: `api/tests/test_config.py`
- Modify: `api/.env.example`

- [x] **Step 1: Add failing readiness tests**

Create `api/tests/ops/test_readiness.py`:

```python
from __future__ import annotations

import pytest

from app.config import Settings
from app.ops.readiness import (
    ProductionReadinessError,
    assert_production_ready,
    redacted_env_status,
)


def _settings(**overrides: object) -> Settings:
    values = {
        "gemini_api_key": "real-gemini-key",
        "tavily_api_key": "real-tavily-key",
        "gemini_model": "gemini-2.5-flash",
        "environment": "production",
        "cors_origins": "https://travel.example.com",
        "e2e_fixture_mode": False,
        "session_data_dir": "/var/lib/travel-planner",
        "metrics_data_dir": "/var/log/travel-planner",
        "rate_limit_enabled": True,
        "rate_limit_max_requests": 30,
        "rate_limit_window_seconds": 60,
        "max_discovery_runs_per_session": 3,
        "max_itinerary_runs_per_session": 4,
        "max_adjustments_per_session": 8,
        "host": "0.0.0.0",
        "port": 8000,
    }
    values.update(overrides)
    return Settings(**values)


def test_production_ready_accepts_safe_settings() -> None:
    assert_production_ready(_settings())


def test_production_ready_rejects_fixture_mode() -> None:
    with pytest.raises(ProductionReadinessError, match="E2E_FIXTURE_MODE"):
        assert_production_ready(_settings(e2e_fixture_mode=True))


def test_production_ready_rejects_placeholder_secrets() -> None:
    with pytest.raises(ProductionReadinessError, match="GEMINI_API_KEY"):
        assert_production_ready(_settings(gemini_api_key="test-gemini"))


def test_production_ready_rejects_localhost_cors() -> None:
    with pytest.raises(ProductionReadinessError, match="CORS_ORIGINS"):
        assert_production_ready(_settings(cors_origins="http://localhost:3000"))


def test_redacted_env_status_never_exposes_secret_values() -> None:
    status = redacted_env_status(
        _settings(gemini_api_key="abc123456789", tavily_api_key="tvly-secret")
    )

    assert status["environment"] == "production"
    assert status["fixture_mode"] is False
    assert status["secrets"]["GEMINI_API_KEY"] == "set"
    assert status["secrets"]["TAVILY_API_KEY"] == "set"
    assert "abc123456789" not in repr(status)
    assert "tvly-secret" not in repr(status)
```

- [x] **Step 2: Run readiness tests and verify failure**

Run:

```bash
cd api && uv run pytest tests/ops/test_readiness.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.ops'`.

- [x] **Step 3: Add settings fields**

In `api/app/config.py`, add the imports:

```python
from typing import Literal
```

Extend `Settings`:

```python
class Settings(BaseSettings):
    """Settings sourced from `.env` file and environment variables."""

    gemini_api_key: str
    tavily_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    environment: Literal["development", "test", "production"] = "development"
    e2e_fixture_mode: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"
    session_data_dir: str = ".data"
    metrics_data_dir: str = ".data"
    rate_limit_enabled: bool = True
    rate_limit_max_requests: int = 60
    rate_limit_window_seconds: int = 60
    max_discovery_runs_per_session: int = 3
    max_itinerary_runs_per_session: int = 4
    max_adjustments_per_session: int = 8
```

- [x] **Step 4: Update env example**

In `api/.env.example`, add:

```text
ENVIRONMENT=development
RATE_LIMIT_ENABLED=1
RATE_LIMIT_MAX_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
MAX_DISCOVERY_RUNS_PER_SESSION=3
MAX_ITINERARY_RUNS_PER_SESSION=4
MAX_ADJUSTMENTS_PER_SESSION=8
```

- [x] **Step 5: Create ops package**

Create `api/app/ops/__init__.py`:

```python
"""Operational guardrails for production-like MVP runs."""

from app.ops.readiness import (
    ProductionReadinessError,
    assert_production_ready,
    redacted_env_status,
)

__all__ = [
    "ProductionReadinessError",
    "assert_production_ready",
    "redacted_env_status",
]
```

- [x] **Step 6: Implement readiness checks**

Create `api/app/ops/readiness.py`:

```python
from __future__ import annotations

from collections.abc import Mapping

from app.config import Settings

SECRET_KEYS = ("GEMINI_API_KEY", "TAVILY_API_KEY")
PLACEHOLDER_PREFIXES = ("test-", "fixture-", "example-", "changeme", "your-")
LOCAL_CORS_MARKERS = ("localhost", "127.0.0.1", "0.0.0.0")


class ProductionReadinessError(RuntimeError):
    """Raised when production mode contains unsafe settings."""


def assert_production_ready(settings: Settings) -> None:
    if settings.environment != "production":
        return

    failures: list[str] = []
    if settings.e2e_fixture_mode:
        failures.append("E2E_FIXTURE_MODE must be 0 in production")
    _check_secret("GEMINI_API_KEY", settings.gemini_api_key, failures)
    _check_secret("TAVILY_API_KEY", settings.tavily_api_key, failures)
    _check_cors(settings.cors_origin_list, failures)
    if settings.rate_limit_enabled is False:
        failures.append("RATE_LIMIT_ENABLED must be enabled in production")
    if not settings.session_data_dir or settings.session_data_dir == ".data":
        failures.append("SESSION_DATA_DIR should be an explicit production path")
    if not settings.metrics_data_dir or settings.metrics_data_dir == ".data":
        failures.append("METRICS_DATA_DIR should be an explicit production path")

    if failures:
        raise ProductionReadinessError("; ".join(failures))


def redacted_env_status(settings: Settings) -> dict[str, object]:
    return {
        "environment": settings.environment,
        "fixture_mode": settings.e2e_fixture_mode,
        "cors_origin_count": len(settings.cors_origin_list),
        "rate_limit_enabled": settings.rate_limit_enabled,
        "budgets": {
            "discovery": settings.max_discovery_runs_per_session,
            "itinerary": settings.max_itinerary_runs_per_session,
            "adjustment": settings.max_adjustments_per_session,
        },
        "secrets": {
            "GEMINI_API_KEY": _secret_status(settings.gemini_api_key),
            "TAVILY_API_KEY": _secret_status(settings.tavily_api_key),
        },
    }


def _check_secret(key: str, value: str, failures: list[str]) -> None:
    stripped = value.strip()
    if not stripped:
        failures.append(f"{key} must be configured")
        return
    lowered = stripped.lower()
    if any(lowered.startswith(prefix) for prefix in PLACEHOLDER_PREFIXES):
        failures.append(f"{key} must not use a placeholder value")


def _check_cors(origins: list[str], failures: list[str]) -> None:
    if not origins:
        failures.append("CORS_ORIGINS must include the production web origin")
        return
    unsafe = [
        origin
        for origin in origins
        if any(marker in origin for marker in LOCAL_CORS_MARKERS)
    ]
    if unsafe:
        failures.append("CORS_ORIGINS must not include localhost origins in production")


def _secret_status(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return "missing"
    lowered = stripped.lower()
    if any(lowered.startswith(prefix) for prefix in PLACEHOLDER_PREFIXES):
        return "placeholder"
    return "set"
```

- [x] **Step 7: Update config tests**

In `api/tests/test_config.py`, add the new env keys to the existing env-file test payload:

```python
"ENVIRONMENT=development",
"RATE_LIMIT_ENABLED=1",
"RATE_LIMIT_MAX_REQUESTS=60",
"RATE_LIMIT_WINDOW_SECONDS=60",
"MAX_DISCOVERY_RUNS_PER_SESSION=3",
"MAX_ITINERARY_RUNS_PER_SESSION=4",
"MAX_ADJUSTMENTS_PER_SESSION=8",
```

Add assertions:

```python
assert settings.environment == "development"
assert settings.e2e_fixture_mode is False
assert settings.rate_limit_enabled is True
assert settings.max_discovery_runs_per_session == 3
```

- [x] **Step 8: Run tests**

Run:

```bash
cd api && uv run pytest tests/ops/test_readiness.py tests/test_config.py -q
```

Expected: PASS.

---

### Task 2: Install In-Memory HTTP Rate Limiting

**Files:**
- Create: `api/app/ops/rate_limit.py`
- Modify: `api/main.py`
- Create: `api/tests/ops/test_rate_limit.py`

- [x] **Step 1: Add failing limiter tests**

Create `api/tests/ops/test_rate_limit.py`:

```python
from __future__ import annotations

from app.ops.rate_limit import InMemoryRateLimiter


def test_rate_limiter_allows_requests_under_limit() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)

    assert limiter.allow("client", now=100.0) is True
    assert limiter.allow("client", now=101.0) is True


def test_rate_limiter_blocks_requests_over_limit() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)

    assert limiter.allow("client", now=100.0) is True
    assert limiter.allow("client", now=101.0) is True
    assert limiter.allow("client", now=102.0) is False


def test_rate_limiter_expires_old_entries() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=10)

    assert limiter.allow("client", now=100.0) is True
    assert limiter.allow("client", now=101.0) is True
    assert limiter.allow("client", now=111.1) is True
```

- [x] **Step 2: Run limiter tests and verify failure**

Run:

```bash
cd api && uv run pytest tests/ops/test_rate_limit.py -q
```

Expected: FAIL with `ModuleNotFoundError` or missing `InMemoryRateLimiter`.

- [x] **Step 3: Implement limiter and middleware**

Create `api/app/ops/rate_limit.py`:

```python
from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Deque

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class InMemoryRateLimiter:
    max_requests: int
    window_seconds: int
    _hits: dict[str, Deque[float]] = field(default_factory=lambda: defaultdict(deque))

    def allow(self, key: str, *, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        window_start = current - self.window_seconds
        hits = self._hits[key]
        while hits and hits[0] <= window_start:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(current)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        limiter: InMemoryRateLimiter,
        enabled: bool = True,
    ) -> None:
        super().__init__(app)
        self._limiter = limiter
        self._enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable):
        if not self._enabled or request.url.path == "/health":
            return await call_next(request)

        key = _client_key(request)
        if not self._limiter.allow(key):
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(self._limiter.window_seconds)},
            )
        return await call_next(request)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"
```

- [x] **Step 4: Install middleware in main**

In `api/main.py`, import:

```python
from app.ops.rate_limit import InMemoryRateLimiter, RateLimitMiddleware
from app.ops.readiness import assert_production_ready
```

After `settings = get_settings()`, add:

```python
assert_production_ready(settings)
```

After CORS middleware, add:

```python
app.add_middleware(
    RateLimitMiddleware,
    limiter=InMemoryRateLimiter(
        max_requests=settings.rate_limit_max_requests,
        window_seconds=settings.rate_limit_window_seconds,
    ),
    enabled=settings.rate_limit_enabled,
)
```

- [x] **Step 5: Add route-level middleware test**

In `api/tests/ops/test_rate_limit.py`, add:

```python
import httpx
from fastapi import FastAPI

from app.ops.rate_limit import RateLimitMiddleware


async def test_rate_limit_middleware_returns_429_after_limit() -> None:
    app = FastAPI()
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
    app.add_middleware(RateLimitMiddleware, limiter=limiter, enabled=True)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "yes"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/ping")
        second = await client.get("/ping")

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == "Rate limit exceeded"
```

- [x] **Step 6: Run limiter tests**

Run:

```bash
cd api && uv run pytest tests/ops/test_rate_limit.py -q
```

Expected: PASS.

---

### Task 3: Add Per-Session Expensive Operation Budgets

**Files:**
- Create: `api/app/ops/operation_budget.py`
- Modify: `api/app/routes/_shared.py`
- Modify: `api/app/routes/discovery.py`
- Modify: `api/app/routes/itinerary.py`
- Modify: `api/app/routes/adjustments.py`
- Create: `api/tests/ops/test_operation_budget.py`
- Modify: `api/tests/routes/test_discovery_preferences.py`
- Modify: `api/tests/routes/test_itinerary.py`
- Modify: `api/tests/routes/test_adjustments.py`

- [x] **Step 1: Add failing budget tests**

Create `api/tests/ops/test_operation_budget.py`:

```python
from __future__ import annotations

import pytest

from app.ops.operation_budget import (
    OperationBudgetExceeded,
    SessionOperationBudget,
)


def test_session_operation_budget_allows_until_limit() -> None:
    budget = SessionOperationBudget(default_limits={"discovery": 2})

    budget.consume("session_1", "discovery")
    budget.consume("session_1", "discovery")


def test_session_operation_budget_rejects_over_limit() -> None:
    budget = SessionOperationBudget(default_limits={"discovery": 1})

    budget.consume("session_1", "discovery")

    with pytest.raises(OperationBudgetExceeded, match="discovery"):
        budget.consume("session_1", "discovery")


def test_session_operation_budget_is_per_session() -> None:
    budget = SessionOperationBudget(default_limits={"itinerary": 1})

    budget.consume("session_1", "itinerary")
    budget.consume("session_2", "itinerary")
```

- [x] **Step 2: Run budget tests and verify failure**

Run:

```bash
cd api && uv run pytest tests/ops/test_operation_budget.py -q
```

Expected: FAIL with missing module.

- [x] **Step 3: Implement budget guard**

Create `api/app/ops/operation_budget.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Literal

OperationName = Literal["discovery", "itinerary", "adjustment"]


class OperationBudgetExceeded(RuntimeError):
    def __init__(self, session_id: str, operation: OperationName, limit: int) -> None:
        super().__init__(
            f"Operation budget exceeded for {operation}: {limit} per session"
        )
        self.session_id = session_id
        self.operation = operation
        self.limit = limit


@dataclass
class SessionOperationBudget:
    default_limits: dict[OperationName, int]
    _counts: dict[tuple[str, OperationName], int] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def consume(self, session_id: str, operation: OperationName) -> None:
        limit = self.default_limits[operation]
        key = (session_id, operation)
        with self._lock:
            current = self._counts.get(key, 0)
            if current >= limit:
                raise OperationBudgetExceeded(session_id, operation, limit)
            self._counts[key] = current + 1

    def snapshot(self, session_id: str) -> dict[OperationName, int]:
        with self._lock:
            return {
                operation: self._counts.get((session_id, operation), 0)
                for operation in self.default_limits
            }
```

- [x] **Step 4: Add shared route helper**

In `api/app/routes/_shared.py`, import:

```python
from app.config import get_settings
from app.ops.operation_budget import (
    OperationBudgetExceeded,
    OperationName,
    SessionOperationBudget,
)
```

Create a module-level budget:

```python
def _budget_limits() -> dict[OperationName, int]:
    settings = get_settings()
    return {
        "discovery": settings.max_discovery_runs_per_session,
        "itinerary": settings.max_itinerary_runs_per_session,
        "adjustment": settings.max_adjustments_per_session,
    }


_OPERATION_BUDGET = SessionOperationBudget(default_limits=_budget_limits())
```

Route tests may replace `_OPERATION_BUDGET` with a small test budget; production code should not rebuild budgets per request.

Extend `route_error`:

```python
if isinstance(error, OperationBudgetExceeded):
    return HTTPException(status_code=429, detail=str(error))
```

Add helper:

```python
async def guard_expensive_operation(
    session_id: str,
    operation: OperationName,
) -> None:
    _OPERATION_BUDGET.consume(session_id, operation)
    await safe_metric(
        {
            "name": "operation_budget_consumed",
            "session_id": session_id,
            "payload": {"operation": operation},
        }
    )
```

- [x] **Step 5: Add metric event name**

In `api/app/metrics/events.py`, add `"operation_budget_consumed"` to `MetricEventName`.

- [x] **Step 6: Guard discovery route**

In `api/app/routes/discovery.py`, import `guard_expensive_operation` from `_shared` and call it before graph work:

```python
await guard_expensive_operation(session_id, "discovery")
```

Place this after `require_session(...)` and before calling `run_discovery_agent(...)`.

- [x] **Step 7: Guard itinerary routes**

In `api/app/routes/itinerary.py`, import `guard_expensive_operation` and add:

```python
await guard_expensive_operation(session_id, "itinerary")
```

Apply it in:
- `run_itinerary(...)`
- `update_stay_override(...)`
- `_stream_itinerary_events(...)` after `require_session(...)` and `_assert_itinerary_ready(...)`

- [x] **Step 8: Guard adjustments route**

In `api/app/routes/adjustments.py`, import `guard_expensive_operation` and add:

```python
await guard_expensive_operation(session_id, "adjustment")
```

Place it after loading the session and before `run_adjustment_workflow(...)`.

- [x] **Step 9: Add route budget regression tests**

In `api/tests/routes/test_discovery_preferences.py`, add:

```python
from app.ops.operation_budget import SessionOperationBudget
from app.routes import _shared


async def test_discovery_budget_returns_429_after_limit(client, monkeypatch) -> None:
    monkeypatch.setattr(
        _shared,
        "_OPERATION_BUDGET",
        SessionOperationBudget(default_limits={"discovery": 1, "itinerary": 4, "adjustment": 8}),
    )
    session_id = await create_session(client)

    first = await client.post(f"/api/sessions/{session_id}/discovery")
    second = await client.post(f"/api/sessions/{session_id}/discovery")

    assert first.status_code == 200
    assert second.status_code == 429
    assert "Operation budget exceeded for discovery" in second.json()["detail"]
```

In `api/tests/routes/test_itinerary.py`, add:

```python
from app.ops.operation_budget import SessionOperationBudget
from app.routes import _shared


async def test_itinerary_budget_returns_429_after_limit(client, monkeypatch) -> None:
    monkeypatch.setattr(
        _shared,
        "_OPERATION_BUDGET",
        SessionOperationBudget(default_limits={"discovery": 3, "itinerary": 1, "adjustment": 8}),
    )
    session_id = await prepared_session(client)

    first = await client.post(f"/api/sessions/{session_id}/itinerary", json={})
    second = await client.post(f"/api/sessions/{session_id}/itinerary", json={})

    assert first.status_code == 200
    assert second.status_code == 429
```

In `api/tests/routes/test_adjustments.py`, add:

```python
from app.ops.operation_budget import SessionOperationBudget
from app.routes import _shared


async def test_adjustment_budget_returns_429_after_limit(client, monkeypatch) -> None:
    monkeypatch.setattr(
        _shared,
        "_OPERATION_BUDGET",
        SessionOperationBudget(default_limits={"discovery": 3, "itinerary": 4, "adjustment": 1}),
    )
    session_id = await prepared_session_with_itinerary(client)

    first = await client.post(
        f"/api/sessions/{session_id}/adjustments",
        json={"message": "把第二天下午安排轻松一点"},
    )
    second = await client.post(
        f"/api/sessions/{session_id}/adjustments",
        json={"message": "再轻松一点"},
    )

    assert first.status_code == 200
    assert second.status_code == 429
```

The test patches `_OPERATION_BUDGET` directly because route modules are imported before individual test bodies run.

- [x] **Step 10: Run budget and route tests**

Run:

```bash
cd api && uv run pytest tests/ops/test_operation_budget.py tests/routes/test_discovery_preferences.py tests/routes/test_itinerary.py tests/routes/test_adjustments.py -q
```

Expected: PASS.

---

### Task 4: Add Local Ops Summary CLI

**Files:**
- Create: `api/app/ops/summary.py`
- Create: `api/scripts/ops_summary.py`
- Create: `api/tests/ops/test_summary.py`

- [x] **Step 1: Add failing summary tests**

Create `api/tests/ops/test_summary.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from app.ops.summary import build_ops_summary


async def test_build_ops_summary_counts_metrics_and_costs(tmp_path: Path) -> None:
    metrics = tmp_path / "events.jsonl"
    costs = tmp_path / "llm-cost.jsonl"
    metrics.write_text(
        "\n".join(
            [
                json.dumps({"name": "step1_submitted", "session_id": "s1", "payload": {}, "created_at": "2026-05-10T00:00:00Z"}),
                json.dumps({"name": "itinerary_finalized", "session_id": "s1", "payload": {}, "created_at": "2026-05-10T00:01:00Z"}),
            ]
        ),
        encoding="utf-8",
    )
    costs.write_text(
        "\n".join(
            [
                json.dumps({"timestamp": "2026-05-10T00:00:01Z", "label": "discovery", "prompt_tokens_estimate": 10, "completion_tokens_estimate": 5, "duration_ms": 100, "success": True, "failure": None, "retry_count": 0}),
                json.dumps({"timestamp": "2026-05-10T00:00:02Z", "label": "planner", "prompt_tokens_estimate": 20, "completion_tokens_estimate": 10, "duration_ms": 200, "success": False, "failure": "bad", "retry_count": 2}),
            ]
        ),
        encoding="utf-8",
    )

    summary = await build_ops_summary(metric_path=metrics, cost_path=costs)

    assert summary["metrics"]["sessions_submitted"] == 1
    assert summary["metrics"]["sessions_with_final_itinerary"] == 1
    assert summary["llm"]["call_count"] == 2
    assert summary["llm"]["failure_count"] == 1
    assert summary["llm"]["total_tokens_estimate"] == 45
    assert summary["llm"]["retry_count"] == 2
```

- [x] **Step 2: Run summary test and verify failure**

Run:

```bash
cd api && uv run pytest tests/ops/test_summary.py -q
```

Expected: FAIL with missing `app.ops.summary`.

- [x] **Step 3: Implement summary module**

Create `api/app/ops/summary.py`:

```python
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from app.llm.cost_logger import default_cost_log_path
from app.metrics.events import compute_metric_summary, default_metric_file_path


async def build_ops_summary(
    *,
    metric_path: str | Path | None = None,
    cost_path: str | Path | None = None,
) -> dict[str, Any]:
    metrics = await compute_metric_summary(metric_path or default_metric_file_path())
    llm = await asyncio.to_thread(_summarize_cost_log, Path(cost_path or default_cost_log_path()))
    return {
        "metrics": metrics.model_dump(mode="json"),
        "llm": llm,
    }


def _summarize_cost_log(path: Path) -> dict[str, int]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        lines = []

    call_count = 0
    failure_count = 0
    total_tokens = 0
    retry_count = 0
    for raw in lines:
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            continue
        call_count += 1
        if item.get("success") is False:
            failure_count += 1
        total_tokens += int(item.get("prompt_tokens_estimate") or 0)
        total_tokens += int(item.get("completion_tokens_estimate") or 0)
        retry_count += int(item.get("retry_count") or 0)

    return {
        "call_count": call_count,
        "failure_count": failure_count,
        "total_tokens_estimate": total_tokens,
        "retry_count": retry_count,
    }
```

- [x] **Step 4: Add CLI script**

Create `api/scripts/ops_summary.py`:

```python
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def _main() -> int:
    from app.ops.summary import build_ops_summary

    parser = argparse.ArgumentParser(description="Summarize local MVP ops logs.")
    parser.add_argument("--metrics", default=None)
    parser.add_argument("--costs", default=None)
    args = parser.parse_args()

    summary = await build_ops_summary(metric_path=args.metrics, cost_path=args.costs)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
```

- [x] **Step 5: Run summary tests and script**

Run:

```bash
cd api && uv run pytest tests/ops/test_summary.py -q
cd api && uv run python scripts/ops_summary.py
```

Expected: test passes; script prints JSON with `metrics` and `llm` top-level keys.

---

### Task 5: Add Production and Real-Smoke Gates

**Files:**
- Create: `api/scripts/check_production_readiness.py`
- Modify: `Makefile`
- Modify: `scripts/check_launch_readiness.py`
- Modify: `api/.env.example`

- [x] **Step 1: Add production readiness script**

Create `api/scripts/check_production_readiness.py`:

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    from app.config import get_settings
    from app.ops.readiness import assert_production_ready, redacted_env_status

    settings = get_settings()
    assert_production_ready(settings)
    print(json.dumps(redacted_env_status(settings), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] **Step 2: Add Makefile targets**

In `Makefile`, update `.PHONY`:

```make
.PHONY: gen-types check-types launch-check smoke smoke-real production-check ops-summary regression
```

Add:

```make
production-check:
	cd api && uv run python scripts/check_production_readiness.py

ops-summary:
	cd api && uv run python scripts/ops_summary.py

smoke-real:
	cd api && uv run python scripts/smoke_llm.py
	cd api && uv run python scripts/smoke_amap_mcp.py
```

Do not add `smoke-real` to `regression`; it requires live provider credentials and may cost money.

- [x] **Step 3: Update launch readiness checker**

In `scripts/check_launch_readiness.py`, add these keys to `API_ENV_REQUIRED`:

```python
"ENVIRONMENT",
"RATE_LIMIT_ENABLED",
"RATE_LIMIT_MAX_REQUESTS",
"RATE_LIMIT_WINDOW_SECONDS",
"MAX_DISCOVERY_RUNS_PER_SESSION",
"MAX_ITINERARY_RUNS_PER_SESSION",
"MAX_ADJUSTMENTS_PER_SESSION",
```

In `check_docs(...)`, require the new Makefile targets:

```python
require_contains(makefile, "production-check:", failures, reason="production readiness gate")
require_contains(makefile, "ops-summary:", failures, reason="ops summary target")
require_contains(makefile, "smoke-real:", failures, reason="live provider smoke target")
```

- [x] **Step 4: Run gates**

Run:

```bash
make launch-check
cd api && uv run python scripts/check_production_readiness.py
```

Expected:
- `make launch-check` passes.
- The production readiness script passes in development mode and prints redacted JSON.

- [x] **Step 5: Verify production failure path manually in test env**

Run:

```bash
cd api && ENVIRONMENT=production E2E_FIXTURE_MODE=1 uv run python scripts/check_production_readiness.py
```

Expected: exits non-zero with a message containing `E2E_FIXTURE_MODE`.

---

### Task 6: Update Production Docs and Final Verification

**Files:**
- Modify: `README.md`
- Modify: `api/README.md`
- Modify: `docs/mvp-launch-checklist.md`
- Modify: `docs/2026-05-10-real-mvp-work-summary.md`

- [x] **Step 1: Update root README**

In `README.md`, add a section:

````markdown
## Production-Like Demo Guardrails

The default regression suite is offline and fixture-backed. Live provider checks are explicit:

```bash
make production-check
make smoke-real
make ops-summary
```

`make smoke-real` uses live Gemini and map providers and can consume quota. Do not run it in CI unless the environment is intentionally configured with live provider credentials.
````

- [x] **Step 2: Update API README**

In `api/README.md`, document the new env keys:

```markdown
- `ENVIRONMENT`: `development`, `test`, or `production`; production enables strict readiness checks.
- `RATE_LIMIT_ENABLED`: enables in-memory HTTP rate limiting.
- `RATE_LIMIT_MAX_REQUESTS`: request count allowed per client window.
- `RATE_LIMIT_WINDOW_SECONDS`: rate-limit window length.
- `MAX_DISCOVERY_RUNS_PER_SESSION`: per-session discovery generation budget.
- `MAX_ITINERARY_RUNS_PER_SESSION`: per-session itinerary generation budget.
- `MAX_ADJUSTMENTS_PER_SESSION`: per-session adjustment budget.
```

Add:

```markdown
`uv run python scripts/ops_summary.py` summarizes local metrics and LLM cost logs without printing secrets.
```

- [x] **Step 3: Update launch checklist**

In `docs/mvp-launch-checklist.md`, add:

```markdown
## Production-Like Demo Gate

Before a live demo with real users:

1. Rotate any exposed provider keys.
2. Set `ENVIRONMENT=production`.
3. Set `E2E_FIXTURE_MODE=0`.
4. Use production web origins only in `CORS_ORIGINS`.
5. Run `make production-check`.
6. Run `make smoke-real` only after confirming live provider quota is acceptable.
7. Run `make ops-summary` after demo sessions to inspect cost and failure counts.
```

- [x] **Step 4: Update work summary**

In `docs/2026-05-10-real-mvp-work-summary.md`, add under “下一阶段 Plan 建议”:

```markdown
Plan19 已定义为 production readiness guardrails：生产 env 检查、限流、每 session 昂贵操作预算、ops summary、real smoke gate 和上线 checklist。
```

- [x] **Step 5: Run focused tests**

Run:

```bash
cd api && uv run pytest tests/ops tests/routes/test_discovery_preferences.py tests/routes/test_itinerary.py tests/routes/test_adjustments.py tests/test_config.py -q
```

Expected: PASS.

- [x] **Step 6: Run full regression**

Run:

```bash
make regression
```

Expected: launch readiness, generated types, web lint/unit/build, API pytest, API ruff, fixture smoke, and Playwright e2e all pass.

- [x] **Step 7: Commit and push**

Run:

```bash
git add api/app/config.py api/app/ops api/app/routes api/app/metrics/events.py api/scripts/check_production_readiness.py api/scripts/ops_summary.py api/tests/ops api/tests/routes api/tests/test_config.py api/.env.example scripts/check_launch_readiness.py Makefile README.md api/README.md docs/mvp-launch-checklist.md docs/2026-05-10-real-mvp-work-summary.md docs/superpowers/plans/2026-05-10-langgraph-mvp-19-production-readiness.md
git commit -m "feat: add production readiness guardrails"
git push
```

---

## Execution Notes

- Keep all guardrails in-process for this MVP pass. Document that multi-process or multi-instance production needs Redis/database-backed counters later.
- Do not expose ops summaries through public HTTP routes in Plan19.
- Keep `make regression` offline and deterministic.
- Treat live smoke as opt-in because it uses real provider quota.
- Do not print or commit secrets. Status output should be `set`, `missing`, or `placeholder`.

## Self-Review

- **Spec coverage:** The plan covers env safety, rate limiting, session operation budgets, local ops summary, real smoke gates, and documentation.
- **Placeholder scan:** No placeholder values are required from implementers; production examples use explicit env names and test secrets only.
- **Type consistency:** `OperationName` values are `discovery`, `itinerary`, and `adjustment` throughout route guards and tests.
- **Scope check:** Database persistence, authentication, hosted deployment automation, and dashboards are explicitly out of scope for this plan.
