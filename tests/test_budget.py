"""Tests for the budget accounting."""

from __future__ import annotations

import pytest

from context_guard import BudgetExceededError, BudgetPolicy, BudgetTracker, Usage
from context_guard.policy import approximate_token_count


def test_approximate_token_count_is_documented_as_an_approximation() -> None:
    assert approximate_token_count("") == 0
    assert approximate_token_count("abcd") == 1
    assert approximate_token_count("a" * 400) == 100


def test_tracker_counts_attempts_and_tokens() -> None:
    tracker = BudgetTracker(policy=BudgetPolicy(token_counter=lambda text: len(text)))
    tracker.start()
    tracker.record_attempt(text="abc")
    tracker.record_attempt(text="de")
    assert tracker.attempts == 2
    assert tracker.tokens == 5


def test_tracker_prefers_reported_usage() -> None:
    tracker = BudgetTracker(policy=BudgetPolicy(token_counter=lambda text: 9999))
    tracker.start()
    tracker.record_attempt(text="abc", usage=Usage(input_tokens=10, output_tokens=5))
    assert tracker.tokens == 15


def test_tracker_adds_the_cost() -> None:
    tracker = BudgetTracker(policy=BudgetPolicy())
    tracker.start()
    tracker.record_attempt(text="x", usage=Usage(cost=0.25))
    tracker.record_attempt(text="x", usage=Usage(cost=0.75))
    assert tracker.cost == pytest.approx(1.0)


def test_attempt_budget_is_enforced() -> None:
    tracker = BudgetTracker(policy=BudgetPolicy(max_total_attempts=2))
    tracker.start()
    tracker.record_attempt(text="x")
    tracker.check()
    tracker.record_attempt(text="x")
    with pytest.raises(BudgetExceededError) as excinfo:
        tracker.check()
    assert excinfo.value.kind == "attempts"
    assert excinfo.value.limit == 2


def test_token_budget_is_enforced() -> None:
    tracker = BudgetTracker(policy=BudgetPolicy(max_total_tokens=10, token_counter=len))
    tracker.start()
    tracker.record_attempt(text="12345")
    tracker.check()
    tracker.record_attempt(text="67890")
    with pytest.raises(BudgetExceededError) as excinfo:
        tracker.check()
    assert excinfo.value.kind == "tokens"


def test_cost_budget_is_enforced() -> None:
    tracker = BudgetTracker(policy=BudgetPolicy(max_total_cost=1.0))
    tracker.start()
    tracker.record_attempt(text="x", usage=Usage(cost=0.5))
    tracker.check()
    tracker.record_attempt(text="x", usage=Usage(cost=0.75))
    with pytest.raises(BudgetExceededError) as excinfo:
        tracker.check()
    assert excinfo.value.kind == "cost"


def test_time_budget_is_enforced() -> None:
    now = [0.0]

    def clock() -> float:
        return now[0]

    tracker = BudgetTracker(policy=BudgetPolicy(max_total_seconds=10.0), clock=clock)
    tracker.start()
    tracker.check()
    now[0] = 11.0
    with pytest.raises(BudgetExceededError) as excinfo:
        tracker.check()
    assert excinfo.value.kind == "seconds"


def test_snapshot_is_serialisable() -> None:
    tracker = BudgetTracker(policy=BudgetPolicy(max_total_tokens=100))
    tracker.start()
    tracker.record_attempt(text="abcd")
    snapshot = tracker.snapshot()
    assert snapshot["attempts"] == 1
    assert snapshot["limits"]["max_total_tokens"] == 100
