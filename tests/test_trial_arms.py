"""The arms of the trial must be comparable.

Run 1 of the trial (2026-10-20) compared three arms that were hobbled in
three different ways, so its numbers measured the harness and not the
policies:

1. the simple-retry arm wrote the files of an answer only when the claim
   said "completed", so it threw away work the naive arm kept -- the reason
   the baseline looked *worse* than doing nothing;
2. the prompt never told the model that ``progress`` is a number from 0 to
   100, so the agentether arm rejected every completed step as drift and
   never reached the second step;
3. the roadmap order stopped the agentether arm at the first failed step
   while the other two arms walked through every step.

These tests use a scripted fake model; they never touch the network.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))

from harness import (
    ATTEMPT_CAP,
    PROTOCOL,
    fault_for,
    run_arm_agentether,
    run_arm_naive,
    run_arm_simple_retry,
    task_is_correct,
)
from tasks import Check, FileSpec, StepSpec, TaskSpec

from agentether import Usage, WorkerOutput

_STEP_IN_PROMPT = re.compile(r'"step" must be exactly "([^"]+)"')


# ----------------------------------------------------------------------
# the fake model
# ----------------------------------------------------------------------
class ScriptedCaller:
    """A model that replays a script instead of calling a server.

    The script is a function of the step and of the attempt number inside
    that step, so every arm meets the same script even though they make a
    different number of calls.
    """

    def __init__(self, answer_for: Callable[[str, int], str | Exception]) -> None:
        self._answer_for = answer_for
        self.calls: list[tuple[str, int]] = []
        self._attempts: dict[str, int] = {}

    async def call(self, prompt: str) -> WorkerOutput:
        """One scripted answer."""
        match = _STEP_IN_PROMPT.search(prompt)
        step = match.group(1) if match else "?"
        attempt = self._attempts.get(step, 0) + 1
        self._attempts[step] = attempt
        self.calls.append((step, attempt))
        item = self._answer_for(step, attempt)
        if isinstance(item, Exception):
            raise item
        return WorkerOutput(text=item, usage=Usage(input_tokens=11, output_tokens=7))


def answer(
    step: str = "notes",
    status: str = "completed",
    progress: int | None = 100,
    content: str = "# Notes\n## Context\nhello\n",
    artifacts: tuple[str, ...] = ("notes.md",),
    file_block: bool = True,
    step_in_telemetry: str | None = None,
) -> str:
    """A raw model answer, optionally a broken one."""
    parts: list[str] = []
    if file_block:
        parts.append("```\nFILE: notes.md\n" + content + "```")
    payload: dict[str, Any] = {
        "step": step_in_telemetry or step,
        "status": status,
        "summary": "did the work",
        "progress": progress,
        "next_step": None,
        "artifacts": list(artifacts),
    }
    parts.append(json.dumps(payload))
    return "\n".join(parts)


def broken_answer(step: str = "notes") -> str:
    """An answer without a usable telemetry object."""
    return "```\nFILE: notes.md\n# Notes\n## Context\nhello\n```\nI am done, sorry."


def make_task() -> TaskSpec:
    """A one step task with a ground truth the arms never see."""
    step = StepSpec(
        name="notes",
        instruction="Write the file notes.md with the heading '## Context'.",
        files=(FileSpec(path="notes.md"),),
    )
    checks = (
        Check("file_exists", "notes.md"),
        Check("contains", "notes.md", value="## Context"),
    )
    return TaskSpec(name="t1", steps=(step,), checks=checks)


async def run_arm(
    arm: str,
    task: TaskSpec,
    sandbox: Path,
    memory: Path,
    caller: ScriptedCaller,
    condition: str = "natural",
) -> Any:
    """Run one arm and return its result."""
    if arm == "naive":
        return await run_arm_naive(task, sandbox, caller, condition, 0)
    if arm == "simple-retry":
        return await run_arm_simple_retry(task, sandbox, caller, condition, 0)
    return await run_arm_agentether(task, sandbox, memory, caller, condition, 0)


# ----------------------------------------------------------------------
# the simple-retry arm is never worse than the naive arm
# ----------------------------------------------------------------------
SCENARIOS: dict[str, Callable[[str, int], str | Exception]] = {
    "the first answer is good": lambda step, attempt: answer(),
    "the first telemetry is broken": lambda step, attempt: (
        answer() if attempt >= 2 else broken_answer()
    ),
    "the first status is in_progress": lambda step, attempt: (
        answer() if attempt >= 2 else answer(status="in_progress", progress=50)
    ),
    "the first call times out": lambda step, attempt: (
        answer() if attempt >= 2 else TimeoutError("the worker timed out")
    ),
    "the first call fails": lambda step, attempt: (
        answer() if attempt >= 2 else RuntimeError("the connection dropped")
    ),
    "the first step name is wrong": lambda step, attempt: (
        answer() if attempt >= 2 else answer(step_in_telemetry="something_else")
    ),
    "nothing ever works": lambda step, attempt: broken_answer(),
}


@pytest.mark.parametrize("name", sorted(SCENARIOS))
async def test_the_simple_retry_arm_is_never_worse_than_the_naive_arm(
    name: str, tmp_path: Path
) -> None:
    """A retry may cost requests, but it may never cost a result.

    This is the property that run 1 broke: the simple-retry arm scored
    *worse* than the naive arm, which is impossible for a baseline that
    only adds retries.
    """
    script = SCENARIOS[name]
    task = make_task()

    naive = await run_arm(
        "naive", task, tmp_path / "naive", tmp_path / "naive-mem", ScriptedCaller(script)
    )
    retry = await run_arm(
        "simple-retry", task, tmp_path / "retry", tmp_path / "retry-mem", ScriptedCaller(script)
    )

    assert retry.believed >= naive.believed, name
    assert retry.attempts >= naive.attempts, name
    if name != "nothing ever works":
        assert retry.believed is True, name


async def test_a_retry_never_destroys_a_valid_file(tmp_path: Path) -> None:
    """The file of a failed attempt must survive the retry.

    Run 1 wrote the files only when the claim said "completed", so the
    baseline lost a file that the model had really produced.
    """
    task = make_task()
    sandbox = tmp_path / "retry"
    sandbox.mkdir()

    def script(step: str, attempt: int) -> str | Exception:
        if attempt == 1:
            # A valid file, but the claim says the step is not finished.
            return answer(status="in_progress", progress=50)
        return TimeoutError("the worker timed out")

    result = await run_arm_simple_retry(task, sandbox, ScriptedCaller(script), "natural", 0)

    assert result.believed is False
    written = sandbox / "notes.md"
    assert written.is_file(), "the retry destroyed the file of the first attempt"
    assert "## Context" in written.read_text(encoding="utf-8")


async def test_every_arm_keeps_the_files_of_every_answer(tmp_path: Path) -> None:
    """The files of an answer are a fact of the sandbox, not of the claim.

    All three arms must leave the same files behind when the model produced
    the same answers, otherwise the ground truth of the trial compares
    different amounts of work.
    """
    task = make_task()
    script = lambda step, attempt: answer(status="in_progress", progress=50)  # noqa: E731

    for arm in ("naive", "simple-retry", "agentether"):
        sandbox = tmp_path / arm
        sandbox.mkdir()
        await run_arm(arm, task, sandbox, tmp_path / f"{arm}-mem", ScriptedCaller(script))
        assert (sandbox / "notes.md").is_file(), arm


# ----------------------------------------------------------------------
# the agentether arm
# ----------------------------------------------------------------------
async def test_the_agentether_arm_rejects_a_claim_without_the_file(tmp_path: Path) -> None:
    """A claim of "done" without the file is not a completion.

    The naive arm believes it; the agentether arm does not.  This is the
    behaviour the trial is built to measure.
    """
    task = make_task()
    lying = answer(file_block=False)

    naive = await run_arm(
        "naive",
        task,
        tmp_path / "naive",
        tmp_path / "naive-mem",
        ScriptedCaller(lambda step, attempt: lying),
    )
    guarded = await run_arm(
        "agentether",
        task,
        tmp_path / "guarded",
        tmp_path / "guarded-mem",
        ScriptedCaller(lambda step, attempt: lying),
    )

    assert naive.believed is True, "the naive arm trusts the claim"
    assert guarded.believed is False, "the guarded arm accepted a claim without the file"
    assert guarded.verifier_rejections >= 1


async def test_the_agentether_arm_completes_a_good_answer(tmp_path: Path) -> None:
    """A good answer completes the step, and the file is on disk."""
    task = make_task()
    sandbox = tmp_path / "guarded"
    sandbox.mkdir()

    result = await run_arm_agentether(
        task,
        sandbox,
        tmp_path / "mem",
        ScriptedCaller(lambda step, attempt: answer()),
        "natural",
        0,
    )

    assert result.believed is True
    assert task_is_correct(task, sandbox)


async def test_the_agentether_arm_continues_after_a_failed_step(tmp_path: Path) -> None:
    """A step that could not be done must not stop the task.

    The roadmap order was the third defect of run 1: the agentether arm
    stopped at the first failed step while the other arms walked through
    every step, so the arms were never comparable.
    """
    failing = StepSpec(name="first", instruction="Write notes.md.", files=())
    second = StepSpec(name="second", instruction="Write other.md.", files=())
    task = TaskSpec(
        name="t2",
        steps=(failing, second),
        checks=(Check("file_exists", "other.md"),),
    )
    sandbox = tmp_path / "guarded"
    sandbox.mkdir()

    def script(step: str, attempt: int) -> str:
        if step == "first":
            return broken_answer(step)
        return "```\nFILE: other.md\nok\n```\n" + json.dumps(
            {
                "step": "second",
                "status": "completed",
                "summary": "s",
                "progress": 100,
                "next_step": None,
                "artifacts": ["other.md"],
            }
        )

    result = await run_arm_agentether(
        task, sandbox, tmp_path / "mem", ScriptedCaller(script), "natural", 0
    )

    assert result.step_verdicts == [False, True]
    assert (sandbox / "other.md").is_file()


# ----------------------------------------------------------------------
# the protocol
# ----------------------------------------------------------------------
def test_the_protocol_tells_the_model_the_scale_of_progress() -> None:
    """The contract treats a progress below 100 as drift, so the prompt
    must say what the scale is."""
    assert "between 0 and 100" in PROTOCOL
    assert "100" in PROTOCOL
    assert '"progress" is a number' in PROTOCOL


def test_the_progress_of_a_completed_step_is_accepted() -> None:
    """The drift check of the library must not fire on a well formed answer.

    A progress of 100 with the status "completed" is the only combination
    the contract accepts, and the prompt asks for exactly that.
    """
    from agentether import parse_telemetry

    telemetry = parse_telemetry(answer(), "notes")
    assert telemetry.status == "completed"
    assert telemetry.progress == 100


# ----------------------------------------------------------------------
# the fault schedule
# ----------------------------------------------------------------------
def test_the_fault_schedule_is_a_function_of_the_step_and_the_attempt() -> None:
    """The same (task, step, attempt) always gives the same fault."""
    first = [fault_for(0, 0, attempt) for attempt in range(1, 6)]
    second = [fault_for(0, 0, attempt) for attempt in range(1, 6)]
    assert first == second


def test_the_fault_schedule_does_not_depend_on_the_other_steps() -> None:
    """The attempt number is the one *inside* the step.

    Run 1 keyed the schedule on a counter that ran across the whole task,
    so an arm that retried more met different faults for the same step.
    """
    assert fault_for(0, 0, 1) == fault_for(0, 0, 1)
    # The schedule of a step must not change when the schedule of another
    # step is asked for.
    before = fault_for(3, 2, 1)
    fault_for(3, 1, 1)
    fault_for(3, 0, 1)
    assert fault_for(3, 2, 1) == before


def test_the_attempt_cap_is_the_same_for_the_two_arms_that_retry() -> None:
    assert ATTEMPT_CAP == 3
