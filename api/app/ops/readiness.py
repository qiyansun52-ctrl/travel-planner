from __future__ import annotations

from urllib.parse import urlparse

from app.config import Settings

SECRET_KEYS = ("GEMINI_API_KEY", "TAVILY_API_KEY")
PLACEHOLDER_PREFIXES = ("test-", "fixture-", "example-", "changeme", "your-")
PLACEHOLDER_MARKERS = (
    "placeholder",
    "dummy",
    "fake",
    "your_api_key",
    "your_api_token",
)
LOCAL_CORS_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0", "::1")


class ProductionReadinessError(RuntimeError):
    """Raised when production mode contains unsafe settings."""


def assert_production_ready(settings: Settings) -> None:
    if settings.environment != "production":
        return

    failures: list[str] = []
    if settings.e2e_fixture_mode:
        failures.append("E2E_FIXTURE_MODE must be 0 in production")
    _check_secret("GEMINI_API_KEY", settings.gemini_api_key, failures)
    _check_secret("TAVILY_API_KEY", settings.tavily_api_key, failures)
    _check_cors(settings.cors_origin_list, failures)
    if settings.rate_limit_enabled is False:
        failures.append("RATE_LIMIT_ENABLED must be enabled in production")
    _check_data_dir("SESSION_DATA_DIR", settings.session_data_dir, failures)
    _check_data_dir("METRICS_DATA_DIR", settings.metrics_data_dir, failures)

    if failures:
        raise ProductionReadinessError("; ".join(failures))


def redacted_env_status(settings: Settings) -> dict[str, object]:
    return {
        "environment": settings.environment,
        "fixture_mode": settings.e2e_fixture_mode,
        "cors_origin_count": len(settings.cors_origin_list),
        "rate_limit_enabled": settings.rate_limit_enabled,
        "budgets": {
            "discovery": settings.max_discovery_runs_per_session,
            "itinerary": settings.max_itinerary_runs_per_session,
            "adjustment": settings.max_adjustments_per_session,
        },
        "secrets": {
            "GEMINI_API_KEY": _secret_status(settings.gemini_api_key),
            "TAVILY_API_KEY": _secret_status(settings.tavily_api_key),
        },
    }


def _check_secret(key: str, value: str, failures: list[str]) -> None:
    stripped = value.strip()
    if not stripped:
        failures.append(f"{key} must be configured")
        return
    lowered = stripped.lower()
    if _is_placeholder_secret(lowered):
        failures.append(f"{key} must not use a placeholder value")


def _check_cors(origins: list[str], failures: list[str]) -> None:
    if not origins:
        failures.append("CORS_ORIGINS must include the production web origin")
        return
    unsafe = [
        origin
        for origin in origins
        if _is_unsafe_production_origin(origin)
    ]
    if unsafe:
        failures.append(
            "CORS_ORIGINS must include explicit non-local origins in production"
        )


def _secret_status(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return "missing"
    lowered = stripped.lower()
    if _is_placeholder_secret(lowered):
        return "placeholder"
    return "set"


def _is_placeholder_secret(lowered_value: str) -> bool:
    normalized = lowered_value.replace("-", "_").replace(" ", "_")
    return any(
        (
            lowered_value.startswith(prefix)
            for prefix in PLACEHOLDER_PREFIXES
        )
    ) or any(marker in normalized for marker in PLACEHOLDER_MARKERS)


def _is_unsafe_production_origin(origin: str) -> bool:
    lowered = origin.strip().lower()
    if "*" in lowered:
        return True

    parsed = urlparse(lowered)
    if not parsed.scheme or not parsed.hostname:
        return True

    hostname = parsed.hostname.rstrip(".")
    return hostname in LOCAL_CORS_HOSTS or hostname.endswith(".localhost")


def _check_data_dir(key: str, value: str, failures: list[str]) -> None:
    stripped = value.strip()
    if not stripped or _is_dev_data_dir(stripped):
        failures.append(f"{key} should be an explicit production path")


def _is_dev_data_dir(value: str) -> bool:
    normalized = value.replace("\\", "/").rstrip("/")
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    return bool(parts) and parts[-1] == ".data"
