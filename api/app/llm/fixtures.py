from __future__ import annotations

import os

FIXTURE_GEMINI_API_KEY = "test-gemini"
FIXTURE_TAVILY_API_KEY = "test-tavily"


def fixture_mode_enabled() -> bool:
    return os.environ.get("E2E_FIXTURE_MODE") == "1"
