# Tavily Discovery Grounding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the real discovery agent ground its Gemini output in Tavily search results, while preserving fixture-mode determinism and graceful fallback when Tavily is missing or unavailable.

**Architecture:** Keep Tavily as a provider adapter and add a thin discovery-grounding layer inside the discovery node. The discovery agent gathers three bounded Tavily sections, formats them into the LLM prompt, merges Tavily source notes into the returned `DiscoveryOutput`, and removes placeholder image URLs because Tavily results do not provide direct image assets. Fixture mode stays unchanged.

**Tech Stack:** FastAPI backend, LangGraph node functions, Pydantic v2 models, Tavily provider adapter, pytest/pytest-httpx, existing `make regression` gate.

---

## File Map

- Modify `api/app/graph/nodes/discovery.py`: add Tavily search grounding collection, prompt formatting, source-note merging, placeholder image cleanup, and optional `search_provider` injection for tests.
- Modify `api/tests/graph/test_nodes.py`: add tests proving Tavily results reach the LLM prompt, Tavily source notes are retained, placeholder images are removed, and search failures gracefully fall back.
- Modify `docs/2026-05-10-real-mvp-work-summary.md`: update the status after implementation from "Tavily adapter only" to "Tavily grounded discovery implemented" if verification passes.

---

### Task 1: Add Failing Discovery Grounding Tests

**Files:**
- Modify: `api/tests/graph/test_nodes.py`

- [x] **Step 1: Add fake search provider helpers**

Add these imports near the existing imports:

```python
from app.models.schemas import SourceNote
from app.providers.types import ProviderError, SearchRequest, SearchResult
```

Add these helpers below the imports:

```python
class FakeSearchProvider:
    name = "fake-search"

    def __init__(self, results_by_query: dict[str, list[SearchResult]]) -> None:
        self.results_by_query = results_by_query
        self.requests: list[SearchRequest] = []

    async def health(self):
        raise AssertionError("discovery grounding should call search directly")

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        self.requests.append(request)
        return self.results_by_query.get(request.query, [])


class FailingSearchProvider:
    name = "failing-search"

    async def health(self):
        raise AssertionError("discovery grounding should call search directly")

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        raise ProviderError(
            provider="failing-search",
            kind="search",
            code="network_failure",
            message=f"failed {request.query}",
        )


def search_result(title: str, url: str, snippet: str) -> SearchResult:
    return SearchResult(
        title=title,
        url=url,
        snippet=snippet,
        source_note=SourceNote(provider="tavily", url=url, note="Tavily search result"),
    )
```

- [x] **Step 2: Add test that Tavily results are included in the LLM prompt and source notes**

Add this test near `test_run_discovery_agent_live_path_calls_llm_and_normalizes`:

```python
@pytest.mark.asyncio
async def test_run_discovery_agent_adds_tavily_grounding_to_prompt_and_sources(
    monkeypatch,
) -> None:
    recorded = {}
    output_from_llm = fixtures.discovery_output().model_copy(
        update={
            "source_notes": [
                SourceNote(provider="gemini", url=None, note="Generated from prompt")
            ]
        }
    )
    provider = FakeSearchProvider(
        {
            "上海 必去景点 旅游体验 攻略 2025": [
                search_result(
                    "Shanghai waterfront guide",
                    "https://example.com/bund-guide",
                    "The Bund is a classic first-time visitor anchor.",
                )
            ],
            "上海 交通攻略 怎么去 市内出行 交通方式": [
                search_result(
                    "Shanghai metro guide",
                    "https://example.com/metro-guide",
                    "Metro is usually the easiest way to cross the city.",
                )
            ],
            "上海 美食推荐 必吃 餐厅 小吃 2025": [
                search_result(
                    "Shanghai food guide",
                    "https://example.com/food-guide",
                    "Xiaolongbao and shengjianbao are common local highlights.",
                )
            ],
        }
    )

    async def fake_generate_structured(**kwargs):
        recorded.update(kwargs)
        return output_from_llm

    monkeypatch.setenv("LLM_PROVIDER_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.graph.nodes.discovery.generate_structured",
        fake_generate_structured,
    )

    result = await run_discovery_agent(
        fixtures.session(),
        search_provider=provider,
    )

    assert len(provider.requests) == 3
    assert "Search grounding from Tavily" in recorded["user"]
    assert "Shanghai waterfront guide" in recorded["user"]
    assert "Shanghai metro guide" in recorded["user"]
    assert "Shanghai food guide" in recorded["user"]
    assert any(note.provider == "tavily" for note in result.source_notes)
```

- [x] **Step 3: Add test that search failures fall back to LLM-only discovery**

Add this test:

```python
@pytest.mark.asyncio
async def test_run_discovery_agent_continues_when_tavily_grounding_fails(
    monkeypatch,
) -> None:
    recorded = {}

    async def fake_generate_structured(**kwargs):
        recorded.update(kwargs)
        return fixtures.discovery_output()

    monkeypatch.setenv("LLM_PROVIDER_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.graph.nodes.discovery.generate_structured",
        fake_generate_structured,
    )

    result = await run_discovery_agent(
        fixtures.session(),
        search_provider=FailingSearchProvider(),
    )

    assert result.cards
    assert "Search grounding unavailable" in recorded["user"]
```

- [x] **Step 4: Add test that placeholder image URLs are removed**

Add this test:

```python
@pytest.mark.asyncio
async def test_run_discovery_agent_removes_placeholder_image_urls(monkeypatch) -> None:
    card = fixtures.discovery_card().model_copy(
        update={"image_url": "https://example.com/not-a-real-image.jpg"}
    )

    async def fake_generate_structured(**_: object):
        return fixtures.discovery_output().model_copy(update={"cards": [card]})

    monkeypatch.setenv("LLM_PROVIDER_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.graph.nodes.discovery.generate_structured",
        fake_generate_structured,
    )

    result = await run_discovery_agent(fixtures.session(), search_provider=None)

    assert result.cards[0].image_url is None
```

- [x] **Step 5: Run tests to verify failure**

Run:

```bash
cd api
uv run pytest tests/graph/test_nodes.py::test_run_discovery_agent_adds_tavily_grounding_to_prompt_and_sources tests/graph/test_nodes.py::test_run_discovery_agent_continues_when_tavily_grounding_fails tests/graph/test_nodes.py::test_run_discovery_agent_removes_placeholder_image_urls -q
```

Expected: FAIL because `run_discovery_agent` does not accept `search_provider` and does not build grounding context yet.

---

### Task 2: Implement Tavily Grounding in Discovery Agent

**Files:**
- Modify: `api/app/graph/nodes/discovery.py`

- [x] **Step 1: Add imports**

Add imports near the top:

```python
import asyncio
from collections.abc import Iterable
```

Add provider imports:

```python
from app.models.schemas import SourceNote
from app.providers.search.tavily import TavilySearchProvider, build_search_queries
from app.providers.types import ProviderError, SearchProvider, SearchRequest, SearchResult
```

- [x] **Step 2: Add `search_provider` parameter and collect context**

Change the signature:

```python
async def run_discovery_agent(
    session: PlanningSession,
    *,
    fixture_mode: bool = False,
    llm_provider: LLMProvider | None = None,
    search_provider: SearchProvider | None = None,
    cost_logger: LLMCostLogger | None = None,
) -> DiscoveryOutput:
```

Inside the non-fixture branch, before `generate_structured`, add:

```python
    search_results = await _collect_search_grounding(session, search_provider)
    search_context = _format_search_grounding(search_results)
```

Pass the context into the prompt:

```python
        user=_build_discovery_prompt(session, search_context=search_context),
```

After receiving `output`, normalize with:

```python
    grounded_output = output.model_copy(
        update={
            "cards": [_normalize_discovery_card(card, session) for card in output.cards],
            "source_notes": _merge_source_notes(
                _source_notes_from_search_results(search_results),
                output.source_notes,
            ),
        }
    )
    return grounded_output
```

- [x] **Step 3: Update prompt builder**

Change `_build_discovery_prompt` signature:

```python
def _build_discovery_prompt(
    session: PlanningSession,
    *,
    search_context: str | None = None,
) -> str:
```

Append these prompt lines:

```python
            "Use grounded search notes when available, but still return only the DiscoveryOutput JSON shape.",
            "Set image_url to null unless a source gives a direct, real image URL. Never invent example.com image URLs.",
            search_context or "Search grounding unavailable; use general travel knowledge and keep source_notes honest.",
```

- [x] **Step 4: Add helper functions**

Add these helpers below `_build_discovery_prompt`:

```python
async def _collect_search_grounding(
    session: PlanningSession,
    search_provider: SearchProvider | None,
) -> list[SearchResult]:
    provider = search_provider or _default_search_provider()
    if provider is None:
        return []

    destination = session.hard_constraints.destination_city
    country_code = session.hard_constraints.destination_country_code
    queries = build_search_queries(destination)
    batches = await asyncio.gather(
        *[
            _safe_search(provider, SearchRequest(query=query, country_code=country_code, limit=4))
            for query in queries
        ],
        return_exceptions=False,
    )
    return [result for batch in batches for result in batch]


async def _safe_search(
    provider: SearchProvider,
    request: SearchRequest,
) -> list[SearchResult]:
    try:
        return await provider.search(request)
    except ProviderError:
        return []
    except Exception:
        return []


def _default_search_provider() -> SearchProvider | None:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return None
    return TavilySearchProvider(api_key=api_key)


def _format_search_grounding(results: list[SearchResult]) -> str:
    if not results:
        return "Search grounding unavailable; use general travel knowledge and keep source_notes honest."

    lines = ["Search grounding from Tavily:"]
    for index, result in enumerate(results[:12], start=1):
        url = result.url or "no-url"
        snippet = " ".join(result.snippet.split())
        lines.append(f"{index}. {result.title} ({url}) - {snippet[:280]}")
    return "\n".join(lines)


def _source_notes_from_search_results(results: list[SearchResult]) -> list[SourceNote]:
    notes: list[SourceNote] = []
    for result in results:
        if result.source_note is not None:
            notes.append(result.source_note)
        elif result.url:
            notes.append(SourceNote(provider="tavily", url=result.url, note=result.title))
    return notes


def _merge_source_notes(
    grounded_notes: Iterable[SourceNote],
    model_notes: Iterable[SourceNote],
) -> list[SourceNote]:
    merged: list[SourceNote] = []
    seen: set[tuple[str, str | None, str]] = set()
    for note in [*grounded_notes, *model_notes]:
        key = (note.provider, note.url, note.note)
        if key in seen:
            continue
        seen.add(key)
        merged.append(note)
    return merged
```

- [x] **Step 5: Remove placeholder image URLs during normalization**

Change `_normalize_discovery_card` update dict to include:

```python
            "image_url": _usable_image_url(card.image_url),
```

Add helper:

```python
def _usable_image_url(value: str | None) -> str | None:
    if value is None:
        return None
    if "example.com" in value.lower():
        return None
    return value
```

- [x] **Step 6: Run task tests**

Run:

```bash
cd api
uv run pytest tests/graph/test_nodes.py::test_run_discovery_agent_adds_tavily_grounding_to_prompt_and_sources tests/graph/test_nodes.py::test_run_discovery_agent_continues_when_tavily_grounding_fails tests/graph/test_nodes.py::test_run_discovery_agent_removes_placeholder_image_urls -q
```

Expected: PASS.

---

### Task 3: Verify Real Tavily Grounding and Update Status Doc

**Files:**
- Modify: `docs/2026-05-10-real-mvp-work-summary.md`

- [x] **Step 1: Run targeted API tests**

Run:

```bash
cd api
uv run pytest tests/graph/test_nodes.py tests/providers/test_tavily.py tests/routes/test_discovery_preferences.py -q
```

Expected: PASS.

- [x] **Step 2: Run real API smoke with configured local keys**

Run with a real dev server already running or start one:

```bash
cd web
npm run dev
```

In another command:

```bash
BASE_URL=http://127.0.0.1:8000 bash api/scripts/smoke_curl.sh
```

Expected: `Smoke flow passed for session_...`

- [x] **Step 3: Update summary document**

Change `docs/2026-05-10-real-mvp-work-summary.md`:

```markdown
- Tavily adapter 已单独跑通，且 Tavily 搜索结果已接入 discovery 主流程。
```

Change the next-step section so Plan14 is marked complete and the next recommended plan becomes AMap/Mapbox enrichment.

- [x] **Step 4: Run full regression**

Run:

```bash
make regression
```

Expected: all gates pass, including API pytest, fixture smoke, and Playwright e2e.

- [x] **Step 5: Commit**

Run:

```bash
git add api/app/graph/nodes/discovery.py api/tests/graph/test_nodes.py docs/2026-05-10-real-mvp-work-summary.md docs/superpowers/plans/2026-05-10-langgraph-mvp-14-tavily-discovery-grounding.md
git commit -m "feat: ground discovery with tavily search"
```

---

## Self-Review

- Spec coverage: The plan grounds discovery with Tavily, preserves fixture behavior, handles provider failure, removes placeholder images, updates docs, and runs targeted plus full verification.
- Placeholder scan: No TBD/TODO placeholders are present.
- Type consistency: `SearchProvider`, `SearchRequest`, `SearchResult`, and `SourceNote` names match the existing provider/schema modules.
