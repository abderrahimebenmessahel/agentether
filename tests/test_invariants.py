"""The invariants the library claims, each with a test.

This file exists because of the audit in ``docs/audit-notes.md``: every
invariant that was listed there without a test got one here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentether import (
    AgentExecutionError,
    AutoOrchestrator,
    CircuitBreakerOpenError,
    StateManager,
    StepContext,
    Telemetry,
    VerificationFailedError,
    artifacts_exist,
)


def telemetry_answer(step: str, **extra: object) -> str:
    """A telemetry answer for the given step."""
    payload: dict[str, object] = {
        "step": step,
        "status": "completed",
        "summary": "done",
        "progress": 100,
        "next_step": None,
        "artifacts": [],
    }
    payload.update(extra)
    return json.dumps(payload)


async def test_a_failed_verification_never_marks_the_step_completed(
    memory_dir: Path, work_dir: Path
) -> None:
    """The invariant: only a verified step is recorded as completed."""
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
        workdir=str(work_dir),
    )

    @orch.guard_step("research", verify=[artifacts_exist()])
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research", artifacts=["never-written.md"])

    with pytest.raises(CircuitBreakerOpenError):
        await research()

    state = await StateManager(memory_dir).load()
    assert state["completed_steps"] == []
    assert "research" not in (state.get("telemetry") or {})


async def test_a_lying_agent_cannot_write_under_another_step_name(
    memory_dir: Path,
) -> None:
    """The invariant: the state is keyed by the requested step, not by the claim."""
    orch = AutoOrchestrator(
        roadmap=["research", "write"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        # The agent claims to have done the *other* step.
        return telemetry_answer("write")

    with pytest.raises(CircuitBreakerOpenError):
        await research()

    state = await StateManager(memory_dir).load()
    assert "write" not in (state.get("telemetry") or {})
    assert state["completed_steps"] == []


async def test_the_compaction_never_drops_the_human_section(memory_dir: Path) -> None:
    """The invariant: the human text survives the compaction."""
    manager = StateManager(memory_dir, max_memory_chars=400)
    await manager.record_step(
        "research",
        Telemetry(
            step="research",
            status="completed",
            summary="x" * 500,
            progress=100,
        ),
        "out",
    )
    path = memory_dir / "PROJECT_MEMORY.md"
    text = path.read_text(encoding="utf-8")
    human = "the human note that must survive"
    text = text.replace(
        "<!-- agentether:human:start -->\n\n<!-- agentether:human:end -->",
        f"<!-- agentether:human:start -->\n{human}\n<!-- agentether:human:end -->",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)

    reloaded = StateManager(memory_dir, max_memory_chars=400)
    state = await reloaded.load()
    rendered = reloaded.render_context(state)
    assert human in rendered
    assert len(rendered) <= 400


async def test_the_recorded_output_is_the_one_of_the_last_attempt(
    memory_dir: Path,
) -> None:
    """The invariant: steps/NN_<slug>.md holds the latest output."""
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=3,
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        if ctx.attempt == 1:
            # The first attempt is not usable, so the step is retried.
            return "the first answer is not telemetry"
        return telemetry_answer("research", summary="the second answer")

    result = await research()
    assert result.attempts == 2
    stored = (memory_dir / "steps" / "01_research.md").read_text(encoding="utf-8")
    assert "the second answer" in stored
    assert "the first answer" not in stored


async def test_a_step_that_is_not_completed_is_never_resumed_as_completed(
    memory_dir: Path,
) -> None:
    """The invariant: only a completed step is resumed from the cache."""
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research", status="failed", summary="nope")

    with pytest.raises(AgentExecutionError):
        await research()

    state = await StateManager(memory_dir).load()
    assert state["completed_steps"] == []

    # A second orchestrator must not treat the step as done.
    orch2 = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
    )
    calls: list[int] = []

    @orch2.guard_step("research")
    async def research2(ctx: StepContext) -> str:
        calls.append(ctx.attempt)
        return telemetry_answer("research")

    result = await research2()
    assert result.from_cache is False
    assert calls == [1]


async def test_the_verification_result_is_kept_for_the_step(
    memory_dir: Path, work_dir: Path
) -> None:
    """The invariant: the verification outcome is recorded, not just logged."""
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
        workdir=str(work_dir),
    )

    @orch.guard_step("research", verify=[artifacts_exist()])
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research", artifacts=["missing.md"])

    with pytest.raises(CircuitBreakerOpenError):
        await research()

    state = await StateManager(memory_dir).load()
    record = state["verifications"]["research"]
    assert record["ok"] is False
    assert "missing.md" in record["reason"]


async def test_a_verification_error_keeps_the_evidence(memory_dir: Path, work_dir: Path) -> None:
    """The invariant: the evidence of a failed verification is kept."""
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
        workdir=str(work_dir),
    )

    @orch.guard_step("research", verify=[artifacts_exist()])
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research", artifacts=["missing.md"])

    with pytest.raises(CircuitBreakerOpenError) as excinfo:
        await research()
    cause = excinfo.value.__cause__
    assert isinstance(cause, VerificationFailedError)
    assert cause.evidence.get("missing") == ["missing.md"]


async def test_the_human_section_survives_carriage_returns(memory_dir: Path) -> None:
    """The invariant: the human text is preserved byte for byte.

    The universal newline mode would turn a "\r" into a "\n", so the file
    is read with newline="".
    """
    manager = StateManager(memory_dir)
    await manager.record_step(
        "research",
        Telemetry(step="research", status="completed", summary="s", progress=100),
        "out",
    )
    path = memory_dir / "PROJECT_MEMORY.md"
    with path.open("r", encoding="utf-8", newline="") as handle:
        text = handle.read()
    human = "first line\rsecond line"
    text = text.replace(
        "<!-- agentether:human:start -->\n\n<!-- agentether:human:end -->",
        f"<!-- agentether:human:start -->\n{human}\n<!-- agentether:human:end -->",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)

    reloaded = StateManager(memory_dir)
    await reloaded.load()
    assert human in reloaded.human_text
