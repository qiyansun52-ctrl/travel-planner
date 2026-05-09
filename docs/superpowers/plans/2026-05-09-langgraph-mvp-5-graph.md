# LangGraph MVP — Plan 5: Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python LangGraph workflow layer that ports the current TypeScript discovery, stay, transport, planner, validator loop, adjustment classifier, adjustment routing, and metrics event behavior into `api/app/graph/`.

**Architecture:** Graph nodes stay mostly pure: they accept validated `PlanState`, return state patches, and do not mutate the session repository directly. FastAPI routes in Plan 6 will own HTTP validation and persistence writes; Plan 5 exposes reusable workflow runners that take a `PlanningSession` and return structured graph results. The workflow uses one corrective planner pass for error-severity validator issues, preserves warning-only outputs, and routes Type A/B/C adjustments through focused subgraphs.

**Tech Stack:** Python 3.12, Pydantic v2, LangGraph, pytest, pytest-asyncio, google-genai wrapper from Plan 2, provider registry from Plan 3, session schemas and validator from Plan 1, file repository contracts from Plan 4.

---

## Scope

**In scope:**
- Add `langgraph` to the API dependency set with a minor-version pin.
- Add `api/app/graph/` package with state, node, workflow, and adjustment modules.
- Port current TS server behavior from:
  - `web/src/server/agents/discovery.ts`
  - `web/src/server/agents/stay.ts`
  - `web/src/server/agents/transport.ts`
  - `web/src/server/agents/planner.ts`
  - `web/src/server/agents/orchestrator.ts`
  - `web/src/server/agents/adjustmentClassifier.ts`
  - `web/src/server/metrics/events.ts`
- Add `api/app/metrics/events.py`.
- Add black-box graph tests covering happy path, corrective pass, warning-only validation, residual validator errors, Type A/B/C adjustment branches, low-confidence clarification, and metrics JSONL behavior.
- Add a tiny prerequisite cleanup for two inherited Plan 2 review findings because Plan 5 will call the LLM wrapper from long-running graph nodes.

**Out of scope:**
- No FastAPI routes or SSE endpoints. Plan 6 wires HTTP and streaming.
- No frontend changes. Plan 7 performs web cutover.
- No TypeScript deletion.
- No account-backed persistence, SQLite, or provider-backed hotel/ticket inventory.
- No token-level LLM streaming; node-level progress events are enough for Plan 6 SSE.

## Sources Checked

- LangGraph official Graph API documentation checked for `StateGraph`, `START`, `END`, and conditional edges: <https://docs.langchain.com/oss/python/langgraph/graph-api>
- PyPI `langgraph` checked on 2026-05-09. Current stable line is `1.1.x`; pin Plan 5 to `langgraph>=1.1.10,<1.2.0`: <https://pypi.org/project/langgraph/>
- The roadmap says `langgraph>=0.2.0`; treat that as the historical minimum, not the exact dependency target.

## File Structure

**Create:**
- `api/app/graph/__init__.py` — package exports for workflow runners and graph result models.
- `api/app/graph/state.py` — `PlanState`, graph result models, progress event model, and state validation helpers.
- `api/app/graph/nodes/__init__.py`
- `api/app/graph/nodes/discovery.py` — discovery fixture/live LLM node.
- `api/app/graph/nodes/stay.py` — stay recommendation node.
- `api/app/graph/nodes/transport.py` — transport recommendation node.
- `api/app/graph/nodes/planner.py` — deterministic planner node and helpers.
- `api/app/graph/nodes/validator.py` — validator node wrapper around `app.domain.validator`.
- `api/app/graph/nodes/adjustment_classifier.py` — regex classifier matching TS behavior.
- `api/app/graph/workflow.py` — planning graph, corrective loop, and workflow runners.
- `api/app/graph/adjustments/__init__.py`
- `api/app/graph/adjustments/type_a.py` — planner-only adjustment graph.
- `api/app/graph/adjustments/type_b.py` — stay/transport scoped adjustment graph.
- `api/app/graph/adjustments/type_c.py` — confirmation/result builder for root-constraint changes.
- `api/app/metrics/__init__.py`
- `api/app/metrics/events.py`
- `api/tests/graph/__init__.py`
- `api/tests/graph/fixtures.py`
- `api/tests/graph/test_state.py`
- `api/tests/graph/test_metrics_events.py`
- `api/tests/graph/test_nodes.py`
- `api/tests/graph/test_workflow.py`
- `api/tests/graph/test_adjustments.py`

**Modify:**
- `api/pyproject.toml` — add `langgraph>=1.1.10,<1.2.0`.
- `api/uv.lock` — update through `uv lock`.
- `api/app/llm/retry.py` — re-raise cancellation and process-control exceptions.
- `api/app/llm/client.py` — close Gemini async client in `finally`.
- `api/tests/llm/test_retry.py` — cancellation regression.
- `api/tests/llm/test_client.py` — Gemini async client close regression.

**Untouched until Plan 6:**
- `api/app/routes/discover.py`
- `api/app/routes/plan.py`
- `api/app/services/gemini.py`
- `api/app/services/tavily.py`
- `web/src/server/*`
- `web/src/app/api/*`

## Design Decisions

1. **Graph state validation:** `StateGraph` uses a small `GraphState` `TypedDict` for LangGraph compatibility, while every node validates input/output with a Pydantic `PlanState`. This keeps runtime flexible and still enforces schema boundaries.
2. **No repository mutation inside graph:** Graph runners return `PlanningGraphResult` or `AdjustmentGraphResult`; Plan 6 routes write those results through `SessionRepository`.
3. **Corrective pass control:** A dedicated `prepare_corrective` node increments `corrective_attempts` before looping back to `planner`. Warnings never loop. Errors loop once and then finalize even if errors remain.
4. **Discovery live path:** Fixture mode mirrors current TS fallback when no LLM key is present. Live mode calls `generate_structured(...)` and normalizes cards after schema validation.
5. **Adjustment Type C:** Type C never silently changes root constraints. It returns confirmation/resolution metadata that Plan 6 can persist or render.
6. **Metrics are best-effort:** `safe_append_metric_event(...)` swallows write errors so planning is never blocked by analytics.

---

## Task 0 — Preflight And LLM Review Cleanup

**Files:**
- Modify: `api/pyproject.toml`
- Modify: `api/uv.lock`
- Modify: `api/app/llm/retry.py`
- Modify: `api/app/llm/client.py`
- Modify: `api/tests/llm/test_retry.py`
- Modify: `api/tests/llm/test_client.py`

- [ ] **Step 0.1: Add LangGraph dependency**

Run:

```bash
cd api && uv add "langgraph>=1.1.10,<1.2.0"
```

Expected: `api/pyproject.toml` contains `langgraph>=1.1.10,<1.2.0`, and `api/uv.lock` is updated.

- [ ] **Step 0.2: Add retry cancellation regression test**

Add `import asyncio` near the top of `api/tests/llm/test_retry.py`, beside the existing imports:

```python
import asyncio
```

Then append these tests to `api/tests/llm/test_retry.py`:

```python
async def test_reraises_cancelled_error_without_retry_wrapping() -> None:
    async def op() -> None:
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await with_retry(op, RetryOptions(max_retries=3, base_delay_ms=0))


async def test_reraises_keyboard_interrupt_without_retry_wrapping() -> None:
    async def op() -> None:
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        await with_retry(op, RetryOptions(max_retries=3, base_delay_ms=0))
```

- [ ] **Step 0.3: Verify retry regression fails**

Run:

```bash
cd api && uv run pytest tests/llm/test_retry.py::test_reraises_cancelled_error_without_retry_wrapping -v
```

Expected: FAIL because `CancelledError` is wrapped in `RetryExhaustedError`.

- [ ] **Step 0.4: Fix retry control-flow handling**

Edit the `except BaseException` block in `api/app/llm/retry.py`:

```python
        except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
            raise
        except Exception as error:  # noqa: BLE001 -- re-raised below
            if retry_count >= opts.max_retries or not should_retry(error):
                raise RetryExhaustedError(error, retry_count) from error
```

Also narrow the `RetryOptions.should_retry` type:

```python
    should_retry: Callable[[Exception], bool] | None = None
```

And narrow `RetryExhaustedError`:

```python
class RetryExhaustedError(Exception):
    """Wraps the final cause after retries are exhausted."""

    def __init__(self, cause: Exception, retry_count: int) -> None:
        super().__init__(str(cause))
        self.cause = cause
        self.retry_count = retry_count
```

- [ ] **Step 0.5: Add Gemini async-client close regression test**

Add these imports near the top of `api/tests/llm/test_client.py`, beside the existing imports:

```python
import sys
from types import ModuleType, SimpleNamespace
```

Then append this test to `api/tests/llm/test_client.py`:

```python

async def test_gemini_provider_closes_async_client(monkeypatch: pytest.MonkeyPatch) -> None:
    closed: list[bool] = []

    class FakeModels:
        async def generate_content(self, *, model: str, contents: str, config: object):
            assert model == "gemini-test"
            assert contents == "u"
            assert config is not None
            return SimpleNamespace(text='{"message":"ok"}')

    class FakeAio:
        models = FakeModels()

        async def aclose(self) -> None:
            closed.append(True)

    class FakeClient:
        def __init__(self, *, api_key: str) -> None:
            assert api_key == "key"
            self.aio = FakeAio()

    google_module = ModuleType("google")
    genai_module = ModuleType("google.genai")
    errors_module = ModuleType("google.genai.errors")
    types_module = ModuleType("google.genai.types")
    errors_module.APIError = type("APIError", (Exception,), {})
    types_module.GenerateContentConfig = lambda **kwargs: kwargs
    genai_module.Client = FakeClient
    genai_module.errors = errors_module
    genai_module.types = types_module
    google_module.genai = genai_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.errors", errors_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", types_module)

    from app.llm.client import GeminiLLMProvider

    provider = GeminiLLMProvider(api_key="key", model="gemini-test")
    raw = await provider.generate(system="s", user="u", timeout_ms=1000)

    assert raw == '{"message":"ok"}'
    assert closed == [True]
```

- [ ] **Step 0.6: Verify Gemini regression fails**

Run:

```bash
cd api && uv run pytest tests/llm/test_client.py::test_gemini_provider_closes_async_client -v
```

Expected: FAIL because `client.aio.aclose()` is not called.

- [ ] **Step 0.7: Close Gemini async client**

Edit `api/app/llm/client.py` inside `GeminiLLMProvider.generate(...)`:

```python
        client = genai.Client(api_key=self._api_key)
        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
        )
        try:
            response = await client.aio.models.generate_content(
                model=self._model,
                contents=user,
                config=config,
            )
        except genai_errors.APIError as api_err:
            status = getattr(api_err, "code", None)
            if status in (401, 403):
                raise LLMAuthError(str(api_err)) from api_err
            if status in (408, 429) or (isinstance(status, int) and status >= 500):
                raise LLMNetworkError(str(api_err), status=status, cause=api_err) from api_err
            raise LLMProviderError(str(api_err), status=status) from api_err
        except (asyncio.CancelledError, LLMTimeoutError):
            raise
        except Exception as e:
            raise LLMNetworkError("LLM provider network failure", cause=e) from e
        finally:
            await client.aio.aclose()

        text = (response.text or "").strip()
```

- [ ] **Step 0.8: Run LLM tests and commit**

Run:

```bash
cd api && uv run pytest tests/llm -v
cd api && uv run ruff check app/llm tests/llm
```

Expected: all LLM tests pass and ruff reports no issues.

Commit:

```bash
git add api/pyproject.toml api/uv.lock api/app/llm/retry.py api/app/llm/client.py api/tests/llm/test_retry.py api/tests/llm/test_client.py
git commit -m "fix(api): harden llm client for graph usage"
```

---

## Task 1 — Graph Package And State Models

**Files:**
- Create: `api/app/graph/__init__.py`
- Create: `api/app/graph/state.py`
- Create: `api/app/graph/nodes/__init__.py`
- Create: `api/app/graph/adjustments/__init__.py`
- Create: `api/tests/graph/__init__.py`
- Create: `api/tests/graph/fixtures.py`
- Create: `api/tests/graph/test_state.py`

- [ ] **Step 1.1: Create graph directories**

Run:

```bash
mkdir -p api/app/graph/nodes api/app/graph/adjustments api/tests/graph
touch api/app/graph/__init__.py api/app/graph/nodes/__init__.py api/app/graph/adjustments/__init__.py api/tests/graph/__init__.py
```

- [ ] **Step 1.2: Add graph test fixtures**

Create `api/tests/graph/fixtures.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone

from app.models.schemas import (
    AreaSummary,
    BudgetBand,
    BudgetSummary,
    Coordinate,
    DiscoveryCard,
    DiscoveryOutput,
    DiscoveryState,
    FoodSummary,
    HardConstraints,
    Itinerary,
    NormalizedPlace,
    PlanningSession,
    Preference,
    SourceNote,
    StayOption,
    StayRecommendation,
    TransportRecommendation,
    ValidatorIssue,
)


def band(low: float = 100, high: float = 200, basis: str = "per_trip") -> BudgetBand:
    return BudgetBand(currency="CNY", low=low, high=high, confidence="medium", basis=basis)


def budget_summary(user_budget: float = 6000, total_high: float = 1000) -> BudgetSummary:
    base = band()
    total = BudgetBand(
        currency="CNY",
        low=total_high * 0.8,
        high=total_high,
        confidence="medium",
        basis="per_trip",
    )
    return BudgetSummary(
        currency="CNY",
        transport=base,
        stay=base,
        food=base,
        attractions=base,
        other=base,
        total=total,
        user_budget=user_budget,
        overrun_flag=total.high > user_budget * 1.15,
    )


def hard_constraints(total_budget: float = 6000) -> HardConstraints:
    return HardConstraints(
        departure_city="北京",
        destination_city="上海",
        destination_country_code="CN",
        departure_date="2026-05-10",
        duration_days=3,
        traveler_count=2,
        total_budget=total_budget,
        currency="CNY",
    )


def preferences() -> Preference:
    return Preference(
        area_vibe="central, walkable, good food nearby",
        quiet_vs_lively="balanced",
        stay_type="hotel",
        willing_to_change_hotels=False,
        intercity_transport_preference="rail",
        early_departure_tolerance="medium",
        transfer_tolerance="medium",
        pay_more_to_save_time=True,
    )


def area(area_id: str = "area_central", name: str = "上海 central core") -> AreaSummary:
    return AreaSummary(
        id=area_id,
        name=name,
        vibe_tags=["walkable", "transit-rich"],
        note="Best default for a first visit.",
        center=Coordinate(lat=31.23, lng=121.47),
    )


def place(place_id: str = "place_waterfront", name: str = "上海 waterfront") -> NormalizedPlace:
    return NormalizedPlace(
        id=place_id,
        name=name,
        coordinate=Coordinate(lat=31.24, lng=121.48),
        address=name,
        category="poi",
        provider="amap",
    )


def discovery_card(card_id: str = "disc_waterfront", name: str = "上海 waterfront walk") -> DiscoveryCard:
    return DiscoveryCard(
        id=card_id,
        name=name,
        reason="A flexible first stop.",
        category="landmark",
        tags=["orientation"],
        suggested_duration_minutes=120,
        cost_signal="free",
        cost_estimate=band(0, 0, "per_person"),
        image_url="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee",
        reservation_hint=None,
        place=place(),
        enrichment_status="complete",
    )


def discovery_output() -> DiscoveryOutput:
    return DiscoveryOutput(
        cards=[
            discovery_card(),
            discovery_card("disc_museum", "上海 city museum"),
            discovery_card("disc_market", "上海 morning market"),
        ],
        food_summaries=[
            FoodSummary(
                id="food_noodles",
                name="上海 noodle shops",
                category="casual",
                description="Good lunch fallback.",
                image_url=None,
            )
        ],
        area_summaries=[area(), area("area_quiet", "上海 quieter edge")],
        budget_estimate=budget_summary(),
        source_notes=[SourceNote(provider="fixture", url=None, note="Fixture discovery.")],
    )


def session(*, with_discovery: bool = True, with_preferences: bool = True) -> PlanningSession:
    now = datetime(2026, 5, 9, tzinfo=timezone.utc)
    return PlanningSession(
        session_id="session_test",
        hard_constraints=hard_constraints(),
        discovery_state=(
            DiscoveryState(
                payload=discovery_output(),
                selected_card_ids=["disc_waterfront", "disc_museum"],
            )
            if with_discovery
            else None
        ),
        preferences=preferences() if with_preferences else None,
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


def stay_recommendation() -> StayRecommendation:
    option = StayOption(
        id="stay_primary",
        area=area(),
        fit_reason="Central and easy.",
        price_band=band(1200, 2200),
        sample_hotels=[],
    )
    return StayRecommendation(primary=option, alternatives=[], user_override_id=None)


def transport_recommendation() -> TransportRecommendation:
    return TransportRecommendation(
        arrival={"mode": "rail", "duration_minutes": 300, "cost_band": band(500, 900), "note": "Rail."},
        departure={"mode": "rail", "duration_minutes": 300, "cost_band": band(500, 900), "note": "Rail."},
        intracity={"primary_mode": "mixed", "daily_cost_band": band(40, 120, "per_day"), "note": "Transit."},
        tradeoffs=["Rail keeps the trip simple."],
    )


def itinerary(version: int = 1, total_high: float = 1000) -> Itinerary:
    return Itinerary(
        id="itinerary_test",
        session_id="session_test",
        days=[],
        budget=budget_summary(total_high=total_high),
        validator_issues=[],
        version=version,
    )


def validator_error() -> ValidatorIssue:
    return ValidatorIssue(
        code="BUDGET_OVERRUN",
        severity="error",
        scope={"type": "trip"},
        message="Still expensive.",
        suggested_action="Warn user.",
    )
```

- [ ] **Step 1.3: Write state tests**

Create `api/tests/graph/test_state.py`:

```python
from __future__ import annotations

from pydantic import ValidationError

from app.graph.state import (
    PlanState,
    TypeCConfirmation,
    append_progress,
    graph_input_from_state,
    validate_graph_state,
)
from tests.graph.fixtures import session, validator_error


def test_plan_state_validates_session_and_defaults() -> None:
    state = PlanState(session=session(), mode="full_planning")

    assert state.session.session_id == "session_test"
    assert state.corrective_attempts == 0
    assert state.validator_issues == []
    assert state.progress_events == []


def test_graph_state_round_trips_through_json_dict() -> None:
    original = PlanState(session=session(), mode="full_planning")
    raw = graph_input_from_state(original)
    loaded = validate_graph_state(raw)

    assert loaded == original


def test_has_validator_errors_only_for_error_severity() -> None:
    state = PlanState(session=session(), validator_issues=[validator_error()])

    assert state.has_validator_errors is True


def test_append_progress_returns_new_state_without_mutating_original() -> None:
    original = PlanState(session=session())
    updated = append_progress(original, "stay", "started", {"x": 1})

    assert original.progress_events == []
    assert updated.progress_events[0].node == "stay"
    assert updated.progress_events[0].status == "started"
    assert updated.progress_events[0].payload == {"x": 1}


def test_type_c_confirmation_shape_is_strict() -> None:
    confirmation = TypeCConfirmation(
        detected_change="Budget is now 3000",
        rerun_stages=["discovery", "preferences", "itinerary"],
        discard_estimate="Most downstream planning state will be refreshed.",
    )

    assert confirmation.rerun_stages == ["discovery", "preferences", "itinerary"]

    try:
        TypeCConfirmation.model_validate(
            {
                "detected_change": "x",
                "rerun_stages": ["itinerary"],
                "discard_estimate": "x",
                "extra": "no",
            }
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra fields must be rejected")
```

- [ ] **Step 1.4: Verify state tests fail**

Run:

```bash
cd api && uv run pytest tests/graph/test_state.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.graph.state'`.

- [ ] **Step 1.5: Implement `state.py`**

Create `api/app/graph/state.py`:

```python
"""LangGraph state models for the travel planning workflow."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

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


class _StrictGraphModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ProgressEvent(_StrictGraphModel):
    node: str
    status: ProgressStatus
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class TypeCConfirmation(_StrictGraphModel):
    detected_change: str
    rerun_stages: list[TypeCStage]
    discard_estimate: str


class PlanningGraphResult(_StrictGraphModel):
    session_id: str
    stay: StayRecommendation
    transport: TransportRecommendation
    itinerary: Itinerary
    validator_issues: list[ValidatorIssue]
    progress_events: list[ProgressEvent]


class AdjustmentGraphResult(_StrictGraphModel):
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


class PlanState(_StrictGraphModel):
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
    planner_only_reason: str | None
    adjustment_text: str | None
    type_c_action: TypeCAction | None
    discovery_output: dict[str, Any] | None
    stay_recommendation: dict[str, Any] | None
    transport_recommendation: dict[str, Any] | None
    itinerary: dict[str, Any] | None
    validator_issues: list[dict[str, Any]]
    corrective_attempts: int
    classification: dict[str, Any] | None
    message: str | None
    confirmation: dict[str, Any] | None
    reset_to_step: Literal["discovery"] | None
    fork_requested: bool
    progress_events: list[dict[str, Any]]


def graph_input_from_state(state: PlanState) -> GraphState:
    return state.model_dump(mode="json")


def validate_graph_state(raw: GraphState | dict[str, Any] | PlanState) -> PlanState:
    if isinstance(raw, PlanState):
        return raw
    return PlanState.model_validate(raw)


def state_patch(**updates: object) -> GraphState:
    return {key: value for key, value in updates.items() if value is not None}


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
        created_at=datetime.now(timezone.utc),
    )
    return state.model_copy(
        update={"progress_events": [*state.progress_events, event]}
    )
```

- [ ] **Step 1.6: Export graph package**

Create `api/app/graph/__init__.py`:

```python
"""LangGraph planning workflow package."""

from app.graph.state import (
    AdjustmentGraphResult,
    PlanState,
    PlanningGraphResult,
    ProgressEvent,
    TypeCConfirmation,
)

__all__ = [
    "AdjustmentGraphResult",
    "PlanState",
    "PlanningGraphResult",
    "ProgressEvent",
    "TypeCConfirmation",
]
```

- [ ] **Step 1.7: Run state tests and commit**

Run:

```bash
cd api && uv run pytest tests/graph/test_state.py -v
cd api && uv run ruff check app/graph tests/graph
```

Expected: all state tests pass and ruff reports no issues.

Commit:

```bash
git add api/app/graph api/tests/graph
git commit -m "feat(api): add graph state models"
```

---

## Task 2 — Metrics Events

**Files:**
- Create: `api/app/metrics/__init__.py`
- Create: `api/app/metrics/events.py`
- Create: `api/tests/graph/test_metrics_events.py`

- [ ] **Step 2.1: Write metrics tests**

Create `api/tests/graph/test_metrics_events.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from app.metrics.events import (
    append_metric_event,
    compute_metric_summary,
    default_metric_file_path,
    safe_append_metric_event,
)


async def test_writes_jsonl_events_and_computes_funnel_totals(tmp_path: Path) -> None:
    file_path = tmp_path / "events.jsonl"

    await append_metric_event({"name": "step1_submitted", "session_id": "s1", "payload": {}}, file_path)
    await append_metric_event(
        {
            "name": "discovery_enrichment_summary",
            "session_id": "s1",
            "payload": {"total_cards": 3},
        },
        file_path,
    )
    await append_metric_event({"name": "itinerary_finalized", "session_id": "s1", "payload": {}}, file_path)

    lines = file_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    assert json.loads(lines[0])["created_at"].endswith("Z")

    summary = await compute_metric_summary(file_path)
    assert summary.event_counts["step1_submitted"] == 1
    assert summary.event_counts["itinerary_finalized"] == 1
    assert summary.sessions_submitted == 1
    assert summary.sessions_with_final_itinerary == 1


async def test_safe_append_metric_event_swallows_failures() -> None:
    await safe_append_metric_event(
        {"name": "step1_submitted", "session_id": "s1", "payload": {}},
        Path("/dev/null/events.jsonl"),
    )


def test_default_metric_file_path_uses_api_data_dir() -> None:
    path = default_metric_file_path({})

    assert path.name == "events.jsonl"
    assert path.parent.name == ".data"
    assert path.parent.parent.name == "api"
```

- [ ] **Step 2.2: Verify metrics tests fail**

Run:

```bash
cd api && uv run pytest tests/graph/test_metrics_events.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.metrics'`.

- [ ] **Step 2.3: Implement metrics events**

Create `api/app/metrics/events.py`:

```python
"""Best-effort JSONL metric events ported from web/src/server/metrics/events.ts."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field

MetricEventName = Literal[
    "step1_submitted",
    "discovery_arrived",
    "discovery_enrichment_summary",
    "attraction_selected",
    "preferences_completed",
    "itinerary_finalized",
    "validator_error_finalized",
    "adjustment_classified",
    "type_c_action_taken",
    "provider_fallback_used",
    "stay_override_set",
]


class MetricEventPayload(TypedDict, total=False):
    name: MetricEventName
    session_id: str
    payload: dict[str, Any]
    created_at: str


class MetricSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_counts: dict[MetricEventName, int] = Field(default_factory=dict)
    sessions_submitted: int
    sessions_with_final_itinerary: int
    sessions_with_residual_validator_errors: int


def default_metric_file_path(env: dict[str, str] | None = None) -> Path:
    source = env if env is not None else dict(os.environ)
    data_dir = source.get("METRICS_DATA_DIR")
    if data_dir:
        return Path(data_dir) / "events.jsonl"
    return Path(__file__).resolve().parents[2] / ".data" / "events.jsonl"


async def append_metric_event(
    event: MetricEventPayload,
    file_path: str | Path | None = None,
) -> None:
    target = Path(file_path) if file_path is not None else default_metric_file_path()
    payload = {
        **event,
        "created_at": event.get("created_at") or _utc_timestamp(),
    }
    line = json.dumps(payload, ensure_ascii=False)
    await asyncio.to_thread(_append_line, target, line)


async def safe_append_metric_event(
    event: MetricEventPayload,
    file_path: str | Path | None = None,
) -> None:
    try:
        await append_metric_event(event, file_path)
    except Exception:  # noqa: BLE001
        return


async def compute_metric_summary(file_path: str | Path | None = None) -> MetricSummary:
    target = Path(file_path) if file_path is not None else default_metric_file_path()
    events = await asyncio.to_thread(_read_events, target)
    event_counts: dict[MetricEventName, int] = {}
    submitted: set[str] = set()
    finalized: set[str] = set()
    residual_errors: set[str] = set()

    for event in events:
        name = event["name"]
        session_id = event["session_id"]
        event_counts[name] = event_counts.get(name, 0) + 1
        if name == "step1_submitted":
            submitted.add(session_id)
        if name == "itinerary_finalized":
            finalized.add(session_id)
        if name == "validator_error_finalized":
            residual_errors.add(session_id)

    return MetricSummary(
        event_counts=event_counts,
        sessions_submitted=len(submitted),
        sessions_with_final_itinerary=len(finalized),
        sessions_with_residual_validator_errors=len(residual_errors),
    )


def _append_line(file_path: Path, line: str) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{line}\n")


def _read_events(file_path: Path) -> list[MetricEventPayload]:
    try:
        content = file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    events: list[MetricEventPayload] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            events.append(json.loads(stripped))
    return events


def _utc_timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
```

Create `api/app/metrics/__init__.py`:

```python
"""Metrics helpers."""

from app.metrics.events import (
    MetricEventName,
    MetricSummary,
    append_metric_event,
    compute_metric_summary,
    default_metric_file_path,
    safe_append_metric_event,
)

__all__ = [
    "MetricEventName",
    "MetricSummary",
    "append_metric_event",
    "compute_metric_summary",
    "default_metric_file_path",
    "safe_append_metric_event",
]
```

- [ ] **Step 2.4: Run metrics tests and commit**

Run:

```bash
cd api && uv run pytest tests/graph/test_metrics_events.py -v
cd api && uv run ruff check app/metrics tests/graph/test_metrics_events.py
```

Expected: all metrics tests pass and ruff reports no issues.

Commit:

```bash
git add api/app/metrics api/tests/graph/test_metrics_events.py
git commit -m "feat(api): add metrics event logging"
```

---

## Task 3 — Agent Nodes

**Files:**
- Create: `api/app/graph/nodes/discovery.py`
- Create: `api/app/graph/nodes/stay.py`
- Create: `api/app/graph/nodes/transport.py`
- Create: `api/app/graph/nodes/planner.py`
- Create: `api/app/graph/nodes/validator.py`
- Create: `api/tests/graph/test_nodes.py`

- [ ] **Step 3.1: Write node behavior tests**

Create `api/tests/graph/test_nodes.py`:

```python
from __future__ import annotations

from app.graph.nodes.discovery import compute_enrichment_status, run_discovery_agent
from app.graph.nodes.planner import active_stay_option, run_planner_agent
from app.graph.nodes.stay import run_stay_agent
from app.graph.nodes.transport import run_transport_agent
from app.graph.nodes.validator import run_validator_node
from app.graph.state import PlanState
from tests.graph.fixtures import discovery_card, session, stay_recommendation, transport_recommendation


def test_compute_enrichment_status_matches_ts_behavior() -> None:
    complete = discovery_card()
    partial = complete.model_copy(update={"image_url": None})
    minimal = complete.model_copy(update={"place": None})

    assert compute_enrichment_status(complete) == "complete"
    assert compute_enrichment_status(partial) == "partial"
    assert compute_enrichment_status(minimal) == "minimal"


async def test_discovery_fixture_returns_cards_and_budget() -> None:
    output = await run_discovery_agent(session(with_discovery=False), fixture_mode=True)

    assert len(output.cards) >= 3
    assert output.budget_estimate.currency == "CNY"
    assert output.cards[0].cost_signal in {"free", "low", "medium", "high", "unknown"}


async def test_stay_agent_uses_discovery_areas() -> None:
    stay = await run_stay_agent(session())

    assert stay.primary.id == "stay_primary"
    assert stay.primary.area.id == "area_central"
    assert len(stay.alternatives) >= 1


async def test_transport_agent_uses_preference() -> None:
    transport = await run_transport_agent(session())

    assert transport.arrival.mode == "rail"
    assert transport.intracity.primary_mode == "mixed"


async def test_planner_agent_increments_version_and_uses_selected_cards() -> None:
    result = await run_planner_agent(
        session(),
        stay_recommendation(),
        transport_recommendation(),
    )

    assert result.session_id == "session_test"
    assert result.version == 1
    assert len(result.days) == 3
    assert result.days[0].segments


def test_active_stay_option_uses_user_override() -> None:
    stay = stay_recommendation()
    alt = stay.primary.model_copy(update={"id": "stay_alt"})
    overridden = stay.model_copy(update={"alternatives": [alt], "user_override_id": "stay_alt"})

    assert active_stay_option(overridden).id == "stay_alt"


async def test_validator_node_attaches_issues_to_state() -> None:
    stay = await run_stay_agent(session())
    transport = await run_transport_agent(session())
    itinerary = await run_planner_agent(session(), stay, transport)
    state = PlanState(
        session=session(),
        stay_recommendation=stay,
        transport_recommendation=transport,
        itinerary=itinerary,
    )

    patch = await run_validator_node(state)

    assert "validator_issues" in patch
    assert isinstance(patch["validator_issues"], list)
```

- [ ] **Step 3.2: Verify node tests fail**

Run:

```bash
cd api && uv run pytest tests/graph/test_nodes.py -v
```

Expected: FAIL because node modules do not exist.

- [ ] **Step 3.3: Implement discovery node**

Create `api/app/graph/nodes/discovery.py` by porting `web/src/server/agents/discovery.ts`. Required public functions:

```python
async def run_discovery_agent(
    session: PlanningSession,
    *,
    fixture_mode: bool = False,
    llm_provider: LLMProvider | None = None,
    cost_logger: LLMCostLogger | None = None,
) -> DiscoveryOutput: ...

def compute_enrichment_status(card: DiscoveryCard) -> Literal["complete", "partial", "minimal"]: ...

async def run_discovery_node(state: PlanState) -> GraphState: ...
```

Implementation requirements:
- If `fixture_mode` is true or neither `LLM_PROVIDER_API_KEY` nor `GEMINI_API_KEY` is set, return a deterministic fixture.
- Fixture must include at least 6 cards, 2 food summaries, 2 area summaries, a budget summary, and one `SourceNote(provider="fixture", ...)`.
- Normalize each card with:
  - `classify_attraction_cost_signal(card.cost_estimate, session.hard_constraints)`
  - `compute_enrichment_status(card)`
- Live path must call:

```python
output = await generate_structured(
    system="You are a travel discovery agent. Return only valid JSON matching the schema.",
    user=build_discovery_prompt(session),
    schema=DiscoveryOutput,
    label="discovery_agent",
    provider=llm_provider,
    cost_logger=cost_logger,
)
```

- `run_discovery_node(...)` returns:

```python
return graph_input_from_state(
    append_progress(
        state.model_copy(update={"discovery_output": output}),
        "discovery",
        "completed",
        {"card_count": len(output.cards)},
    )
)
```

- [ ] **Step 3.4: Implement stay node**

Create `api/app/graph/nodes/stay.py` with:

```python
async def run_stay_agent(session: PlanningSession) -> StayRecommendation: ...
async def run_stay_node(state: PlanState) -> GraphState: ...
```

Port the current TS behavior:
- Choose `session.discovery_state.payload.area_summaries[0]` as primary area when available.
- Use fallback central/quiet areas when discovery payload is missing.
- Return `stay_primary`, `stay_alt_quiet`, and `stay_alt_value`.
- Preserve `session.stay_recommendation.user_override_id` when present.
- `run_stay_node(...)` should update `stay_recommendation` and append a completed progress event with `{"primary_area": stay.primary.area.id}`.

- [ ] **Step 3.5: Implement transport node**

Create `api/app/graph/nodes/transport.py` with:

```python
async def run_transport_agent(session: PlanningSession) -> TransportRecommendation: ...
async def run_transport_node(state: PlanState) -> GraphState: ...
```

Port the current TS behavior:
- Read `session.preferences.intercity_transport_preference`; default to `"flexible"`.
- Use `"flight"` only when explicitly requested, otherwise `"rail"`.
- Return arrival/departure legs, intracity strategy, and one tradeoff string.
- `run_transport_node(...)` should update `transport_recommendation` and append progress with `{"arrival_mode": transport.arrival.mode}`.

- [ ] **Step 3.6: Implement planner node**

Create `api/app/graph/nodes/planner.py` with:

```python
async def run_planner_agent(
    session: PlanningSession,
    stay: StayRecommendation,
    transport: TransportRecommendation,
    validator_issues: list[ValidatorIssue] | None = None,
) -> Itinerary: ...

def active_stay_option(stay: StayRecommendation) -> StayOption: ...
async def run_planner_node(state: PlanState) -> GraphState: ...
```

Port the current TS behavior:
- Use selected discovery cards when available.
- Fall back to the first 3 discovery cards when no cards are selected.
- Build one day per `session.hard_constraints.duration_days`.
- Add hotel start, attraction, food, rest/second attraction, and hotel return segments.
- Increment version from existing `session.itinerary.version`; start at `1`.
- Include `"Corrective pass used validator errors as planning context."` in day notes when `validator_issues` is non-empty.
- `run_planner_node(...)` must require `stay_recommendation` and `transport_recommendation`, update `itinerary`, and append progress with `{"version": itinerary.version}`.

- [ ] **Step 3.7: Implement validator node**

Create `api/app/graph/nodes/validator.py` with:

```python
async def run_validator_node(state: PlanState) -> GraphState: ...
```

Implementation:
- Require `state.itinerary`.
- Build `ValidatorContext(discovery_cards=state.session.discovery_state.payload.cards)` when discovery payload exists; otherwise use an empty card list.
- Call `validate_itinerary(...)`.
- Return `validator_issues` and an itinerary copy with `validator_issues` attached.
- Append progress with `{"issue_count": len(issues), "error_count": error_count}`.

- [ ] **Step 3.8: Run node tests and commit**

Run:

```bash
cd api && uv run pytest tests/graph/test_nodes.py -v
cd api && uv run ruff check app/graph/nodes tests/graph/test_nodes.py
```

Expected: all node tests pass and ruff reports no issues.

Commit:

```bash
git add api/app/graph/nodes api/tests/graph/test_nodes.py
git commit -m "feat(api): add graph planning nodes"
```

---

## Task 4 — Main Planning Workflow

**Files:**
- Create: `api/app/graph/workflow.py`
- Modify: `api/app/graph/__init__.py`
- Create: `api/tests/graph/test_workflow.py`

- [ ] **Step 4.1: Write workflow tests**

Create `api/tests/graph/test_workflow.py`:

```python
from __future__ import annotations

from app.graph.workflow import run_full_planning_workflow, run_planner_only_workflow
from app.models.schemas import ValidatorIssue
from tests.graph.fixtures import session


async def test_full_workflow_finalizes_without_corrective_pass() -> None:
    result = await run_full_planning_workflow(session())

    assert result.session_id == "session_test"
    assert result.stay.primary.id == "stay_primary"
    assert result.transport.arrival.mode == "rail"
    assert result.itinerary.version == 1
    assert result.validator_issues == result.itinerary.validator_issues
    assert [event.node for event in result.progress_events] == ["stay", "transport", "planner", "validator"]


async def test_planner_only_workflow_requires_existing_stay_and_transport() -> None:
    base = session()

    try:
        await run_planner_only_workflow(base, reason="stay_override")
    except ValueError as exc:
        assert "requires existing stay and transport" in str(exc)
    else:
        raise AssertionError("planner-only workflow must reject incomplete sessions")


async def test_corrective_pass_runs_once_for_error(monkeypatch) -> None:
    from app.graph import workflow

    calls = {"planner": 0}
    error = ValidatorIssue(
        code="BUDGET_OVERRUN",
        severity="error",
        scope={"type": "trip"},
        message="Still expensive",
        suggested_action="Warn user",
    )

    original_planner = workflow.run_planner_node

    async def counting_planner(state):
        calls["planner"] += 1
        return await original_planner(state)

    async def always_error(state):
        state = workflow.validate_graph_state(state)
        itinerary = state.itinerary.model_copy(update={"validator_issues": [error]})
        return workflow.graph_input_from_state(
            state.model_copy(update={"itinerary": itinerary, "validator_issues": [error]})
        )

    monkeypatch.setattr(workflow, "run_planner_node", counting_planner)
    monkeypatch.setattr(workflow, "run_validator_node", always_error)

    result = await run_full_planning_workflow(session())

    assert calls["planner"] == 2
    assert result.validator_issues == [error]
    assert result.itinerary.validator_issues == [error]


async def test_warning_only_validation_does_not_rerun_planner(monkeypatch) -> None:
    from app.graph import workflow

    calls = {"planner": 0}
    warning = ValidatorIssue(
        code="DAY_OVERLOADED",
        severity="warning",
        scope={"type": "day", "day_index": 1},
        message="Dense day",
        suggested_action="Move one stop",
    )

    original_planner = workflow.run_planner_node

    async def counting_planner(state):
        calls["planner"] += 1
        return await original_planner(state)

    async def warning_only(state):
        state = workflow.validate_graph_state(state)
        itinerary = state.itinerary.model_copy(update={"validator_issues": [warning]})
        return workflow.graph_input_from_state(
            state.model_copy(update={"itinerary": itinerary, "validator_issues": [warning]})
        )

    monkeypatch.setattr(workflow, "run_planner_node", counting_planner)
    monkeypatch.setattr(workflow, "run_validator_node", warning_only)

    result = await run_full_planning_workflow(session())

    assert calls["planner"] == 1
    assert result.validator_issues == [warning]
```

- [ ] **Step 4.2: Verify workflow tests fail**

Run:

```bash
cd api && uv run pytest tests/graph/test_workflow.py -v
```

Expected: FAIL because `app.graph.workflow` does not exist.

- [ ] **Step 4.3: Implement planning workflow**

Create `api/app/graph/workflow.py`:

```python
"""LangGraph workflow runner for full itinerary generation."""
from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.planner import run_planner_node
from app.graph.nodes.stay import run_stay_agent, run_stay_node
from app.graph.nodes.transport import run_transport_agent, run_transport_node
from app.graph.nodes.validator import run_validator_node
from app.graph.state import (
    GraphState,
    PlanState,
    PlanningGraphResult,
    graph_input_from_state,
    validate_graph_state,
)
from app.models.schemas import PlanningSession

RouteName = Literal["prepare_corrective", "end"]


async def prepare_corrective_node(state: GraphState) -> GraphState:
    current = validate_graph_state(state)
    return graph_input_from_state(
        current.model_copy(
            update={"corrective_attempts": current.corrective_attempts + 1}
        )
    )


def route_after_validation(state: GraphState) -> RouteName:
    current = validate_graph_state(state)
    if current.has_validator_errors and current.corrective_attempts < 1:
        return "prepare_corrective"
    return "end"


def create_planning_graph():
    graph = StateGraph(GraphState)
    graph.add_node("stay", run_stay_node)
    graph.add_node("transport", run_transport_node)
    graph.add_node("planner", run_planner_node)
    graph.add_node("validator", run_validator_node)
    graph.add_node("prepare_corrective", prepare_corrective_node)
    graph.add_edge(START, "stay")
    graph.add_edge("stay", "transport")
    graph.add_edge("transport", "planner")
    graph.add_edge("planner", "validator")
    graph.add_conditional_edges(
        "validator",
        route_after_validation,
        {"prepare_corrective": "prepare_corrective", "end": END},
    )
    graph.add_edge("prepare_corrective", "planner")
    return graph.compile()


def create_planner_only_graph():
    graph = StateGraph(GraphState)
    graph.add_node("planner", run_planner_node)
    graph.add_node("validator", run_validator_node)
    graph.add_node("prepare_corrective", prepare_corrective_node)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "validator")
    graph.add_conditional_edges(
        "validator",
        route_after_validation,
        {"prepare_corrective": "prepare_corrective", "end": END},
    )
    graph.add_edge("prepare_corrective", "planner")
    return graph.compile()


async def run_full_planning_workflow(session: PlanningSession) -> PlanningGraphResult:
    initial = PlanState(session=session, mode="full_planning")
    raw = await create_planning_graph().ainvoke(graph_input_from_state(initial))
    final = validate_graph_state(raw)
    return _planning_result(final)


async def run_planner_only_workflow(
    session: PlanningSession,
    *,
    reason: str,
) -> PlanningGraphResult:
    if session.stay_recommendation is None or session.transport_recommendation is None:
        raise ValueError("planner-only workflow requires existing stay and transport")
    initial = PlanState(
        session=session,
        mode="planner_only",
        planner_only_reason=reason,
        stay_recommendation=session.stay_recommendation,
        transport_recommendation=session.transport_recommendation,
    )
    raw = await create_planner_only_graph().ainvoke(graph_input_from_state(initial))
    final = validate_graph_state(raw)
    return _planning_result(final)


def _planning_result(state: PlanState) -> PlanningGraphResult:
    if state.stay_recommendation is None:
        raise ValueError("planning graph ended without stay recommendation")
    if state.transport_recommendation is None:
        raise ValueError("planning graph ended without transport recommendation")
    if state.itinerary is None:
        raise ValueError("planning graph ended without itinerary")
    return PlanningGraphResult(
        session_id=state.session.session_id,
        stay=state.stay_recommendation,
        transport=state.transport_recommendation,
        itinerary=state.itinerary,
        validator_issues=state.validator_issues,
        progress_events=state.progress_events,
    )
```

- [ ] **Step 4.4: Export workflow runners**

Modify `api/app/graph/__init__.py`:

```python
"""LangGraph planning workflow package."""

from app.graph.state import (
    AdjustmentGraphResult,
    PlanState,
    PlanningGraphResult,
    ProgressEvent,
    TypeCConfirmation,
)
from app.graph.workflow import (
    run_full_planning_workflow,
    run_planner_only_workflow,
)

__all__ = [
    "AdjustmentGraphResult",
    "PlanState",
    "PlanningGraphResult",
    "ProgressEvent",
    "TypeCConfirmation",
    "run_full_planning_workflow",
    "run_planner_only_workflow",
]
```

- [ ] **Step 4.5: Run workflow tests and commit**

Run:

```bash
cd api && uv run pytest tests/graph/test_workflow.py -v
cd api && uv run ruff check app/graph tests/graph/test_workflow.py
```

Expected: all workflow tests pass and ruff reports no issues.

Commit:

```bash
git add api/app/graph api/tests/graph/test_workflow.py
git commit -m "feat(api): add langgraph planning workflow"
```

---

## Task 5 — Adjustment Classifier And Type A/B/C Subgraphs

**Files:**
- Create: `api/app/graph/nodes/adjustment_classifier.py`
- Create: `api/app/graph/adjustments/type_a.py`
- Create: `api/app/graph/adjustments/type_b.py`
- Create: `api/app/graph/adjustments/type_c.py`
- Modify: `api/app/graph/adjustments/__init__.py`
- Modify: `api/app/graph/__init__.py`
- Create: `api/tests/graph/test_adjustments.py`

- [ ] **Step 5.1: Write adjustment tests**

Create `api/tests/graph/test_adjustments.py`:

```python
from __future__ import annotations

from app.graph.adjustments import run_adjustment_workflow
from app.graph.nodes.adjustment_classifier import classify_adjustment
from tests.graph.fixtures import session, stay_recommendation, transport_recommendation, itinerary


def session_with_plan():
    base = session()
    return base.model_copy(
        update={
            "stay_recommendation": stay_recommendation(),
            "transport_recommendation": transport_recommendation(),
            "itinerary": itinerary(),
        }
    )


def test_classifier_matches_type_a_day_adjustment() -> None:
    result = classify_adjustment("Make the second afternoon easier.")

    assert result.type == "A"
    assert result.confidence >= 0.55
    assert result.target_scope == "day"


def test_classifier_matches_type_b_stay_adjustment() -> None:
    result = classify_adjustment("酒店换到更安静的区域")

    assert result.type == "B"
    assert result.target_scope == "stay"


def test_classifier_matches_type_c_budget_adjustment() -> None:
    result = classify_adjustment("预算改成 3000")

    assert result.type == "C"
    assert result.target_scope == "budget"


def test_classifier_low_confidence_unknown() -> None:
    result = classify_adjustment("ok")

    assert result.type == "unknown"
    assert result.confidence < 0.55


async def test_type_a_adjustment_runs_planner_only() -> None:
    result = await run_adjustment_workflow(
        session_with_plan(),
        message="Make day two easier.",
    )

    assert result.classification.type == "A"
    assert result.itinerary is not None
    assert result.message == "Itinerary updated."


async def test_type_b_stay_adjustment_reruns_stay_then_planner() -> None:
    result = await run_adjustment_workflow(
        session_with_plan(),
        message="酒店换到更安静的区域",
    )

    assert result.classification.type == "B"
    assert result.classification.target_scope == "stay"
    assert result.stay is not None
    assert result.stay.user_override_id is None
    assert result.itinerary is not None


async def test_type_b_transport_adjustment_reruns_transport_then_planner() -> None:
    result = await run_adjustment_workflow(
        session_with_plan(),
        message="不要坐飞机，改高铁",
    )

    assert result.classification.type == "B"
    assert result.classification.target_scope == "transport"
    assert result.transport is not None
    assert result.itinerary is not None


async def test_low_confidence_adjustment_returns_clarification() -> None:
    result = await run_adjustment_workflow(session_with_plan(), message="ok")

    assert result.classification.type == "unknown"
    assert result.itinerary is None
    assert "clarify" in result.message.lower()


async def test_type_c_without_action_returns_confirmation() -> None:
    result = await run_adjustment_workflow(
        session_with_plan(),
        message="预算改成 3000",
    )

    assert result.classification.type == "C"
    assert result.confirmation is not None
    assert result.reset_to_step is None
    assert result.fork_requested is False


async def test_type_c_replan_returns_reset_instruction() -> None:
    result = await run_adjustment_workflow(
        session_with_plan(),
        message="预算改成 3000",
        type_c_action="replan",
    )

    assert result.classification.type == "C"
    assert result.reset_to_step == "discovery"
    assert result.message == "Session reset to discovery."


async def test_type_c_save_and_start_new_returns_fork_instruction() -> None:
    result = await run_adjustment_workflow(
        session_with_plan(),
        message="预算改成 3000",
        type_c_action="save_and_start_new",
    )

    assert result.classification.type == "C"
    assert result.fork_requested is True
    assert result.message == "New session requested."


async def test_type_c_cancel_returns_cancelled_message() -> None:
    result = await run_adjustment_workflow(
        session_with_plan(),
        message="预算改成 3000",
        type_c_action="cancel",
    )

    assert result.classification.type == "C"
    assert result.message == "Root change cancelled."
```

- [ ] **Step 5.2: Verify adjustment tests fail**

Run:

```bash
cd api && uv run pytest tests/graph/test_adjustments.py -v
```

Expected: FAIL because adjustment modules do not exist.

- [ ] **Step 5.3: Implement classifier**

Create `api/app/graph/nodes/adjustment_classifier.py`:

```python
"""Adjustment classifier ported from web/src/server/agents/adjustmentClassifier.ts."""
from __future__ import annotations

import re

from app.models.schemas import AdjustmentRequest


def classify_adjustment(raw_text: str) -> AdjustmentRequest:
    text = raw_text.strip()
    lower = text.lower()

    if not text or len(text) < 4:
        return _base(text, "unknown", 0.2, "none", None)

    if re.search(r"预算|天数|人数|目的地|出发日期|departure|budget|destination|traveler|duration", text, re.I):
        return _base(text, "C", 0.86, _root_scope(lower), text)

    if re.search(r"酒店|住宿|住|hotel|stay|area|区域|民宿|homestay", text, re.I):
        return _base(text, "B", 0.82, "stay", text)

    if re.search(r"交通|高铁|火车|飞机|航班|rail|train|flight|transport", text, re.I):
        return _base(text, "B", 0.82, "transport", text)

    if re.search(r"轻松|紧凑|换|删除|添加|第二天|下午|itinerary|plan|day", text, re.I):
        return _base(text, "A", 0.78, "day", text)

    return _base(text, "unknown", 0.45, "none", None)


def _base(
    raw_text: str,
    type_: str,
    confidence: float,
    target_scope: str,
    proposed_change: str | None,
) -> AdjustmentRequest:
    return AdjustmentRequest(
        raw_text=raw_text,
        type=type_,
        confidence=confidence,
        target_scope=target_scope,
        proposed_change=proposed_change,
    )


def _root_scope(text: str) -> str:
    if re.search(r"budget|预算", text, re.I):
        return "budget"
    if re.search(r"duration|天数", text, re.I):
        return "duration"
    if re.search(r"destination|目的地", text, re.I):
        return "destination"
    if re.search(r"traveler|人数", text, re.I):
        return "traveler_count"
    return "none"
```

- [ ] **Step 5.4: Implement Type A adjustment**

Create `api/app/graph/adjustments/type_a.py`:

```python
"""Type A light itinerary adjustments."""
from __future__ import annotations

from app.graph.state import AdjustmentGraphResult
from app.graph.workflow import run_planner_only_workflow
from app.models.schemas import AdjustmentRequest, PlanningSession


async def run_type_a_adjustment(
    session: PlanningSession,
    classification: AdjustmentRequest,
) -> AdjustmentGraphResult:
    result = await run_planner_only_workflow(
        session,
        reason="type_a_adjustment",
    )
    return AdjustmentGraphResult(
        session_id=session.session_id,
        classification=classification,
        message="Itinerary updated.",
        stay=result.stay,
        transport=result.transport,
        itinerary=result.itinerary,
        validator_issues=result.validator_issues,
        progress_events=result.progress_events,
    )
```

- [ ] **Step 5.5: Implement Type B adjustment**

Create `api/app/graph/adjustments/type_b.py`:

```python
"""Type B stay/transport adjustments."""
from __future__ import annotations

from app.graph.nodes.stay import run_stay_agent
from app.graph.nodes.transport import run_transport_agent
from app.graph.state import AdjustmentGraphResult
from app.graph.workflow import run_planner_only_workflow
from app.models.schemas import AdjustmentRequest, PlanningSession


async def run_type_b_adjustment(
    session: PlanningSession,
    classification: AdjustmentRequest,
) -> AdjustmentGraphResult:
    working = session
    if classification.target_scope == "stay":
        stay = await run_stay_agent(
            working.model_copy(update={"stay_recommendation": None})
        )
        working = working.model_copy(
            update={"stay_recommendation": stay.model_copy(update={"user_override_id": None})}
        )
    elif classification.target_scope == "transport":
        transport = await run_transport_agent(working)
        working = working.model_copy(update={"transport_recommendation": transport})

    result = await run_planner_only_workflow(
        working,
        reason=f"type_b_{classification.target_scope}_adjustment",
    )
    return AdjustmentGraphResult(
        session_id=session.session_id,
        classification=classification,
        message="Itinerary updated.",
        stay=result.stay,
        transport=result.transport,
        itinerary=result.itinerary,
        validator_issues=result.validator_issues,
        progress_events=result.progress_events,
    )
```

- [ ] **Step 5.6: Implement Type C adjustment**

Create `api/app/graph/adjustments/type_c.py`:

```python
"""Type C root-constraint adjustment handling."""
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
```

- [ ] **Step 5.7: Implement adjustment dispatcher**

Create `api/app/graph/adjustments/__init__.py`:

```python
"""Adjustment workflow dispatcher."""
from __future__ import annotations

from app.graph.adjustments.type_a import run_type_a_adjustment
from app.graph.adjustments.type_b import run_type_b_adjustment
from app.graph.adjustments.type_c import run_type_c_adjustment
from app.graph.nodes.adjustment_classifier import classify_adjustment
from app.graph.state import AdjustmentGraphResult, TypeCAction
from app.models.schemas import PlanningSession


async def run_adjustment_workflow(
    session: PlanningSession,
    *,
    message: str,
    type_c_action: TypeCAction | None = None,
) -> AdjustmentGraphResult:
    classification = classify_adjustment(message)
    if classification.type == "unknown" or classification.confidence < 0.55:
        return AdjustmentGraphResult(
            session_id=session.session_id,
            classification=classification,
            message="Can you clarify whether this changes the itinerary, stay, transport, or core trip constraints?",
        )
    if classification.type == "A":
        return await run_type_a_adjustment(session, classification)
    if classification.type == "B":
        return await run_type_b_adjustment(session, classification)
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
```

- [ ] **Step 5.8: Export adjustment runner**

Modify `api/app/graph/__init__.py` to include:

```python
from app.graph.adjustments import run_adjustment_workflow

__all__ = [
    "AdjustmentGraphResult",
    "PlanState",
    "PlanningGraphResult",
    "ProgressEvent",
    "TypeCConfirmation",
    "run_adjustment_workflow",
    "run_full_planning_workflow",
    "run_planner_only_workflow",
]
```

- [ ] **Step 5.9: Run adjustment tests and commit**

Run:

```bash
cd api && uv run pytest tests/graph/test_adjustments.py -v
cd api && uv run ruff check app/graph tests/graph/test_adjustments.py
```

Expected: all adjustment tests pass and ruff reports no issues.

Commit:

```bash
git add api/app/graph api/tests/graph/test_adjustments.py
git commit -m "feat(api): add adjustment graph routing"
```

---

## Task 6 — Full Graph Verification

**Files:**
- Modify: any graph files needed to satisfy full-suite failures.

- [ ] **Step 6.1: Run Plan 5 test suite**

Run:

```bash
cd api && uv run pytest tests/graph -v
```

Expected:
- `test_state.py` passes.
- `test_metrics_events.py` passes.
- `test_nodes.py` passes.
- `test_workflow.py` passes.
- `test_adjustments.py` passes.

- [ ] **Step 6.2: Run dependency suites**

Run:

```bash
cd api && uv run pytest tests/domain tests/llm tests/providers tests/persistence tests/graph -v
```

Expected: all tests from Plans 1-5 pass.

- [ ] **Step 6.3: Run full API test suite**

Run:

```bash
cd api && uv run pytest -v
```

Expected: full backend suite passes.

- [ ] **Step 6.4: Run ruff**

Run:

```bash
cd api && uv run ruff check app tests
```

Expected: `All checks passed!`

- [ ] **Step 6.5: Commit verification fixes**

If Step 6 required code changes, commit them:

```bash
git add api/app/graph api/app/metrics api/tests/graph
git commit -m "test(api): verify langgraph workflow behavior"
```

If Step 6 required no code changes, do not create an empty commit.

---

## Definition Of Done

- [ ] `api/pyproject.toml` has `langgraph>=1.1.10,<1.2.0`.
- [ ] `api/app/graph/` exists with state, nodes, workflow, and adjustment modules.
- [ ] `api/app/metrics/events.py` exists and writes JSONL events.
- [ ] `cd api && uv run pytest tests/graph -v` passes.
- [ ] `cd api && uv run pytest -v` passes.
- [ ] `cd api && uv run ruff check app tests` passes.
- [ ] Happy path planning produces stay, transport, itinerary, validator issues, and progress events.
- [ ] Error-severity validator issues trigger exactly one corrective planner pass.
- [ ] Warning-only validator issues do not trigger a corrective planner pass.
- [ ] Residual error-severity validator issues are attached to the final itinerary.
- [ ] Type A adjustment routes planner-only.
- [ ] Type B stay adjustment reruns stay then planner.
- [ ] Type B transport adjustment reruns transport then planner.
- [ ] Type C adjustment returns confirmation unless an explicit action is passed.
- [ ] Low-confidence/unknown adjustment returns clarification without rerunning planner.

## Subagent Execution Slices

Recommended fresh-subagent ownership if using Subagent-Driven:

1. **Task 0 worker:** owns only `api/app/llm/*`, `api/tests/llm/*`, `api/pyproject.toml`, and `api/uv.lock`.
2. **Task 1 worker:** owns `api/app/graph/state.py`, graph package init files, and `api/tests/graph/{fixtures,test_state}.py`.
3. **Task 2 worker:** owns `api/app/metrics/*` and `api/tests/graph/test_metrics_events.py`.
4. **Task 3 worker:** owns `api/app/graph/nodes/{discovery,stay,transport,planner,validator}.py` and `api/tests/graph/test_nodes.py`.
5. **Task 4 worker:** owns `api/app/graph/workflow.py`, `api/app/graph/__init__.py`, and `api/tests/graph/test_workflow.py`.
6. **Task 5 worker:** owns `api/app/graph/nodes/adjustment_classifier.py`, `api/app/graph/adjustments/*`, `api/app/graph/__init__.py`, and `api/tests/graph/test_adjustments.py`.
7. **Task 6 reviewer:** owns verification only; applies small fixes in touched graph/metrics/test files after full-suite failures are understood.

Each worker must assume others may be editing adjacent files and must not revert unrelated changes.

## Self-Review Notes

- Spec coverage: covers Plan 5 roadmap files, corrective loop, Type A/B/C branches, metrics, and graph tests. FastAPI/SSE remains Plan 6 by design.
- Placeholder scan: no open-ended implementation markers are required for execution; TS parity points identify exact source files and exact behavior.
- Type consistency: all graph result models use Pydantic schema names from `api/app/models/schemas.py`; route-level persistence is deliberately excluded from graph runners.

Plan complete and saved to `docs/superpowers/plans/2026-05-09-langgraph-mvp-5-graph.md`. Two execution options:

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
