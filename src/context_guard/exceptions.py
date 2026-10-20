"""Exception hierarchy for ContextGuard.

Every error raised by the library derives from :class:`ContextGuardError`, so a
caller can catch the whole family with a single ``except`` clause::

    try:
        await research()
    except ContextGuardError as exc:
        log.warning("step failed: %s", exc)

Each exception carries structured attributes (not just a message) so that a
supervisor can make decisions programmatically without parsing strings.

.. versionchanged:: 0.2.0
   ``CircuitBreakerOpenError`` is a plain class again.  The dynamically created
   dual-typed error of v0.1 has been removed; see ``CHANGELOG.md``.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

__all__ = [
    "AgentExecutionError",
    "AgentTimeoutError",
    "BudgetExceededError",
    "CircuitBreakerOpenError",
    "ConfigurationError",
    "ContextDriftError",
    "ContextGuardError",
    "FailureKind",
    "LoopDetectedError",
    "StateCorruptionError",
    "TelemetryParseError",
    "VerificationFailedError",
]

#: Raw LLM output longer than this is never embedded in an exception message.
MAX_EXCERPT_CHARS = 500


class FailureKind(str, Enum):
    """The kind of failure that made an attempt fail.

    Used by the attempt log, the circuit breaker and the event stream so that
    a failure can be classified without parsing human readable messages.
    """

    TIMEOUT = "timeout"
    PARSE_ERROR = "parse_error"
    DRIFT = "drift"
    EXECUTION_ERROR = "execution_error"
    VERIFICATION_FAILED = "verification_failed"
    LOOP_DETECTED = "loop_detected"
    STALL_DETECTED = "stall_detected"
    IN_PROGRESS = "in_progress"
    BUDGET_EXCEEDED = "budget_exceeded"
    AGENT_BLOCKED = "agent_blocked"
    AGENT_FAILED = "agent_failed"

    def __str__(self) -> str:
        return self.value


class ContextGuardError(Exception):
    """Base class for every error raised by ContextGuard."""


class ConfigurationError(ContextGuardError):
    """Raised when the supervisor is set up with invalid arguments.

    This is a programming error, not a runtime failure of the agent: it is
    raised eagerly from ``AutoOrchestrator.__init__`` and is never retried.
    """


class AgentTimeoutError(ContextGuardError):
    """Raised when the wrapped agent call exceeded its time budget.

    Attributes:
        step: Name of the step that timed out.
        timeout_seconds: The configured budget that was exceeded.
    """

    def __init__(self, step: str, timeout_seconds: float) -> None:
        self.step = step
        self.timeout_seconds = timeout_seconds
        Exception.__init__(self, f"Step '{step}' timed out after {timeout_seconds}s")


class TelemetryParseError(ContextGuardError):
    """Raised when the agent output does not contain usable telemetry.

    Attributes:
        step: Name of the step whose output could not be parsed.
        reason: Human readable explanation of what was wrong.
        raw_excerpt: A short excerpt of the offending output (truncated to
            :data:`MAX_EXCERPT_CHARS` characters).
    """

    def __init__(self, step: str, reason: str, raw_excerpt: str = "") -> None:
        self.step = step
        self.reason = reason
        self.raw_excerpt = raw_excerpt[:MAX_EXCERPT_CHARS]
        message = f"Could not parse telemetry for step '{step}': {reason}"
        if self.raw_excerpt:
            message = f"{message} | excerpt: {self.raw_excerpt!r}"
        Exception.__init__(self, message)


class ContextDriftError(ContextGuardError):
    """Raised when the agent's answer does not line up with the plan.

    Two flavours exist, distinguished by :attr:`retryable`:

    * *in-step drift* -- the agent reported the wrong step name, an unknown
      status, an incomplete progress value or a wrong ``next_step``. This is
      usually worth another attempt, so ``retryable`` is ``True``.
    * *roadmap violation* -- the caller asked for a step that is not in the
      roadmap, or asked for a step whose predecessors are not finished. These
      are programming errors and are never retried (``retryable`` is ``False``).

    Attributes:
        step: Name of the step involved.
        expected: What the supervisor expected (a step name or a description).
        observed: What the agent or caller actually provided.
        reason: Human readable explanation.
        retryable: Whether the supervisor may retry the step.
    """

    def __init__(
        self,
        step: str,
        expected: object,
        observed: object,
        reason: str,
        *,
        retryable: bool = False,
    ) -> None:
        self.step = step
        self.expected = expected
        self.observed = observed
        self.reason = reason
        self.retryable = retryable
        Exception.__init__(
            self,
            f"Context drift at step '{step}': {reason} "
            f"(expected={expected!r}, observed={observed!r})",
        )


class AgentExecutionError(ContextGuardError):
    """Wraps an exception raised by the developer's worker function.

    The original exception is kept both as :attr:`original` and as the
    exception's ``__cause__`` (``raise ... from exc``), so nothing is lost.

    Attributes:
        step: Name of the step that failed.
        original: The exception raised by the wrapped function.
    """

    def __init__(self, step: str, original: BaseException) -> None:
        self.step = step
        self.original = original
        Exception.__init__(self, f"Step '{step}' failed with {type(original).__name__}: {original}")


class VerificationFailedError(ContextGuardError):
    """Raised when an independent verifier rejected the agent's claim.

    The reason is injected into the next attempt as a corrective hint, so the
    agent learns *why* the claim was rejected instead of retrying blindly.

    Attributes:
        step: Name of the step that was verified.
        reason: Why the verification failed.
        evidence: Structured evidence collected by the verifier.
    """

    def __init__(self, step: str, reason: str, evidence: dict[str, Any] | None = None) -> None:
        self.step = step
        self.reason = reason
        self.evidence: dict[str, Any] = dict(evidence or {})
        Exception.__init__(self, f"Verification failed for step '{step}': {reason}")


class LoopDetectedError(ContextGuardError):
    """Raised when the agent keeps producing near-identical output.

    Attributes:
        step: Name of the step that is looping.
        reason: Human readable explanation of the detection.
        similarity: Similarity of the offending outputs (0.0 - 1.0).
        window: Number of attempts that were compared.
    """

    def __init__(
        self,
        step: str,
        reason: str,
        similarity: float = 0.0,
        window: int = 0,
    ) -> None:
        self.step = step
        self.reason = reason
        self.similarity = similarity
        self.window = window
        Exception.__init__(
            self,
            f"Loop detected in step '{step}': {reason} "
            f"(similarity={similarity:.2f}, window={window})",
        )


class BudgetExceededError(ContextGuardError):
    """Raised when a configured budget is exhausted.

    A budget violation is never retried: retrying would only spend more of
    the budget that is already gone.  The state stays resumable.

    Attributes:
        kind: Which budget was exhausted (``seconds``, ``attempts``,
            ``tokens`` or ``cost``).
        limit: The configured limit.
        used: How much was used when the limit was hit.
    """

    def __init__(self, kind: str, limit: float, used: float) -> None:
        self.kind = kind
        self.limit = limit
        self.used = used
        Exception.__init__(
            self,
            f"Budget '{kind}' exceeded: limit {limit} reached (used {used})",
        )


class CircuitBreakerOpenError(ContextGuardError):
    """Raised when the circuit breaker is open and a step is attempted.

    The breaker is persisted in the project memory, so it survives process
    restarts -- that is what stops an agent from looping forever across
    restarts.

    Attributes:
        step: Name of the step that opened the breaker.
        attempts: Number of failed attempts that opened the breaker.
        reason: The kind of the final failure (``FailureKind`` value).
        last_error: The corrective hint / error message from the last attempt.
    """

    def __init__(
        self,
        step: str,
        attempts: int,
        reason: str = "",
        last_error: str | None = None,
    ) -> None:
        self.step = step
        self.attempts = attempts
        self.reason = reason
        self.last_error = last_error
        Exception.__init__(
            self,
            f"Circuit breaker is open for step '{step}' after {attempts} attempts "
            f"(reason={reason}, last error: {last_error})",
        )


class StateCorruptionError(ContextGuardError):
    """Raised when the on-disk project memory cannot be trusted.

    ContextGuard never silently resets a corrupted state file: doing so would
    throw away the plan the agent already executed, which is exactly the kind
    of drift this library exists to prevent.

    The message points at ``contextguard doctor`` and at the ``.bak`` file that
    is written before an automatic migration.
    """
