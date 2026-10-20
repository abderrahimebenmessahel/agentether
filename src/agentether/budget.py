"""Budget accounting.

A budget is a hard limit on what a run may spend.  When a limit is hit the
supervisor stops with :class:`~agentether.exceptions.BudgetExceededError`:
retrying would only spend more of the budget that is already gone.

Token and cost accounting is driven by the optional ``usage`` field a worker
may return, or by a pluggable ``token_counter``.  The default counter is a
character heuristic -- an approximation, not a tokenizer.

.. versionadded:: 0.2.0
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .exceptions import BudgetExceededError
from .models import Usage
from .policy import BudgetPolicy

__all__ = ["BudgetTracker"]


@dataclass
class BudgetTracker:
    """Tracks the resources used by one orchestrator run.

    Attributes:
        policy: The budget policy in use.
        clock: Monotonic clock used for the time budget.  Injectable so that
            tests do not have to sleep.
    """

    policy: BudgetPolicy = field(default_factory=BudgetPolicy)
    clock: Callable[[], float] = lambda: 0.0
    _started_at: float | None = field(default=None, init=False, repr=False)
    _restored_elapsed: float = field(default=0.0, init=False, repr=False)
    attempts: int = field(default=0, init=False)
    tokens: int = field(default=0, init=False)
    cost: float = field(default=0.0, init=False)

    def start(self) -> None:
        """Start the clock.  Called once when the orchestrator is created."""
        if self._started_at is None:
            self._started_at = self.clock()

    def restore(self, snapshot: Mapping[str, Any]) -> None:
        """Restore the counters of an earlier run from the project memory.

        The budgets are *global per project*, not per process: a run that was
        interrupted and started again continues to spend the same budget.
        The elapsed time of the earlier run is added to the elapsed time of
        this one.

        Args:
            snapshot: The ``budget`` section of the state file.
        """
        self.attempts = int(snapshot.get("attempts", 0) or 0)
        self.tokens = int(snapshot.get("tokens", 0) or 0)
        self.cost = float(snapshot.get("cost", 0.0) or 0.0)
        self._restored_elapsed = float(snapshot.get("elapsed_seconds", 0.0) or 0.0)

    @property
    def elapsed_seconds(self) -> float:
        """Seconds spent in this run plus the restored ones."""
        session = 0.0
        if self._started_at is not None:
            session = max(0.0, self.clock() - self._started_at)
        return self._restored_elapsed + session

    def estimate_tokens(self, text: str) -> int:
        """Estimate the tokens of ``text`` with the configured counter."""
        return int(self.policy.token_counter(text))

    def record_attempt(
        self,
        text: str = "",
        usage: Usage | None = None,
        tokens: int | None = None,
    ) -> int:
        """Account one finished attempt and return the tokens it cost.

        When the worker reported :class:`Usage`, its numbers win.  Otherwise
        the text is measured with the configured ``token_counter``.
        """
        self.attempts += 1
        if usage is not None:
            used = usage.total_tokens
            if usage.cost is not None:
                self.cost += float(usage.cost)
        elif tokens is not None:
            used = int(tokens)
        else:
            used = self.estimate_tokens(text)
        self.tokens += used
        return used

    def check(self) -> None:
        """Raise :class:`BudgetExceededError` if any budget is exhausted.

        Raises:
            BudgetExceededError: If one of the configured limits is reached.
        """
        policy = self.policy
        elapsed = self.elapsed_seconds
        if policy.max_total_seconds is not None and elapsed >= policy.max_total_seconds:
            raise BudgetExceededError("seconds", policy.max_total_seconds, elapsed)
        if policy.max_total_attempts is not None and self.attempts >= policy.max_total_attempts:
            raise BudgetExceededError("attempts", policy.max_total_attempts, self.attempts)
        if policy.max_total_tokens is not None and self.tokens >= policy.max_total_tokens:
            raise BudgetExceededError("tokens", policy.max_total_tokens, self.tokens)
        if policy.max_total_cost is not None and self.cost >= policy.max_total_cost:
            raise BudgetExceededError("cost", policy.max_total_cost, self.cost)

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serialisable snapshot of the budget usage."""
        return {
            "elapsed_seconds": round(self.elapsed_seconds, 6),
            "attempts": self.attempts,
            "tokens": self.tokens,
            "cost": round(self.cost, 8),
            "limits": {
                "max_total_seconds": self.policy.max_total_seconds,
                "max_total_attempts": self.policy.max_total_attempts,
                "max_total_tokens": self.policy.max_total_tokens,
                "max_total_cost": self.policy.max_total_cost,
            },
        }
