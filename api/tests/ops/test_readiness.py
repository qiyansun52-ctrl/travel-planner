from __future__ import annotations

import pytest

from app.config import Settings
from app.ops.readiness import (
    ProductionReadinessError,
    assert_production_ready,
    redacted_env_status,
)


def _settings(**overrides: object) -> Settings:
    values = {
        "gemini_api_key": "real-gemini-key",
        "tavily_api_key": "real-tavily-key",
        "gemini_model": "gemini-2.5-flash",
        "environment": "production",
        "cors_origins": "https://travel.example.com",
        "e2e_fixture_mode": False,
        "session_data_dir": "/var/lib/travel-planner",
        "metrics_data_dir": "/var/log/travel-planner",
        "rate_limit_enabled": True,
        "rate_limit_max_requests": 30,
        "rate_limit_window_seconds": 60,
        "max_discovery_runs_per_session": 3,
        "max_itinerary_runs_per_session": 4,
        "max_adjustments_per_session": 8,
        "host": "0.0.0.0",
        "port": 8000,
    }
    values.update(overrides)
    return Settings(**values)


def test_production_ready_accepts_safe_settings() -> None:
    assert_production_ready(_settings())


def test_production_ready_rejects_fixture_mode() -> None:
    with pytest.raises(ProductionReadinessError, match="E2E_FIXTURE_MODE"):
        assert_production_ready(_settings(e2e_fixture_mode=True))


def test_production_ready_rejects_placeholder_secrets() -> None:
    with pytest.raises(ProductionReadinessError, match="GEMINI_API_KEY"):
        assert_production_ready(_settings(gemini_api_key="test-gemini"))


@pytest.mark.parametrize(
    ("field", "key", "secret_value"),
    [
        ("gemini_api_key", "GEMINI_API_KEY", "placeholder"),
        ("gemini_api_key", "GEMINI_API_KEY", "dummy-key"),
        ("tavily_api_key", "TAVILY_API_KEY", "fake-token"),
        ("tavily_api_key", "TAVILY_API_KEY", "your_api_key_here"),
    ],
)
def test_production_ready_rejects_common_placeholder_secrets(
    field: str,
    key: str,
    secret_value: str,
) -> None:
    with pytest.raises(ProductionReadinessError, match=key):
        assert_production_ready(_settings(**{field: secret_value}))


def test_production_ready_rejects_localhost_cors() -> None:
    with pytest.raises(ProductionReadinessError, match="CORS_ORIGINS"):
        assert_production_ready(_settings(cors_origins="http://localhost:3000"))


@pytest.mark.parametrize("cors_origins", ["*", "http://[::1]:3000"])
def test_production_ready_rejects_non_explicit_or_loopback_cors(
    cors_origins: str,
) -> None:
    with pytest.raises(ProductionReadinessError, match="CORS_ORIGINS"):
        assert_production_ready(_settings(cors_origins=cors_origins))


@pytest.mark.parametrize(
    ("field", "key", "data_dir"),
    [
        ("session_data_dir", "SESSION_DATA_DIR", "./.data"),
        ("session_data_dir", "SESSION_DATA_DIR", ".data/"),
        ("metrics_data_dir", "METRICS_DATA_DIR", "api/.data"),
    ],
)
def test_production_ready_rejects_equivalent_dev_data_dirs(
    field: str,
    key: str,
    data_dir: str,
) -> None:
    with pytest.raises(ProductionReadinessError, match=key):
        assert_production_ready(_settings(**{field: data_dir}))


def test_redacted_env_status_never_exposes_secret_values() -> None:
    status = redacted_env_status(
        _settings(gemini_api_key="abc123456789", tavily_api_key="tvly-secret")
    )

    assert status["environment"] == "production"
    assert status["fixture_mode"] is False
    assert status["secrets"]["GEMINI_API_KEY"] == "set"
    assert status["secrets"]["TAVILY_API_KEY"] == "set"
    assert "abc123456789" not in repr(status)
    assert "tvly-secret" not in repr(status)
