from __future__ import annotations

import importlib
import sys
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.config import get_settings
from app.ops.readiness import ProductionReadinessError
from app.ops.rate_limit import InMemoryRateLimiter, RateLimitMiddleware


def test_rate_limiter_allows_requests_under_limit() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)

    assert limiter.allow("client", now=100.0) is True
    assert limiter.allow("client", now=101.0) is True


def test_rate_limiter_blocks_requests_over_limit() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)

    assert limiter.allow("client", now=100.0) is True
    assert limiter.allow("client", now=101.0) is True
    assert limiter.allow("client", now=102.0) is False


def test_rate_limiter_expires_old_entries() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=10)

    assert limiter.allow("client", now=100.0) is True
    assert limiter.allow("client", now=101.0) is True
    assert limiter.allow("client", now=111.1) is True


def test_rate_limiter_rejects_new_keys_when_key_cap_is_reached() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60, max_keys=1)

    assert limiter.allow("client-a", now=100.0) is True
    assert limiter.allow("client-b", now=101.0) is False
    assert set(limiter._hits) == {"client-a"}


async def test_rate_limit_middleware_returns_429_after_limit() -> None:
    app = FastAPI()
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
    app.add_middleware(RateLimitMiddleware, limiter=limiter, enabled=True)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "yes"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/ping")
        second = await client.get("/ping")

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json() == {"detail": "Rate limit exceeded"}
    assert second.headers["Retry-After"] == "60"


async def test_rate_limit_middleware_bypasses_options_without_consuming_quota() -> None:
    app = FastAPI()
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
    app.add_middleware(RateLimitMiddleware, limiter=limiter, enabled=True)

    @app.options("/ping")
    async def options_ping() -> dict[str, str]:
        return {"ok": "preflight"}

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "yes"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first_options = await client.options("/ping")
        second_options = await client.options("/ping")
        first_get = await client.get("/ping")
        second_get = await client.get("/ping")

    assert first_options.status_code == 200
    assert second_options.status_code == 200
    assert first_get.status_code == 200
    assert second_get.status_code == 429


async def test_rate_limit_middleware_bypasses_health() -> None:
    app = FastAPI()
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
    app.add_middleware(RateLimitMiddleware, limiter=limiter, enabled=True)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "yes"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first_health = await client.get("/health")
        second_health = await client.get("/health")
        first_ping = await client.get("/ping")
        second_ping = await client.get("/ping")

    assert first_health.status_code == 200
    assert second_health.status_code == 200
    assert first_ping.status_code == 200
    assert second_ping.status_code == 429


async def test_rate_limit_middleware_ignores_spoofed_x_forwarded_for() -> None:
    app = FastAPI()
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
    app.add_middleware(RateLimitMiddleware, limiter=limiter, enabled=True)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "yes"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/ping", headers={"X-Forwarded-For": "203.0.113.1"})
        second = await client.get("/ping", headers={"X-Forwarded-For": "203.0.113.2"})

    assert first.status_code == 200
    assert second.status_code == 429


def test_main_applies_production_readiness_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_main_env(tmp_path, monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "0")

    with pytest.raises(ProductionReadinessError, match="RATE_LIMIT_ENABLED"):
        _import_fresh_main()


async def test_main_installs_rate_limit_middleware_and_bypasses_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_main_env(tmp_path, monkeypatch)
    monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    main = _import_fresh_main()

    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        first_health = await client.get("/health")
        second_health = await client.get("/health")
        first_missing = await client.get("/__missing__")
        second_missing = await client.get("/__missing__")

    assert first_health.status_code == 200
    assert second_health.status_code == 200
    assert first_missing.status_code == 404
    assert second_missing.status_code == 429


async def test_main_rate_limit_429_includes_cors_headers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_main_env(tmp_path, monkeypatch)
    monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    main = _import_fresh_main()

    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        await client.get(
            "/__missing__",
            headers={"Origin": "https://travel.example.com"},
        )
        limited = await client.get(
            "/__missing__",
            headers={"Origin": "https://travel.example.com"},
        )

    assert limited.status_code == 429
    assert limited.headers["access-control-allow-origin"] == (
        "https://travel.example.com"
    )


async def test_main_disables_rate_limit_for_fixture_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_main_env(tmp_path, monkeypatch)
    monkeypatch.setenv("E2E_FIXTURE_MODE", "1")
    monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    main = _import_fresh_main()

    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        first_missing = await client.get("/__missing__")
        second_missing = await client.get("/__missing__")

    assert first_missing.status_code == 404
    assert second_missing.status_code == 404


def _configure_main_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "real-gemini-key")
    monkeypatch.setenv("TAVILY_API_KEY", "real-tavily-key")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CORS_ORIGINS", "https://travel.example.com")
    monkeypatch.setenv("E2E_FIXTURE_MODE", "0")
    monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("METRICS_DATA_DIR", str(tmp_path / "metrics"))
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "1")
    get_settings.cache_clear()


def _import_fresh_main():
    get_settings.cache_clear()
    sys.modules.pop("main", None)
    return importlib.import_module("main")
