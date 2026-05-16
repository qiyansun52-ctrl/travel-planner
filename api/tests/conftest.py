from __future__ import annotations

import pytest

_REAL_PROVIDER_ENV_KEYS = (
    "AMAP_API_KEY",
    "AMAP_MCP_URL",
    "E2E_FIXTURE_MODE",
    "ENVIRONMENT",
    "GEMINI_API_KEY",
    "LLM_COST_LOG_PATH",
    "LLM_PROVIDER_API_KEY",
    "MAPBOX_ACCESS_TOKEN",
    "MAX_ADJUSTMENTS_PER_SESSION",
    "MAX_DISCOVERY_RUNS_PER_SESSION",
    "MAX_ITINERARY_RUNS_PER_SESSION",
    "METRICS_DATA_DIR",
    "RATE_LIMIT_ENABLED",
    "RATE_LIMIT_MAX_REQUESTS",
    "RATE_LIMIT_WINDOW_SECONDS",
    "SESSION_DATA_DIR",
    "TAVILY_API_KEY",
)


@pytest.fixture(autouse=True)
def isolate_real_provider_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _REAL_PROVIDER_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
