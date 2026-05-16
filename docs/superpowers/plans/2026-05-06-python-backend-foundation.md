> **STATUS: COMPLETED (2026-05-09)**
> 本计划作为 Python 后端基础已落地;原始提交范围为 `1ab156f..6433d19`,迁移到当前仓库后的等价范围为 `a17094e..ba2a015`。
> 后续后端演进见:`docs/superpowers/plans/2026-05-09-langgraph-single-city-mvp.md`

# Python Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the Next.js API routes (`/api/discover` and `/api/plan/generate`) to a standalone Python FastAPI backend, while keeping the Next.js frontend functionally identical. This is Plan 1 of 3 — it delivers no new features, but lays the foundation for LangGraph multi-agent work in Plan 2.

**Architecture:** Two-service architecture. Frontend stays in `web/` (Next.js, only UI). New `api/` directory holds FastAPI app with Pydantic models mirroring TypeScript types, async services for Tavily search and Gemini LLM, and routes that mirror the existing Next.js API surface. Frontend calls Python backend via `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`). Old Next.js API routes stay in place as fallback during migration; they'll be removed in Plan 3.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Pydantic 2, `google-generativeai`, `tavily-python`, `pytest`, `httpx` (for testing), `python-dotenv`. Package manager: `uv` (modern Rust-based, replaces pip+poetry).

---

## File Map

```
travel-planner/
├── web/                                        (existing Next.js, mostly unchanged)
│   ├── .env.local                              MODIFY — add NEXT_PUBLIC_API_URL
│   └── src/
│       ├── lib/
│       │   └── apiClient.ts                    CREATE — centralized API wrapper
│       ├── app/discover/[destination]/
│       │   └── page.tsx                        MODIFY — use apiClient
│       └── hooks/
│           └── usePlan.ts                      MODIFY — use apiClient
│
└── api/                                        CREATE — new Python service
    ├── pyproject.toml                          CREATE — uv project file
    ├── .env.example                            CREATE — env template
    ├── .gitignore                              CREATE
    ├── README.md                               CREATE — quickstart for Python service
    ├── main.py                                 CREATE — FastAPI entry point
    ├── app/
    │   ├── __init__.py                         CREATE
    │   ├── config.py                           CREATE — env vars + settings
    │   ├── models/
    │   │   ├── __init__.py                     CREATE
    │   │   ├── attraction.py                   CREATE — AttractionCard, DiscoverSections
    │   │   ├── plan.py                         CREATE — TravelPlan, DayPlan, Activity
    │   │   └── preferences.py                  CREATE — UserPreferences
    │   ├── prompts/
    │   │   ├── __init__.py                     CREATE
    │   │   ├── discover.py                     CREATE — buildDiscoverPrompt port
    │   │   └── plan.py                         CREATE — plan + adjustment prompts
    │   ├── services/
    │   │   ├── __init__.py                     CREATE
    │   │   ├── tavily.py                       CREATE — async search client
    │   │   └── gemini.py                       CREATE — async LLM client
    │   └── routes/
    │       ├── __init__.py                     CREATE
    │       ├── discover.py                     CREATE — POST /api/discover
    │       └── plan.py                         CREATE — POST /api/plan/generate
    └── tests/
        ├── __init__.py                         CREATE
        ├── test_prompts_discover.py            CREATE
        ├── test_prompts_plan.py                CREATE
        ├── test_tavily_query_builder.py        CREATE
        └── test_models_serialization.py        CREATE
```

**Working directory throughout this plan:** `/Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app/`
**Git commits run from:** the worktree root above (where `web/` lives).

---

## Task 1: Install uv and Python 3.12

**Files:** none (system setup)

- [ ] **Step 1: Install uv**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

If already installed: `uv --version` should print `uv 0.5.0` or higher.

- [ ] **Step 2: Verify Python 3.12 available**

```bash
uv python install 3.12
uv python list | grep "3.12"
```

Expected: lists at least one `cpython-3.12.x` entry.

- [ ] **Step 3: No commit (system change only).**

---

## Task 2: Create `api/` directory and Python project scaffold

**Files:**
- Create: `api/pyproject.toml`
- Create: `api/.env.example`
- Create: `api/.gitignore`

- [ ] **Step 1: Create the api directory**

```bash
cd /Users/gabriel/Projects/travel-planner/.worktrees/feature/mvp-web-app
mkdir -p api/app/models api/app/prompts api/app/services api/app/routes api/tests
```

- [ ] **Step 2: Create `api/pyproject.toml`**

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
    "google-generativeai>=0.8.0",
    "tavily-python>=0.5.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.27.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-httpx>=0.30.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.uv]
package = false
```

- [ ] **Step 3: Create `api/.env.example`**

```
GEMINI_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
GEMINI_MODEL=gemini-1.5-flash
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://127.50.100.1:3000
```

- [ ] **Step 4: Create `api/.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
.pytest_cache/
.ruff_cache/
*.egg-info/
```

- [ ] **Step 5: Install dependencies and verify Python project works**

```bash
cd api
uv sync
```

Expected: creates `.venv/`, prints "Resolved N packages", no errors.

- [ ] **Step 6: Create real `.env` file from template**

```bash
cp .env.example .env
```

Then open `api/.env` and replace:
- `GEMINI_API_KEY=...` with the value from `web/.env.local`
- `TAVILY_API_KEY=...` with the value from `web/.env.local`

- [ ] **Step 7: Commit**

```bash
cd ..
git add api/pyproject.toml api/.env.example api/.gitignore
git commit -m "feat(api): scaffold Python FastAPI project with uv"
```

(Note: `api/.env` and `api/.venv/` are gitignored — they should not appear in `git status`.)

---

## Task 3: Configuration loader

**Files:**
- Create: `api/app/__init__.py`
- Create: `api/app/config.py`

- [ ] **Step 1: Create `api/app/__init__.py`** (empty file)

```bash
touch api/app/__init__.py
```

- [ ] **Step 2: Create `api/app/config.py`**

```python
"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings sourced from `.env` file and environment variables."""

    gemini_api_key: str
    tavily_api_key: str
    gemini_model: str = "gemini-1.5-flash"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def cors_origin_list(self) -> list[str]:
        """Split comma-separated CORS_ORIGINS into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor — reads `.env` once per process."""
    return Settings()
```

- [ ] **Step 3: Verify config loads**

```bash
cd api
uv run python -c "from app.config import get_settings; s = get_settings(); print('CORS:', s.cors_origin_list); print('Model:', s.gemini_model); print('Has Gemini key:', bool(s.gemini_api_key)); print('Has Tavily key:', bool(s.tavily_api_key))"
```

Expected:
```
CORS: ['http://localhost:3000', 'http://127.0.0.1:3000', 'http://127.50.100.1:3000']
Model: gemini-1.5-flash
Has Gemini key: True
Has Tavily key: True
```

- [ ] **Step 4: Commit**

```bash
cd ..
git add api/app/__init__.py api/app/config.py
git commit -m "feat(api): add Settings config loader with cached accessor"
```

---

## Task 4: Pydantic Models

**Files:**
- Create: `api/app/models/__init__.py`
- Create: `api/app/models/preferences.py`
- Create: `api/app/models/attraction.py`
- Create: `api/app/models/plan.py`
- Create: `api/tests/__init__.py`
- Create: `api/tests/test_models_serialization.py`

- [ ] **Step 1: Create `api/tests/__init__.py`** (empty)

```bash
touch api/tests/__init__.py
```

- [ ] **Step 2: Write failing tests for model serialization**

Create `api/tests/test_models_serialization.py`:

```python
"""Models serialize to camelCase JSON to match the TypeScript frontend contract."""

from app.models.preferences import UserPreferences
from app.models.attraction import AttractionCard, DiscoverSections
from app.models.plan import TravelPlan, DayPlan, Activity, BudgetBreakdown


def test_user_preferences_uses_camel_case_keys():
    prefs = UserPreferences(
        destination="上海",
        departureCity="北京",
        departureDate="2026-06-01",
        days=3,
        totalBudget=5000,
        accommodationDescription="精品民宿",
        experienceDescription="本地小馆",
    )
    data = prefs.model_dump(by_alias=True)
    assert data["departureCity"] == "北京"
    assert data["departureDate"] == "2026-06-01"
    assert data["totalBudget"] == 5000
    assert data["accommodationDescription"] == "精品民宿"


def test_attraction_card_section_literal():
    card = AttractionCard(
        id="c1",
        name="外滩",
        section="experience",
        description="滨江夜景",
        estimatedCost="免费",
        imageUrl="",
        tags=["地标"],
    )
    assert card.section == "experience"
    data = card.model_dump(by_alias=True)
    assert data["estimatedCost"] == "免费"
    assert data["imageUrl"] == ""


def test_discover_sections_three_lists():
    sections = DiscoverSections(experience=[], transport=[], food=[])
    data = sections.model_dump(by_alias=True)
    assert "experience" in data
    assert "transport" in data
    assert "food" in data


def test_travel_plan_includes_selected_attractions():
    plan = TravelPlan(
        id="p1",
        preferences=UserPreferences(
            destination="上海",
            departureCity="北京",
            departureDate="2026-06-01",
            days=2,
            totalBudget=3000,
            accommodationDescription="",
            experienceDescription="",
        ),
        selectedAttractions=[],
        days=[
            DayPlan(
                day=1,
                date="2026-06-01",
                title="抵达",
                activities=[
                    Activity(
                        id="a1",
                        time="10:00",
                        place="酒店",
                        description="入住",
                        type="hotel",
                    )
                ],
                totalCost=200,
            )
        ],
        budget=BudgetBreakdown(
            transport=500, accommodation=1000, food=500, attractions=300, other=100, total=2400
        ),
        tips=["带身份证"],
        createdAt="2026-05-06T10:00:00Z",
    )
    data = plan.model_dump(by_alias=True)
    assert "selectedAttractions" in data
    assert data["budget"]["total"] == 2400


def test_activity_optional_fields_omitted_when_none():
    a = Activity(id="x", time="09:00", place="P", description="D", type="free")
    data = a.model_dump(by_alias=True, exclude_none=True)
    assert "endTime" not in data
    assert "estimatedCost" not in data
    assert "tips" not in data
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd api
uv run pytest tests/test_models_serialization.py -v 2>&1 | tail -10
```

Expected: ImportError — `No module named 'app.models.preferences'`

- [ ] **Step 4: Create `api/app/models/__init__.py`** (empty)

```bash
touch app/models/__init__.py
```

- [ ] **Step 5: Create `api/app/models/preferences.py`**

```python
"""User preferences model — mirror of TypeScript UserPreferences."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class UserPreferences(BaseModel):
    """Trip preferences gathered from the home form + selection bar."""

    destination: str
    departure_city: str
    departure_date: str
    days: int
    total_budget: int
    accommodation_description: str
    experience_description: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
```

- [ ] **Step 6: Create `api/app/models/attraction.py`**

```python
"""Attraction card models — mirror of TypeScript AttractionCard, DiscoverSections."""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

CardSection = Literal["experience", "transport", "food"]


class AttractionCard(BaseModel):
    """Single discoverable item shown in the gallery."""

    id: str
    name: str
    section: CardSection
    description: str
    estimated_cost: str
    image_url: str
    tags: list[str]

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DiscoverSections(BaseModel):
    """Three-section response shape returned by /api/discover."""

    experience: list[AttractionCard]
    transport: list[AttractionCard]
    food: list[AttractionCard]
```

- [ ] **Step 7: Create `api/app/models/plan.py`**

```python
"""Travel plan models — mirror of TypeScript TravelPlan and friends."""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.models.attraction import AttractionCard
from app.models.preferences import UserPreferences

ActivityType = Literal["attraction", "food", "transport", "hotel", "free"]


class Activity(BaseModel):
    id: str
    time: str
    end_time: str | None = None
    place: str
    description: str
    type: ActivityType
    estimated_cost: int | None = None
    tips: str | None = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DayPlan(BaseModel):
    day: int
    date: str
    title: str
    activities: list[Activity]
    total_cost: int

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class BudgetBreakdown(BaseModel):
    transport: int
    accommodation: int
    food: int
    attractions: int
    other: int
    total: int


class TravelPlan(BaseModel):
    id: str
    preferences: UserPreferences
    selected_attractions: list[AttractionCard]
    days: list[DayPlan]
    budget: BudgetBreakdown
    tips: list[str]
    created_at: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
cd api
uv run pytest tests/test_models_serialization.py -v 2>&1 | tail -15
```

Expected: PASS — 5 tests passing

- [ ] **Step 9: Commit**

```bash
cd ..
git add api/app/models/ api/tests/__init__.py api/tests/test_models_serialization.py
git commit -m "feat(api): add Pydantic models with camelCase JSON aliases mirroring TS types"
```

---

## Task 5: Discover Prompt Builder

**Files:**
- Create: `api/app/prompts/__init__.py`
- Create: `api/app/prompts/discover.py`
- Create: `api/tests/test_prompts_discover.py`

- [ ] **Step 1: Write failing tests**

Create `api/tests/test_prompts_discover.py`:

```python
from app.prompts.discover import build_discover_prompt, SearchItem


def _item(title: str, snippet: str = "snippet") -> SearchItem:
    return SearchItem(title=title, snippet=snippet, link="https://x.com", image_url="")


def test_includes_destination():
    prompt = build_discover_prompt("上海", [], [], [])
    assert "上海" in prompt


def test_includes_experience_search_results():
    prompt = build_discover_prompt("上海", [_item("外滩夜景")], [], [])
    assert "外滩夜景" in prompt


def test_includes_transport_search_results():
    prompt = build_discover_prompt("上海", [], [_item("地铁攻略")], [])
    assert "地铁攻略" in prompt


def test_includes_food_search_results():
    prompt = build_discover_prompt("上海", [], [], [_item("小笼包推荐")])
    assert "小笼包推荐" in prompt


def test_requests_three_section_json():
    prompt = build_discover_prompt("上海", [], [], [])
    assert "experience" in prompt
    assert "transport" in prompt
    assert "food" in prompt
    assert "JSON" in prompt
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd api
uv run pytest tests/test_prompts_discover.py -v 2>&1 | tail -10
```

Expected: ImportError — `No module named 'app.prompts.discover'`

- [ ] **Step 3: Create `api/app/prompts/__init__.py`** (empty)

```bash
touch app/prompts/__init__.py
```

- [ ] **Step 4: Create `api/app/prompts/discover.py`**

```python
"""Prompt builder for the /api/discover endpoint.

This is a Python port of `web/src/lib/claude.ts::buildDiscoverPrompt`.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class SearchItem(BaseModel):
    """One result from Tavily search, normalized for prompt formatting."""

    title: str
    snippet: str
    link: str
    image_url: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


def _format_items(items: list[SearchItem]) -> str:
    if not items:
        return "（无搜索结果，请根据你的知识补充）"
    return "\n".join(
        f"[{i + 1}] {item.title}\n    {item.snippet}" for i, item in enumerate(items)
    )


def build_discover_prompt(
    destination: str,
    experience_items: list[SearchItem],
    transport_items: list[SearchItem],
    food_items: list[SearchItem],
) -> str:
    """Build the prompt that turns three sets of search results into card JSON."""
    return f"""你是一位旅游信息整理专家。根据以下三组关于「{destination}」的搜索结果，分别整理出体验景点、交通方式、美食推荐的信息卡片。

===== 体验/景点 搜索结果 =====
{_format_items(experience_items)}

===== 交通 搜索结果 =====
{_format_items(transport_items)}

===== 美食 搜索结果 =====
{_format_items(food_items)}

请为每个分类整理出 5–8 张信息卡片，要求：
- 内容来自搜索结果中提及最多、最具代表性的内容
- name：简洁名称，不超过15字
- description：一句话描述，不超过40字，突出亮点
- estimatedCost：预计费用，格式如 "¥50–100"、"免费" 或 "¥553（二等座）"
- tags：2–3个标签

以 JSON 格式返回，结构：
{{
  "experience": [
    {{
      "name": "外滩",
      "description": "上海最具代表性的滨江历史建筑群，夜景尤为壮观",
      "estimatedCost": "免费",
      "tags": ["地标", "夜景", "必去"]
    }}
  ],
  "transport": [
    {{
      "name": "高铁（北京→上海）",
      "description": "G字头高铁约4.5小时，是最主流的城际方案",
      "estimatedCost": "¥553（二等座）",
      "tags": ["高铁", "城际", "推荐"]
    }}
  ],
  "food": [
    {{
      "name": "南翔小笼包",
      "description": "豫园内百年老店，皮薄汁多，必吃经典",
      "estimatedCost": "¥30–60",
      "tags": ["小吃", "老字号", "必吃"]
    }}
  ]
}}"""
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd api
uv run pytest tests/test_prompts_discover.py -v 2>&1 | tail -10
```

Expected: PASS — 5 tests passing

- [ ] **Step 6: Commit**

```bash
cd ..
git add api/app/prompts/__init__.py api/app/prompts/discover.py api/tests/test_prompts_discover.py
git commit -m "feat(api): port buildDiscoverPrompt to Python with tests"
```

---

## Task 6: Plan Prompt Builders

**Files:**
- Create: `api/app/prompts/plan.py`
- Create: `api/tests/test_prompts_plan.py`

- [ ] **Step 1: Write failing tests**

Create `api/tests/test_prompts_plan.py`:

```python
from app.models.attraction import AttractionCard
from app.models.preferences import UserPreferences
from app.prompts.plan import build_plan_prompt, build_adjustment_prompt


PREFS = UserPreferences(
    destination="上海",
    departureCity="北京",
    departureDate="2026-05-10",
    days=3,
    totalBudget=5000,
    accommodationDescription="精品民宿",
    experienceDescription="本地小馆",
)

CARDS = [
    AttractionCard(
        id="c1",
        name="外滩",
        section="experience",
        description="滨江夜景",
        estimatedCost="免费",
        imageUrl="",
        tags=["地标"],
    ),
    AttractionCard(
        id="c2",
        name="高铁G1",
        section="transport",
        description="北京→上海",
        estimatedCost="¥553",
        imageUrl="",
        tags=["高铁"],
    ),
    AttractionCard(
        id="c3",
        name="南翔小笼",
        section="food",
        description="百年老店",
        estimatedCost="¥30",
        imageUrl="",
        tags=["小吃"],
    ),
]


def test_plan_prompt_includes_destination_and_budget():
    p = build_plan_prompt(PREFS, [])
    assert "上海" in p
    assert "5000" in p


def test_plan_prompt_includes_accommodation_and_experience():
    p = build_plan_prompt(PREFS, [])
    assert "精品民宿" in p
    assert "本地小馆" in p


def test_plan_prompt_includes_all_three_card_names():
    p = build_plan_prompt(PREFS, CARDS)
    assert "外滩" in p
    assert "高铁G1" in p
    assert "南翔小笼" in p


def test_plan_prompt_labels_each_section():
    p = build_plan_prompt(PREFS, CARDS)
    assert "体验" in p
    assert "交通" in p
    assert "美食" in p


def test_adjustment_prompt_includes_user_request():
    p = build_adjustment_prompt('{"days":[]}', "改成轻松一点", CARDS)
    assert "改成轻松一点" in p


def test_adjustment_prompt_includes_original_attractions():
    p = build_adjustment_prompt('{"days":[]}', "改一下", CARDS)
    assert "外滩" in p
    assert "南翔小笼" in p


def test_adjustment_prompt_works_with_no_attractions():
    p = build_adjustment_prompt('{"days":[]}', "调整", [])
    assert "调整" in p
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd api
uv run pytest tests/test_prompts_plan.py -v 2>&1 | tail -10
```

Expected: ImportError — `No module named 'app.prompts.plan'`

- [ ] **Step 3: Create `api/app/prompts/plan.py`**

```python
"""Plan prompt builders.

Python port of `web/src/lib/claude.ts::buildPlanPromptWithAttractions` and
`buildAdjustmentPrompt`.
"""

from app.models.attraction import AttractionCard
from app.models.preferences import UserPreferences

_SECTION_LABEL: dict[str, str] = {
    "experience": "体验/景点",
    "transport": "交通",
    "food": "美食",
}


def _format_selected(cards: list[AttractionCard]) -> str:
    if not cards:
        return ""
    by_section: dict[str, list[AttractionCard]] = {
        "experience": [],
        "transport": [],
        "food": [],
    }
    for c in cards:
        by_section[c.section].append(c)

    lines = ["\n用户已选择的感兴趣内容（请优先将这些安排进行程中）："]
    for section, items in by_section.items():
        if not items:
            continue
        names = "、".join(f"{c.name}（{c.estimated_cost}）" for c in items)
        lines.append(f"【{_SECTION_LABEL[section]}】{names}")
    return "\n".join(lines) + "\n"


def build_plan_prompt(prefs: UserPreferences, selected: list[AttractionCard]) -> str:
    """Prompt that turns preferences + selected cards into a day-by-day plan."""
    attractions_section = _format_selected(selected)
    return f"""你是一位专业的旅行规划师。请根据以下信息，生成一份详细的旅行规划。

目的地：{prefs.destination}
出发城市：{prefs.departure_city}
出发日期：{prefs.departure_date}
旅行天数：{prefs.days}天
总预算：¥{prefs.total_budget}（含交通、住宿、餐饮、景点）
{attractions_section}
住宿期待：
{prefs.accommodation_description}

旅行体验期待：
{prefs.experience_description}

请生成以下内容：
1. 逐日行程（每天5-7个活动，包含时间、地点、活动描述、预计费用）
2. 预算分配（交通/住宿/餐饮/景点/其他）
3. 实用提示（3-5条，关于当地注意事项）

输出格式为 JSON，结构如下：
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
}}"""


def build_adjustment_prompt(
    current_plan: str,
    user_request: str,
    selected: list[AttractionCard],
) -> str:
    """Prompt for AI chat-driven plan adjustments. Includes original selections as context."""
    context = (
        f"\n用户最初感兴趣的内容：{'、'.join(c.name for c in selected)}\n" if selected else ""
    )
    return f"""你是旅行规划助手。用户有以下调整请求：

"{user_request}"
{context}
当前行程：
{current_plan}

请只修改受影响的部分，保持其他内容不变。以相同的 JSON 格式返回完整的修改后行程。"""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd api
uv run pytest tests/test_prompts_plan.py -v 2>&1 | tail -15
```

Expected: PASS — 7 tests passing

- [ ] **Step 5: Commit**

```bash
cd ..
git add api/app/prompts/plan.py api/tests/test_prompts_plan.py
git commit -m "feat(api): port plan and adjustment prompt builders to Python"
```

---

## Task 7: Tavily Service

**Files:**
- Create: `api/app/services/__init__.py`
- Create: `api/app/services/tavily.py`
- Create: `api/tests/test_tavily_query_builder.py`

- [ ] **Step 1: Write failing tests**

Create `api/tests/test_tavily_query_builder.py`:

```python
from app.services.tavily import build_search_queries


def test_returns_three_queries():
    qs = build_search_queries("上海")
    assert len(qs) == 3


def test_all_queries_contain_destination():
    qs = build_search_queries("北京")
    for q in qs:
        assert "北京" in q


def test_query_zero_targets_attractions():
    qs = build_search_queries("成都")
    assert any(token in qs[0] for token in ["景点", "体验", "攻略"])


def test_query_one_targets_transport():
    qs = build_search_queries("成都")
    assert any(token in qs[1] for token in ["交通", "出行", "怎么去"])


def test_query_two_targets_food():
    qs = build_search_queries("成都")
    assert any(token in qs[2] for token in ["美食", "餐厅", "必吃"])
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd api
uv run pytest tests/test_tavily_query_builder.py -v 2>&1 | tail -10
```

Expected: ImportError

- [ ] **Step 3: Create `api/app/services/__init__.py`** (empty)

```bash
touch app/services/__init__.py
```

- [ ] **Step 4: Create `api/app/services/tavily.py`**

```python
"""Async Tavily search client.

Python port of `web/src/lib/googleSearch.ts` (which actually uses Tavily despite
the file name — a holdover from the Google CSE migration).
"""

import asyncio

import httpx

from app.prompts.discover import SearchItem


def build_search_queries(destination: str) -> tuple[str, str, str]:
    """Build the three section-specific queries used by /api/discover."""
    return (
        f"{destination} 必去景点 旅游体验 攻略 2025",
        f"{destination} 交通攻略 怎么去 市内出行 交通方式",
        f"{destination} 美食推荐 必吃 餐厅 小吃 2025",
    )


def _parse_results(results: list[dict]) -> list[SearchItem]:
    """Normalize Tavily results into our SearchItem shape."""
    return [
        SearchItem(
            title=r.get("title", "") or "",
            snippet=r.get("content", "") or "",
            link=r.get("url", "") or "",
            imageUrl="",
        )
        for r in results
    ]


async def search_tavily(query: str, api_key: str) -> list[SearchItem]:
    """Fire a single Tavily search and return normalized results."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": 8,
                "include_answer": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return _parse_results(data.get("results", []))


async def search_tavily_three_sections(
    destination: str, api_key: str
) -> tuple[list[SearchItem], list[SearchItem], list[SearchItem]]:
    """Run the three section-specific searches in parallel.

    Returns (experience_items, transport_items, food_items). Failed queries
    return empty lists so the caller can continue (Gemini still has fallback knowledge).
    """
    q1, q2, q3 = build_search_queries(destination)
    results = await asyncio.gather(
        search_tavily(q1, api_key),
        search_tavily(q2, api_key),
        search_tavily(q3, api_key),
        return_exceptions=True,
    )

    def safe(r) -> list[SearchItem]:
        return r if isinstance(r, list) else []

    return safe(results[0]), safe(results[1]), safe(results[2])
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd api
uv run pytest tests/test_tavily_query_builder.py -v 2>&1 | tail -10
```

Expected: PASS — 5 tests passing

- [ ] **Step 6: Manually test real Tavily call**

```bash
cd api
uv run python -c "
import asyncio
from app.config import get_settings
from app.services.tavily import search_tavily

async def main():
    settings = get_settings()
    items = await search_tavily('上海 必去景点 2025', settings.tavily_api_key)
    print(f'Got {len(items)} results')
    for i, item in enumerate(items[:3]):
        print(f'{i+1}. {item.title[:50]}')

asyncio.run(main())
"
```

Expected: prints `Got 8 results` (or similar) and the first 3 titles in Chinese.

- [ ] **Step 7: Commit**

```bash
cd ..
git add api/app/services/__init__.py api/app/services/tavily.py api/tests/test_tavily_query_builder.py
git commit -m "feat(api): add async Tavily search client with parallel three-section helper"
```

---

## Task 8: Gemini Service

**Files:**
- Create: `api/app/services/gemini.py`

The Gemini call doesn't need TDD — it's a thin SDK wrapper. We verify it manually.

- [ ] **Step 1: Create `api/app/services/gemini.py`**

```python
"""Async wrapper around the google-generativeai SDK."""

import asyncio
import json
import re

import google.generativeai as genai

from app.config import get_settings


def _configure_once() -> None:
    """Configure SDK with API key. Idempotent — safe to call repeatedly."""
    genai.configure(api_key=get_settings().gemini_api_key)


async def generate_text(prompt: str) -> str:
    """Run Gemini once with the given prompt, return raw text response."""
    _configure_once()
    model = genai.GenerativeModel(get_settings().gemini_model)
    # The SDK is sync; offload to a thread so we don't block the event loop.
    response = await asyncio.to_thread(model.generate_content, prompt)
    return response.text


def extract_json_block(raw: str) -> dict:
    """Extract the first JSON object from an LLM response.

    Robust against markdown code fences, trailing commas, and trailing prose.
    Raises ValueError if no JSON is recoverable.
    """
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\n?", "", raw).strip()

    # Find the first {...} block (greedy on inner braces)
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError("No JSON object found in response")
    candidate = match.group(0)

    # Try parsing as-is
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Strip trailing commas before } or ]
    candidate2 = re.sub(r",(\s*[}\]])", r"\1", candidate)
    try:
        return json.loads(candidate2)
    except json.JSONDecodeError:
        pass

    # Truncate to last complete } and retry
    last_brace = candidate2.rfind("}")
    if last_brace > 0:
        try:
            return json.loads(candidate2[: last_brace + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError("JSON parse failed after sanitization attempts")
```

- [ ] **Step 2: Manually test Gemini call**

```bash
cd api
uv run python -c "
import asyncio
from app.services.gemini import generate_text, extract_json_block

async def main():
    raw = await generate_text('Return JSON: {\"hello\": \"world\"}. Just the JSON, no markdown.')
    print('Raw:', raw[:200])
    parsed = extract_json_block(raw)
    print('Parsed:', parsed)

asyncio.run(main())
"
```

Expected: prints raw response and `Parsed: {'hello': 'world'}` (or similar — Gemini may add formatting).

- [ ] **Step 3: Commit**

```bash
cd ..
git add api/app/services/gemini.py
git commit -m "feat(api): add async Gemini wrapper with robust JSON extraction"
```

---

## Task 9: Discover Route

**Files:**
- Create: `api/app/routes/__init__.py`
- Create: `api/app/routes/discover.py`

- [ ] **Step 1: Create `api/app/routes/__init__.py`** (empty)

```bash
touch api/app/routes/__init__.py
```

- [ ] **Step 2: Create `api/app/routes/discover.py`**

```python
"""POST /api/discover endpoint.

Mirrors the behavior of `web/src/app/api/discover/route.ts`:
1. Run three Tavily searches in parallel.
2. Pass all results to Gemini with the discover prompt.
3. Return JSON shaped { sections: { experience, transport, food } }.
"""

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.models.attraction import AttractionCard, DiscoverSections
from app.prompts.discover import build_discover_prompt
from app.services.gemini import extract_json_block, generate_text
from app.services.tavily import search_tavily_three_sections

router = APIRouter()


@router.get("/api/discover", response_model=dict)
async def discover(destination: str) -> dict:
    """Generate three-section attraction cards for a destination."""
    if not destination:
        raise HTTPException(status_code=400, detail="destination is required")

    settings = get_settings()

    experience_items, transport_items, food_items = await search_tavily_three_sections(
        destination, settings.tavily_api_key
    )

    prompt = build_discover_prompt(destination, experience_items, transport_items, food_items)

    try:
        raw = await generate_text(prompt)
        parsed = extract_json_block(raw)
    except Exception as err:
        raise HTTPException(status_code=502, detail=f"LLM failed: {err}") from err

    def to_cards(raw_cards: list[dict], section: str) -> list[AttractionCard]:
        return [
            AttractionCard(
                id=str(uuid4()),
                name=c.get("name", ""),
                section=section,  # type: ignore[arg-type]
                description=c.get("description", ""),
                estimatedCost=c.get("estimatedCost", ""),
                imageUrl="",
                tags=c.get("tags", []),
            )
            for c in raw_cards
        ]

    sections = DiscoverSections(
        experience=to_cards(parsed.get("experience", []), "experience"),
        transport=to_cards(parsed.get("transport", []), "transport"),
        food=to_cards(parsed.get("food", []), "food"),
    )
    return {"sections": sections.model_dump(by_alias=True)}
```

- [ ] **Step 3: Commit**

```bash
cd ..
git add api/app/routes/__init__.py api/app/routes/discover.py
git commit -m "feat(api): add /api/discover route — Tavily + Gemini section extraction"
```

---

## Task 10: Plan Generate Route

**Files:**
- Create: `api/app/routes/plan.py`

- [ ] **Step 1: Create `api/app/routes/plan.py`**

```python
"""POST /api/plan/generate endpoint.

Handles two modes:
1. New plan generation — body has `preferences` and optional `selectedAttractions`.
2. Adjustment — body has `currentPlan` (JSON string), `adjustment` (text), and
   optional `selectedAttractions` for context.

Returns plain text (raw LLM JSON output) for compatibility with the frontend's
existing parse logic. The frontend already handles JSON extraction, so we don't
parse on the server side here.
"""

from typing import Annotated

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import PlainTextResponse

from app.models.attraction import AttractionCard
from app.models.preferences import UserPreferences
from app.prompts.plan import build_adjustment_prompt, build_plan_prompt
from app.services.gemini import generate_text

router = APIRouter()


@router.post("/api/plan/generate", response_class=PlainTextResponse)
async def generate_plan(
    body: Annotated[dict, Body(...)],
) -> str:
    """Either generate a new plan or apply an adjustment."""
    selected_raw = body.get("selectedAttractions") or []
    selected = [AttractionCard.model_validate(c) for c in selected_raw]

    if body.get("currentPlan") and body.get("adjustment"):
        prompt = build_adjustment_prompt(
            body["currentPlan"], body["adjustment"], selected
        )
    elif body.get("preferences"):
        prefs = UserPreferences.model_validate(body["preferences"])
        prompt = build_plan_prompt(prefs, selected)
    else:
        raise HTTPException(
            status_code=400,
            detail="must provide either preferences or (currentPlan + adjustment)",
        )

    try:
        return await generate_text(prompt)
    except Exception as err:
        raise HTTPException(status_code=502, detail=f"LLM failed: {err}") from err
```

- [ ] **Step 2: Commit**

```bash
cd ..
git add api/app/routes/plan.py
git commit -m "feat(api): add /api/plan/generate route handling both new plan and adjustment"
```

---

## Task 11: FastAPI Entry Point

**Files:**
- Create: `api/main.py`

- [ ] **Step 1: Create `api/main.py`**

```python
"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.discover import router as discover_router
from app.routes.plan import router as plan_router

app = FastAPI(title="Travel Planner API", version="0.1.0")


settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(discover_router)
app.include_router(plan_router)


@app.get("/health")
async def health() -> dict:
    """Liveness check — used by Docker/load balancer."""
    return {"status": "ok", "model": settings.gemini_model}
```

- [ ] **Step 2: Start the server**

```bash
cd api
uv run uvicorn main:app --reload --port 8000
```

Expected log: `Uvicorn running on http://127.0.0.1:8000`. Leave running.

- [ ] **Step 3: Verify health endpoint (in another terminal)**

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","model":"gemini-1.5-flash"}`

- [ ] **Step 4: Verify discover endpoint**

```bash
curl -s "http://localhost:8000/api/discover?destination=上海" | python3 -m json.tool | head -30
```

Expected: JSON with `{ "sections": { "experience": [...], "transport": [...], "food": [...] } }`, each list 5–8 items.

- [ ] **Step 5: Verify plan generation endpoint**

```bash
curl -s -X POST http://localhost:8000/api/plan/generate \
  -H "Content-Type: application/json" \
  -d '{
    "preferences": {
      "destination": "上海",
      "departureCity": "北京",
      "departureDate": "2026-06-01",
      "days": 2,
      "totalBudget": 3000,
      "accommodationDescription": "市中心",
      "experienceDescription": "外滩"
    },
    "selectedAttractions": []
  }' | head -50
```

Expected: text response containing JSON with `"days"`, `"budget"`, `"tips"` keys.

- [ ] **Step 6: Stop the server (Ctrl-C) and commit**

```bash
cd ..
git add api/main.py
git commit -m "feat(api): wire up FastAPI app with CORS, routes, and health check"
```

---

## Task 12: Frontend API Client

**Files:**
- Create: `web/src/lib/apiClient.ts`
- Modify: `web/.env.local`

- [ ] **Step 1: Append API URL to `web/.env.local`**

Add to `web/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 2: Create `web/src/lib/apiClient.ts`**

```typescript
"use client"

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
```

- [ ] **Step 3: Commit**

```bash
git add web/src/lib/apiClient.ts web/.env.local
git commit -m "feat(web): add apiClient that targets NEXT_PUBLIC_API_URL"
```

(`.env.local` contains an API key, so confirm it is gitignored before committing — `git status` should NOT show `web/.env.local` if `.gitignore` is set up. If it does show, abort, add `.env.local` to `web/.gitignore`, retry.)

---

## Task 13: Migrate Discover Page to apiClient

**Files:**
- Modify: `web/src/app/discover/[destination]/page.tsx`

- [ ] **Step 1: Add the apiClient import**

Open `web/src/app/discover/[destination]/page.tsx` and add this import next to the other `@/lib/...` imports near the top:

```typescript
import { discoverDestination, generatePlan } from "@/lib/apiClient"
```

- [ ] **Step 2: Replace the discover fetch block**

Find this block inside the `useEffect`:

```typescript
fetch(`/api/discover?destination=${encodeURIComponent(destination)}`)
  .then((res) => {
    if (!res.ok) throw new Error("搜索失败，请返回重试")
    return res.json()
  })
  .then((data: { sections: DiscoverSections }) => {
    setSections(data.sections)
    sessionStorage.setItem(cacheKey, JSON.stringify(data.sections))
  })
  .catch((err: Error) => setError(err.message))
  .finally(() => {
    clearInterval(interval)
    setLoading(false)
  })
```

Replace with:

```typescript
discoverDestination(destination)
  .then((data) => {
    const typed = data as { sections: DiscoverSections }
    setSections(typed.sections)
    sessionStorage.setItem(cacheKey, JSON.stringify(typed.sections))
  })
  .catch((err: Error) => setError(err.message))
  .finally(() => {
    clearInterval(interval)
    setLoading(false)
  })
```

- [ ] **Step 3: Replace the plan generation fetch**

Find the block in `handleGenerate`:

```typescript
const res = await fetch("/api/plan/generate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ preferences: prefs, selectedAttractions: selectedCards }),
})
if (!res.ok) throw new Error("生成失败，请重试")
const raw = await res.text()
```

Replace with:

```typescript
const raw = await generatePlan({ preferences: prefs, selectedAttractions: selectedCards })
```

- [ ] **Step 4: Verify the page still works**

Make sure the Python backend is running:

```bash
cd api
uv run uvicorn main:app --reload --port 8000
```

In another terminal, restart the Next.js dev server:

```bash
cd web
npm run dev
```

Open http://localhost:3000, enter `上海` + `5000`, click 探索目的地. Cards should load from the Python backend.

Check the api server terminal — you should see `INFO: GET /api/discover?destination=上海 200`.

- [ ] **Step 5: Commit**

```bash
cd ..
git add web/src/app/discover/
git commit -m "feat(web): switch discover page to use apiClient (Python backend)"
```

---

## Task 14: Migrate usePlan Hook to apiClient

**Files:**
- Modify: `web/src/hooks/usePlan.ts`

- [ ] **Step 1: Update the adjustment fetch**

Open `web/src/hooks/usePlan.ts`, add at the top with other imports:

```typescript
import { generatePlan } from "@/lib/apiClient"
```

Find the block:

```typescript
const res = await fetch("/api/plan/generate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    currentPlan: JSON.stringify(plan.days),
    adjustment: userMessage,
    selectedAttractions: plan.selectedAttractions,
  }),
})

if (!res.ok) throw new Error("调整失败")
const raw = await res.text()
```

Replace with:

```typescript
const raw = await generatePlan({
  currentPlan: JSON.stringify(plan.days),
  adjustment: userMessage,
  selectedAttractions: plan.selectedAttractions,
})
```

- [ ] **Step 2: Verify chat adjustment works**

With both servers running:
1. Complete the full flow: home → discover → select cards → generate plan → land on `/plan/[id]`.
2. Type "把第一天改轻松一点" in the chat panel.
3. Itinerary should update.

Check the api terminal — you should see `INFO: POST /api/plan/generate 200`.

- [ ] **Step 3: Commit**

```bash
git add web/src/hooks/usePlan.ts
git commit -m "feat(web): switch usePlan adjustment to use apiClient (Python backend)"
```

---

## Task 15: Add api/README.md

**Files:**
- Create: `api/README.md`

- [ ] **Step 1: Create `api/README.md`**

```markdown
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
- `POST /api/plan/generate` — new plan generation OR chat adjustment

## Tests

```bash
uv run pytest -v
```
```

- [ ] **Step 2: Commit**

```bash
git add api/README.md
git commit -m "docs(api): add README with setup and run instructions"
```

---

## Task 16: End-to-End Verification

- [ ] **Step 1: Run all Python tests**

```bash
cd api
uv run pytest -v
```

Expected: all tests pass (5 + 7 + 5 + 5 = 22 tests).

- [ ] **Step 2: Run Next.js tests**

```bash
cd ../web
npm test
```

Expected: 23 tests pass.

- [ ] **Step 3: Build Next.js**

```bash
npm run build
```

Expected: zero errors.

- [ ] **Step 4: Start both servers**

Terminal A:
```bash
cd api
uv run uvicorn main:app --reload --port 8000
```

Terminal B:
```bash
cd web
npm run dev
```

- [ ] **Step 5: Walk through the full flow**

Open http://localhost:3000:

1. Enter `上海` + `5000` → click 探索目的地
2. Loading spinner shows; api terminal logs `GET /api/discover...`
3. Three sections appear (体验/交通/美食) with 5–8 cards each
4. Select 2 experience + 1 transport + 1 food card
5. Bottom bar appears → click 继续规划
6. Fill: `北京` / `2026-06-15` / `3` / `市区精品酒店`
7. Click 生成我的行程 → loading; api terminal logs `POST /api/plan/generate`
8. Land on `/plan/[id]` — chat greeting mentions selected card names
9. Type "把第一天改成轻松一点" → itinerary updates; api logs another POST
10. Refresh `/plan/[id]` — plan persists (localStorage works)

- [ ] **Step 6: Final commit**

```bash
cd ..
git add .
git commit -m "feat: complete Python backend foundation — Plan 1 of 3 done"
```

---

## Done — What You Have

- A second deployable service in `api/` with FastAPI, Pydantic models, async services for Tavily and Gemini, and routes that mirror the Next.js endpoints exactly.
- The Next.js frontend points at `NEXT_PUBLIC_API_URL` via the new `apiClient`. Existing UI is unchanged; UX is identical.
- 22 Python tests covering models, prompt builders, and query construction.
- The old Next.js API routes (`web/src/app/api/...`) still exist as fallback. They will be deleted in Plan 3 once production deployment is solid.

## Why this matters for Plan 2

Plan 2 will replace the single `generate_text(prompt)` call in `routes/plan.py` with a LangGraph state machine that runs Transport, Stay, and Planner agents. Because we now have:

- A Python service to host the agent graph,
- Pydantic models that match the frontend contract,
- Working async LLM and search services,
- Tests that pin the prompt builder behavior,

…the LangGraph addition becomes a contained change inside `routes/plan.py` rather than a frontend rewrite.
