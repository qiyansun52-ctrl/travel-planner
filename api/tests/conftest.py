from __future__ import annotations

import pytest

_REAL_PROVIDER_ENV_KEYS = (
    "AMAP_API_KEY",
    "E2E_FIXTURE_MODE",
    "GEMINI_API_KEY",
    "LLM_COST_LOG_PATH",
    "LLM_PROVIDER_API_KEY",
    "MAPBOX_ACCESS_TOKEN",
    "METRICS_DATA_DIR",
    "SESSION_DATA_DIR",
    "TAVILY_API_KEY",
)


@pytest.fixture(autouse=True)
def isolate_real_provider_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _REAL_PROVIDER_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
