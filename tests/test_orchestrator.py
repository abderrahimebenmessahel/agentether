"""Tests for the supervisor."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest

from agentether import (
    AgentExecutionError,
    AgentTimeoutError,
    AutoOrchestrator,
    BudgetExceededError,
    BudgetPolicy,
    CircuitBreakerOpenError,
    ContextDriftError,
    GuardPolicy,
    StateManager,
    StepContext,
    StepResult,
    Telemetry,
    TelemetryParseError,
    Usage,
    VerificationFailedError,
    VerifyContext,
    WorkerOutput,
    artifacts_exist,
    callable_verifier,
)
from conftest import telemetry_answer


def assert_cause(excinfo: pytest.ExceptionInfo[BaseException], error: type[BaseException]) -> None:
    """The breaker error carries the original failure as its cause.

    Since v0.2 ``CircuitBreakerOpenError`` is a plain class again: when the
    attempts are exhausted the breaker opens and the *original* error is
    chained as ``__cause__``.
    """
    cause = excinfo.value.__cause__
    assert isinstance(cause, error), f"expected {error.__name__}, got {cause!r}"


def make_orchestrator(
    memory_dir: Path,
    *,
    roadmap: list[str] | None = None,
    timeout_seconds: float = 5.0,
    max_retries: int = 3,
    sleep: Callable[[float], Awaitable[None]] | None = None,
    **kwargs: Any,
) -> AutoOrchestrator:
    return AutoOrchestrator(
        roadmap=roadmap if roadmap is not None else ["research", "write"],
        memory_dir=str(memory_dir),
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        sleep=sleep,
        **kwargs,
    )


async def test_success_path(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir)
    calls: list[StepContext] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        calls.append(ctx)
        return telemetry_answer("research", summary="found three sources")

    result = await research()

    assert isinstance(result, StepResult)
    assert result.step == "research"
    assert result.telemetry.status == "completed"
    assert result.telemetry.summary == "found three sources"
    assert result.attempts == 1
    assert result.from_cache is False
    assert len(calls) == 1
    assert calls[0].step_name == "research"
    assert calls[0].attempt == 1

    manager = StateManager(memory_dir)
    state = await manager.load()
    assert state["completed_steps"] == ["research"]


async def test_prompt_contains_the_telemetry_contract(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir)
    prompts: list[str] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        prompts.append(ctx.build_prompt("Research X"))
        return telemetry_answer("research")

    await research()
    prompt = prompts[0]
    assert "Research X" in prompt
    assert '"step"' in prompt
    assert '"status"' in prompt
    assert "# Project Memory" in prompt


async def test_worker_output_carries_usage(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir)

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> WorkerOutput:
        return WorkerOutput(
            text=telemetry_answer("research"),
            usage=Usage(input_tokens=10, output_tokens=5, cost=0.25),
        )

    result = await research()
    assert result.usage is not None
    assert result.usage.total_tokens == 15
    assert result.usage.cost == pytest.approx(0.25)


async def test_timeout_then_success(memory_dir: Path, recording_sleep) -> None:
    delays, sleep = recording_sleep
    orch = make_orchestrator(memory_dir, timeout_seconds=0.05, sleep=sleep)
    attempts: list[int] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        attempts.append(ctx.attempt)
        if ctx.attempt == 1:
            await asyncio.sleep(5)
        return telemetry_answer("research")

    result = await research()

    assert result.telemetry.status == "completed"
    assert result.attempts == 2
    assert attempts == [1, 2]
    assert len(delays) == 1


async def test_timeout_uses_the_timeout_error(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir, timeout_seconds=0.05, max_retries=1)

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        await asyncio.sleep(5)
        return telemetry_answer("research")

    with pytest.raises(CircuitBreakerOpenError) as excinfo:
        await research()
    assert "timed out" in (excinfo.value.last_error or "")
    assert isinstance(excinfo.value.__cause__, AgentTimeoutError)
    assert excinfo.value.reason == "timeout"


async def test_breaker_opens_persists_and_fails_fast(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir, timeout_seconds=0.05, max_retries=2)
    calls: list[int] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        calls.append(ctx.attempt)
        await asyncio.sleep(5)
        return telemetry_answer("research")

    with pytest.raises(CircuitBreakerOpenError):
        await research()
    assert calls == [1, 2]

    manager = StateManager(memory_dir)
    state = await manager.load()
    assert state["breaker"]["open"] is True
    assert state["breaker"]["attempts"] == 2
    assert state["breaker"]["step"] == "research"

    # A fresh orchestrator over the same memory fails fast, without calling
    # the agent again: this is what survives a process restart.
    orch2 = make_orchestrator(memory_dir, timeout_seconds=0.05, max_retries=2)

    @orch2.guard_step("research")
    async def research2(ctx: StepContext) -> str:  # pragma: no cover - never called
        calls.append(99)
        return telemetry_answer("research")

    with pytest.raises(CircuitBreakerOpenError):
        await research2()
    assert calls == [1, 2]

    await orch2.reset_breaker()
    state = await manager.load()
    assert state["breaker"]["open"] is False


async def test_half_open_breaker_allows_one_trial(memory_dir: Path, fake_clock) -> None:
    orch = make_orchestrator(
        memory_dir,
        timeout_seconds=0.05,
        max_retries=1,
        breaker_cooldown_seconds=60.0,
        clock=fake_clock,
    )
    calls: list[int] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        calls.append(ctx.attempt)
        await asyncio.sleep(5)
        return telemetry_answer("research")

    with pytest.raises(CircuitBreakerOpenError):
        await research()
    assert calls == [1]

    # Still inside the cooldown: the breaker stays shut.
    with pytest.raises(CircuitBreakerOpenError):
        await research()
    assert calls == [1]

    # After the cooldown one trial attempt is allowed -- and it succeeds.
    fake_clock.advance(61.0)

    @orch.guard_step("research")
    async def research2(ctx: StepContext) -> str:
        calls.append(100 + ctx.attempt)
        return telemetry_answer("research")

    result = await research2()
    assert result.telemetry.status == "completed"

    manager = StateManager(memory_dir)
    state = await manager.load()
    assert state["breaker"]["open"] is False


async def test_half_open_breaker_reopens_after_a_failed_trial(memory_dir: Path, fake_clock) -> None:
    orch = make_orchestrator(
        memory_dir,
        timeout_seconds=0.05,
        max_retries=1,
        breaker_cooldown_seconds=60.0,
        clock=fake_clock,
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        await asyncio.sleep(5)
        return telemetry_answer("research")

    with pytest.raises(CircuitBreakerOpenError):
        await research()
    fake_clock.advance(61.0)

    @orch.guard_step("research")
    async def research2(ctx: StepContext) -> str:
        await asyncio.sleep(5)
        return telemetry_answer("research")

    with pytest.raises(CircuitBreakerOpenError):
        await research2()

    manager = StateManager(memory_dir)
    state = await manager.load()
    assert state["breaker"]["open"] is True


async def test_parse_failure_retries_and_passes_the_hint(memory_dir: Path, recording_sleep) -> None:
    delays, sleep = recording_sleep
    orch = make_orchestrator(memory_dir, sleep=sleep)
    seen: list[StepContext] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        seen.append(ctx)
        if ctx.attempt == 1:
            return "I forgot the JSON, sorry."
        return telemetry_answer("research")

    result = await research()

    assert result.telemetry.status == "completed"
    assert result.attempts == 2
    assert seen[0].last_error is None
    assert seen[1].last_error is not None
    assert "telemetry" in (seen[1].last_error or "").lower()
    assert len(delays) == 1


async def test_drift_on_wrong_step_name(memory_dir: Path, recording_sleep) -> None:
    _, sleep = recording_sleep
    orch = make_orchestrator(memory_dir, max_retries=1, sleep=sleep)

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("writing")

    with pytest.raises(CircuitBreakerOpenError) as excinfo:
        await research()
    assert_cause(excinfo, ContextDriftError)
    drift = excinfo.value.__cause__
    assert isinstance(drift, ContextDriftError)
    assert drift.step == "research"
    assert drift.observed == "writing"
    assert "did not match" in drift.reason


async def test_drift_triggers_a_retry(memory_dir: Path, recording_sleep) -> None:
    _, sleep = recording_sleep
    orch = make_orchestrator(memory_dir, max_retries=3, sleep=sleep)
    attempts: list[int] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        attempts.append(ctx.attempt)
        if ctx.attempt == 1:
            return telemetry_answer("writing")
        return telemetry_answer("research")

    result = await research()
    assert result.telemetry.step == "research"
    assert result.attempts == 2


async def test_out_of_order_step_is_rejected(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir)
    called: list[int] = []

    @orch.guard_step("write")
    async def write(ctx: StepContext) -> str:  # pragma: no cover - never called
        called.append(1)
        return telemetry_answer("write")

    with pytest.raises(ContextDriftError) as excinfo:
        await write()
    assert "research" in excinfo.value.reason
    assert called == []


async def test_unknown_step_is_rejected(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir)

    @orch.guard_step("nope")
    async def nope(ctx: StepContext) -> str:  # pragma: no cover - never called
        return telemetry_answer("nope")

    with pytest.raises(ContextDriftError):
        await nope()


async def test_next_step_mismatch_only_warns(
    memory_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    orch = make_orchestrator(memory_dir)

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research", next_step="something-else")

    with caplog.at_level(logging.WARNING, logger="agentether"):
        result = await research()

    assert result.telemetry.status == "completed"
    messages = [record.getMessage() for record in caplog.records]
    assert any("next_step" in message for message in messages)
    assert all(record.levelno == logging.WARNING for record in caplog.records)


async def test_next_step_mismatch_raises_in_strict_mode(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir, strict_next_step=True)

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research", next_step="something-else")

    with pytest.raises(CircuitBreakerOpenError) as excinfo:
        await research()
    assert_cause(excinfo, ContextDriftError)


async def test_missing_next_step_also_warns(memory_dir: Path, caplog) -> None:
    orch = make_orchestrator(memory_dir)

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research", next_step=None)

    with caplog.at_level(logging.WARNING, logger="agentether"):
        await research()

    assert any("next_step" in record.getMessage() for record in caplog.records)


async def test_resume_returns_the_cached_result(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir)
    calls: list[int] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        calls.append(1)
        return telemetry_answer("research", summary="cached summary")

    first = await research()
    assert first.from_cache is False

    orch2 = make_orchestrator(memory_dir)

    @orch2.guard_step("research")
    async def research2(ctx: StepContext) -> str:  # pragma: no cover - never called
        calls.append(2)
        return telemetry_answer("research")

    second = await research2()
    assert second.from_cache is True
    assert second.telemetry.summary == "cached summary"
    assert calls == [1]


async def test_rerun_ignores_the_cached_result(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir)
    calls: list[int] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        calls.append(1)
        return telemetry_answer("research", summary="again")

    await research()
    result = await research.rerun()
    assert result.from_cache is False
    assert calls == [1, 1]


async def test_blocked_status_raises_without_retry(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir, max_retries=3)
    calls: list[int] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        calls.append(1)
        return telemetry_answer("research", status="blocked", summary="need credentials")

    with pytest.raises(AgentExecutionError) as excinfo:
        await research()
    assert calls == [1]
    assert "need credentials" in str(excinfo.value)

    manager = StateManager(memory_dir)
    state = await manager.load()
    assert state["last_failure"]["step"] == "research"
    assert state["last_failure"]["reason"] == "need credentials"
    assert state["completed_steps"] == []


async def test_in_progress_is_treated_as_a_failed_attempt(
    memory_dir: Path, recording_sleep
) -> None:
    _, sleep = recording_sleep
    orch = make_orchestrator(memory_dir, max_retries=2, sleep=sleep)
    seen: list[StepContext] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        seen.append(ctx)
        return telemetry_answer("research", status="in_progress")

    with pytest.raises(CircuitBreakerOpenError):
        await research()
    assert seen[1].last_error == "step not completed, continue"


async def test_agent_exception_is_wrapped(memory_dir: Path, recording_sleep) -> None:
    _, sleep = recording_sleep
    orch = make_orchestrator(memory_dir, max_retries=1, sleep=sleep)

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        raise RuntimeError("the model exploded")

    with pytest.raises(CircuitBreakerOpenError) as excinfo:
        await research()
    assert_cause(excinfo, AgentExecutionError)
    wrapped = excinfo.value.__cause__
    assert isinstance(wrapped, AgentExecutionError)
    assert isinstance(wrapped.original, RuntimeError)
    assert "the model exploded" in str(wrapped)


async def test_sync_function_is_supported(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir)

    @orch.guard_step("research")
    def research(ctx: StepContext) -> str:
        assert isinstance(ctx, StepContext)
        return telemetry_answer("research", summary="from a thread")

    result = await research()
    assert result.telemetry.summary == "from a thread"
    assert result.telemetry.status == "completed"


async def test_cancellation_propagates(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir)
    started = asyncio.Event()

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        started.set()
        await asyncio.sleep(10)
        return telemetry_answer("research")  # pragma: no cover - never reached

    async def _call() -> StepResult:
        return await research()

    task = asyncio.create_task(_call())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_backoff_uses_the_injected_sleep(
    memory_dir: Path, recording_sleep, monkeypatch: pytest.MonkeyPatch
) -> None:
    delays, sleep = recording_sleep
    monkeypatch.setattr("agentether.orchestrator.random.uniform", lambda a, b: b)
    orch = make_orchestrator(
        memory_dir, max_retries=4, backoff_base=1.0, backoff_max=30.0, sleep=sleep
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        raise RuntimeError("nope")

    with pytest.raises(CircuitBreakerOpenError):
        await research()

    # Full jitter exponential backoff: 1, 2, 4 (capped at backoff_max).
    assert delays == [1.0, 2.0, 4.0]


async def test_backoff_is_capped(memory_dir: Path, recording_sleep, monkeypatch) -> None:
    delays, sleep = recording_sleep
    monkeypatch.setattr("agentether.orchestrator.random.uniform", lambda a, b: b)
    orch = make_orchestrator(
        memory_dir, max_retries=4, backoff_base=10.0, backoff_max=15.0, sleep=sleep
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        raise RuntimeError("nope")

    with pytest.raises(CircuitBreakerOpenError):
        await research()
    assert delays == [10.0, 15.0, 15.0]


async def test_completed_step_with_low_progress_is_drift(memory_dir: Path, recording_sleep) -> None:
    _, sleep = recording_sleep
    orch = make_orchestrator(memory_dir, max_retries=1, sleep=sleep)

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research", progress=40)

    with pytest.raises(CircuitBreakerOpenError) as excinfo:
        await research()
    assert_cause(excinfo, ContextDriftError)
    drift = excinfo.value.__cause__
    assert isinstance(drift, ContextDriftError)
    assert "progress" in drift.reason


async def test_invalid_status_is_drift(memory_dir: Path, recording_sleep) -> None:
    _, sleep = recording_sleep
    orch = make_orchestrator(memory_dir, max_retries=1, sleep=sleep)

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return json.dumps({"step": "research", "status": "almost", "summary": "s"})

    with pytest.raises(CircuitBreakerOpenError) as excinfo:
        await research()
    assert_cause(excinfo, ContextDriftError)


async def test_invalid_telemetry_is_a_parse_error(memory_dir: Path, recording_sleep) -> None:
    _, sleep = recording_sleep
    orch = make_orchestrator(memory_dir, max_retries=1, sleep=sleep)

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return json.dumps({"status": "completed", "summary": "no step field"})

    with pytest.raises(CircuitBreakerOpenError) as excinfo:
        await research()
    assert_cause(excinfo, TelemetryParseError)


async def test_memory_is_reread_on_every_attempt(memory_dir: Path, recording_sleep) -> None:
    _, sleep = recording_sleep
    orch = make_orchestrator(memory_dir, max_retries=2, sleep=sleep)
    memories: list[str] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        memories.append(ctx.memory)
        if ctx.attempt == 1:
            # Something else wrote to the memory in the meantime.
            manager = StateManager(memory_dir)
            await manager.record_step(
                "other",
                Telemetry(
                    step="other",
                    status="completed",
                    summary="written by someone else",
                ),
                "x",
            )
            return "this attempt forgets the telemetry contract"
        return telemetry_answer("research")

    await research()
    assert "written by someone else" not in memories[0]
    assert "written by someone else" in memories[1]


async def test_module_level_guard_step(memory_dir: Path) -> None:
    from agentether import guard_step

    orch = make_orchestrator(memory_dir)

    @guard_step(orch, "research")
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research")

    result = await research()
    assert result.telemetry.status == "completed"


async def test_configuration_errors(memory_dir: Path) -> None:
    from agentether import ConfigurationError

    with pytest.raises(ConfigurationError):
        AutoOrchestrator([], str(memory_dir), 10, 1)
    with pytest.raises(ConfigurationError):
        AutoOrchestrator(["a", "a"], str(memory_dir), 10, 1)
    with pytest.raises(ConfigurationError):
        AutoOrchestrator(["a", ""], str(memory_dir), 10, 1)
    with pytest.raises(ConfigurationError):
        AutoOrchestrator(["a"], str(memory_dir), 0, 1)
    with pytest.raises(ConfigurationError):
        AutoOrchestrator(["a"], str(memory_dir), 10, 0)


# ----------------------------------------------------------------------
# verification
# ----------------------------------------------------------------------
async def test_verifier_passes(memory_dir: Path, work_dir: Path) -> None:
    orch = make_orchestrator(memory_dir, workdir=str(work_dir))
    (work_dir / "result.md").write_text("done", encoding="utf-8")

    @orch.guard_step("research", verify=[artifacts_exist()])
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research", artifacts=["result.md"])

    result = await research()
    assert result.telemetry.status == "completed"


async def test_verifier_rejects_a_false_claim(
    memory_dir: Path, work_dir: Path, recording_sleep
) -> None:
    _, sleep = recording_sleep
    orch = make_orchestrator(memory_dir, max_retries=2, workdir=str(work_dir), sleep=sleep)
    seen: list[StepContext] = []

    @orch.guard_step("research", verify=[artifacts_exist()])
    async def research(ctx: StepContext) -> str:
        seen.append(ctx)
        return telemetry_answer("research", artifacts=["result.md"])

    with pytest.raises(CircuitBreakerOpenError) as excinfo:
        await research()
    assert_cause(excinfo, VerificationFailedError)
    failure = excinfo.value.__cause__
    assert isinstance(failure, VerificationFailedError)
    assert "result.md" in failure.reason
    assert seen[1].last_error is not None
    assert "you reported completed but" in (seen[1].last_error or "")


async def test_a_broken_verifier_is_a_failed_verification(
    memory_dir: Path, work_dir: Path, recording_sleep
) -> None:
    _, sleep = recording_sleep
    orch = make_orchestrator(memory_dir, max_retries=1, workdir=str(work_dir), sleep=sleep)

    def broken(ctx: VerifyContext) -> bool:
        raise RuntimeError("verifier is broken")

    @orch.guard_step("research", verify=[callable_verifier(broken)])
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research")

    with pytest.raises(CircuitBreakerOpenError) as excinfo:
        await research()
    assert_cause(excinfo, VerificationFailedError)
    failure = excinfo.value.__cause__
    assert isinstance(failure, VerificationFailedError)
    assert "verifier is broken" in failure.reason


async def test_a_slow_verifier_times_out(memory_dir: Path, work_dir: Path, recording_sleep) -> None:
    _, sleep = recording_sleep
    orch = make_orchestrator(
        memory_dir,
        max_retries=1,
        workdir=str(work_dir),
        sleep=sleep,
        verify_timeout_seconds=0.05,
    )

    async def slow(ctx: VerifyContext) -> bool:
        await asyncio.sleep(5)
        return True  # pragma: no cover - never reached

    @orch.guard_step("research", verify=[callable_verifier(slow)])
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research")

    with pytest.raises(CircuitBreakerOpenError) as excinfo:
        await research()
    assert_cause(excinfo, VerificationFailedError)
    failure = excinfo.value.__cause__
    assert isinstance(failure, VerificationFailedError)
    assert "timed out" in failure.reason


async def test_verification_results_are_persisted(memory_dir: Path, work_dir: Path) -> None:
    orch = make_orchestrator(memory_dir, workdir=str(work_dir))
    (work_dir / "result.md").write_text("done", encoding="utf-8")

    @orch.guard_step("research", verify=[artifacts_exist()])
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research", artifacts=["result.md"])

    await research()
    manager = StateManager(memory_dir)
    state = await manager.load()
    assert state["verifications"]["research"]["ok"] is True
    text = (memory_dir / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    assert "## Verification" in text


# ----------------------------------------------------------------------
# loop detection, budgets, events, human in the loop
# ----------------------------------------------------------------------
async def test_looping_output_is_detected(memory_dir: Path, recording_sleep) -> None:
    _, sleep = recording_sleep
    orch = make_orchestrator(memory_dir, max_retries=5, sleep=sleep)

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return (
            f"I keep working on it, token {ctx.attempt:08x}. "
            "The same summary text repeated verbatim. " * 3
        )

    with pytest.raises(CircuitBreakerOpenError) as excinfo:
        await research()
    assert excinfo.value.reason in ("loop_detected", "stall_detected")


async def test_budget_exceeded_is_not_retried(memory_dir: Path) -> None:
    orch = make_orchestrator(
        memory_dir,
        max_retries=5,
        policy=GuardPolicy(budget=BudgetPolicy(max_total_attempts=1)),
    )
    calls: list[int] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        calls.append(ctx.attempt)
        # The first attempt fails, so the second one would be needed -- and
        # the attempt budget does not allow it.
        return "no telemetry at all"

    with pytest.raises(BudgetExceededError) as excinfo:
        await research()
    assert excinfo.value.kind == "attempts"
    assert calls == [1]

    manager = StateManager(memory_dir)
    state = await manager.load()
    assert state["last_failure"]["status"] == "budget_exceeded"


async def test_events_are_emitted(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir)
    seen: list[str] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research")

    orch.on("attempt_started", lambda payload: seen.append("attempt_started"))
    orch.on("step_completed", lambda payload: seen.append("step_completed"))
    await research()
    assert seen == ["attempt_started", "step_completed"]

    log = memory_dir / "events.jsonl"
    assert log.exists()
    records = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]
    assert {record["event"] for record in records} >= {"attempt_started", "step_completed"}


async def test_blocked_step_waits_for_human_input(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir, max_retries=1)
    calls: list[int] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        calls.append(ctx.attempt)
        return telemetry_answer("research", status="blocked", summary="need the API key")

    with pytest.raises(AgentExecutionError):
        await research()
    assert calls == [1]

    # A second attempt without a human answer is refused.
    with pytest.raises(ContextDriftError) as excinfo:
        await research()
    assert "human" in excinfo.value.reason
    assert calls == [1]


async def test_human_input_unblocks_a_blocked_step(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir, max_retries=1)
    hints: list[str | None] = []

    calls: list[int] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        hints.append(ctx.last_error)
        calls.append(ctx.attempt)
        if len(calls) == 1:
            return telemetry_answer("research", status="blocked", summary="need the API key")
        return telemetry_answer("research")

    with pytest.raises(AgentExecutionError):
        await research()

    # The human answers in their own section of the memory file.
    path = memory_dir / "PROJECT_MEMORY.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "<!-- agentether:human:start -->\n\n<!-- agentether:human:end -->",
        "<!-- agentether:human:start -->\nthe key is 12345\n<!-- agentether:human:end -->",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)

    result = await research.rerun()
    assert result.telemetry.status == "completed"
    assert hints[-1] is not None
    assert "the key is 12345" in hints[-1]


# ----------------------------------------------------------------------
# retry classification
# ----------------------------------------------------------------------
async def test_retry_on_makes_a_class_retryable(memory_dir: Path, recording_sleep) -> None:
    _, sleep = recording_sleep
    orch = make_orchestrator(
        memory_dir,
        max_retries=2,
        sleep=sleep,
        retry_on=(ValueError,),
        no_retry_on=(),
    )
    calls: list[int] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        calls.append(ctx.attempt)
        if ctx.attempt == 1:
            raise ValueError("not in the default retry set")
        return telemetry_answer("research")

    result = await research()
    assert result.attempts == 2
    assert calls == [1, 2]


async def test_no_retry_on_wins_over_retry_on(memory_dir: Path) -> None:
    orch = make_orchestrator(
        memory_dir,
        max_retries=3,
        retry_on=(AgentExecutionError,),
        no_retry_on=(AgentExecutionError,),
    )
    calls: list[int] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        calls.append(ctx.attempt)
        raise RuntimeError("boom")

    with pytest.raises(AgentExecutionError):
        await research()
    assert calls == [1]


async def test_cancellation_is_never_retried(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir, max_retries=3)
    calls: list[int] = []

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        calls.append(ctx.attempt)
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await research()
    assert calls == [1]


async def test_a_worker_that_raises_its_own_timeout_is_an_execution_error(
    memory_dir: Path,
) -> None:
    # The supervisor's timeout and the worker's own timeout are different
    # things; the classification must not depend on the clock resolution.
    orch = make_orchestrator(memory_dir, timeout_seconds=5.0, max_retries=1)

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        raise asyncio.TimeoutError("the provider gave up")

    with pytest.raises(CircuitBreakerOpenError) as excinfo:
        await research()
    assert_cause(excinfo, AgentExecutionError)
    assert excinfo.value.reason == "execution_error"


async def test_a_worker_that_raises_its_own_timeout_in_a_thread(memory_dir: Path) -> None:
    orch = make_orchestrator(memory_dir, timeout_seconds=5.0, max_retries=1)

    @orch.guard_step("research")
    def research(ctx: StepContext) -> str:
        raise TimeoutError("the provider gave up")

    with pytest.raises(CircuitBreakerOpenError) as excinfo:
        await research()
    assert_cause(excinfo, AgentExecutionError)
