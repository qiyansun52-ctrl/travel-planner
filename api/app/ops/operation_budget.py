from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Literal

OperationName = Literal["discovery", "itinerary", "adjustment"]


class OperationBudgetExceeded(RuntimeError):
    def __init__(self, session_id: str, operation: OperationName, limit: int) -> None:
        super().__init__(
            f"Operation budget exceeded for {operation}: {limit} per session"
        )
        self.session_id = session_id
        self.operation = operation
        self.limit = limit


@dataclass
class SessionOperationBudget:
    default_limits: dict[OperationName, int]
    _counts: dict[tuple[str, OperationName], int] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def consume(self, session_id: str, operation: OperationName) -> None:
        limit = self.default_limits[operation]
        key = (session_id, operation)
        with self._lock:
            current = self._counts.get(key, 0)
            if current >= limit:
                raise OperationBudgetExceeded(session_id, operation, limit)
            self._counts[key] = current + 1

    def snapshot(self, session_id: str) -> dict[OperationName, int]:
        with self._lock:
            return {
                operation: self._counts.get((session_id, operation), 0)
                for operation in self.default_limits
            }
