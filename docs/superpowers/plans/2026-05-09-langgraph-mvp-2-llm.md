# LangGraph MVP — Plan 2: LLM Wrapper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `web/src/server/llm/`(client / retry / jsonRepair / costLogger 共 4 个模块)逐文件移植到 Python `api/app/llm/`,得到一个**异步、带超时、带指数退避重试、带 JSON 修复、带成本日志**的 LLM 调用门面 `generate_structured(...)`,作为 Plan 5 LangGraph 节点的唯一 LLM 入口。

**Architecture:**
- `LLMProvider` 抽象成 Protocol(input: system+user+timeout, output: 原始字符串)。`GeminiLLMProvider` 是默认实现,基于 `google.genai.Client().aio.models.generate_content`(异步),沿用 `services/gemini.py` 已经验证可用的 SDK 用法,不再走 TS 那套手写 fetch + Gemini REST。
- 错误层级照搬 TS:`LLMConfigurationError` / `LLMAuthError` / `LLMNetworkError` / `LLMProviderError` / `LLMTimeoutError` / `LLMJsonParseError`,共享 `transient/retryable` 标记字段,`with_retry` 用同一套 `should_retry` 判定。
- 时间用 `time.perf_counter()` 计算 `duration_ms`;Cost log 用 `aiofiles` 不引入则用 `asyncio.to_thread` 包同步 `open(...,"a")` 调用。**为了少加依赖,本计划用 `asyncio.to_thread` + 标准 `pathlib`,不引 `aiofiles`。**
- TDD:每个文件先写 pytest(失败),再实现。`pytest-asyncio` 已在 dev 依赖里。

**Tech Stack:** Python 3.12, Pydantic v2, google-genai(已装), pytest, pytest-asyncio(已装)。**不新增依赖**。

**Out of scope:**
- ❌ 不删 `api/app/services/gemini.py`(当前还被 `routes/{plan,discover}.py` 引用,Plan 6 删路由时一起清)
- ❌ 不接 LangGraph(Plan 5)
- ❌ 不接 FastAPI 路由(Plan 6)
- ❌ 不写 streaming token 接口(MVP 后再说)

---

## File Structure

**Create:**
- `api/app/llm/__init__.py` — 包入口,导出 `generate_structured / LLMProvider / 各错误类`
- `api/app/llm/json_repair.py` — `extract_json_candidate / repair_json / parse_json_with_repair / JsonRepairError`
- `api/app/llm/retry.py` — `with_retry / RetryOptions / RetryResult / RetryExhaustedError / is_transient_network_error`
- `api/app/llm/cost_logger.py` — `LLMCostLogEntry / create_cost_log_entry / log_cost / estimate_token_count / default_cost_log_path`
- `api/app/llm/client.py` — `LLMProvider(Protocol) / GeminiLLMProvider / generate_structured / 6 种错误类`
- `api/tests/llm/__init__.py`(空文件)
- `api/tests/llm/test_json_repair.py`
- `api/tests/llm/test_retry.py`
- `api/tests/llm/test_cost_logger.py`
- `api/tests/llm/test_client.py`
- `api/scripts/smoke_llm.py` — 烟测脚本,只在 `GEMINI_API_KEY` 存在时跑通真实 SDK

**Untouched (deleted in Plan 6):**
- `api/app/services/gemini.py`(老 `generate_text` / `extract_json_block`,被 routes/{plan,discover}.py 用,Plan 6 整体删)
- `api/app/routes/{plan,discover}.py`

**Reference (read-only — TS 源文件,不改):**
- `web/src/server/llm/{client,retry,jsonRepair,costLogger}.ts`
- `web/src/server/llm/{client,jsonRepair}.test.ts`

---

## Task 0 — Setup

**Files:**
- Create: `api/app/llm/__init__.py`(暂空,Step 5.1 再填导出)
- Create: `api/tests/llm/__init__.py`(空文件)

- [ ] **Step 0.1: 创建空目录占位**

```bash
mkdir -p api/app/llm api/tests/llm
touch api/app/llm/__init__.py api/tests/llm/__init__.py
```

- [ ] **Step 0.2: 跑现有测试基线**

Run: `cd api && uv run pytest -v`
Expected: 全绿(66 个,Plan 1 完成后基线)。

- [ ] **Step 0.3: 提交**

```bash
git add api/app/llm/__init__.py api/tests/llm/__init__.py
git commit -m "chore(api): scaffold llm package"
```

---

## Task 1 — `json_repair.py`

**Files:**
- Create: `api/app/llm/json_repair.py`
- Create: `api/tests/llm/test_json_repair.py`

**TS reference:** `web/src/server/llm/jsonRepair.ts`(行 1-86)、`web/src/server/llm/jsonRepair.test.ts`

- [ ] **Step 1.1: 写测试**

写到 `api/tests/llm/test_json_repair.py`:

```python
"""Mirror of web/src/server/llm/jsonRepair.test.ts plus extra edge cases."""
from __future__ import annotations

import pytest

from app.llm.json_repair import (
    JsonRepairError,
    extract_json_candidate,
    parse_json_with_repair,
    repair_json,
)


def test_strips_leading_and_trailing_non_json_text() -> None:
    assert repair_json('Here is the payload:\n{"ok":true}\nDone.') == '{"ok":true}'


def test_fixes_trailing_commas_in_object_and_array() -> None:
    parsed = parse_json_with_repair("""{
      "items": [
        { "name": "Bund", },
      ],
    }""")
    assert parsed == {"items": [{"name": "Bund"}]}


def test_throws_when_no_json_payload_found() -> None:
    with pytest.raises(JsonRepairError, match="No JSON payload"):
        repair_json("no structured payload")


def test_throws_when_no_complete_json_payload() -> None:
    with pytest.raises(JsonRepairError, match="No complete JSON payload"):
        extract_json_candidate('{"unterminated": "value"')


def test_extracts_array_when_array_comes_first() -> None:
    assert repair_json('Result: [1,2,3] tail') == '[1,2,3]'


def test_handles_nested_braces_inside_strings() -> None:
    raw = '{"k":"a } b { c","x":1}'
    assert parse_json_with_repair(raw) == {"k": "a } b { c", "x": 1}


def test_handles_escaped_quotes_inside_strings() -> None:
    raw = '{"msg":"He said \\"hi\\""}'
    assert parse_json_with_repair(raw) == {"msg": 'He said "hi"'}


def test_throws_on_mismatched_delimiters() -> None:
    with pytest.raises(JsonRepairError, match="Mismatched"):
        extract_json_candidate('{"a": [1, 2}')
```

- [ ] **Step 1.2: 跑测试,确认全失败**

Run: `cd api && uv run pytest tests/llm/test_json_repair.py -v`
Expected: ImportError / module not found。

- [ ] **Step 1.3: 实现 `json_repair.py`**

写到 `api/app/llm/json_repair.py`:

```python
"""LLM output JSON repair — port of web/src/server/llm/jsonRepair.ts.

Strips non-JSON prefix/suffix, fixes trailing commas, balances delimiters.
"""
from __future__ import annotations

import json
import re
from typing import Any

_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


class JsonRepairError(ValueError):
    """Raised when the repair pipeline cannot recover a JSON payload."""


def repair_json(raw: str) -> str:
    candidate = extract_json_candidate(raw)
    return _TRAILING_COMMA_RE.sub(r"\1", candidate)


def parse_json_with_repair(raw: str) -> Any:
    return json.loads(repair_json(raw))


def extract_json_candidate(raw: str) -> str:
    start = _find_first_json_start(raw)
    if start == -1:
        raise JsonRepairError("No JSON payload found in LLM output")

    end = _find_balanced_json_end(raw, start)
    if end == -1:
        raise JsonRepairError("No complete JSON payload found in LLM output")

    return raw[start : end + 1].strip()


def _find_first_json_start(raw: str) -> int:
    obj_start = raw.find("{")
    arr_start = raw.find("[")
    if obj_start == -1:
        return arr_start
    if arr_start == -1:
        return obj_start
    return min(obj_start, arr_start)


def _find_balanced_json_end(raw: str, start: int) -> int:
    stack: list[str] = []
    in_string = False
    escaped = False

    for i in range(start, len(raw)):
        ch = raw[i]

        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            stack.append("}")
            continue
        if ch == "[":
            stack.append("]")
            continue
        if ch in ("}", "]"):
            if not stack:
                raise JsonRepairError("Mismatched JSON delimiters in LLM output")
            expected = stack.pop()
            if expected != ch:
                raise JsonRepairError("Mismatched JSON delimiters in LLM output")
            if not stack:
                return i

    return -1
```

- [ ] **Step 1.4: 跑测试,确认全过**

Run: `cd api && uv run pytest tests/llm/test_json_repair.py -v`
Expected: 8 个用例全 PASS。

- [ ] **Step 1.5: 跑全套基线**

Run: `cd api && uv run pytest -v`
Expected: 66 + 8 = 74 个全绿。

- [ ] **Step 1.6: 提交**

```bash
git add api/app/llm/json_repair.py api/tests/llm/test_json_repair.py
git commit -m "feat(api): add llm json_repair ported from web jsonRepair.ts"
```

---

## Task 2 — `retry.py`(异步指数退避)

**Files:**
- Create: `api/app/llm/retry.py`
- Create: `api/tests/llm/test_retry.py`

**TS reference:** `web/src/server/llm/retry.ts`(行 1-86)

**关键差异:** TS 端 `withRetry` 抛 `RetryExhaustedError(cause, retryCount)`,client 用 `unwrapRetryError` 把内层 cause 抛回。Python 版**保留同样行为**,让 client 可以拿到原始 cause(如 `LLMNetworkError`)与 `retry_count` 同时返回。

- [ ] **Step 2.1: 写测试**

写到 `api/tests/llm/test_retry.py`:

```python
"""Mirror of withRetry behavior in web/src/server/llm/retry.ts."""
from __future__ import annotations

import pytest

from app.llm.retry import (
    RetryExhaustedError,
    RetryOptions,
    is_transient_network_error,
    with_retry,
)


class _Transient(Exception):
    transient = True


class _PermanentHTTP(Exception):
    status = 400


class _TransientHTTP(Exception):
    status = 503


# ---------- with_retry: success path ----------

async def test_returns_value_with_zero_retries_on_first_success() -> None:
    async def op() -> int:
        return 42

    result = await with_retry(op, RetryOptions(base_delay_ms=0))
    assert result.value == 42
    assert result.retry_count == 0


async def test_retries_then_succeeds_and_reports_retry_count() -> None:
    calls = {"n": 0}

    async def op() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise _Transient("flaky")
        return "ok"

    result = await with_retry(op, RetryOptions(max_retries=3, base_delay_ms=0))
    assert result.value == "ok"
    assert result.retry_count == 2
    assert calls["n"] == 3


# ---------- with_retry: exhaustion ----------

async def test_raises_retry_exhausted_with_cause_after_max() -> None:
    async def op() -> None:
        raise _Transient("always")

    with pytest.raises(RetryExhaustedError) as ei:
        await with_retry(op, RetryOptions(max_retries=2, base_delay_ms=0))
    assert ei.value.retry_count == 2
    assert isinstance(ei.value.cause, _Transient)


async def test_does_not_retry_when_should_retry_returns_false() -> None:
    calls = {"n": 0}

    async def op() -> None:
        calls["n"] += 1
        raise _PermanentHTTP("hard fail")

    with pytest.raises(RetryExhaustedError):
        await with_retry(op, RetryOptions(max_retries=5, base_delay_ms=0))
    assert calls["n"] == 1  # never retried


# ---------- is_transient_network_error ----------

def test_is_transient_for_network_typeerror() -> None:
    # Python's analogue: any explicit transient-marked exception
    assert is_transient_network_error(_Transient()) is True


def test_is_transient_for_5xx_and_429_and_408() -> None:
    e1 = _TransientHTTP("503")
    assert is_transient_network_error(e1) is True
    e408 = type("E", (Exception,), {"status": 408})()
    assert is_transient_network_error(e408) is True
    e429 = type("E", (Exception,), {"status": 429})()
    assert is_transient_network_error(e429) is True


def test_is_not_transient_for_4xx_other_than_408_429() -> None:
    assert is_transient_network_error(_PermanentHTTP()) is False


def test_is_transient_for_unix_network_codes() -> None:
    e = type("E", (Exception,), {"code": "ECONNRESET"})()
    assert is_transient_network_error(e) is True
```

- [ ] **Step 2.2: 跑测试,确认全失败**

Run: `cd api && uv run pytest tests/llm/test_retry.py -v`
Expected: ImportError。

- [ ] **Step 2.3: 实现 `retry.py`**

写到 `api/app/llm/retry.py`:

```python
"""Retry with exponential backoff — async port of web/src/server/llm/retry.ts."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")

DEFAULT_MAX_RETRIES = 2
DEFAULT_BASE_DELAY_MS = 250
DEFAULT_MAX_DELAY_MS = 2_000

_TRANSIENT_UNIX_CODES = frozenset({
    "ECONNRESET",
    "ECONNREFUSED",
    "EHOSTUNREACH",
    "ENETUNREACH",
    "ETIMEDOUT",
    "EAI_AGAIN",
})


@dataclass(frozen=True)
class RetryOptions:
    max_retries: int = DEFAULT_MAX_RETRIES
    base_delay_ms: int = DEFAULT_BASE_DELAY_MS
    max_delay_ms: int = DEFAULT_MAX_DELAY_MS
    should_retry: Callable[[BaseException], bool] | None = None


@dataclass(frozen=True)
class RetryResult(Generic[T]):
    value: T
    retry_count: int


class RetryExhaustedError(Exception):
    """Wraps the final cause after retries are exhausted."""

    def __init__(self, cause: BaseException, retry_count: int) -> None:
        super().__init__(str(cause))
        self.cause = cause
        self.retry_count = retry_count


async def with_retry(
    operation: Callable[[], Awaitable[T]],
    options: RetryOptions | None = None,
) -> RetryResult[T]:
    opts = options or RetryOptions()
    should_retry = opts.should_retry or is_transient_network_error
    retry_count = 0

    while True:
        try:
            value = await operation()
            return RetryResult(value=value, retry_count=retry_count)
        except BaseException as error:  # noqa: BLE001 — re-raised below
            if retry_count >= opts.max_retries or not should_retry(error):
                raise RetryExhaustedError(error, retry_count) from error

            delay_ms = min(opts.base_delay_ms * (2 ** retry_count), opts.max_delay_ms)
            retry_count += 1
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)


def is_transient_network_error(error: Any) -> bool:
    if isinstance(error, asyncio.TimeoutError):
        return True
    if getattr(error, "transient", False):
        return True
    if getattr(error, "retryable", False):
        return True

    status = getattr(error, "status", None)
    if status in (408, 429):
        return True
    if isinstance(status, int) and status >= 500:
        return True

    code = getattr(error, "code", None)
    if isinstance(code, str) and code in _TRANSIENT_UNIX_CODES:
        return True
    return False
```

- [ ] **Step 2.4: 跑测试,确认全过**

Run: `cd api && uv run pytest tests/llm/test_retry.py -v`
Expected: 8 个用例全 PASS。

- [ ] **Step 2.5: 提交**

```bash
git add api/app/llm/retry.py api/tests/llm/test_retry.py
git commit -m "feat(api): add llm retry with exponential backoff"
```

---

## Task 3 — `cost_logger.py`(jsonl 落盘)

**Files:**
- Create: `api/app/llm/cost_logger.py`
- Create: `api/tests/llm/test_cost_logger.py`

**TS reference:** `web/src/server/llm/costLogger.ts`(行 1-56)

**关键差异:** Python 端用 `asyncio.to_thread` + `pathlib.Path.write_text(append)` 避免 `aiofiles` 依赖。`log_cost` 异步且**异常自吞**(成本日志不能影响 LLM 主路径)。默认路径 `api/.data/llm-cost.jsonl`,可被 `LLM_COST_LOG_PATH` env 覆盖,以方便测试用 `tmp_path`。

- [ ] **Step 3.1: 写测试**

写到 `api/tests/llm/test_cost_logger.py`:

```python
"""Mirror of web/src/server/llm/costLogger behaviour."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.llm.cost_logger import (
    LLMCostLogEntry,
    create_cost_log_entry,
    estimate_token_count,
    log_cost,
)


# ---------- estimate_token_count ----------

def test_estimate_token_count_for_empty_string() -> None:
    assert estimate_token_count("") == 0
    assert estimate_token_count("   ") == 0


def test_estimate_token_count_for_short_text() -> None:
    # ceil(len/4), min 1
    assert estimate_token_count("hi") == 1
    assert estimate_token_count("hello world") == 3  # ceil(11/4)=3


# ---------- create_cost_log_entry ----------

def test_create_entry_populates_token_estimates_and_metadata() -> None:
    entry = create_cost_log_entry(
        label="unit.test",
        system="sys",
        user="hi there",
        completion='{"ok":true}',
        duration_ms=42,
        success=True,
        failure=None,
        retry_count=0,
    )
    assert isinstance(entry, LLMCostLogEntry)
    assert entry.label == "unit.test"
    assert entry.success is True
    assert entry.failure is None
    assert entry.retry_count == 0
    assert entry.duration_ms == 42
    assert entry.prompt_tokens_estimate >= 1
    assert entry.completion_tokens_estimate >= 1
    assert entry.timestamp.endswith("Z") or "+" in entry.timestamp


# ---------- log_cost (async, append-only jsonl) ----------

async def test_log_cost_appends_jsonl(tmp_path: Path) -> None:
    target = tmp_path / "llm-cost.jsonl"
    entry = create_cost_log_entry(
        label="L",
        system="",
        user="",
        completion="",
        duration_ms=1,
        success=True,
        failure=None,
        retry_count=0,
    )

    await log_cost(entry, file_path=target)
    await log_cost(entry, file_path=target)

    lines = target.read_text("utf-8").splitlines()
    assert len(lines) == 2
    parsed = json.loads(lines[0])
    assert parsed["label"] == "L"
    assert parsed["success"] is True


async def test_log_cost_swallows_io_failure(tmp_path: Path) -> None:
    # Path is a directory — append should fail; log_cost must not raise.
    bad = tmp_path / "is-a-dir"
    bad.mkdir()
    entry = create_cost_log_entry(
        label="L", system="", user="", completion="",
        duration_ms=1, success=True, failure=None, retry_count=0,
    )
    await log_cost(entry, file_path=bad)  # no exception expected


async def test_log_cost_creates_parent_dir(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "deep" / "llm-cost.jsonl"
    entry = create_cost_log_entry(
        label="L", system="", user="", completion="",
        duration_ms=1, success=True, failure=None, retry_count=0,
    )
    await log_cost(entry, file_path=target)
    assert target.exists()


# ---------- env override ----------

def test_default_path_uses_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.llm.cost_logger import default_cost_log_path
    monkeypatch.setenv("LLM_COST_LOG_PATH", str(tmp_path / "x.jsonl"))
    assert default_cost_log_path() == tmp_path / "x.jsonl"
```

- [ ] **Step 3.2: 跑测试,确认全失败**

Run: `cd api && uv run pytest tests/llm/test_cost_logger.py -v`

- [ ] **Step 3.3: 实现 `cost_logger.py`**

写到 `api/app/llm/cost_logger.py`:

```python
"""LLM cost logger — async append to .data/llm-cost.jsonl.

Estimates tokens by character count (matches web/src/server/llm/costLogger.ts).
Failures are swallowed: cost logging must never affect the user-facing LLM call.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

DEFAULT_COST_LOG_FILENAME = "llm-cost.jsonl"
DEFAULT_DATA_DIR = Path(".data")


@dataclass(frozen=True)
class LLMCostLogEntry:
    timestamp: str
    label: str
    prompt_tokens_estimate: int
    completion_tokens_estimate: int
    duration_ms: int
    success: bool
    failure: str | None
    retry_count: int


LLMCostLogger = Callable[[LLMCostLogEntry], Awaitable[None]]


def estimate_token_count(text: str) -> int:
    trimmed = text.strip()
    if not trimmed:
        return 0
    return max(1, math.ceil(len(trimmed) / 4))


def create_cost_log_entry(
    *,
    label: str,
    system: str,
    user: str,
    completion: str,
    duration_ms: int,
    success: bool,
    failure: str | None,
    retry_count: int,
) -> LLMCostLogEntry:
    return LLMCostLogEntry(
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        label=label,
        prompt_tokens_estimate=estimate_token_count(f"{system}\n\n{user}"),
        completion_tokens_estimate=estimate_token_count(completion),
        duration_ms=duration_ms,
        success=success,
        failure=failure,
        retry_count=retry_count,
    )


def default_cost_log_path() -> Path:
    override = os.environ.get("LLM_COST_LOG_PATH")
    if override:
        return Path(override)
    return DEFAULT_DATA_DIR / DEFAULT_COST_LOG_FILENAME


async def log_cost(
    entry: LLMCostLogEntry,
    *,
    file_path: Path | None = None,
) -> None:
    target = file_path or default_cost_log_path()
    payload = json.dumps(asdict(entry), ensure_ascii=False) + "\n"
    try:
        await asyncio.to_thread(_append_sync, target, payload)
    except Exception:  # noqa: BLE001 — cost logging must never raise
        return


def _append_sync(target: Path, payload: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(payload)
```

- [ ] **Step 3.4: 跑测试,确认全过**

Run: `cd api && uv run pytest tests/llm/test_cost_logger.py -v`

- [ ] **Step 3.5: 提交**

```bash
git add api/app/llm/cost_logger.py api/tests/llm/test_cost_logger.py
git commit -m "feat(api): add llm cost_logger ported from web costLogger.ts"
```

---

## Task 4 — `client.py`(`generate_structured` 门面 + GeminiLLMProvider)

**Files:**
- Create: `api/app/llm/client.py`
- Create: `api/tests/llm/test_client.py`

**TS reference:** `web/src/server/llm/client.ts`(行 1-328)、`web/src/server/llm/client.test.ts`(行 1-135)

**设计要点:**
1. `LLMProvider` 是 `typing.Protocol`,有一个方法 `async def generate(*, system: str, user: str, timeout_ms: int) -> str`(用 timeout_ms 而非 AbortSignal,Python 风格)。
2. `GeminiLLMProvider` 用 `google.genai.Client().aio.models.generate_content`,把 `system_instruction + user content + response_mime_type=application/json` 拼好,返回 `response.text`。Timeout 由 `asyncio.wait_for` 套在外层。
3. `generate_structured` 是公开门面,签名:
   ```python
   async def generate_structured[M: BaseModel](
       *,
       system: str,
       user: str,
       schema: type[M],
       label: str,
       timeout_ms: int = 30_000,
       provider: LLMProvider | None = None,
       cost_logger: LLMCostLogger | None = None,
       retry: RetryOptions | None = None,
   ) -> M
   ```
4. 流程严格照搬 TS:
   - 如果 `provider` 为 None,用 `create_default_provider()` 读 env;
   - 用 `with_retry(...)` 包 `asyncio.wait_for(provider.generate(...), timeout)`;
   - 拿到 raw 文本后先 `json.loads`,失败再走 `parse_json_with_repair`,都失败抛 `LLMJsonParseError`;
   - 用 `schema.model_validate(parsed)` 做最终校验;
   - 不论成功失败,**finally 内** 异步 `log_cost` 并吞掉 logger 异常。

- [ ] **Step 4.1: 写测试(只用 fixture provider,不打真 SDK)**

写到 `api/tests/llm/test_client.py`:

```python
"""Mirror of web/src/server/llm/client.test.ts.

Uses an in-memory FakeProvider so no real Gemini call is made.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable

import pytest
from pydantic import BaseModel, ConfigDict

from app.llm.client import (
    LLMConfigurationError,
    LLMJsonParseError,
    LLMProvider,
    LLMTimeoutError,
    generate_structured,
)
from app.llm.cost_logger import LLMCostLogEntry
from app.llm.retry import RetryOptions


class _Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str


# ---------- helpers ----------

@dataclass
class FakeProvider:
    """Provider stub with scripted responses or behaviour callable."""

    handler: Callable[..., Awaitable[str]]
    calls: list[dict] = field(default_factory=list)

    async def generate(self, *, system: str, user: str, timeout_ms: int) -> str:
        self.calls.append({"system": system, "user": user, "timeout_ms": timeout_ms})
        return await self.handler(system=system, user=user, timeout_ms=timeout_ms)


def _capturing_logger(sink: list[LLMCostLogEntry]):
    async def _log(entry: LLMCostLogEntry) -> None:
        sink.append(entry)
    return _log


# ---------- success path ----------

async def test_returns_validated_pydantic_model_and_logs_cost() -> None:
    entries: list[LLMCostLogEntry] = []

    async def ok(**_: object) -> str:
        return '{"message":"hello"}'

    result = await generate_structured(
        system="You return JSON.",
        user="Say hello.",
        schema=_Output,
        label="unit.success",
        provider=FakeProvider(handler=ok),
        cost_logger=_capturing_logger(entries),
        retry=RetryOptions(base_delay_ms=0),
    )

    assert result == _Output(message="hello")
    assert len(entries) == 1
    assert entries[0].label == "unit.success"
    assert entries[0].success is True
    assert entries[0].retry_count == 0
    assert entries[0].prompt_tokens_estimate > 0
    assert entries[0].completion_tokens_estimate > 0


# ---------- json repair path ----------

async def test_repairs_malformed_json_before_schema_validation() -> None:
    async def messy(**_: object) -> str:
        return 'Sure:\n{"message":"hello",}\n'

    result = await generate_structured(
        system="s", user="u", schema=_Output, label="unit.repair",
        provider=FakeProvider(handler=messy),
        cost_logger=_capturing_logger([]),
        retry=RetryOptions(base_delay_ms=0),
    )
    assert result.message == "hello"


async def test_raises_llm_json_parse_error_when_unrecoverable() -> None:
    async def bad(**_: object) -> str:
        return "this is not json at all"

    with pytest.raises(LLMJsonParseError):
        await generate_structured(
            system="s", user="u", schema=_Output, label="unit.parse_fail",
            provider=FakeProvider(handler=bad),
            cost_logger=_capturing_logger([]),
            retry=RetryOptions(base_delay_ms=0),
        )


# ---------- retry path ----------

async def test_retries_transient_then_succeeds_and_records_retry_count() -> None:
    entries: list[LLMCostLogEntry] = []
    state = {"calls": 0}

    async def flaky(**_: object) -> str:
        state["calls"] += 1
        if state["calls"] == 1:
            err = ConnectionError("flaky")
            err.transient = True  # type: ignore[attr-defined]
            raise err
        return '{"message":"recovered"}'

    result = await generate_structured(
        system="s", user="u", schema=_Output, label="unit.retry",
        provider=FakeProvider(handler=flaky),
        cost_logger=_capturing_logger(entries),
        retry=RetryOptions(base_delay_ms=0),
    )
    assert result.message == "recovered"
    assert state["calls"] == 2
    assert entries[0].success is True
    assert entries[0].retry_count == 1


# ---------- timeout path ----------

async def test_enforces_configured_timeout() -> None:
    async def hang(**_: object) -> str:
        await asyncio.sleep(10)
        return ""

    with pytest.raises(LLMTimeoutError):
        await generate_structured(
            system="s", user="u", schema=_Output, label="unit.timeout",
            provider=FakeProvider(handler=hang),
            cost_logger=_capturing_logger([]),
            retry=RetryOptions(base_delay_ms=0, max_retries=0),
            timeout_ms=20,
        )


# ---------- cost logger isolation ----------

async def test_does_not_fail_when_cost_logger_raises() -> None:
    async def ok(**_: object) -> str:
        return '{"message":"hello"}'

    async def bad_logger(_entry: LLMCostLogEntry) -> None:
        raise RuntimeError("disk full")

    result = await generate_structured(
        system="s", user="u", schema=_Output, label="unit.logging_failure",
        provider=FakeProvider(handler=ok),
        cost_logger=bad_logger,
        retry=RetryOptions(base_delay_ms=0),
    )
    assert result.message == "hello"


# ---------- failure logging ----------

async def test_logs_failure_when_retries_exhausted() -> None:
    entries: list[LLMCostLogEntry] = []

    async def always_fail(**_: object) -> str:
        err = ConnectionError("always")
        err.transient = True  # type: ignore[attr-defined]
        raise err

    with pytest.raises(ConnectionError):
        await generate_structured(
            system="s", user="u", schema=_Output, label="unit.exhaust",
            provider=FakeProvider(handler=always_fail),
            cost_logger=_capturing_logger(entries),
            retry=RetryOptions(base_delay_ms=0, max_retries=1),
        )

    assert len(entries) == 1
    assert entries[0].success is False
    assert entries[0].failure is not None
    assert entries[0].retry_count == 1


# ---------- default provider config error ----------

async def test_default_provider_raises_config_error_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER_API_KEY", raising=False)

    from app.llm.client import create_default_provider

    with pytest.raises(LLMConfigurationError):
        create_default_provider(env={})
```

- [ ] **Step 4.2: 跑测试,确认全失败**

Run: `cd api && uv run pytest tests/llm/test_client.py -v`
Expected: ImportError。

- [ ] **Step 4.3: 实现 `client.py`**

写到 `api/app/llm/client.py`:

```python
"""LLM client facade — async port of web/src/server/llm/client.ts.

Public entry point: `generate_structured(...)`. All node code in Plan 5
must call this and never bypass to GeminiLLMProvider directly.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Mapping, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.cost_logger import (
    LLMCostLogEntry,
    LLMCostLogger,
    create_cost_log_entry,
    log_cost,
)
from app.llm.json_repair import JsonRepairError, parse_json_with_repair
from app.llm.retry import (
    RetryExhaustedError,
    RetryOptions,
    with_retry,
)

DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

M = TypeVar("M", bound=BaseModel)


# ---------- Errors ----------

class LLMConfigurationError(Exception):
    """API key missing or model misconfigured."""


class LLMAuthError(Exception):
    """401/403 from provider — not retryable."""


class LLMNetworkError(Exception):
    """Transient network or provider error — retryable."""

    transient = True
    retryable = True

    def __init__(self, message: str, *, status: int | None = None, cause: object | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.cause = cause


class LLMProviderError(Exception):
    """Non-retryable HTTP error returned by the provider."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class LLMTimeoutError(Exception):
    def __init__(self, timeout_ms: int) -> None:
        super().__init__(f"LLM call timed out after {timeout_ms}ms")
        self.timeout_ms = timeout_ms


class LLMJsonParseError(Exception):
    def __init__(self, message: str, *, cause: object) -> None:
        super().__init__(message)
        self.cause = cause


# ---------- Provider Protocol ----------

class LLMProvider(Protocol):
    async def generate(self, *, system: str, user: str, timeout_ms: int) -> str: ...


# ---------- Public facade ----------

async def generate_structured(
    *,
    system: str,
    user: str,
    schema: type[M],
    label: str,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    provider: LLMProvider | None = None,
    cost_logger: LLMCostLogger | None = None,
    retry: RetryOptions | None = None,
) -> M:
    chosen_provider = provider or create_default_provider()
    started = time.perf_counter()
    completion = ""
    retry_count = 0
    success = False
    failure: str | None = None

    try:
        async def _call() -> str:
            return await _with_timeout(
                chosen_provider.generate(system=system, user=user, timeout_ms=timeout_ms),
                timeout_ms=timeout_ms,
            )

        result = await with_retry(_call, retry)
        completion = result.value
        retry_count = result.retry_count

        parsed = _parse_llm_json(completion)
        try:
            validated = schema.model_validate(parsed)
        except ValidationError as ve:
            raise LLMJsonParseError("LLM JSON failed schema validation", cause=ve) from ve

        success = True
        return validated
    except RetryExhaustedError as exhausted:
        retry_count = exhausted.retry_count
        failure = str(exhausted.cause)
        raise exhausted.cause  # noqa: B904 — surface original cause to caller
    except Exception as e:
        failure = str(e)
        raise
    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)
        entry = create_cost_log_entry(
            label=label,
            system=system,
            user=user,
            completion=completion,
            duration_ms=duration_ms,
            success=success,
            failure=failure,
            retry_count=retry_count,
        )
        await _safe_log(cost_logger or log_cost, entry)


# ---------- Default provider ----------

def create_default_provider(env: Mapping[str, str] | None = None) -> LLMProvider:
    env = env if env is not None else os.environ
    api_key = read_api_key(env)
    model = env.get("LLM_PROVIDER_MODEL") or env.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    return GeminiLLMProvider(api_key=api_key, model=model)


def read_api_key(env: Mapping[str, str] | None = None) -> str:
    env = env if env is not None else os.environ
    api_key = env.get("LLM_PROVIDER_API_KEY") or env.get("GEMINI_API_KEY")
    if not api_key:
        raise LLMConfigurationError("LLM_PROVIDER_API_KEY is not configured")
    return api_key


# ---------- GeminiLLMProvider ----------

class GeminiLLMProvider:
    def __init__(self, *, api_key: str, model: str = DEFAULT_GEMINI_MODEL) -> None:
        self._api_key = api_key
        self._model = model

    async def generate(self, *, system: str, user: str, timeout_ms: int) -> str:
        # Lazy import — keeps unit tests free of SDK imports unless explicitly used.
        from google import genai
        from google.genai import errors as genai_errors
        from google.genai import types as genai_types

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
        except Exception as e:  # network failure, DNS, etc.
            raise LLMNetworkError("LLM provider network failure", cause=e) from e

        text = (response.text or "").strip()
        if not text:
            raise LLMProviderError("LLM provider returned no text")
        return text


# ---------- helpers ----------

async def _with_timeout(awaitable, *, timeout_ms: int):
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_ms / 1000)
    except asyncio.TimeoutError as e:
        raise LLMTimeoutError(timeout_ms) from e


def _parse_llm_json(raw: str) -> object:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as initial:
        try:
            return parse_json_with_repair(raw)
        except (JsonRepairError, json.JSONDecodeError) as repair:
            raise LLMJsonParseError(
                "LLM returned invalid JSON",
                cause={"initial": str(initial), "repair": str(repair)},
            ) from repair


async def _safe_log(logger: LLMCostLogger, entry: LLMCostLogEntry) -> None:
    try:
        await logger(entry)
    except Exception:  # noqa: BLE001
        return
```

- [ ] **Step 4.4: 跑测试,确认全过**

Run: `cd api && uv run pytest tests/llm/test_client.py -v`
Expected: 8 个用例全 PASS。

**Self-review checklist:** 如果失败,逐项核对:
- `LLMTimeoutError` 是不是从 `_with_timeout` 抛出且没被 `with_retry` 默认 `should_retry` 视作 transient(它没有 transient/retryable/status 标记,默认就不会重试,符合 TS 行为)
- `RetryExhaustedError` 在最外层 `except` 中被正确解包,把 `cause` 重新抛给调用方
- `cost_logger` 抛异常时 `_safe_log` 必须吞掉
- 测试中的 `FakeProvider.handler` 用 `**_: object` 是为了忽略 system/user/timeout_ms 三个 kw 参数

- [ ] **Step 4.5: 跑全套基线**

Run: `cd api && uv run pytest -v`
Expected: 66(老) + 8(json_repair) + 8(retry) + 6(cost_logger) + 8(client) = 96 个全绿。

- [ ] **Step 4.6: 提交**

```bash
git add api/app/llm/client.py api/tests/llm/test_client.py
git commit -m "feat(api): add llm generate_structured facade with Gemini provider"
```

---

## Task 5 — 收尾(`__init__.py` 公开 API + 烟测)

**Files:**
- Modify: `api/app/llm/__init__.py`
- Create: `api/scripts/smoke_llm.py`

- [ ] **Step 5.1: 写 `api/app/llm/__init__.py`**

```python
"""Async LLM client — port of web/src/server/llm/."""

from app.llm.client import (
    GeminiLLMProvider,
    LLMAuthError,
    LLMConfigurationError,
    LLMJsonParseError,
    LLMNetworkError,
    LLMProvider,
    LLMProviderError,
    LLMTimeoutError,
    create_default_provider,
    generate_structured,
    read_api_key,
)
from app.llm.cost_logger import (
    LLMCostLogEntry,
    LLMCostLogger,
    create_cost_log_entry,
    default_cost_log_path,
    estimate_token_count,
    log_cost,
)
from app.llm.json_repair import (
    JsonRepairError,
    extract_json_candidate,
    parse_json_with_repair,
    repair_json,
)
from app.llm.retry import (
    RetryExhaustedError,
    RetryOptions,
    RetryResult,
    is_transient_network_error,
    with_retry,
)

__all__ = [
    # client
    "GeminiLLMProvider",
    "LLMAuthError",
    "LLMConfigurationError",
    "LLMJsonParseError",
    "LLMNetworkError",
    "LLMProvider",
    "LLMProviderError",
    "LLMTimeoutError",
    "create_default_provider",
    "generate_structured",
    "read_api_key",
    # cost_logger
    "LLMCostLogEntry",
    "LLMCostLogger",
    "create_cost_log_entry",
    "default_cost_log_path",
    "estimate_token_count",
    "log_cost",
    # json_repair
    "JsonRepairError",
    "extract_json_candidate",
    "parse_json_with_repair",
    "repair_json",
    # retry
    "RetryExhaustedError",
    "RetryOptions",
    "RetryResult",
    "is_transient_network_error",
    "with_retry",
]
```

- [ ] **Step 5.2: 写烟测脚本 `api/scripts/smoke_llm.py`**

```python
"""Smoke test: real Gemini call returning a structured object.

Usage:
    cd api && uv run python scripts/smoke_llm.py

Requires GEMINI_API_KEY (or LLM_PROVIDER_API_KEY) in env.
This is NOT run in pytest — it hits the real API and costs money/quota.
"""
from __future__ import annotations

import asyncio
import os
import sys

from pydantic import BaseModel, ConfigDict, Field

from app.llm import generate_structured


class CityHint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    city: str = Field(description="The city the user is asking about")
    country_code: str = Field(description="ISO-3166 alpha-2 code, uppercase")


async def main() -> int:
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("LLM_PROVIDER_API_KEY")):
        print("[smoke] skipped: no GEMINI_API_KEY in env", file=sys.stderr)
        return 0

    result = await generate_structured(
        system="You return strict JSON matching the requested schema.",
        user='Return JSON for: {"city":"Shanghai"}. Include the ISO country code.',
        schema=CityHint,
        label="smoke.city_hint",
    )
    print(f"[smoke] OK city={result.city} country={result.country_code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
```

- [ ] **Step 5.3: 跑全套测试**

Run: `cd api && uv run pytest -v`
Expected: 96 全绿。

- [ ] **Step 5.4: lint 检查**

Run: `cd api && uv run python -m compileall app/llm tests/llm scripts/smoke_llm.py`
Expected: 无 SyntaxError。

Run: `cd api && uv run ruff check app/llm tests/llm scripts/smoke_llm.py`
Expected: All checks passed。如果有 noqa 抱怨,确认每个 `# noqa: BLE001` 都有对应说明。

- [ ] **Step 5.5: (可选)烟测真实 SDK**

如果本地 `.env` 有 `GEMINI_API_KEY`:

```bash
cd api && uv run python scripts/smoke_llm.py
```

Expected: 打印 `[smoke] OK city=Shanghai country=CN`。如果 SDK 报错,先确认 `gemini-2.5-flash` 模型可用,再确认 `response.text` 字段存在;不影响本子计划 DoD(纯 unit 测试已绿)。

- [ ] **Step 5.6: 总验收 — Plan 2 DoD 对账**

确认以下条件全部成立:

1. `api/app/llm/{__init__,client,retry,json_repair,cost_logger}.py` 全部存在
2. `api/tests/llm/test_*.py` 4 个测试文件全部存在
3. `cd api && uv run pytest tests/llm -v` 全绿(预期 30 个用例:8+8+6+8)
4. `cd api && uv run pytest -v` 全绿(预期 96 个)
5. `cd api && uv run ruff check app/llm tests/llm` 通过
6. `api/app/services/gemini.py` 仍在(由 Plan 6 删路由后一起删)
7. `api/scripts/smoke_llm.py` 存在,在无 API key 时打印 skipped 退出 0
8. `web/src/server/llm/*.ts` 没动(由 Plan 7 删除)

- [ ] **Step 5.7: 提交收尾**

```bash
git add api/app/llm/__init__.py api/scripts/smoke_llm.py
git commit -m "feat(api): expose llm package public surface and add smoke script"
```

- [ ] **Step 5.8: 推送(可选)**

```bash
git push origin feature/mvp-web-app
```

---

## Self-Review 备忘

实施过程中如果遇到以下场景,按提示调整:

| 场景 | 处理 |
|---|---|
| `pytest` 报 `RuntimeError: no running event loop` | 确认 `pyproject.toml` 里 `asyncio_mode = "auto"` 已开;或在测试函数前加 `@pytest.mark.asyncio` |
| `with_retry` 把 `LLMTimeoutError` 当 transient 重试 | 检查 `is_transient_network_error` — Timeout 没有 `transient/retryable/status` 标记,不应被重试。本计划的实现里 `asyncio.TimeoutError` 视作 transient,但客户端把它包成 `LLMTimeoutError`(非 transient),所以最外层 retry 不会再吃掉它 |
| Gemini SDK 报 `400 INVALID_ARGUMENT: response_mime_type` | 个别老版本 SDK 不支持,可在 `GenerateContentConfig` 里去掉这行,client 端依然会用 `parse_json_with_repair` 兜底 |
| `cost_logger` 测试创建嵌套目录失败 | `mkdir(parents=True, exist_ok=True)` 已经在 `_append_sync` 里了,确认没被吞错误吞掉 |
| `LLMJsonParseError` 测试把它视作 transient 重试 | 它不是 `BaseException` 的 transient 标记类型,默认 `should_retry` 返回 False,只会立刻抛 |
| Type checker 警告 `M` 泛型在 `generate_structured` 返回处不解析 | Python 3.12 PEP 695 新写法 `[M: BaseModel]` 已支持;如果 IDE 不识别,改写成 `M = TypeVar("M", bound=BaseModel)` 也一样 |

## 不做的事(Out of Scope,留给后续 Plan)

- ❌ 不动 `web/src/server/llm/`(Plan 7 一起删)
- ❌ 不动 `api/app/services/gemini.py`(Plan 6 删路由后一起清)
- ❌ 不接 LangGraph 节点(Plan 5)
- ❌ 不写 streaming token 接口(MVP 后再考虑)
- ❌ 不引 `aiofiles` 依赖(用 `asyncio.to_thread` 包同步 IO)
- ❌ 不写真实 Gemini 集成测试(只在 Step 5.5 烟测,且不进 pytest)
