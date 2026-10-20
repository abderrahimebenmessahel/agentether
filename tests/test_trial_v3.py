"""The parts of the trial v3: the new fault, the new task set and the arms.

The trial v3 adds a fault (``hide_file``), a task set and an arm that
declares what the step must produce.  These tests use a scripted fake
model; they never touch the network.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))

from harness import (
    FAULT_SEED,
    FAULT_SEED_V3,
    FAULTS,
    FAULTS_V3,
    fault_for,
    inject_fault,
    parse_file_blocks,
    run_arm_agentether,
    run_arm_naive,
    run_arm_simple_retry,
)
from tasks import Check, FileSpec, StepSpec, TaskSpec, expectations_of
from tasks_v3 import TASKS_V3

from agentether import Usage, WorkerOutput

_STEP_IN_PROMPT = re.compile(r'"step" must be exactly "([^"]+)"')


class ScriptedCaller:
    """A model that replays a script instead of calling a server."""

    def __init__(self, answer_for: Any) -> None:
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
    content: str = "# Notes\n## Context\nhello\n",
    artifacts: tuple[str, ...] = ("notes.md",),
    path: str = "notes.md",
    file_block: bool = True,
) -> str:
    """A raw model answer."""
    parts: list[str] = []
    if file_block:
        parts.append("````\nFILE: " + path + "\n" + content + "````")
    payload: dict[str, Any] = {
        "step": step,
        "status": "completed",
        "summary": "did the work",
        "progress": 100,
        "next_step": None,
        "artifacts": list(artifacts),
    }
    parts.append(json.dumps(payload))
    return "\n".join(parts)


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


# ----------------------------------------------------------------------
# the fault that hides a file
# ----------------------------------------------------------------------
def test_the_fault_that_hides_a_file_removes_it_and_its_name() -> None:
    """The claim mentions only the files the model really produced."""
    raw = answer(artifacts=("notes.md", "extra.md"), path="notes.md")
    faulty = inject_fault(raw, "hide_file", None)
    blocks = parse_file_blocks(faulty)
    assert [path for path, _ in blocks] == []
    data = json.loads(faulty[faulty.rfind("{") : faulty.rfind("}") + 1])
    assert data["artifacts"] == ["extra.md"]
    assert data["status"] == "completed"


def test_the_fault_that_hides_a_file_leaves_the_other_files() -> None:
    """Only one file is hidden."""
    raw = "````\nFILE: a.md\ncontent a\n````\n\n````\nFILE: b.md\ncontent b\n````\n\n" + json.dumps(
        {
            "step": "s",
            "status": "completed",
            "summary": "x",
            "progress": 100,
            "next_step": None,
            "artifacts": ["a.md", "b.md"],
        }
    )
    faulty = inject_fault(raw, "hide_file", None)
    blocks = parse_file_blocks(faulty)
    assert len(blocks) == 1
    data = json.loads(faulty[faulty.rfind("{") : faulty.rfind("}") + 1])
    assert data["artifacts"] == ["b.md"]


# ----------------------------------------------------------------------
# the schedule
# ----------------------------------------------------------------------
def test_the_v3_uses_another_seed_and_another_fault_set() -> None:
    """The trial v3 does not reuse the schedule of the trial v2."""
    assert FAULT_SEED_V3 != FAULT_SEED
    assert set(FAULTS_V3) - set(FAULTS) == {"hide_file"}
    assert len(FAULTS_V3) == len(FAULTS) + 1


def test_the_schedule_of_the_v3_differs_from_the_schedule_of_the_v2() -> None:
    """Two seeds give two different schedules."""
    v2 = [fault_for(index, 0, 1, FAULT_SEED, FAULTS) for index in range(40)]
    v3 = [fault_for(index, 0, 1, FAULT_SEED_V3, FAULTS_V3) for index in range(40)]
    assert v2 != v3


# ----------------------------------------------------------------------
# the task set
# ----------------------------------------------------------------------
def test_the_task_set_of_the_v3_is_new() -> None:
    """The tasks of the v3 are not the tasks of the v2."""
    from tasks import TASKS

    old = {task.name for task in TASKS}
    new = {task.name for task in TASKS_V3}
    assert len(new) == 20
    assert not (old & new)


def test_the_tasks_of_the_v3_have_the_same_shape() -> None:
    """Twenty tasks, three or four steps, a ground truth that is not empty."""
    for task in TASKS_V3:
        assert 3 <= len(task.steps) <= 4
        assert len(task.checks) >= 10


def test_the_expectations_of_a_step_are_built_from_its_visible_specification() -> None:
    """The expectation says what the step asks for."""
    for task in TASKS_V3:
        for step in task.steps:
            declared = expectations_of(step)
            assert declared
            paths = {expectation.path for expectation in declared}
            expected = {spec.path for spec in step.files}
            assert paths == expected


def test_the_visible_specification_says_what_the_ground_truth_checks() -> None:
    """The expectation of the v3 is as strong as the ground truth.

    Every file that the ground truth checks is declared by the visible
    specification of its step, and every check of a content is carried by
    the expectation of that file.
    """
    for task in TASKS_V3:
        declared = {
            expectation.path: expectation
            for step in task.steps
            for expectation in expectations_of(step)
        }
        checked = {check.path for check in task.checks}
        assert checked == set(declared)
        for check in task.checks:
            expectation = declared[check.path]
            if check.kind == "contains":
                assert check.value in expectation.contains
            elif check.kind == "headings":
                assert check.value in expectation.markdown_headings
            elif check.kind == "json_keys":
                assert set(check.value.split(",")) == set(expectation.json_keys)
            elif check.kind == "json_value":
                key, _, _value = check.value.partition("=")
                assert any(key in pattern for pattern in expectation.contains)
            elif check.kind == "python_valid":
                assert expectation.python_valid


# ----------------------------------------------------------------------
# the arms
# ----------------------------------------------------------------------
async def test_the_claims_only_arm_does_not_catch_a_file_it_never_claimed(
    tmp_path: Path,
) -> None:
    """The verifier of the claims cannot see a file the step owes."""
    task = make_task()
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    memory = tmp_path / "memory"
    memory.mkdir()
    # The model writes another file and claims that one: the verifier of
    # the claims has nothing to complain about.
    caller = ScriptedCaller(
        lambda step, attempt: answer(
            step, content="other" + chr(10), artifacts=("other.md",), path="other.md"
        )
    )

    result = await run_arm_agentether(
        task, sandbox, memory, caller, "natural", 0, expectations=None
    )
    assert result.believed is True
    assert result.verifier_rejections == 0


async def test_the_arm_with_the_expectations_catches_a_file_it_never_produced(
    tmp_path: Path,
) -> None:
    """The declaration of the step is what the library checks."""
    task = make_task()
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    memory = tmp_path / "memory"
    memory.mkdir()
    caller = ScriptedCaller(
        lambda step, attempt: answer(
            step, content="other" + chr(10), artifacts=("other.md",), path="other.md"
        )
    )
    declared = [expectations_of(step) for step in task.steps]

    result = await run_arm_agentether(
        task, sandbox, memory, caller, "natural", 0, expectations=declared
    )
    assert result.believed is False
    assert result.verifier_rejections > 0


async def test_the_two_guarded_arms_differ_only_in_the_expectations(
    tmp_path: Path,
) -> None:
    """With a model that produces the file, the two arms agree."""
    task = make_task()
    caller = ScriptedCaller(lambda step, attempt: answer(step))
    outcomes: list[tuple[bool, int]] = []
    for declared in (None, [expectations_of(step) for step in task.steps]):
        sandbox = tmp_path / f"sandbox{len(outcomes)}"
        sandbox.mkdir()
        memory = tmp_path / f"memory{len(outcomes)}"
        memory.mkdir()
        result = await run_arm_agentether(
            task, sandbox, memory, caller, "natural", 0, expectations=declared
        )
        outcomes.append((result.believed, result.attempts))
    assert outcomes[0] == outcomes[1]


async def test_the_naive_arm_believes_a_step_that_produced_nothing(
    tmp_path: Path,
) -> None:
    """The naive arm trusts the claim."""
    task = make_task()
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    caller = ScriptedCaller(lambda step, attempt: answer(step, file_block=False))
    result = await run_arm_naive(task, sandbox, caller, "natural", 0)
    assert result.believed is True


async def test_the_baseline_believes_a_step_that_produced_nothing(
    tmp_path: Path,
) -> None:
    """The baseline checks the contract, not the files."""
    task = make_task()
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    caller = ScriptedCaller(lambda step, attempt: answer(step, file_block=False))
    result = await run_arm_simple_retry(task, sandbox, caller, "natural", 0)
    assert result.believed is True


@pytest.mark.parametrize("fault", FAULTS_V3)
def test_every_fault_of_the_v3_leaves_a_valid_answer(fault: str) -> None:
    """No fault of the schedule breaks the answer in an unexpected way."""
    raw = answer(artifacts=("notes.md",))
    faulty = inject_fault(raw, fault, None)
    assert isinstance(faulty, str)
    assert faulty
