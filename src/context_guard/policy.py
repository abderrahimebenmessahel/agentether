"""Configuration objects for the supervisor.

Everything the orchestrator can be tuned with lives in one frozen
:class:`GuardPolicy`.  The flat constructor arguments of v0.1
(``timeout_seconds``, ``max_retries``, ``backoff_base``, ...) keep working and
are mapped onto the policy by :meth:`AutoOrchestrator.__init__`.

.. versionadded:: 0.2.0
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Final

from .exceptions import (
    AgentExecutionError,
    AgentTimeoutError,
    BudgetExceededError,
    ConfigurationError,
    ContextDriftError,
    LoopDetectedError,
    StateCorruptionError,
    TelemetryParseError,
    VerificationFailedError,
)

__all__ = [
    "BreakerPolicy",
    "BudgetPolicy",
    "GuardPolicy",
    "LoopPolicy",
    "RetryPolicy",
    "StallPolicy",
    "approximate_token_count",
]


def approximate_token_count(text: str) -> int:
    """Estimate the number of tokens in ``text``.

    The default estimator is a character-count heuristic: roughly four
    characters per token for English text.  It is an **approximation**, not a
    tokenizer, and it is wrong for code, CJK text and JSON.  Supply your own
    ``token_counter`` (for example a real tokenizer) when accuracy matters.
    """
    return max(1, len(text) // 4) if text else 0


@dataclass(frozen=True)
class LoopPolicy:
    """Semantic loop detection.

    The agent's answer is normalised (lowercased, whitespace collapsed,
    numbers / ids / timestamps masked) and hashed into shingles.  Two answers
    are similar when the Jaccard similarity of their shingle sets is at least
    ``similarity_threshold``.

    Attributes:
        enabled: Whether loop detection runs at all.
        similarity_threshold: Minimum similarity to call two answers alike.
        repeat_window: How many consecutive similar attempts trip the loop.
        shingle_size: Number of words per shingle.
        max_retries_after_detection: How many extra attempts the agent gets
            after a loop was detected (with a strong corrective hint) before
            the circuit breaker trips.
    """

    enabled: bool = True
    similarity_threshold: float = 0.9
    repeat_window: int = 3
    shingle_size: int = 5
    max_retries_after_detection: int = 1

    def __post_init__(self) -> None:
        if not 0.0 < self.similarity_threshold <= 1.0:
            raise ConfigurationError(
                "loop.similarity_threshold must be in (0.0, 1.0], "
                f"got {self.similarity_threshold!r}"
            )
        if self.repeat_window < 2:
            raise ConfigurationError(f"loop.repeat_window must be >= 2, got {self.repeat_window!r}")
        if self.max_retries_after_detection < 0:
            raise ConfigurationError("loop.max_retries_after_detection must be >= 0")


@dataclass(frozen=True)
class StallPolicy:
    """Stall detection for steps that keep reporting ``in_progress``.

    Attributes:
        enabled: Whether stall detection runs at all.
        stall_window: How many consecutive non-progressing attempts trip the
            stall.
        require_progress: A stall needs a lack of strict progress increase.
        require_artifacts: A stall also needs no new artifacts.
    """

    enabled: bool = True
    stall_window: int = 3
    require_progress: bool = True
    require_artifacts: bool = True

    def __post_init__(self) -> None:
        if self.stall_window < 2:
            raise ConfigurationError(f"stall.stall_window must be >= 2, got {self.stall_window!r}")


@dataclass(frozen=True)
class BudgetPolicy:
    """Global budgets for one orchestrator.

    All limits are optional; ``None`` means "no limit".

    Attributes:
        max_total_seconds: Wall clock budget for the whole run.
        max_total_attempts: Total number of attempts across all steps.
        max_total_tokens: Total token budget (input + output).
        max_total_cost: Total monetary budget.
        token_counter: Callable that estimates the tokens of a text.  Defaults
            to :func:`approximate_token_count`.
    """

    max_total_seconds: float | None = None
    max_total_attempts: int | None = None
    max_total_tokens: int | None = None
    max_total_cost: float | None = None
    token_counter: Callable[[str], int] = approximate_token_count

    def __post_init__(self) -> None:
        limits = (
            "max_total_seconds",
            "max_total_attempts",
            "max_total_tokens",
            "max_total_cost",
        )
        for name in limits:
            value = getattr(self, name)
            if value is not None and value <= 0:
                raise ConfigurationError(f"{name} must be > 0, got {value!r}")


#: Failures that are retried by default.
DEFAULT_RETRY_ON: Final[tuple[type[BaseException], ...]] = (
    AgentTimeoutError,
    TelemetryParseError,
    ContextDriftError,
    AgentExecutionError,
    VerificationFailedError,
    LoopDetectedError,
)

#: Failures that are never retried.
DEFAULT_NO_RETRY_ON: Final[tuple[type[BaseException], ...]] = (
    ConfigurationError,
    StateCorruptionError,
    BudgetExceededError,
)


@dataclass(frozen=True)
class RetryPolicy:
    """How often and how a failed attempt is repeated.

    Attributes:
        max_attempts: Total attempts per step (including the first one).
        backoff_base: Base of the exponential backoff.
        backoff_max: Upper bound of a single backoff delay.
        retry_on: Exception classes that may be retried.
        no_retry_on: Exception classes that are never retried.  A class listed
            here wins over ``retry_on``.
    """

    max_attempts: int = 3
    backoff_base: float = 1.0
    backoff_max: float = 30.0
    retry_on: tuple[type[BaseException], ...] = DEFAULT_RETRY_ON
    no_retry_on: tuple[type[BaseException], ...] = DEFAULT_NO_RETRY_ON

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ConfigurationError(f"retry.max_attempts must be >= 1, got {self.max_attempts!r}")
        if self.backoff_base < 0:
            raise ConfigurationError("retry.backoff_base must be >= 0")
        if self.backoff_max <= 0:
            raise ConfigurationError("retry.backoff_max must be > 0")

    def is_retryable(self, error: BaseException) -> bool:
        """Return whether ``error`` may be retried.

        ``no_retry_on`` always wins, then explicit ``retry_on``, then the
        default behaviour: only the exception classes in ``retry_on`` are
        retried.
        """
        if isinstance(error, self.no_retry_on):
            return False
        return isinstance(error, self.retry_on)


@dataclass(frozen=True)
class BreakerPolicy:
    """Circuit breaker configuration.

    Attributes:
        enabled: Whether the breaker is used at all.
        cooldown_seconds: When set, the breaker moves to *half open* after
            this many seconds and allows exactly one trial attempt.  ``None``
            keeps the breaker open until :meth:`AutoOrchestrator.reset_breaker`
            is called.
    """

    enabled: bool = True
    cooldown_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.cooldown_seconds is not None and self.cooldown_seconds < 0:
            raise ConfigurationError("breaker.cooldown_seconds must be >= 0")


@dataclass(frozen=True)
class GuardPolicy:
    """The complete configuration of an orchestrator.

    Attributes:
        strict_order: A step may only run once all previous roadmap steps are
            completed.
        strict_next_step: A mismatching ``next_step`` is an error instead of
            a warning.
        resume: Steps that are already recorded as completed are not executed
            again; their cached result is returned.
        loop: Semantic loop detection.
        stall: Stall detection.
        budget: Global budgets.
        retry: Retry classification and backoff.
        breaker: Circuit breaker.
        verification_enabled: Whether verifiers run at all.
        verify_timeout_seconds: Per-verifier timeout.
        store_raw_outputs: Whether the attempt log keeps the full output
            instead of only its length and hash.
        events_enabled: Whether events are written to ``events.jsonl``.
        events_max_bytes: Size at which ``events.jsonl`` is rotated.
        workdir: Directory the agent works in.  ``None`` means "the current
            working directory".
    """

    strict_order: bool = True
    strict_next_step: bool = False
    resume: bool = True
    loop: LoopPolicy = field(default_factory=LoopPolicy)
    stall: StallPolicy = field(default_factory=StallPolicy)
    budget: BudgetPolicy = field(default_factory=BudgetPolicy)
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    breaker: BreakerPolicy = field(default_factory=BreakerPolicy)
    verification_enabled: bool = True
    verify_timeout_seconds: float = 30.0
    store_raw_outputs: bool = False
    events_enabled: bool = True
    events_max_bytes: int = 5 * 1024 * 1024
    workdir: str | None = None
