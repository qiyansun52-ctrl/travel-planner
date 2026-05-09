> **STATUS: SUPERSEDED (2026-05-09)**
> 本计划的 LangGraph 后端方向仍然有效,但 legacy `/api/plan/generate` 适配形态已被单城市 session MVP 取代。
> 当前唯一 active 计划见:`docs/superpowers/plans/2026-05-09-langgraph-single-city-mvp.md`

# LangGraph Multi-Agent Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-shot `/api/plan/generate` backend call with a LangGraph-driven planner that runs Transport, Stay, and Planner agents, while streaming progress updates to the existing web UI without breaking the final `TravelPlan` contract.

**Architecture:** Keep the current two-service split: Next.js remains a thin UI, FastAPI remains the only backend. Add a small `api/app/graph/` package that owns graph state, specialized prompts, node functions, and compiled LangGraph workflows. The `/api/plan/generate` route becomes an adapter: plain text for legacy callers, `text/event-stream` for progress-aware callers. The frontend consumes the streamed events through a new fetch-stream parser but still ends with the same parsed JSON plan object in `localStorage`.

**Tech Stack:** Python 3.12, FastAPI, LangGraph 1.x, google-genai, Pydantic 2, pytest, httpx-sse, Next.js 16, TypeScript, fetch `ReadableStream`, Jest.

---

**Scope note:** I am keeping backend graph orchestration and frontend stream consumption in one plan because the SSE backend is not user-visible until the current UI consumes it. This ships as one coherent feature rather than two independent subsystems.

## File Map

```text
api/
├── pyproject.toml                               MODIFY — add LangGraph and SSE test dependency
├── README.md                                    MODIFY — document stream mode and LangGraph workflow
├── app/
│   ├── graph/
│   │   ├── __init__.py                          CREATE — graph package marker
│   │   ├── state.py                             CREATE — PlanRunInput, ProgressEvent, PlanState
│   │   ├── prompts.py                           CREATE — transport/stay/planner prompt builders
│   │   └── workflow.py                          CREATE — LangGraph nodes + compiled workflows + stream helpers
│   └── routes/
│       └── plan.py                              MODIFY — switch from one-shot LLM call to plain/SSE graph adapter
└── tests/
    ├── test_graph_prompts.py                    CREATE — prompt builder tests
    ├── test_graph_state.py                      CREATE — request/state/progress model tests
    ├── test_graph_workflow.py                   CREATE — workflow execution tests
    └── test_plan_route_sse.py                   CREATE — plain text + SSE route tests

web/
└── src/
    ├── lib/
    │   ├── types.ts                             MODIFY — PlanAgent + PlanProgressEvent types
    │   ├── planStream.ts                        CREATE — SSE block splitter and event parser
    │   └── apiClient.ts                         MODIFY — generatePlanStream + existing plain helpers
    ├── __tests__/
    │   └── lib/
    │       └── planStream.test.ts              CREATE — stream parser tests
    ├── app/
    │   └── discover/[destination]/page.tsx     MODIFY — consume stream during initial plan generation
    ├── hooks/
    │   └── usePlan.ts                           MODIFY — consume stream during plan adjustment
    └── components/
        ├── discover/SelectionBar.tsx            MODIFY — show live generation status
        └── plan/AIChatPanel.tsx                 MODIFY — show live adjustment status
```

---

### Task 1: Add LangGraph and SSE Test Dependencies

**Files:**
- Modify: `api/pyproject.toml`
- Create: `api/app/graph/__init__.py`

- [ ] **Step 1: Add the backend dependencies**

Update `api/pyproject.toml`:

```toml
[project]
name = "travel-planner-api"
version = "0.1.0"
description = "Python FastAPI backend for travel planner — Plan 1 (foundation)"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "google-genai>=1.73.1",
    "tavily-python>=0.5.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.27.0",
    "langgraph>=1.1.6",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-httpx>=0.30.0",
    "httpx-sse>=0.4.3",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.uv]
package = false
```

- [ ] **Step 2: Sync the environment**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/api
uv sync
```

Expected: finishes successfully and installs `langgraph` plus `httpx-sse`.

- [ ] **Step 3: Verify the imports exist**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/api
uv run python -c "from langgraph.graph import StateGraph, START, END; from httpx_sse import aconnect_sse; print('langgraph-ok')"
```

Expected:

```text
langgraph-ok
```

- [ ] **Step 4: Create the graph package marker**

Create `api/app/graph/__init__.py`:

```python
"""LangGraph workflow package for travel plan generation."""
```

- [ ] **Step 5: Commit**

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app
git add api/pyproject.toml api/app/graph/__init__.py api/uv.lock
git commit -m "chore(api): add langgraph and sse test dependencies"
```

---

### Task 2: Add Multi-Agent Prompt Builders

**Files:**
- Create: `api/app/graph/prompts.py`
- Create: `api/tests/test_graph_prompts.py`

- [ ] **Step 1: Write the failing prompt tests**

Create `api/tests/test_graph_prompts.py`:

```python
from app.graph.prompts import (
    build_adjustment_planner_prompt,
    build_planner_prompt,
    build_stay_prompt,
    build_transport_prompt,
)
from app.models.attraction import AttractionCard
from app.models.preferences import UserPreferences


PREFS = UserPreferences(
    destination="上海",
    departureCity="北京",
    departureDate="2026-05-10",
    days=3,
    totalBudget=5000,
    accommodationDescription="想住在老城区的精品民宿",
    experienceDescription="想去当地人才知道的小馆子",
)

CARDS = [
    AttractionCard(
        id="c1",
        name="外滩",
        section="experience",
        description="夜景地标",
        estimatedCost="免费",
        imageUrl="",
        tags=["地标"],
    ),
    AttractionCard(
        id="c2",
        name="高铁G1",
        section="transport",
        description="北京到上海",
        estimatedCost="¥553",
        imageUrl="",
        tags=["高铁"],
    ),
]


def test_transport_prompt_mentions_destination_and_budget():
    prompt = build_transport_prompt(PREFS, CARDS)
    assert "上海" in prompt
    assert "5000" in prompt
    assert "交通规划专员" in prompt


def test_stay_prompt_mentions_accommodation_expectation():
    prompt = build_stay_prompt(PREFS, CARDS)
    assert "精品民宿" in prompt
    assert "住宿规划专员" in prompt


def test_planner_prompt_includes_transport_and_stay_summaries():
    prompt = build_planner_prompt(
        PREFS,
        CARDS,
        transport_summary="高铁优先，去程早班。",
        stay_summary="建议住人民广场附近。",
    )
    assert "高铁优先" in prompt
    assert "人民广场附近" in prompt
    assert '"days"' in prompt


def test_planner_prompt_includes_selected_cards():
    prompt = build_planner_prompt(
        PREFS,
        CARDS,
        transport_summary="高铁优先",
        stay_summary="住老城区",
    )
    assert "外滩" in prompt
    assert "高铁G1" in prompt


def test_adjustment_prompt_mentions_current_plan_and_request():
    prompt = build_adjustment_planner_prompt(
        current_plan='{"days":[]}',
        user_request="把第二天下午改轻松一点",
        selected=CARDS,
    )
    assert "把第二天下午改轻松一点" in prompt
    assert '{"days":[]}' in prompt
    assert "外滩" in prompt
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/api
uv run pytest tests/test_graph_prompts.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.graph.prompts'`.

- [ ] **Step 3: Write the prompt builder module**

Create `api/app/graph/prompts.py`:

```python
"""Prompt builders for the LangGraph multi-agent planner."""

from app.models.attraction import AttractionCard
from app.models.preferences import UserPreferences


def _selected_text(selected: list[AttractionCard]) -> str:
    if not selected:
        return "（用户还没有额外勾选内容）"
    return "、".join(f"{card.name}（{card.estimated_cost}）" for card in selected)


def build_transport_prompt(
    prefs: UserPreferences,
    selected: list[AttractionCard],
) -> str:
    return f"""你是一名交通规划专员。请只输出简洁中文摘要，不要 JSON，不要 Markdown。

目的地：{prefs.destination}
出发城市：{prefs.departure_city}
出发日期：{prefs.departure_date}
旅行天数：{prefs.days}天
总预算：¥{prefs.total_budget}
用户已选内容：{_selected_text(selected)}

请给出：
1. 去程建议（航班/高铁/落地交通）
2. 市内出行建议（地铁/步行/打车）
3. 节奏提醒（早出发、避开高峰等）

输出 4-6 行中文摘要。"""


def build_stay_prompt(
    prefs: UserPreferences,
    selected: list[AttractionCard],
) -> str:
    return f"""你是一名住宿规划专员。请只输出简洁中文摘要，不要 JSON，不要 Markdown。

目的地：{prefs.destination}
出发日期：{prefs.departure_date}
旅行天数：{prefs.days}天
总预算：¥{prefs.total_budget}
住宿期待：{prefs.accommodation_description or '未填写'}
体验期待：{prefs.experience_description}
用户已选内容：{_selected_text(selected)}

请给出：
1. 推荐住宿区域
2. 住宿风格建议
3. 预算取舍建议
4. 与行程动线的关系

输出 4-6 行中文摘要。"""


def build_planner_prompt(
    prefs: UserPreferences,
    selected: list[AttractionCard],
    transport_summary: str,
    stay_summary: str,
) -> str:
    return f"""你是一位总旅行规划师。请根据用户偏好、交通建议和住宿建议，输出最终旅行 JSON。

目的地：{prefs.destination}
出发城市：{prefs.departure_city}
出发日期：{prefs.departure_date}
旅行天数：{prefs.days}天
总预算：¥{prefs.total_budget}
住宿期待：{prefs.accommodation_description or '未填写'}
体验期待：{prefs.experience_description}
用户已选内容：{_selected_text(selected)}

交通专员摘要：
{transport_summary}

住宿专员摘要：
{stay_summary}

请输出完整 JSON，结构必须是：
{{
  "days": [
    {{
      "day": 1,
      "date": "YYYY-MM-DD",
      "title": "今日主题",
      "activities": [
        {{
          "id": "act_1_1",
          "time": "09:00",
          "endTime": "11:00",
          "place": "地点名称",
          "description": "活动描述",
          "type": "attraction|food|transport|hotel|free",
          "estimatedCost": 40,
          "tips": "注意事项（可选）"
        }}
      ],
      "totalCost": 300
    }}
  ],
  "budget": {{
    "transport": 1200,
    "accommodation": 1800,
    "food": 1200,
    "attractions": 600,
    "other": 200,
    "total": 5000
  }},
  "tips": ["提示1", "提示2", "提示3"]
}}

不要输出解释性文字，只输出 JSON。"""


def build_adjustment_planner_prompt(
    current_plan: str,
    user_request: str,
    selected: list[AttractionCard],
) -> str:
    return f"""你是一位总旅行规划师。用户希望在保留大部分行程的前提下调整计划。

用户请求：
{user_request}

用户最初选中的内容：
{_selected_text(selected)}

当前行程 JSON：
{current_plan}

请只修改受影响的部分，返回完整 JSON，结构保持与原行程一致。不要输出解释性文字，只输出 JSON。"""
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/api
uv run pytest tests/test_graph_prompts.py -v
```

Expected: PASS — `5 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app
git add api/app/graph/prompts.py api/tests/test_graph_prompts.py
git commit -m "feat(api): add langgraph agent prompt builders"
```

---

### Task 3: Add Graph Input, State, and Progress Models

**Files:**
- Create: `api/app/graph/state.py`
- Create: `api/tests/test_graph_state.py`

- [ ] **Step 1: Write the failing model tests**

Create `api/tests/test_graph_state.py`:

```python
import pytest

from app.graph.state import PlanRunInput, ProgressEvent


def test_generate_mode_accepts_preferences_only():
    payload = PlanRunInput(
        preferences={
            "destination": "上海",
            "departureCity": "北京",
            "departureDate": "2026-05-10",
            "days": 3,
            "totalBudget": 5000,
            "accommodationDescription": "精品民宿",
            "experienceDescription": "本地小馆",
        }
    )
    assert payload.mode == "generate"
    state = payload.to_state()
    assert state["preferences"].destination == "上海"
    assert state["selected_attractions"] == []


def test_adjust_mode_accepts_current_plan_and_request():
    payload = PlanRunInput(
        currentPlan='{"days":[]}',
        adjustment="把第二天改轻松一点",
    )
    assert payload.mode == "adjust"
    state = payload.to_state()
    assert state["current_plan"] == '{"days":[]}'
    assert state["adjustment"] == "把第二天改轻松一点"


def test_invalid_payload_rejected():
    with pytest.raises(ValueError):
        PlanRunInput()


def test_progress_event_serializes_complete_payload():
    event = ProgressEvent(type="complete", raw='{"days":[]}')
    data = event.model_dump(by_alias=True, exclude_none=True)
    assert data["type"] == "complete"
    assert data["raw"] == '{"days":[]}'


def test_progress_event_serializes_status_payload():
    event = ProgressEvent(type="status", agent="transport", message="正在整理交通方案")
    data = event.model_dump(by_alias=True, exclude_none=True)
    assert data == {
        "type": "status",
        "agent": "transport",
        "message": "正在整理交通方案",
    }
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/api
uv run pytest tests/test_graph_state.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.graph.state'`.

- [ ] **Step 3: Implement the input/state/progress model module**

Create `api/app/graph/state.py`:

```python
"""Shared request, stream-event, and graph-state models."""

from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from app.models.attraction import AttractionCard
from app.models.preferences import UserPreferences

PlanMode = Literal["generate", "adjust"]
PlanAgent = Literal["transport", "stay", "planner"]


class PlanRunInput(BaseModel):
    """Validated request body shared by the route and the graph runner."""

    preferences: UserPreferences | None = None
    selected_attractions: list[AttractionCard] = Field(default_factory=list)
    current_plan: str | None = None
    adjustment: str | None = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @model_validator(mode="after")
    def validate_shape(self) -> "PlanRunInput":
        has_generate = self.preferences is not None
        has_adjust = bool(self.current_plan and self.adjustment)
        if has_generate == has_adjust:
            raise ValueError(
                "must provide either preferences or (currentPlan + adjustment)"
            )
        return self

    @property
    def mode(self) -> PlanMode:
        return "generate" if self.preferences is not None else "adjust"

    def to_state(self) -> "PlanState":
        return {
            "mode": self.mode,
            "preferences": self.preferences,
            "selected_attractions": self.selected_attractions,
            "current_plan": self.current_plan,
            "adjustment": self.adjustment,
        }


class ProgressEvent(BaseModel):
    """SSE payload emitted by the route."""

    type: Literal["status", "complete", "error"]
    agent: PlanAgent | None = None
    message: str | None = None
    raw: str | None = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PlanState(TypedDict, total=False):
    mode: PlanMode
    preferences: UserPreferences | None
    selected_attractions: list[AttractionCard]
    current_plan: str | None
    adjustment: str | None
    transport_summary: str
    stay_summary: str
    final_plan_raw: str
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/api
uv run pytest tests/test_graph_state.py -v
```

Expected: PASS — `5 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app
git add api/app/graph/state.py api/tests/test_graph_state.py
git commit -m "feat(api): add langgraph request and progress models"
```

---

### Task 4: Implement the LangGraph Workflow Runner

**Files:**
- Create: `api/app/graph/workflow.py`
- Create: `api/tests/test_graph_workflow.py`

- [ ] **Step 1: Write the failing workflow tests**

Create `api/tests/test_graph_workflow.py`:

```python
import pytest

from app.graph.state import PlanRunInput
from app.models.attraction import AttractionCard
from app.graph import workflow


PREFS = {
    "destination": "上海",
    "departureCity": "北京",
    "departureDate": "2026-05-10",
    "days": 3,
    "totalBudget": 5000,
    "accommodationDescription": "精品民宿",
    "experienceDescription": "本地小馆",
}

CARDS = [
    AttractionCard(
        id="c1",
        name="外滩",
        section="experience",
        description="夜景地标",
        estimatedCost="免费",
        imageUrl="",
        tags=["地标"],
    )
]


@pytest.mark.asyncio
async def test_generate_workflow_calls_transport_then_stay_then_planner(monkeypatch):
    calls = []

    async def fake_transport(state):
        calls.append("transport")
        return "交通摘要"

    async def fake_stay(state):
        calls.append("stay")
        return "住宿摘要"

    async def fake_planner(state):
        calls.append("planner")
        assert state["transport_summary"] == "交通摘要"
        assert state["stay_summary"] == "住宿摘要"
        return '{"days":[],"budget":{"transport":0,"accommodation":0,"food":0,"attractions":0,"other":0,"total":0},"tips":[]}'

    monkeypatch.setattr(workflow, "_call_transport_agent", fake_transport)
    monkeypatch.setattr(workflow, "_call_stay_agent", fake_stay)
    monkeypatch.setattr(workflow, "_call_planner_agent", fake_planner)

    payload = PlanRunInput(preferences=PREFS, selectedAttractions=CARDS)
    raw = await workflow.run_plan_graph_once(payload)

    assert calls == ["transport", "stay", "planner"]
    assert raw.startswith('{"days":[')


@pytest.mark.asyncio
async def test_adjustment_workflow_calls_only_planner(monkeypatch):
    calls = []

    async def fake_planner(state):
        calls.append("planner")
        assert state["current_plan"] == '{"days":[]}'
        assert state["adjustment"] == "改轻松一点"
        return '{"days":[],"budget":{"transport":1,"accommodation":1,"food":1,"attractions":1,"other":1,"total":5},"tips":["ok"]}'

    monkeypatch.setattr(workflow, "_call_planner_agent", fake_planner)

    payload = PlanRunInput(
        currentPlan='{"days":[]}',
        adjustment="改轻松一点",
        selectedAttractions=CARDS,
    )
    raw = await workflow.run_plan_graph_once(payload)

    assert calls == ["planner"]
    assert '"tips":["ok"]' in raw
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/api
uv run pytest tests/test_graph_workflow.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.graph.workflow'`.

- [ ] **Step 3: Implement the workflow module**

Create `api/app/graph/workflow.py`:

```python
"""LangGraph workflow runner for plan generation and adjustment."""

from collections.abc import AsyncIterator
from functools import lru_cache

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from app.graph.prompts import (
    build_adjustment_planner_prompt,
    build_planner_prompt,
    build_stay_prompt,
    build_transport_prompt,
)
from app.graph.state import PlanRunInput, PlanState, ProgressEvent
from app.services.gemini import generate_text


def _emit(event: ProgressEvent) -> None:
    try:
        writer = get_stream_writer()
    except Exception:
        return
    writer(event.model_dump(by_alias=True, exclude_none=True))


async def _call_transport_agent(state: PlanState) -> str:
    prefs = state["preferences"]
    if prefs is None:
        return ""
    return await generate_text(
        build_transport_prompt(prefs, state.get("selected_attractions", []))
    )


async def _call_stay_agent(state: PlanState) -> str:
    prefs = state["preferences"]
    if prefs is None:
        return ""
    return await generate_text(
        build_stay_prompt(prefs, state.get("selected_attractions", []))
    )


async def _call_planner_agent(state: PlanState) -> str:
    if state["mode"] == "adjust":
        return await generate_text(
            build_adjustment_planner_prompt(
                current_plan=state["current_plan"] or "",
                user_request=state["adjustment"] or "",
                selected=state.get("selected_attractions", []),
            )
        )

    prefs = state["preferences"]
    if prefs is None:
        raise ValueError("generate mode requires preferences")

    return await generate_text(
        build_planner_prompt(
            prefs,
            state.get("selected_attractions", []),
            transport_summary=state.get("transport_summary", ""),
            stay_summary=state.get("stay_summary", ""),
        )
    )


async def transport_node(state: PlanState) -> dict:
    _emit(
        ProgressEvent(
            type="status",
            agent="transport",
            message="正在整理交通方案",
        )
    )
    summary = await _call_transport_agent(state)
    return {"transport_summary": summary}


async def stay_node(state: PlanState) -> dict:
    _emit(
        ProgressEvent(
            type="status",
            agent="stay",
            message="正在整理住宿建议",
        )
    )
    summary = await _call_stay_agent(state)
    return {"stay_summary": summary}


async def planner_node(state: PlanState) -> dict:
    _emit(
        ProgressEvent(
            type="status",
            agent="planner",
            message="正在生成最终行程",
        )
    )
    raw = await _call_planner_agent(state)
    return {"final_plan_raw": raw}


@lru_cache(maxsize=1)
def _generate_graph():
    graph = StateGraph(PlanState)
    graph.add_node("transport", transport_node)
    graph.add_node("stay", stay_node)
    graph.add_node("planner", planner_node)
    graph.add_edge(START, "transport")
    graph.add_edge("transport", "stay")
    graph.add_edge("stay", "planner")
    graph.add_edge("planner", END)
    return graph.compile()


@lru_cache(maxsize=1)
def _adjust_graph():
    graph = StateGraph(PlanState)
    graph.add_node("planner", planner_node)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", END)
    return graph.compile()


def _pick_graph(mode: str):
    return _generate_graph() if mode == "generate" else _adjust_graph()


async def run_plan_graph_once(payload: PlanRunInput) -> str:
    graph = _pick_graph(payload.mode)
    result = await graph.ainvoke(payload.to_state())
    final_raw = result.get("final_plan_raw", "")
    if not final_raw:
        raise ValueError("graph finished without final_plan_raw")
    return final_raw


async def run_plan_graph_stream(
    payload: PlanRunInput,
) -> AsyncIterator[ProgressEvent]:
    graph = _pick_graph(payload.mode)
    final_raw = ""

    async for chunk in graph.astream(
        payload.to_state(),
        stream_mode=["updates", "custom"],
        version="v2",
    ):
        if chunk["type"] == "custom":
            yield ProgressEvent.model_validate(chunk["data"])
            continue

        if chunk["type"] == "updates":
            for update in chunk["data"].values():
                if "final_plan_raw" in update:
                    final_raw = update["final_plan_raw"]

    if not final_raw:
        raise ValueError("graph stream finished without final_plan_raw")

    yield ProgressEvent(type="complete", raw=final_raw)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/api
uv run pytest tests/test_graph_workflow.py -v
```

Expected: PASS — `2 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app
git add api/app/graph/workflow.py api/tests/test_graph_workflow.py
git commit -m "feat(api): add langgraph workflow runner for planner"
```

---

### Task 5: Stream Plan Progress from the FastAPI Route

**Files:**
- Modify: `api/app/routes/plan.py`
- Create: `api/tests/test_plan_route_sse.py`

- [ ] **Step 1: Write the failing route tests**

Create `api/tests/test_plan_route_sse.py`:

```python
import pytest
import httpx
from httpx_sse import aconnect_sse

from app.graph.state import ProgressEvent
from main import app


@pytest.mark.asyncio
async def test_plain_plan_route_returns_text(monkeypatch):
    async def fake_run_once(payload):
        return '{"days":[],"budget":{"transport":0,"accommodation":0,"food":0,"attractions":0,"other":0,"total":0},"tips":[]}'

    monkeypatch.setattr("app.routes.plan.run_plan_graph_once", fake_run_once)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/api/plan/generate",
            json={
                "preferences": {
                    "destination": "上海",
                    "departureCity": "北京",
                    "departureDate": "2026-05-10",
                    "days": 3,
                    "totalBudget": 5000,
                    "accommodationDescription": "精品民宿",
                    "experienceDescription": "本地小馆",
                }
            },
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert resp.text.startswith('{"days":[')


@pytest.mark.asyncio
async def test_sse_plan_route_emits_status_then_complete(monkeypatch):
    async def fake_stream(payload):
        yield ProgressEvent(type="status", agent="transport", message="正在整理交通方案")
        yield ProgressEvent(type="complete", raw='{"days":[],"budget":{"transport":0,"accommodation":0,"food":0,"attractions":0,"other":0,"total":0},"tips":[]}')

    monkeypatch.setattr("app.routes.plan.run_plan_graph_stream", fake_stream)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        async with aconnect_sse(
            client,
            "POST",
            "http://testserver/api/plan/generate",
            json={
                "preferences": {
                    "destination": "上海",
                    "departureCity": "北京",
                    "departureDate": "2026-05-10",
                    "days": 3,
                    "totalBudget": 5000,
                    "accommodationDescription": "精品民宿",
                    "experienceDescription": "本地小馆",
                }
            },
            headers={"Accept": "text/event-stream"},
        ) as event_source:
            events = [event async for event in event_source.aiter_sse()]

    assert [event.event for event in events] == ["status", "complete"]
    assert events[0].json()["message"] == "正在整理交通方案"
    assert events[1].json()["raw"].startswith('{"days":[')
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/api
uv run pytest tests/test_plan_route_sse.py -v
```

Expected: FAIL because the current route always returns plain text and does not emit SSE events.

- [ ] **Step 3: Replace the route with a plain-text + SSE adapter**

Update `api/app/routes/plan.py`:

```python
"""POST /api/plan/generate endpoint with plain-text and SSE modes."""

import json
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.graph.state import PlanRunInput, ProgressEvent
from app.graph.workflow import run_plan_graph_once, run_plan_graph_stream

router = APIRouter()


def _encode_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _wants_stream(request: Request) -> bool:
    return "text/event-stream" in request.headers.get("accept", "")


@router.post("/api/plan/generate")
async def generate_plan(
    request: Request,
    body: Annotated[dict, Body(...)],
):
    try:
        payload = PlanRunInput.model_validate(body)
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    if _wants_stream(request):
        async def event_source():
            try:
                async for event in run_plan_graph_stream(payload):
                    data = event.model_dump(by_alias=True, exclude_none=True)
                    yield _encode_sse(event.type, data)
            except Exception as err:
                error = ProgressEvent(type="error", message=str(err))
                yield _encode_sse(
                    "error",
                    error.model_dump(by_alias=True, exclude_none=True),
                )

        return StreamingResponse(event_source(), media_type="text/event-stream")

    try:
        raw = await run_plan_graph_once(payload)
    except Exception as err:
        raise HTTPException(status_code=502, detail=f"LLM failed: {err}") from err

    return PlainTextResponse(raw)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/api
uv run pytest tests/test_plan_route_sse.py -v
```

Expected: PASS — `2 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app
git add api/app/routes/plan.py api/tests/test_plan_route_sse.py
git commit -m "feat(api): stream langgraph planner progress over sse"
```

---

### Task 6: Add Frontend Stream Types, Parser, and Streaming Client

**Files:**
- Modify: `web/src/lib/types.ts`
- Create: `web/src/lib/planStream.ts`
- Modify: `web/src/lib/apiClient.ts`
- Create: `web/src/__tests__/lib/planStream.test.ts`

- [ ] **Step 1: Write the failing stream-parser tests**

Create `web/src/__tests__/lib/planStream.test.ts`:

```typescript
import { parsePlanStreamEvent, splitEventBlocks } from "@/lib/planStream"

describe("splitEventBlocks", () => {
  it("returns complete blocks and keeps the trailing partial chunk", () => {
    const result = splitEventBlocks(
      "event: status\ndata: {\"type\":\"status\",\"message\":\"one\"}\n\npartial"
    )
    expect(result.blocks).toHaveLength(1)
    expect(result.rest).toBe("partial")
  })
})

describe("parsePlanStreamEvent", () => {
  it("parses a status event", () => {
    const event = parsePlanStreamEvent(
      "event: status\ndata: {\"type\":\"status\",\"agent\":\"transport\",\"message\":\"正在整理交通方案\"}"
    )
    expect(event).toEqual({
      type: "status",
      agent: "transport",
      message: "正在整理交通方案",
    })
  })

  it("parses a complete event", () => {
    const event = parsePlanStreamEvent(
      "event: complete\ndata: {\"type\":\"complete\",\"raw\":\"{\\\"days\\\":[]}\"}"
    )
    expect(event).toEqual({
      type: "complete",
      raw: "{\"days\":[]}",
    })
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/web
npm test -- --runInBand planStream.test.ts
```

Expected: FAIL with `Cannot find module '@/lib/planStream'`.

- [ ] **Step 3: Add the shared stream types and parser**

Update `web/src/lib/types.ts` by appending:

```typescript
export type PlanAgent = "transport" | "stay" | "planner"

export type PlanProgressEvent =
  | {
      type: "status"
      agent: PlanAgent
      message: string
    }
  | {
      type: "complete"
      raw: string
    }
  | {
      type: "error"
      message: string
    }
```

Create `web/src/lib/planStream.ts`:

```typescript
import { PlanProgressEvent } from "./types"

export function splitEventBlocks(buffer: string): {
  blocks: string[]
  rest: string
} {
  const parts = buffer.split("\n\n")
  return {
    blocks: parts.slice(0, -1).filter(Boolean),
    rest: parts.at(-1) ?? "",
  }
}

export function parsePlanStreamEvent(block: string): PlanProgressEvent {
  const lines = block
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)

  const eventName =
    lines.find((line) => line.startsWith("event:"))?.replace("event:", "").trim() ??
    "message"

  const dataText = lines
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.replace("data:", "").trim())
    .join("\n")

  const payload = JSON.parse(dataText) as PlanProgressEvent

  if (
    eventName !== "status" &&
    eventName !== "complete" &&
    eventName !== "error"
  ) {
    throw new Error(`Unknown stream event: ${eventName}`)
  }

  return payload
}
```

Update `web/src/lib/apiClient.ts`:

```typescript
"use client"

import { parsePlanStreamEvent, splitEventBlocks } from "./planStream"
import { PlanProgressEvent } from "./types"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? ""

if (!API_URL && typeof window !== "undefined") {
  console.warn("NEXT_PUBLIC_API_URL not set — falling back to same-origin Next.js routes")
}

function url(path: string): string {
  return API_URL ? `${API_URL}${path}` : path
}

export async function discoverDestination(destination: string): Promise<unknown> {
  const res = await fetch(
    url(`/api/discover?destination=${encodeURIComponent(destination)}`)
  )
  if (!res.ok) throw new Error(`Discover failed: ${res.status}`)
  return res.json()
}

export async function generatePlan(body: object): Promise<string> {
  const res = await fetch(url("/api/plan/generate"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Generate failed: ${res.status}`)
  return res.text()
}

export async function generatePlanStream(
  body: object,
  onEvent: (event: PlanProgressEvent) => void
): Promise<string> {
  const res = await fetch(url("/api/plan/generate"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "text/event-stream",
    },
    body: JSON.stringify(body),
  })

  if (!res.ok || !res.body) {
    throw new Error(`Generate stream failed: ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let finalRaw = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const { blocks, rest } = splitEventBlocks(buffer)
    buffer = rest

    for (const block of blocks) {
      const event = parsePlanStreamEvent(block)
      onEvent(event)
      if (event.type === "complete") finalRaw = event.raw
      if (event.type === "error") throw new Error(event.message)
    }
  }

  if (!finalRaw) {
    throw new Error("Plan stream finished without a complete event")
  }

  return finalRaw
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/web
npm test -- --runInBand planStream.test.ts
```

Expected: PASS — `3 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app
git add web/src/lib/types.ts web/src/lib/planStream.ts web/src/lib/apiClient.ts web/src/__tests__/lib/planStream.test.ts
git commit -m "feat(web): add sse plan stream parser and client"
```

---

### Task 7: Show Streaming Status During Initial Plan Generation

**Files:**
- Modify: `web/src/components/discover/SelectionBar.tsx`
- Modify: `web/src/app/discover/[destination]/page.tsx`

- [ ] **Step 1: Add a status prop to the selection bar**

Update the prop interface and render block in `web/src/components/discover/SelectionBar.tsx`:

```typescript
interface SelectionBarProps {
  selected: AttractionCard[]
  destination: string
  budget: number
  onGenerate: (prefs: UserPreferences) => void
  generating: boolean
  statusText?: string
}

export function SelectionBar({
  selected,
  destination,
  budget,
  onGenerate,
  generating,
  statusText,
}: SelectionBarProps) {
```

Inside the expanded form, add the status line just above the submit button:

```typescript
          {generating && statusText ? (
            <p className="text-sm text-blue-600 bg-blue-50 border border-blue-100 rounded-lg px-3 py-2">
              {statusText}
            </p>
          ) : null}

          <Button type="submit" disabled={generating} className="w-full py-3 text-base">
            {generating ? "AI 正在规划中…" : "生成我的行程 →"}
          </Button>
```

- [ ] **Step 2: Switch discover-page generation to the streamed client**

Update the imports and state in `web/src/app/discover/[destination]/page.tsx`:

```typescript
import { discoverDestination, generatePlanStream } from "@/lib/apiClient"

const [generating, setGenerating] = useState(false)
const [generationStatus, setGenerationStatus] = useState("")
```

Replace `handleGenerate` with:

```typescript
  async function handleGenerate(prefs: UserPreferences) {
    setGenerating(true)
    setGenerationStatus("正在启动多 agent 规划流程…")

    try {
      const raw = await generatePlanStream(
        { preferences: prefs, selectedAttractions: selectedCards },
        (event) => {
          if (event.type === "status") {
            setGenerationStatus(event.message)
          }
        }
      )

      const jsonMatch = raw.match(/\{[\s\S]*\}/)
      if (!jsonMatch) throw new Error("无法解析行程数据")

      const planData = JSON.parse(jsonMatch[0])
      const plan: TravelPlan = {
        id: nanoid(),
        preferences: prefs,
        selectedAttractions: selectedCards,
        days: planData.days,
        budget: planData.budget,
        tips: planData.tips,
        createdAt: new Date().toISOString(),
      }

      savePlan(plan)
      router.push(`/plan/${plan.id}`)
    } catch (err) {
      alert(err instanceof Error ? err.message : "发生错误，请重试")
      setGenerating(false)
      setGenerationStatus("")
    }
  }
```

Update the component usage at the bottom:

```typescript
      <SelectionBar
        selected={selectedCards}
        destination={destination}
        budget={budget}
        onGenerate={handleGenerate}
        generating={generating}
        statusText={generationStatus}
      />
```

- [ ] **Step 3: Run the focused frontend tests**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/web
npm test -- --runInBand
```

Expected: PASS — all existing Jest tests still pass.

- [ ] **Step 4: Manually verify the generation status UI**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/api
uv run uvicorn main:app --reload --port 8000
```

In a second terminal:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/web
npm run dev
```

Expected in the browser:

```text
1. 首页输入目的地和预算
2. discover 页面勾选内容并点击“生成我的行程”
3. 底部看到状态依次变化，例如“正在整理交通方案” → “正在整理住宿建议” → “正在生成最终行程”
```

- [ ] **Step 5: Commit**

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app
git add web/src/components/discover/SelectionBar.tsx web/src/app/discover/[destination]/page.tsx
git commit -m "feat(web): show streamed status during initial plan generation"
```

---

### Task 8: Show Streaming Status During Plan Adjustment

**Files:**
- Modify: `web/src/hooks/usePlan.ts`
- Modify: `web/src/components/plan/AIChatPanel.tsx`
- Modify: `web/src/app/plan/[id]/page.tsx`

- [ ] **Step 1: Add a status prop to the AI chat panel**

Update `web/src/components/plan/AIChatPanel.tsx`:

```typescript
interface AIChatPanelProps {
  messages: ChatMessage[]
  isGenerating: boolean
  statusText?: string | null
  onSend: (message: string) => void
}

export function AIChatPanel({
  messages,
  isGenerating,
  statusText,
  onSend,
}: AIChatPanelProps) {
```

Render the live status above the composer:

```typescript
      {isGenerating && statusText ? (
        <div className="px-4 py-2 border-t border-gray-100 bg-blue-50 text-blue-700 text-xs">
          {statusText}
        </div>
      ) : null}

      <div className="p-4 border-t border-gray-100 bg-white">
```

- [ ] **Step 2: Switch the hook to the streamed client**

Update `web/src/hooks/usePlan.ts`:

```typescript
import { generatePlanStream } from "@/lib/apiClient"
```

Add state near the top:

```typescript
  const [statusText, setStatusText] = useState<string | null>(null)
```

Replace the body of `sendAdjustment` with:

```typescript
  const sendAdjustment = useCallback(
    async (userMessage: string) => {
      setMessages((prev) => [
        ...prev,
        { role: "user", content: userMessage, timestamp: new Date().toISOString() },
      ])
      setIsGenerating(true)
      setStatusText("正在启动多 agent 调整流程…")

      try {
        const raw = await generatePlanStream(
          {
            currentPlan: JSON.stringify(plan.days),
            adjustment: userMessage,
            selectedAttractions: plan.selectedAttractions,
          },
          (event) => {
            if (event.type === "status") {
              setStatusText(event.message)
            }
          }
        )

        const jsonMatch = raw.match(/\{[\s\S]*\}/)
        if (!jsonMatch) throw new Error("无法解析调整结果")

        const updated = JSON.parse(jsonMatch[0])
        const newPlan: TravelPlan = {
          ...plan,
          days: updated.days ?? plan.days,
          budget: updated.budget ?? plan.budget,
          tips: updated.tips ?? plan.tips,
        }

        setPlan(newPlan)
        savePlan(newPlan)
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "已按你的要求更新行程，右侧已同步刷新。还有什么需要调整的吗？",
            timestamp: new Date().toISOString(),
          },
        ])
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "调整时出现问题，请再试一次。",
            timestamp: new Date().toISOString(),
          },
        ])
      } finally {
        setIsGenerating(false)
        setStatusText(null)
      }
    },
    [plan]
  )
```

Update the return line:

```typescript
  return { plan, messages, isGenerating, statusText, sendAdjustment }
```

Update `web/src/app/plan/[id]/page.tsx`:

```typescript
  const { plan, messages, isGenerating, statusText, sendAdjustment } = usePlan(initialPlan)
```

```typescript
        <AIChatPanel
          messages={messages}
          isGenerating={isGenerating}
          statusText={statusText}
          onSend={sendAdjustment}
        />
```

- [ ] **Step 3: Run the frontend tests**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/web
npm test -- --runInBand
```

Expected: PASS — all Jest tests still pass.

- [ ] **Step 4: Manually verify chat adjustment status**

With both dev servers still running, open a generated plan and send:

```text
把第二天下午改轻松一点
```

Expected in the browser:

```text
1. 输入框上方出现状态，例如“正在生成最终行程”
2. 聊天区保持 loading dots
3. 右侧 itinerary 更新
4. localStorage 中对应 plan id 的 JSON 被覆盖为新结果
```

- [ ] **Step 5: Commit**

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app
git add web/src/hooks/usePlan.ts web/src/components/plan/AIChatPanel.tsx web/src/app/plan/[id]/page.tsx
git commit -m "feat(web): show streamed status during plan adjustment"
```

---

### Task 9: Update Docs and Run Full Verification

**Files:**
- Modify: `api/README.md`

- [ ] **Step 1: Update the backend README**

Update `api/README.md`:

````markdown
# Travel Planner API (Python Backend)

FastAPI backend for the travel planner. Mirrors the Next.js `/api/*` routes
during the multi-agent migration.

## Setup

Requires Python 3.12 and [uv](https://github.com/astral-sh/uv).

```bash
cd api
cp .env.example .env
# Edit .env — fill in GEMINI_API_KEY and TAVILY_API_KEY
uv sync
```

## Run

```bash
uv run uvicorn main:app --reload --port 8000
```

Server listens on http://localhost:8000. Health check: http://localhost:8000/health.

## Endpoints

- `GET /health` — liveness check
- `GET /api/discover?destination=...` — three-section attraction cards
- `POST /api/plan/generate` — plain text response for legacy callers
- `POST /api/plan/generate` with `Accept: text/event-stream` — LangGraph progress stream followed by a `complete` event

## LangGraph workflow

Initial generation runs:
1. `transport`
2. `stay`
3. `planner`

Adjustment runs:
1. `planner`

## Tests

```bash
uv run pytest -v
```
````

- [ ] **Step 2: Run the backend test suite**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/api
uv run pytest -v
```

Expected: PASS — existing 22 tests plus the new graph/route tests all pass.

- [ ] **Step 3: Run the frontend test suite**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/web
npm test -- --runInBand
```

Expected: PASS — existing 23 tests plus the new stream parser tests all pass.

- [ ] **Step 4: Run the production build**

Run:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/web
npm run build
```

Expected: PASS with the same routes still present:

```text
Route (app)
┌ ○ /
├ ○ /_not-found
├ ƒ /api/discover
├ ƒ /api/plan/generate
├ ƒ /discover/[destination]
└ ƒ /plan/[id]
```

- [ ] **Step 5: Smoke-test the SSE contract from the terminal**

Run the API in one terminal:

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/api
uv run uvicorn main:app --reload --port 8000
```

Run the SSE request in a second terminal:

```bash
curl -N -X POST http://localhost:8000/api/plan/generate \
  -H "Accept: text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{
    "preferences": {
      "destination": "上海",
      "departureCity": "北京",
      "departureDate": "2026-05-10",
      "days": 3,
      "totalBudget": 5000,
      "accommodationDescription": "精品民宿",
      "experienceDescription": "本地小馆"
    },
    "selectedAttractions": []
  }'
```

Expected: the response contains status events and ends with a complete event, for example:

```text
event: status
data: {"type":"status","agent":"transport","message":"正在整理交通方案"}

event: status
data: {"type":"status","agent":"stay","message":"正在整理住宿建议"}

event: status
data: {"type":"status","agent":"planner","message":"正在生成最终行程"}

event: complete
data: {"type":"complete","raw":"{\"days\":[..."}
```

- [ ] **Step 6: Commit**

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app
git add api/README.md
git commit -m "docs(api): document langgraph workflow and sse mode"
```

---

## Self-Review

### 1. Spec coverage

- Replace one-shot plan generation with LangGraph: covered by Tasks 2-5.
- Use Transport / Stay / Planner agents: covered by Tasks 2 and 4.
- Keep frontend contract stable: covered by Tasks 3, 4, 5, and 6.
- Add progress streaming to the user flow: covered by Tasks 5, 6, 7, and 8.
- Keep legacy plain-text mode available: covered by Task 5.
- Keep migration incremental instead of rewriting the frontend: covered by Tasks 6-8.

No uncovered requirement remains from the Plan 2 direction established in the existing Plan 1 document and prior handoff.

### 2. Placeholder scan

- No `TBD`, `TODO`, or deferred "implement later" phrasing remains.
- All new files have concrete contents.
- All tests include executable code.
- All commands include expected outcomes.

### 3. Type consistency

- Python stream payload uses `ProgressEvent.type/agent/message/raw`.
- Frontend `PlanProgressEvent` mirrors that exact shape.
- Request body still uses camelCase over the wire (`selectedAttractions`, `currentPlan`), matching `PlanRunInput` alias handling.
- Final plan payload remains the same `TravelPlan` JSON shape already consumed by the frontend.

## Execution Handoff

Plan complete and saved to `Projects/travel-planner/docs/superpowers/plans/2026-05-06-langgraph-multi-agent-planner.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
