"""The supervisor: deterministic control path around a single worker call.

``AutoOrchestrator`` owns the roadmap, the limits, the validation and the
persistence.  The developer's LLM function is the *data path*: it is called
with a :class:`~agentether.models.StepContext` and it returns the agent's
text (or a :class:`~agentether.models.WorkerOutput` with usage data).

Only one step is executed per decorated call.  The orchestrator is not a
multi-agent framework and does not spawn agents of its own.

.. versionchanged:: 0.2.0
    Added independent verification, semantic loop and stall detection,
    budgets, a half-open circuit breaker, event hooks and the explicit
    ``rerun()`` API (the magic ``force=True`` keyword is gone).
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import os
import random
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Concatenate, Generic, ParamSpec, Protocol, TypeAlias, TypeVar, cast

from .budget import BudgetTracker
from .events import EventBus, EventLog
from .exceptions import (
    AgentExecutionError,
    AgentTimeoutError,
    BudgetExceededError,
    CircuitBreakerOpenError,
    ConfigurationError,
    ContextDriftError,
    FailureKind,
    LoopDetectedError,
    StateCorruptionError,
    TelemetryParseError,
    VerificationFailedError,
)
from .logging_utils import logger
from .loop_detector import LoopDetector, StallDetector
from .models import (
    ALLOWED_STATUSES,
    StepContext,
    StepResult,
    Telemetry,
    Usage,
    Verifier,
    VerifyContext,
    VerifyResult,
    WorkerOutput,
)
from .parser import extract_json_telemetry
from .policy import GuardPolicy
from .state_manager import StateManager, sha256_text

__all__ = ["AutoOrchestrator", "GuardedStep", "StepFunction", "guard_step"]

P = ParamSpec("P")
# The worker returns the agent's raw text, so the return type is bound to
# ``str``.  The bound also lets type checkers infer the type variable when
# the worker is either synchronous or asynchronous.
R = TypeVar("R", bound=str)

#: A worker function: it receives the step context as its first argument and
#: returns either the raw agent text (or a
#: :class:`~agentether.models.WorkerOutput`) or an awaitable producing it.
StepFunction: TypeAlias = Callable[
    Concatenate[StepContext, P], "Awaitable[R | WorkerOutput] | R | WorkerOutput"
]


class GuardedStep(Protocol[P]):
    """The callable returned by :meth:`AutoOrchestrator.guard_step`.

    It behaves like the decorated worker (the supervisor injects the step
    context) and additionally offers :meth:`rerun`, which ignores the cached
    result and executes the step again.
    """

    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> StepResult: ...

    async def rerun(self, *args: P.args, **kwargs: P.kwargs) -> StepResult: ...


class _WorkerTimeout(Exception):
    """The worker itself raised a timeout.

    It is used to tell "the worker gave up" apart from "the supervisor gave
    up", without depending on the resolution of the clock.
    """

    def __init__(self, original: BaseException) -> None:
        super().__init__(str(original))
        self.original = original


@dataclass
class _Failure:
    """Internal description of a failed attempt.

    ``retryable`` overrides the class based policy when it is not ``None``.
    """

    exception: BaseException
    hint: str
    detail: str
    kind: FailureKind
    retryable: bool | None = None
    trip_breaker: bool = False


@dataclass
class _AttemptResult:
    """Internal result of a single attempt."""

    telemetry: Telemetry | None = None
    raw_output: str = ""
    usage: Usage | None = None
    failure: _Failure | None = None


class _GuardedStepImpl(Generic[P]):
    """Concrete :class:`GuardedStep` implementation."""

    def __init__(
        self,
        run: Callable[..., Awaitable[StepResult]],
        rerun: Callable[..., Awaitable[StepResult]],
    ) -> None:
        self._run = run
        self._rerun = rerun

    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> StepResult:
        return await self._run(*args, **kwargs)

    async def rerun(self, *args: P.args, **kwargs: P.kwargs) -> StepResult:
        return await self._rerun(*args, **kwargs)


class AutoOrchestrator:
    """Supervises a sequence of roadmap steps around one worker function.

    Args:
        roadmap: Ordered list of step names.  Must be non-empty, free of
            duplicates and contain only non-empty strings.
        memory_dir: Directory used for the durable project memory.
        timeout_seconds: Per-attempt time budget.  Must be positive.
        max_retries: **Total** number of attempts allowed per step (including
            the first one).  Must be at least 1.
        strict_order: When true (default) a step may only run once all
            previous roadmap steps are completed.
        strict_next_step: When true a mismatching ``next_step`` raises
            :class:`~agentether.exceptions.ContextDriftError` instead of
            only logging a warning.
        backoff_base: Base of the exponential backoff between attempts.
        backoff_max: Upper bound for a single backoff delay.
        resume: When true (default) steps that are already recorded in the
            project memory are not executed again; their cached result is
            returned instead.
        sleep: Injectable sleep function, used for the backoff.  Tests pass
            a recorder here so no real time is spent waiting.
        policy: The complete configuration.  The flat arguments above always
            win over the matching policy fields; everything else (loop,
            stall, budget, verification, events) comes from the policy.
        workdir: Directory the agent works in.  All paths from telemetry are
            resolved inside it.  Defaults to the current working directory.
        breaker_cooldown_seconds: When set, the breaker becomes half open
            after this delay and allows exactly one trial attempt.
        token_counter: Callable that estimates the tokens of a text.
        store_raw_outputs: Keep the full output in the attempt log instead of
            only its length and hash.
        events_enabled: Write ``events.jsonl`` and emit events.
        events_max_bytes: Size at which ``events.jsonl`` is rotated.
        clock: Monotonic clock used for budgets and the breaker cooldown.
            Injectable so that tests do not have to sleep.
        retry_on: Exception classes that may be retried.
        no_retry_on: Exception classes that are never retried.  A class listed
            here wins over ``retry_on``.

    Raises:
        ConfigurationError: If any argument is invalid.
    """

    def __init__(
        self,
        roadmap: list[str],
        memory_dir: str,
        timeout_seconds: float,
        max_retries: int,
        *,
        strict_order: bool | None = None,
        strict_next_step: bool | None = None,
        backoff_base: float | None = None,
        backoff_max: float | None = None,
        resume: bool | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
        policy: GuardPolicy | None = None,
        workdir: str | os.PathLike[str] | None = None,
        breaker_cooldown_seconds: float | None = None,
        token_counter: Callable[[str], int] | None = None,
        verify_timeout_seconds: float | None = None,
        store_raw_outputs: bool | None = None,
        events_enabled: bool | None = None,
        events_max_bytes: int | None = None,
        clock: Callable[[], float] | None = None,
        retry_on: tuple[type[BaseException], ...] | None = None,
        no_retry_on: tuple[type[BaseException], ...] | None = None,
    ) -> None:
        if policy is not None and not isinstance(policy, GuardPolicy):
            raise ConfigurationError(
                f"policy must be a GuardPolicy instance, got {type(policy).__name__}"
            )
        base_policy = policy or GuardPolicy()
        self._policy = self._merge_policy(
            base_policy,
            max_retries=max_retries,
            strict_order=strict_order,
            strict_next_step=strict_next_step,
            backoff_base=backoff_base,
            backoff_max=backoff_max,
            resume=resume,
            workdir=workdir,
            breaker_cooldown_seconds=breaker_cooldown_seconds,
            token_counter=token_counter,
            verify_timeout_seconds=verify_timeout_seconds,
            store_raw_outputs=store_raw_outputs,
            events_enabled=events_enabled,
            events_max_bytes=events_max_bytes,
            retry_on=retry_on,
            no_retry_on=no_retry_on,
        )
        self._roadmap = self._validate_roadmap(roadmap)
        self._index = {name: index for index, name in enumerate(self._roadmap)}
        self._timeout_seconds = self._validate_positive_number(timeout_seconds, "timeout_seconds")
        self._sleep: Callable[[float], Awaitable[None]] = sleep or asyncio.sleep
        self._clock: Callable[[], float] = clock or time.monotonic
        self._workdir = Path(self._policy.workdir or Path.cwd()).resolve()
        self._state = StateManager(
            memory_dir,
            token_counter=self._policy.budget.token_counter,
        )
        self._state.set_roadmap(self._roadmap)
        self._budget = BudgetTracker(policy=self._policy.budget, clock=self._clock)
        self._budget.start()
        self._loop_detector = LoopDetector(self._policy.loop)
        self._stall_detector = StallDetector(self._policy.stall)
        self._events = EventBus(enabled=self._policy.events_enabled)
        self._event_log = EventLog(
            self._state.memory_dir,
            max_bytes=self._policy.events_max_bytes,
            enabled=self._policy.events_enabled,
        )
        self._loop_retries: dict[str, int] = {}
        # One lock per step: two concurrent calls to the same step are
        # serialised, and the second one sees the cached result.
        self._step_locks: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Lock]] = {}
        self._budget_restored = False

    # ------------------------------------------------------------------
    # configuration
    # ------------------------------------------------------------------
    def _merge_policy(
        self,
        base: GuardPolicy,
        *,
        max_retries: int,
        strict_order: bool | None,
        strict_next_step: bool | None,
        backoff_base: float | None,
        backoff_max: float | None,
        resume: bool | None,
        workdir: str | os.PathLike[str] | None,
        breaker_cooldown_seconds: float | None,
        token_counter: Callable[[str], int] | None,
        verify_timeout_seconds: float | None,
        store_raw_outputs: bool | None,
        events_enabled: bool | None,
        events_max_bytes: int | None,
        retry_on: tuple[type[BaseException], ...] | None,
        no_retry_on: tuple[type[BaseException], ...] | None,
    ) -> GuardPolicy:
        """Fold the flat constructor arguments into the policy.

        The flat arguments always win; everything they do not cover is taken
        from ``base``.
        """
        retry = replace(
            base.retry,
            max_attempts=self._validate_max_retries(max_retries),
            backoff_base=(
                base.retry.backoff_base
                if backoff_base is None
                else self._validate_non_negative(backoff_base, "backoff_base")
            ),
            backoff_max=(
                base.retry.backoff_max
                if backoff_max is None
                else self._validate_positive_number(backoff_max, "backoff_max")
            ),
            retry_on=base.retry.retry_on if retry_on is None else tuple(retry_on),
            no_retry_on=base.retry.no_retry_on if no_retry_on is None else tuple(no_retry_on),
        )
        breaker = replace(
            base.breaker,
            cooldown_seconds=(
                base.breaker.cooldown_seconds
                if breaker_cooldown_seconds is None
                else breaker_cooldown_seconds
            ),
        )
        budget = replace(
            base.budget,
            token_counter=base.budget.token_counter if token_counter is None else token_counter,
        )
        return replace(
            base,
            verification_enabled=base.verification_enabled,
            verify_timeout_seconds=(
                base.verify_timeout_seconds
                if verify_timeout_seconds is None
                else self._validate_positive_number(
                    verify_timeout_seconds, "verify_timeout_seconds"
                )
            ),
            retry=retry,
            breaker=breaker,
            budget=budget,
            strict_order=base.strict_order if strict_order is None else strict_order,
            strict_next_step=(
                base.strict_next_step if strict_next_step is None else strict_next_step
            ),
            store_raw_outputs=(
                base.store_raw_outputs if store_raw_outputs is None else store_raw_outputs
            ),
            events_enabled=base.events_enabled if events_enabled is None else events_enabled,
            events_max_bytes=(
                base.events_max_bytes if events_max_bytes is None else events_max_bytes
            ),
            workdir=base.workdir if workdir is None else str(workdir),
        )

    @staticmethod
    def _validate_roadmap(roadmap: Any) -> tuple[str, ...]:
        if not isinstance(roadmap, (list, tuple)):
            raise ConfigurationError(
                f"roadmap must be a list of step names, got {type(roadmap).__name__}"
            )
        if len(roadmap) == 0:
            raise ConfigurationError("roadmap must not be empty")
        names: list[str] = []
        for name in roadmap:
            if not isinstance(name, str) or not name.strip():
                raise ConfigurationError(
                    f"roadmap step names must be non-empty strings, got {name!r}"
                )
            names.append(name)
        if len(set(names)) != len(names):
            duplicates = sorted({name for name in names if names.count(name) > 1})
            raise ConfigurationError(f"roadmap step names must be unique, duplicates: {duplicates}")
        return tuple(names)

    @staticmethod
    def _validate_positive_number(value: Any, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigurationError(f"{name} must be a number, got {type(value).__name__}")
        if value <= 0:
            raise ConfigurationError(f"{name} must be > 0, got {value!r}")
        return float(value)

    @staticmethod
    def _validate_non_negative(value: Any, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigurationError(f"{name} must be a number, got {type(value).__name__}")
        if value < 0:
            raise ConfigurationError(f"{name} must be >= 0, got {value!r}")
        return float(value)

    @staticmethod
    def _validate_max_retries(value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigurationError(f"max_retries must be an integer, got {type(value).__name__}")
        if value < 1:
            raise ConfigurationError(f"max_retries must be >= 1, got {value!r}")
        return value

    # ------------------------------------------------------------------
    # public properties
    # ------------------------------------------------------------------
    @property
    def roadmap(self) -> tuple[str, ...]:
        """The ordered roadmap."""
        return self._roadmap

    @property
    def memory_dir(self) -> str:
        """Directory that holds the project memory."""
        return str(self._state.memory_dir)

    @property
    def workdir(self) -> Path:
        """Directory the agent works in; all claimed paths stay inside it."""
        return self._workdir

    @property
    def policy(self) -> GuardPolicy:
        """The effective configuration."""
        return self._policy

    @property
    def max_retries(self) -> int:
        """Total number of attempts allowed per step."""
        return self._policy.retry.max_attempts

    @property
    def timeout_seconds(self) -> float:
        """Per-attempt time budget in seconds."""
        return self._timeout_seconds

    def on(self, event: str, callback: Callable[[dict[str, Any]], Any]) -> None:
        """Register an event callback.

        Args:
            event: One of the event names in
                :data:`agentether.events.EVENT_NAMES`.
            callback: A synchronous or asynchronous callable that receives the
                event payload.  Exceptions raised by a callback are logged and
                never break the run.

        Raises:
            ValueError: If the event name is unknown.
        """
        self._events.on(event, callback)

    # ------------------------------------------------------------------
    # decorator
    # ------------------------------------------------------------------
    def guard_step(
        self,
        step_name: str,
        *,
        verify: Sequence[Verifier] | None = None,
    ) -> Callable[[StepFunction[P, R]], GuardedStep[P]]:
        """Return a decorator that supervises one roadmap step.

        The decorated function receives a :class:`StepContext` as its first
        argument and returns the agent's raw text (or a
        :class:`~agentether.models.WorkerOutput`).  The decorated callable
        is always asynchronous, even when the wrapped function is a plain
        ``def`` -- such functions are executed in a worker thread.

        Args:
            step_name: The roadmap step this decorator guards.
            verify: Independent verifiers that check the agent's completion
                claim.  They run in order and all of them must pass.

        .. note::
            A thread cannot be killed.  When a *synchronous* function exceeds
            ``timeout_seconds`` the supervisor stops waiting, but the thread
            keeps running in the background.  Use an ``async def`` function
            when the work must actually be cancellable.
        """
        if not isinstance(step_name, str) or not step_name:
            raise ConfigurationError("step name must be a non-empty string")
        verifiers = list(verify or ())

        def decorator(func: StepFunction[P, R]) -> GuardedStep[P]:
            async def _run(*args: P.args, **kwargs: P.kwargs) -> StepResult:
                return await self._run_step(step_name, func, args, kwargs, False, verifiers)

            async def _rerun(*args: P.args, **kwargs: P.kwargs) -> StepResult:
                return await self._run_step(step_name, func, args, kwargs, True, verifiers)

            guarded = _GuardedStepImpl[P](run=_run, rerun=_rerun)
            functools.update_wrapper(guarded, func)
            return cast(GuardedStep[P], guarded)

        return decorator

    # ------------------------------------------------------------------
    # supervisor loop
    # ------------------------------------------------------------------
    async def _run_step(
        self,
        step_name: str,
        func: StepFunction[Any, Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        force: bool,
        verifiers: list[Verifier],
    ) -> StepResult:
        # Two concurrent calls to the same step are serialised: the second
        # one waits and then finds the cached result.
        loop = asyncio.get_running_loop()
        entry = self._step_locks.get(step_name)
        if entry is None or entry[0] is not loop:
            entry = (loop, asyncio.Lock())
            self._step_locks[step_name] = entry
        async with entry[1]:
            return await self._run_step_locked(step_name, func, args, kwargs, force, verifiers)

    async def _run_step_locked(
        self,
        step_name: str,
        func: StepFunction[Any, Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        force: bool,
        verifiers: list[Verifier],
    ) -> StepResult:
        if step_name not in self._index:
            raise ContextDriftError(
                step_name,
                expected="a step from the roadmap",
                observed=step_name,
                reason=f"step '{step_name}' is not part of the roadmap",
                retryable=False,
            )

        state = await self._state.load()
        if not self._budget_restored:
            # The budgets are global per project: a run that was interrupted
            # continues to spend the same budget after a restart.
            self._budget.restore(state.get("budget") or {})
            self._budget_restored = True
        human_text = self._state.human_text
        # The hash is computed on the normalised text, so that the empty
        # section and a section with only whitespace compare equal.
        human_changed = sha256_text(human_text.strip()) != str(state.get("human_hash") or "")

        half_open = await self._check_breaker(state, step_name)
        if half_open:
            logger.info(
                "Supervisor: circuit breaker for '%s' is half open - allowing one trial attempt",
                step_name,
            )

        completed = list(state.get("completed_steps", []))
        if self._policy.strict_order:
            for previous in self._roadmap[: self._index[step_name]]:
                if previous not in completed:
                    raise ContextDriftError(
                        step_name,
                        expected=f"all steps before '{step_name}' to be completed",
                        observed=f"'{previous}' is not completed",
                        reason=(f"step '{previous}' must be completed before '{step_name}'"),
                        retryable=False,
                    )

        needs_human = dict(state.get("needs_human") or {})
        if step_name in needs_human and not human_changed:
            raise ContextDriftError(
                step_name,
                expected="new input in the human section of PROJECT_MEMORY.md",
                observed="the human section was not changed",
                reason=(
                    f"step '{step_name}' is blocked and waiting for human input: "
                    f"{needs_human[step_name]}"
                ),
                retryable=False,
            )
        human_hint = ""
        if step_name in needs_human and human_changed:
            human_hint = (
                f"The human answered in the PROJECT_MEMORY.md human section:\n{human_text.strip()}"
            )
            logger.info("Supervisor: step '%s' is unblocked by new human input", step_name)

        if self._policy.resume and not force and step_name in completed:
            cached = await self._cached_result(step_name, state)
            logger.info(
                "Supervisor: Step '%s' already completed - returning cached result",
                step_name,
            )
            return cached

        hint: str | None = human_hint or None
        last_exception: BaseException | None = None
        last_kind = FailureKind.EXECUTION_ERROR
        attempt = 0
        started = self._clock()
        while attempt < self._policy.retry.max_attempts:
            attempt += 1
            try:
                self._budget.check()
            except BudgetExceededError as exc:
                await self._state.record_budget_exceeded(step_name, exc.kind, exc.limit, exc.used)
                await self._emit(
                    "budget_exceeded",
                    step=step_name,
                    kind=exc.kind,
                    limit=exc.limit,
                    used=exc.used,
                )
                raise
            # The memory is re-read from disk on every attempt: this is the
            # external memory guarantee the whole library is built around.
            state = await self._state.load()
            state["roadmap"] = list(self._roadmap)
            memory = self._state.render_context(state)
            context = StepContext(
                step_name=step_name,
                step_index=self._index[step_name],
                attempt=attempt,
                max_attempts=self._policy.retry.max_attempts,
                memory=memory,
                last_error=hint,
                roadmap=self._roadmap,
                workdir=self._workdir,
                human_memory=self._state.human_text,
            )
            await self._emit(
                "attempt_started",
                step=step_name,
                attempt=attempt,
                max_attempts=self._policy.retry.max_attempts,
            )

            outcome = await self._attempt(step_name, func, args, kwargs, context, verifiers)
            self._budget.record_attempt(
                text=outcome.raw_output,
                usage=outcome.usage,
            )
            if outcome.failure is None and outcome.telemetry is not None:
                telemetry = outcome.telemetry
                logger.debug(
                    "Supervisor: Step '%s' raw output (%d characters):\n%s",
                    step_name,
                    len(outcome.raw_output),
                    outcome.raw_output,
                )
                await self._state.record_step(step_name, telemetry, outcome.raw_output)
                await self._state.append_attempt(
                    step_name,
                    attempt,
                    "completed",
                    output=outcome.raw_output,
                    store_raw=self._policy.store_raw_outputs,
                    usage=outcome.usage.to_dict() if outcome.usage else None,
                    budget=self._budget.snapshot(),
                )
                self._loop_retries.pop(step_name, None)
                self._loop_detector.reset(step_name)
                self._stall_detector.reset(step_name)
                if half_open:
                    await self._state.set_breaker(False, "")
                duration = self._clock() - started
                await self._emit(
                    "step_completed",
                    step=step_name,
                    attempt=attempt,
                    duration_seconds=duration,
                    status=telemetry.status,
                )
                logger.info(
                    "Supervisor: Step '%s' completed in %.1fs (attempt %d/%d)",
                    step_name,
                    duration,
                    attempt,
                    self._policy.retry.max_attempts,
                )
                return StepResult(
                    step=step_name,
                    raw_output=outcome.raw_output,
                    telemetry=telemetry,
                    attempts=attempt,
                    duration_seconds=duration,
                    from_cache=False,
                    usage=outcome.usage,
                )

            failure = outcome.failure
            assert failure is not None  # invariant: one of the two is set
            hint = failure.hint
            last_exception = failure.exception
            last_kind = failure.kind
            await self._state.append_attempt(
                step_name,
                attempt,
                failure.kind.value,
                error=str(failure.exception),
                output=outcome.raw_output,
                store_raw=self._policy.store_raw_outputs,
                usage=outcome.usage.to_dict() if outcome.usage else None,
                budget=self._budget.snapshot(),
            )
            retryable = self._classify(failure.exception, failure.retryable)
            if failure.kind is FailureKind.LOOP_DETECTED:
                self._loop_retries[step_name] = self._loop_retries.get(step_name, 0) + 1
                if self._loop_retries[step_name] > self._policy.loop.max_retries_after_detection:
                    retryable = False
            if not retryable:
                if failure.trip_breaker:
                    # The loop repeated: the breaker trips and the loop error
                    # is chained as the cause.
                    await self._open_breaker(step_name, attempt, last_kind, hint)
                    raise CircuitBreakerOpenError(
                        step_name, attempt, last_kind.value, hint
                    ) from failure.exception
                # A non retryable failure (a blocked step, a broken budget)
                # is reported as is.  The breaker stays closed: a blocked
                # step must be retryable once a human answered.
                raise failure.exception
            if attempt >= self._policy.retry.max_attempts:
                break
            delay = self._backoff_delay(attempt)
            logger.warning(
                "Supervisor: Step '%s' %s (attempt %d/%d) - retrying in %.1fs",
                step_name,
                failure.detail,
                attempt,
                self._policy.retry.max_attempts,
                delay,
            )
            await self._sleep(delay)

        await self._open_breaker(step_name, attempt, last_kind, hint)
        raise CircuitBreakerOpenError(step_name, attempt, last_kind.value, hint) from last_exception

    async def _open_breaker(
        self, step_name: str, attempts: int, kind: FailureKind, hint: str | None
    ) -> None:
        """Persist the open breaker and announce it."""
        if not self._policy.breaker.enabled:
            return
        await self._state.set_breaker(
            True,
            kind.value,
            step=step_name,
            attempts=attempts,
            last_error=hint,
            opened_at=self._clock(),
        )
        await self._emit(
            "breaker_opened",
            step=step_name,
            attempts=attempts,
            reason=kind.value,
            last_error=hint,
        )
        logger.error(
            "Supervisor: CIRCUIT BREAKER OPEN on '%s' after %d attempts",
            step_name,
            attempts,
        )

    async def _check_breaker(self, state: dict[str, Any], step_name: str) -> bool:
        """Fail fast when the breaker is open.

        Returns:
            True when the breaker is half open (a single trial attempt is
            allowed), False when it is closed.
        """
        breaker = state.get("breaker") or {}
        if not breaker.get("open"):
            return False
        cooldown = self._policy.breaker.cooldown_seconds
        opened_at = breaker.get("opened_at")
        if cooldown is not None and opened_at is not None:
            elapsed = self._clock() - float(opened_at)
            if elapsed >= cooldown:
                return True
        raise CircuitBreakerOpenError(
            str(breaker.get("step") or step_name),
            int(breaker.get("attempts") or 0),
            str(breaker.get("reason") or ""),
            breaker.get("last_error"),
        )

    @staticmethod
    def _with_loop_hint(hint: str, loop_failure: _Failure | None) -> str:
        """Add the loop hint to a corrective hint, when a loop was detected."""
        if loop_failure is None:
            return hint
        return f"{hint}. {loop_failure.hint}"

    def _classify(self, error: BaseException, explicit: bool | None = None) -> bool:
        """Decide whether an error may be retried.

        The order is: ``no_retry_on`` always wins, then the explicit decision
        of the failure, then the ``retryable`` attribute of the exception
        (in-step drift carries one), and finally the class based policy.
        """
        if isinstance(error, self._policy.retry.no_retry_on):
            return False
        if explicit is not None:
            return explicit
        flag = getattr(error, "retryable", None)
        if isinstance(flag, bool):
            return flag
        # The worker exceptions are wrapped in an AgentExecutionError, so the
        # *original* exception decides as well: an adapter that says
        # "this will never work" (``retryable = False``) must not be retried.
        original = getattr(error, "original", None)
        if isinstance(original, BaseException):
            original_flag = getattr(original, "retryable", None)
            if isinstance(original_flag, bool):
                return original_flag
        if isinstance(error, self._policy.retry.retry_on):
            return True
        if isinstance(original, BaseException):
            return isinstance(original, self._policy.retry.retry_on)
        return False

    async def _attempt(
        self,
        step_name: str,
        func: StepFunction[Any, Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        context: StepContext,
        verifiers: list[Verifier],
    ) -> _AttemptResult:
        try:
            raw_output, usage = await self._invoke(func, context, args, kwargs)
        except AgentTimeoutError as exc:
            return _AttemptResult(
                failure=_Failure(
                    exception=exc,
                    hint=(
                        f"Previous attempt timed out after "
                        f"{self._timeout_seconds:g}s; produce a shorter answer"
                    ),
                    detail=f"timed out after {self._timeout_seconds:g}s",
                    kind=FailureKind.TIMEOUT,
                )
            )
        except AgentExecutionError as exc:
            return _AttemptResult(
                failure=_Failure(
                    exception=exc,
                    hint=(
                        f"Previous attempt raised {type(exc.original).__name__}: "
                        f"{exc.original}; fix the error and try again"
                    ),
                    detail=f"raised {type(exc.original).__name__}: {exc.original}",
                    kind=FailureKind.EXECUTION_ERROR,
                )
            )

        # The loop detector looks at every answer, even one that does not
        # parse: an agent that repeats itself is looping whether or not it
        # manages to produce valid JSON.
        verdict = self._loop_detector.record(step_name, raw_output)
        loop_failure: _Failure | None = None
        if verdict.loop:
            await self._emit(
                "loop_detected",
                step=step_name,
                similarity=verdict.similarity,
                window=verdict.window,
            )
            loop_failure = _Failure(
                exception=LoopDetectedError(
                    step_name,
                    verdict.hint,
                    verdict.similarity,
                    verdict.window,
                ),
                hint=verdict.hint,
                detail=verdict.hint,
                kind=FailureKind.LOOP_DETECTED,
                # A loop gets one more attempt with a strong hint; when it
                # repeats, the breaker trips.
                trip_breaker=True,
            )

        try:
            data = extract_json_telemetry(raw_output)
        except TelemetryParseError as exc:
            if loop_failure is not None:
                # Unparsable output that repeats itself is a loop first and a
                # parse error second: the loop is the actionable diagnosis.
                return _AttemptResult(
                    failure=loop_failure,
                    raw_output=raw_output,
                    usage=usage,
                )
            return _AttemptResult(
                failure=_Failure(
                    exception=exc,
                    hint=(
                        "Previous attempt did not emit a usable telemetry JSON "
                        f"object ({exc.reason}); end your answer with exactly one "
                        "JSON object containing 'step', 'status' and 'summary'"
                    ),
                    detail=f"returned invalid telemetry ({exc.reason})",
                    kind=FailureKind.PARSE_ERROR,
                )
            )

        observed_status = data.get("status")
        if isinstance(observed_status, str) and observed_status not in ALLOWED_STATUSES:
            return _AttemptResult(
                failure=_Failure(
                    exception=ContextDriftError(
                        step_name,
                        expected="one of " + ", ".join(ALLOWED_STATUSES),
                        observed=observed_status,
                        reason=f"telemetry reported an unknown status {observed_status!r}",
                        retryable=True,
                    ),
                    hint=(
                        f"Previous attempt reported status {observed_status!r}; "
                        "use one of " + ", ".join(ALLOWED_STATUSES)
                    ),
                    detail=f"reported an unknown status {observed_status!r}",
                    kind=FailureKind.DRIFT,
                )
            )

        try:
            telemetry = Telemetry.from_dict(data)
        except TelemetryParseError as exc:
            return _AttemptResult(
                failure=_Failure(
                    exception=exc,
                    hint=(
                        f"Previous attempt emitted invalid telemetry: {exc.reason}; "
                        "fix the JSON object and try again"
                    ),
                    detail=f"returned invalid telemetry ({exc.reason})",
                    kind=FailureKind.PARSE_ERROR,
                )
            )

        if telemetry.step != step_name:
            return _AttemptResult(
                failure=_Failure(
                    exception=ContextDriftError(
                        step_name,
                        expected=step_name,
                        observed=telemetry.step,
                        reason=(
                            f"telemetry step '{telemetry.step}' did not match "
                            f"expected step '{step_name}'"
                        ),
                        retryable=True,
                    ),
                    hint=self._with_loop_hint(
                        f"Telemetry step '{telemetry.step}' did not match expected "
                        f"step '{step_name}'; report the step you were asked to run",
                        loop_failure,
                    ),
                    detail=(f"reported step '{telemetry.step}' instead of '{step_name}'"),
                    kind=FailureKind.DRIFT,
                )
            )

        if (
            telemetry.status == "completed"
            and telemetry.progress is not None
            and telemetry.progress < 100
        ):
            return _AttemptResult(
                failure=_Failure(
                    exception=ContextDriftError(
                        step_name,
                        expected="progress >= 100 for a completed step",
                        observed=telemetry.progress,
                        reason=(
                            f"step was reported as completed but progress is {telemetry.progress:g}"
                        ),
                        retryable=True,
                    ),
                    hint=(
                        f"Previous attempt reported status 'completed' with progress "
                        f"{telemetry.progress:g}; either finish the work or report a "
                        "progress value of 100"
                    ),
                    detail=(f"reported 'completed' with progress {telemetry.progress:g}"),
                    kind=FailureKind.DRIFT,
                )
            )

        expected_next = self._expected_next_step(step_name)
        if telemetry.next_step != expected_next:
            message = (
                f"Step '{step_name}' reported next_step {telemetry.next_step!r} "
                f"but expected {expected_next!r}"
            )
            if self._policy.strict_next_step:
                return _AttemptResult(
                    failure=_Failure(
                        exception=ContextDriftError(
                            step_name,
                            expected=expected_next,
                            observed=telemetry.next_step,
                            reason=message,
                            retryable=True,
                        ),
                        hint=self._with_loop_hint(
                            f"Previous attempt reported next_step "
                            f"{telemetry.next_step!r}; expected {expected_next!r}",
                            loop_failure,
                        ),
                        detail=(
                            f"reported next_step {telemetry.next_step!r} instead of "
                            f"{expected_next!r}"
                        ),
                        kind=FailureKind.DRIFT,
                    )
                )
            logger.warning("Supervisor: %s", message)

        stall = self._stall_detector.record(step_name, telemetry)
        if stall.stalled:
            await self._emit("loop_detected", step=step_name, stall=True, window=stall.window)
            return _AttemptResult(
                failure=_Failure(
                    exception=LoopDetectedError(step_name, stall.hint, window=stall.window),
                    hint=stall.hint,
                    detail=stall.hint,
                    kind=FailureKind.STALL_DETECTED,
                ),
                raw_output=raw_output,
                usage=usage,
            )

        if telemetry.status == "completed" and verifiers:
            verification = await self._verify(step_name, telemetry, raw_output, verifiers)
            if verification is not None:
                return _AttemptResult(
                    failure=verification,
                    raw_output=raw_output,
                    usage=usage,
                )

        if telemetry.status == "completed":
            return _AttemptResult(telemetry=telemetry, raw_output=raw_output, usage=usage)

        if telemetry.status == "in_progress":
            return _AttemptResult(
                failure=_Failure(
                    exception=ContextDriftError(
                        step_name,
                        expected="status 'completed'",
                        observed="in_progress",
                        reason="the step was not completed",
                        retryable=True,
                    ),
                    hint="step not completed, continue",
                    detail="did not complete the step",
                    kind=FailureKind.IN_PROGRESS,
                    retryable=True,
                ),
                raw_output=raw_output,
                usage=usage,
            )

        # blocked / failed: persist the reason, then give up immediately.
        await self._state.record_step(step_name, telemetry, raw_output)
        reason = telemetry.summary or f"the agent reported status {telemetry.status!r}"
        kind = (
            FailureKind.AGENT_BLOCKED if telemetry.status == "blocked" else FailureKind.AGENT_FAILED
        )
        return _AttemptResult(
            failure=_Failure(
                exception=AgentExecutionError(
                    step_name, RuntimeError(f"agent reported {telemetry.status}: {reason}")
                ),
                hint=(
                    f"Previous attempt reported status {telemetry.status!r}: {reason}; "
                    "resolve the blocker before retrying"
                ),
                detail=f"reported status {telemetry.status!r}: {reason}",
                kind=kind,
                retryable=False,
            ),
            raw_output=raw_output,
            usage=usage,
        )

    async def _verify(
        self,
        step_name: str,
        telemetry: Telemetry,
        raw_output: str,
        verifiers: list[Verifier],
    ) -> _Failure | None:
        """Run the verifiers.  Returns a failure when one of them rejects."""
        if not self._policy.verification_enabled:
            return None
        context = VerifyContext(
            step=step_name,
            telemetry=telemetry,
            raw_output=raw_output,
            memory_dir=self._state.memory_dir,
            workdir=self._workdir,
        )
        for verifier in verifiers:
            try:
                result = await asyncio.wait_for(
                    verifier(context), self._policy.verify_timeout_seconds
                )
            except asyncio.TimeoutError:
                result = VerifyResult(
                    ok=False,
                    reason=f"verifier timed out after {self._policy.verify_timeout_seconds:g}s",
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                result = VerifyResult(
                    ok=False,
                    reason=f"verifier raised {type(exc).__name__}: {exc}",
                )
            if not result.ok:
                await self._state.set_verification(step_name, False, result.reason, result.evidence)
                await self._emit(
                    "verification_failed",
                    step=step_name,
                    reason=result.reason,
                    evidence=result.evidence,
                )
                return _Failure(
                    exception=VerificationFailedError(step_name, result.reason, result.evidence),
                    hint=(
                        f"you reported completed but: {result.reason}; "
                        "do that work before reporting the step as done"
                    ),
                    detail=f"verification failed: {result.reason}",
                    kind=FailureKind.VERIFICATION_FAILED,
                )
        await self._state.set_verification(step_name, True)
        return None

    # ------------------------------------------------------------------
    # invocation
    # ------------------------------------------------------------------
    async def _invoke(
        self,
        func: StepFunction[Any, Any],
        context: StepContext,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> tuple[str, Usage | None]:
        target = func
        timeout = self._timeout_seconds
        try:
            if inspect.iscoroutinefunction(target):
                outcome = cast("Awaitable[Any]", target(context, *args, **kwargs))
                raw = await asyncio.wait_for(self._await_worker(outcome), timeout)
            else:
                raw = await asyncio.wait_for(
                    self._call_in_thread(target, context, *args, **kwargs), timeout
                )
        except asyncio.TimeoutError as exc:
            # The supervisor's own timer fired: the worker was too slow.
            raise AgentTimeoutError(context.step_name, timeout) from exc
        except _WorkerTimeout as exc:
            # The worker raised a timeout itself: that is an agent error.
            raise AgentExecutionError(context.step_name, exc.original) from exc.original
        except asyncio.CancelledError:
            # Cancellation is never swallowed and never retried.
            raise
        except (ConfigurationError, StateCorruptionError, BudgetExceededError):
            # Configuration, state and budget problems are never retried.
            raise
        except Exception as exc:
            raise AgentExecutionError(context.step_name, exc) from exc
        if isinstance(raw, WorkerOutput):
            return raw.text, raw.usage
        if isinstance(raw, str):
            return raw, None
        return str(raw), None

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @staticmethod
    async def _await_worker(awaitable: Awaitable[Any]) -> Any:
        """Await the worker, tagging a timeout it raises itself."""
        try:
            return await awaitable
        except asyncio.TimeoutError as exc:
            raise _WorkerTimeout(exc) from exc

    @staticmethod
    async def _call_in_thread(target: Callable[..., Any], *args: Any) -> Any:
        """Run a synchronous worker in a thread, tagging its own timeouts."""
        try:
            return await asyncio.to_thread(target, *args)
        except asyncio.TimeoutError as exc:
            raise _WorkerTimeout(exc) from exc

    def _expected_next_step(self, step_name: str) -> str | None:
        index = self._index[step_name]
        if index + 1 < len(self._roadmap):
            return self._roadmap[index + 1]
        return None

    def _backoff_delay(self, attempt: int) -> float:
        """Full jitter exponential backoff."""
        cap = min(
            self._policy.retry.backoff_max,
            self._policy.retry.backoff_base * (2 ** (attempt - 1)),
        )
        return random.uniform(0.0, cap)

    async def _cached_result(self, step_name: str, state: dict[str, Any]) -> StepResult:
        record = (state.get("telemetry") or {}).get(step_name)
        if not isinstance(record, dict):
            raise StateCorruptionError(
                f"step '{step_name}' is marked as completed but has no telemetry"
            )
        try:
            telemetry = Telemetry.from_dict(record)
        except TelemetryParseError as exc:
            raise StateCorruptionError(
                f"stored telemetry for step '{step_name}' is invalid: {exc.reason}"
            ) from exc
        relative = (state.get("step_files") or {}).get(step_name)
        raw_output = ""
        if isinstance(relative, str) and relative:
            raw_output = await asyncio.to_thread(self._read_step_output, relative)
        return StepResult(
            step=step_name,
            raw_output=raw_output,
            telemetry=telemetry,
            attempts=0,
            duration_seconds=0.0,
            from_cache=True,
        )

    def _read_step_output(self, relative: str) -> str:
        path = self._state.memory_dir / relative
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    async def _emit(self, event: str, **payload: Any) -> None:
        """Emit an event to the callbacks and to ``events.jsonl``."""
        record = self._event_log.append(event, **payload)
        await self._events.emit(event, record)

    # ------------------------------------------------------------------
    # breaker / reset
    # ------------------------------------------------------------------
    async def reset_breaker(self) -> None:
        """Close the circuit breaker so the roadmap can continue."""
        await self._state.set_breaker(False, "")
        self._loop_retries.clear()

    async def reset(self) -> None:
        """Clear the whole project memory (steps, telemetry, breaker)."""
        await self._state.reset()
        self._loop_retries.clear()


def guard_step(
    orchestrator: AutoOrchestrator, step_name: str
) -> Callable[[StepFunction[P, R]], GuardedStep[P]]:
    """Module level convenience wrapper around :meth:`AutoOrchestrator.guard_step`.

    ``guard_step(orchestrator, "research")`` is equivalent to
    ``orchestrator.guard_step("research")``.
    """
    return orchestrator.guard_step(step_name)
