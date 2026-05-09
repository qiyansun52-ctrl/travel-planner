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
                "AMAP_API_KEY=test-amap",
                "MAPBOX_ACCESS_TOKEN=test-mapbox",
                "SESSION_DATA_DIR=.data",
                "METRICS_DATA_DIR=.data",
                "CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000",
                "E2E_FIXTURE_MODE=0",
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
        "CORS_ORIGINS",
        "HOST",
        "PORT",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=env_file)

    assert settings.gemini_api_key == "test-gemini"
    assert settings.tavily_api_key == "test-tavily"
    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


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
