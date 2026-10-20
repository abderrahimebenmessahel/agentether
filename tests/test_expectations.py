"""The declarative expectations of a step.

An expectation is the contract of a step: the files it must produce and
what those files must look like.  The library checks it after every
attempt, whatever the agent claimed, and the step cannot complete while an
expectation is unmet.

The tests below cover the invariant ("a step cannot complete while a
declared expectation is unmet"), the path confinement, the validators and
the corrective hint.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agentether import (
    AutoOrchestrator,
    CircuitBreakerOpenError,
    ConfigurationError,
    Expectation,
    StateManager,
    StepContext,
    VerificationFailedError,
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


def orchestrator(memory_dir: Path, work_dir: Path, **kwargs: object) -> AutoOrchestrator:
    """An orchestrator with a short timeout and no backoff."""
    options: dict[str, object] = {
        "roadmap": ["write"],
        "memory_dir": str(memory_dir),
        "timeout_seconds": 5,
        "max_retries": 3,
        "workdir": str(work_dir),
        "backoff_base": 0.0,
    }
    options.update(kwargs)
    return AutoOrchestrator(**options)  # type: ignore[arg-type]


# ----------------------------------------------------------------------
# the invariant
# ----------------------------------------------------------------------
async def test_a_step_cannot_complete_while_an_expectation_is_unmet(
    memory_dir: Path, work_dir: Path
) -> None:
    """The invariant: the declaration is checked, not the claim."""
    orch = orchestrator(memory_dir, work_dir, max_retries=1)

    @orch.guard_step("write", expects=["report.md"])
    async def write(ctx: StepContext) -> str:
        # The agent claims to be done and lists nothing at all.
        return telemetry_answer("write", artifacts=[])

    with pytest.raises(CircuitBreakerOpenError):
        await write()

    state = await StateManager(memory_dir).load()
    assert state["completed_steps"] == []
    assert "write" not in (state.get("telemetry") or {})


async def test_a_step_completes_when_the_expectation_is_met(
    memory_dir: Path, work_dir: Path
) -> None:
    """The expectation that is met lets the step complete."""
    (work_dir / "report.md").write_text("# Report\n", encoding="utf-8")
    orch = orchestrator(memory_dir, work_dir)

    @orch.guard_step("write", expects=["report.md"])
    async def write(ctx: StepContext) -> str:
        return telemetry_answer("write", artifacts=["report.md"])

    result = await write()
    assert result.telemetry is not None
    assert result.telemetry.status == "completed"
    state = await StateManager(memory_dir).load()
    assert state["completed_steps"] == ["write"]


async def test_the_expectation_is_checked_even_when_the_claim_lists_the_file(
    memory_dir: Path, work_dir: Path
) -> None:
    """The claim of the agent does not make the file exist."""
    orch = orchestrator(memory_dir, work_dir, max_retries=1)

    @orch.guard_step("write", expects=["report.md"])
    async def write(ctx: StepContext) -> str:
        return telemetry_answer("write", artifacts=["report.md"])

    with pytest.raises(CircuitBreakerOpenError):
        await write()


async def test_the_hint_names_the_missing_files(memory_dir: Path, work_dir: Path) -> None:
    """The corrective hint of the next attempt names the missing files."""
    orch = orchestrator(memory_dir, work_dir, max_retries=2)
    hints: list[str] = []

    @orch.guard_step("write", expects=["report.md", "data.json"])
    async def write(ctx: StepContext) -> str:
        if ctx.last_error:
            hints.append(ctx.last_error)
        return telemetry_answer("write")

    with pytest.raises(CircuitBreakerOpenError):
        await write()

    assert hints
    assert "report.md" in hints[0]
    assert "data.json" in hints[0]
    assert "missing" in hints[0].lower()


async def test_the_failure_is_a_retryable_verification_error(
    memory_dir: Path, work_dir: Path
) -> None:
    """The failure of an expectation is a retryable VerificationFailedError."""
    orch = orchestrator(memory_dir, work_dir, max_retries=1)

    @orch.guard_step("write", expects=["report.md"])
    async def write(ctx: StepContext) -> str:
        return telemetry_answer("write")

    with pytest.raises(CircuitBreakerOpenError) as info:
        await write()
    cause = info.value.__cause__
    assert isinstance(cause, VerificationFailedError)
    assert cause.evidence["missing"] == ["report.md"]


async def test_the_step_is_retried_until_the_expectation_is_met(
    memory_dir: Path, work_dir: Path
) -> None:
    """The step is retried and the second attempt completes it."""
    orch = orchestrator(memory_dir, work_dir, max_retries=3)
    seen: list[int] = []

    @orch.guard_step("write", expects=["report.md"])
    async def write(ctx: StepContext) -> str:
        seen.append(ctx.attempt)
        if ctx.attempt == 1:
            return telemetry_answer("write")
        (work_dir / "report.md").write_text("# Report\n", encoding="utf-8")
        return telemetry_answer("write", artifacts=["report.md"])

    result = await write()
    assert seen == [1, 2]
    assert result.attempts == 2
    assert result.telemetry is not None
    assert result.telemetry.status == "completed"


async def test_the_expectations_are_checked_on_every_attempt(
    memory_dir: Path, work_dir: Path
) -> None:
    """The declaration is evaluated whatever the agent claimed."""
    orch = orchestrator(memory_dir, work_dir, max_retries=2)
    events: list[dict[str, object]] = []
    orch.on("verification_failed", events.append)

    @orch.guard_step("write", expects=["report.md"])
    async def write(ctx: StepContext) -> str:
        # The agent says the step is not done: the step does not complete
        # either way, and the declaration is still evaluated.
        return telemetry_answer("write", status="in_progress", progress=10)

    with pytest.raises(CircuitBreakerOpenError):
        await write()

    assert events
    assert events[0]["reason"]
    assert "report.md" in str(events[0]["reason"])


# ----------------------------------------------------------------------
# the validators
# ----------------------------------------------------------------------
async def test_a_json_file_must_parse(memory_dir: Path, work_dir: Path) -> None:
    """A JSON file that does not parse does not satisfy the declaration."""
    (work_dir / "data.json").write_text('{"a": 1', encoding="utf-8")
    orch = orchestrator(memory_dir, work_dir, max_retries=1)

    @orch.guard_step("write", expects=[Expectation("data.json", json_valid=True)])
    async def write(ctx: StepContext) -> str:
        return telemetry_answer("write", artifacts=["data.json"])

    with pytest.raises(CircuitBreakerOpenError):
        await write()


async def test_a_json_file_must_have_the_declared_keys(memory_dir: Path, work_dir: Path) -> None:
    """The keys of the declaration are the keys of the file."""
    (work_dir / "data.json").write_text('{"a": 1}', encoding="utf-8")
    orch = orchestrator(memory_dir, work_dir, max_retries=1)

    @orch.guard_step("write", expects=[Expectation("data.json", json_keys=("a", "b"))])
    async def write(ctx: StepContext) -> str:
        return telemetry_answer("write", artifacts=["data.json"])

    with pytest.raises(CircuitBreakerOpenError):
        await write()


async def test_a_python_file_must_compile(memory_dir: Path, work_dir: Path) -> None:
    """A Python file that does not compile does not satisfy the declaration."""
    (work_dir / "build.py").write_text("def broken(:\n", encoding="utf-8")
    orch = orchestrator(memory_dir, work_dir, max_retries=1)

    @orch.guard_step("write", expects=[Expectation("build.py", python_valid=True)])
    async def write(ctx: StepContext) -> str:
        return telemetry_answer("write", artifacts=["build.py"])

    with pytest.raises(CircuitBreakerOpenError):
        await write()


async def test_a_markdown_file_must_have_its_headings(memory_dir: Path, work_dir: Path) -> None:
    """The headings of the declaration are the headings of the file."""
    (work_dir / "README.md").write_text("# Title\n", encoding="utf-8")
    orch = orchestrator(memory_dir, work_dir, max_retries=1)

    @orch.guard_step("write", expects=[Expectation("README.md", markdown_headings=("## Install",))])
    async def write(ctx: StepContext) -> str:
        return telemetry_answer("write", artifacts=["README.md"])

    with pytest.raises(CircuitBreakerOpenError):
        await write()


async def test_a_file_must_contain_the_declared_text(memory_dir: Path, work_dir: Path) -> None:
    """The content of the file must hold the declared pattern."""
    (work_dir / "README.md").write_text("# Title\n", encoding="utf-8")
    orch = orchestrator(memory_dir, work_dir, max_retries=1)

    @orch.guard_step("write", expects=[Expectation("README.md", contains=("def build",))])
    async def write(ctx: StepContext) -> str:
        return telemetry_answer("write", artifacts=["README.md"])

    with pytest.raises(CircuitBreakerOpenError):
        await write()


async def test_a_file_must_not_be_empty(memory_dir: Path, work_dir: Path) -> None:
    """An empty file does not satisfy the declaration."""
    (work_dir / "notes.md").write_text("", encoding="utf-8")
    orch = orchestrator(memory_dir, work_dir, max_retries=1)

    @orch.guard_step("write", expects=["notes.md"])
    async def write(ctx: StepContext) -> str:
        return telemetry_answer("write", artifacts=["notes.md"])

    with pytest.raises(CircuitBreakerOpenError):
        await write()


# ----------------------------------------------------------------------
# the confinement of the paths
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "path",
    ["/etc/passwd", "../outside.md", "sub/../../outside.md", "C:\\Windows\\system.ini"],
)
def test_an_absolute_or_escaping_path_is_refused(
    memory_dir: Path, work_dir: Path, path: str
) -> None:
    """A path that leaves the work directory is a programming error."""
    orch = orchestrator(memory_dir, work_dir)
    with pytest.raises(ConfigurationError):
        orch.guard_step("write", expects=[path])


def test_a_path_that_escapes_through_a_symbolic_link_is_refused(
    memory_dir: Path, work_dir: Path, tmp_path: Path
) -> None:
    """A symbolic link that points outside the work directory is refused."""
    if os.name == "nt":
        pytest.skip("symlinks are not supported on Windows without a privilege")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("secret", encoding="utf-8")
    (work_dir / "link").symlink_to(outside, target_is_directory=True)
    orch = orchestrator(memory_dir, work_dir)
    with pytest.raises(ConfigurationError):
        orch.guard_step("write", expects=["link/secret.md"])


def test_an_expectation_must_be_a_path_or_an_expectation(memory_dir: Path, work_dir: Path) -> None:
    """Anything else in the list is a programming error."""
    orch = orchestrator(memory_dir, work_dir)
    with pytest.raises(ConfigurationError):
        orch.guard_step("write", expects=[42])  # type: ignore[list-item]


def test_an_expectation_needs_a_path() -> None:
    """An expectation without a path is a programming error."""
    with pytest.raises(ConfigurationError):
        Expectation("")


# ----------------------------------------------------------------------
# the record of the failure
# ----------------------------------------------------------------------
async def test_the_ledger_records_the_failed_expectation(memory_dir: Path, work_dir: Path) -> None:
    """The claims ledger keeps the claim and the verdict of the library."""
    orch = orchestrator(memory_dir, work_dir, max_retries=1)

    @orch.guard_step("write", expects=["report.md"])
    async def write(ctx: StepContext) -> str:
        return telemetry_answer("write", artifacts=["report.md"])

    with pytest.raises(CircuitBreakerOpenError):
        await write()

    ledger = (memory_dir / "claims.jsonl").read_text(encoding="utf-8")
    assert "report.md" in ledger
    record = json.loads(ledger.splitlines()[0])
    assert record["verification"]["ok"] is False
    assert record["verification"]["evidence"]["missing"] == ["report.md"]
