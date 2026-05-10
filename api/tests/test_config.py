from __future__ import annotations

import os

from app.config import Settings, load_environment


def test_settings_accepts_shared_env_file_keys(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "GEMINI_API_KEY=test-gemini",
                "TAVILY_API_KEY=test-tavily",
                "GEMINI_MODEL=gemini-2.5-flash",
                "ENVIRONMENT=development",
                "AMAP_API_KEY=test-amap",
                "MAPBOX_ACCESS_TOKEN=test-mapbox",
                "SESSION_DATA_DIR=.data",
                "METRICS_DATA_DIR=.data",
                "CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000",
                "E2E_FIXTURE_MODE=0",
                "RATE_LIMIT_ENABLED=1",
                "RATE_LIMIT_MAX_REQUESTS=60",
                "RATE_LIMIT_WINDOW_SECONDS=60",
                "MAX_DISCOVERY_RUNS_PER_SESSION=3",
                "MAX_ITINERARY_RUNS_PER_SESSION=4",
                "MAX_ADJUSTMENTS_PER_SESSION=8",
                "HOST=127.0.0.1",
                "PORT=8000",
            ]
        ),
        encoding="utf-8",
    )
    for key in (
        "GEMINI_API_KEY",
        "TAVILY_API_KEY",
        "GEMINI_MODEL",
        "ENVIRONMENT",
        "CORS_ORIGINS",
        "E2E_FIXTURE_MODE",
        "SESSION_DATA_DIR",
        "METRICS_DATA_DIR",
        "RATE_LIMIT_ENABLED",
        "RATE_LIMIT_MAX_REQUESTS",
        "RATE_LIMIT_WINDOW_SECONDS",
        "MAX_DISCOVERY_RUNS_PER_SESSION",
        "MAX_ITINERARY_RUNS_PER_SESSION",
        "MAX_ADJUSTMENTS_PER_SESSION",
        "HOST",
        "PORT",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=env_file)

    assert settings.gemini_api_key == "test-gemini"
    assert settings.tavily_api_key == "test-tavily"
    assert settings.environment == "development"
    assert settings.e2e_fixture_mode is False
    assert settings.session_data_dir == ".data"
    assert settings.metrics_data_dir == ".data"
    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    assert settings.rate_limit_enabled is True
    assert settings.rate_limit_max_requests == 60
    assert settings.rate_limit_window_seconds == 60
    assert settings.max_discovery_runs_per_session == 3
    assert settings.max_itinerary_runs_per_session == 4
    assert settings.max_adjustments_per_session == 8


def test_load_environment_populates_process_env_for_direct_consumers(
    tmp_path,
    monkeypatch,
):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "GEMINI_API_KEY=loaded-gemini",
                "TAVILY_API_KEY=loaded-tavily",
                "E2E_FIXTURE_MODE=0",
                "SESSION_DATA_DIR=/tmp/travel-planner-sessions",
                "METRICS_DATA_DIR=/tmp/travel-planner-metrics",
            ]
        ),
        encoding="utf-8",
    )
    for key in (
        "GEMINI_API_KEY",
        "TAVILY_API_KEY",
        "E2E_FIXTURE_MODE",
        "SESSION_DATA_DIR",
        "METRICS_DATA_DIR",
    ):
        monkeypatch.delenv(key, raising=False)

    assert load_environment(env_file) is True
    assert os.environ["GEMINI_API_KEY"] == "loaded-gemini"
    assert os.environ["TAVILY_API_KEY"] == "loaded-tavily"
    assert os.environ["E2E_FIXTURE_MODE"] == "0"
    assert os.environ["SESSION_DATA_DIR"] == "/tmp/travel-planner-sessions"
    assert os.environ["METRICS_DATA_DIR"] == "/tmp/travel-planner-metrics"
