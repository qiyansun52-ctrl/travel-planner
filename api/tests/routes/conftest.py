from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import httpx
import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def isolated_route_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("METRICS_DATA_DIR", str(tmp_path / "metrics"))
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily")
    monkeypatch.setenv("E2E_FIXTURE_MODE", "1")
    monkeypatch.setenv("MAX_DISCOVERY_RUNS_PER_SESSION", "3")
    monkeypatch.setenv("MAX_ITINERARY_RUNS_PER_SESSION", "4")
    monkeypatch.setenv("MAX_ADJUSTMENTS_PER_SESSION", "8")
    get_settings.cache_clear()
    _reset_operation_budget()
    yield
    _reset_operation_budget()
    get_settings.cache_clear()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as async_client:
        yield async_client


def _reset_operation_budget() -> None:
    from app.routes import _shared

    _shared._OPERATION_BUDGET = None
