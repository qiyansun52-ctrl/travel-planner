from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class InMemoryRateLimiter:
    max_requests: int
    window_seconds: int
    max_keys: int = 10_000
    _hits: dict[str, deque[float]] = field(default_factory=dict)

    def allow(self, key: str, *, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        self._prune_expired(current)

        if self.max_requests <= 0 or self.max_keys <= 0:
            return False

        hits = self._hits.get(key)
        if hits is None:
            if len(self._hits) >= self.max_keys:
                return False
            hits = deque()
            self._hits[key] = hits

        if len(hits) >= self.max_requests:
            return False

        hits.append(current)
        return True

    def _prune_expired(self, now: float) -> None:
        window_start = now - self.window_seconds
        for key, hits in list(self._hits.items()):
            while hits and hits[0] <= window_start:
                hits.popleft()
            if not hits:
                del self._hits[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: object,
        *,
        limiter: InMemoryRateLimiter,
        enabled: bool = True,
    ) -> None:
        super().__init__(app)
        self._limiter = limiter
        self._enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if (
            not self._enabled
            or request.url.path == "/health"
            or request.method == "OPTIONS"
        ):
            return await call_next(request)

        key = _client_key(request)
        if not self._limiter.allow(key):
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(self._limiter.window_seconds)},
            )

        return await call_next(request)


def _client_key(request: Request) -> str:
    if request.client is not None:
        return request.client.host
    return "unknown"
