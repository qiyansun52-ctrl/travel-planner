"""Mirror of web/src/server/llm/costLogger behaviour."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.llm.cost_logger import (
    LLMCostLogEntry,
    create_cost_log_entry,
    default_cost_log_path,
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
    # Path is a directory -- append should fail; log_cost must not raise.
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

def test_default_path_uses_env_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LLM_COST_LOG_PATH", str(tmp_path / "x.jsonl"))
    assert default_cost_log_path() == tmp_path / "x.jsonl"


def test_default_path_uses_metrics_dir_without_cost_log_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("LLM_COST_LOG_PATH", raising=False)
    monkeypatch.setenv("METRICS_DATA_DIR", str(tmp_path / "metrics"))

    assert default_cost_log_path() == tmp_path / "metrics" / "llm-cost.jsonl"
