from __future__ import annotations

import pytest

from app.ops.operation_budget import (
    OperationBudgetExceeded,
    SessionOperationBudget,
)


def test_session_operation_budget_allows_until_limit() -> None:
    budget = SessionOperationBudget(default_limits={"discovery": 2})

    budget.consume("session_1", "discovery")
    budget.consume("session_1", "discovery")


def test_session_operation_budget_rejects_over_limit() -> None:
    budget = SessionOperationBudget(default_limits={"discovery": 1})

    budget.consume("session_1", "discovery")

    with pytest.raises(OperationBudgetExceeded, match="discovery"):
        budget.consume("session_1", "discovery")


def test_session_operation_budget_is_per_session() -> None:
    budget = SessionOperationBudget(default_limits={"itinerary": 1})

    budget.consume("session_1", "itinerary")
    budget.consume("session_2", "itinerary")


def test_session_operation_budget_snapshot_returns_session_counts() -> None:
    budget = SessionOperationBudget(
        default_limits={"discovery": 2, "itinerary": 1, "adjustment": 1}
    )

    budget.consume("session_1", "discovery")
    budget.consume("session_1", "itinerary")
    budget.consume("session_2", "discovery")

    assert budget.snapshot("session_1") == {
        "discovery": 1,
        "itinerary": 1,
        "adjustment": 0,
    }
