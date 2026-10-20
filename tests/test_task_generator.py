"""The procedural extension of the task set of the trial v3.

The protocol of the trial v3 planned sixty tasks per cell and the set had
twenty.  The twenty are extended by a **seeded** generator, and this file
pins the properties the extension must have:

* the generator is **deterministic**: the same seed always builds the same
  tasks, and another seed builds other ones;
* the tasks are **distinct**, and none of them reuses the subject of a task
  of another run;
* the twenty hand-written tasks are **untouched**: they are the first
  twenty of the combined set, in the same order, and the fault schedule of
  a task is a function of its index, so their schedule is unchanged too;
* the **ground truth** of a generated task passes on a correct solution and
  fails on a broken one, and the expectations of the guarded arm (which are
  built from the visible specification alone) fail on the same broken
  solution.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))

from harness import task_is_correct
from tasks import FileSpec, TaskSpec, expectations_of
from tasks_v3 import TASKS_V3
from tasks_v3_gen import (
    GENERATED_TASK_COUNT,
    SUBJECT_POOL,
    TASK_GENERATOR_SEED,
    TASKS_V3_FULL,
    build_generated_tasks,
)

from agentether import Telemetry, VerifyContext
from agentether.expectations import expectations_verifier


# ----------------------------------------------------------------------
# the reference solution
# ----------------------------------------------------------------------
def _content(spec: FileSpec) -> str:
    """The content of a file that satisfies its specification."""
    if spec.json_keys or spec.json_values:
        data: dict[str, object] = dict.fromkeys(spec.json_keys)
        for key, value in spec.json_values:
            data[key] = value
        if data.get("c") is None and "c" in data:
            data["c"] = []
        return json.dumps(data, indent=2) + "\n"
    if spec.python_valid:
        function = "task"
        number = "0"
        for item in spec.contains:
            if item.startswith("def "):
                function = item[len("def ") :]
            elif item.isdigit():
                number = item
        return (
            f'def {function}():\n    """The build of the task."""\n'
            f"    print({number})\n    return {number}\n"
        )
    parts: list[str] = []
    for heading in spec.headings:
        parts.extend([heading, ""])
    for item in spec.contains:
        parts.append(item)
    return "\n".join(parts) + "\n"


def write_correct_solution(task: TaskSpec, sandbox: Path) -> None:
    """Write the files of a task that satisfy its ground truth."""
    for step in task.steps:
        for spec in step.files:
            target = sandbox / spec.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(_content(spec), encoding="utf-8")


async def expectations_hold(task: TaskSpec, sandbox: Path) -> bool:
    """Whether the expectations of every step of a task hold in a sandbox."""
    for step in task.steps:
        declared = expectations_of(step)
        if not declared:
            continue
        verifier = expectations_verifier(declared)
        context = VerifyContext(
            step=step.name,
            telemetry=Telemetry(step=step.name, status="completed", summary="x", progress=100),
            raw_output="",
            memory_dir=sandbox,
            workdir=sandbox,
        )
        result = await verifier(context)
        if not result.ok:
            return False
    return True


# ----------------------------------------------------------------------
# the determinism
# ----------------------------------------------------------------------
def test_the_generator_is_deterministic() -> None:
    """The same seed builds the same tasks, every time."""
    first = build_generated_tasks()
    second = build_generated_tasks()
    assert [task.name for task in first] == [task.name for task in second]
    assert first == second


def test_another_seed_builds_other_tasks() -> None:
    """The seed is the only source of the randomness."""
    first = build_generated_tasks()
    other = build_generated_tasks(seed=TASK_GENERATOR_SEED + 1)
    assert [task.name for task in first] != [task.name for task in other]


def test_the_seed_is_declared() -> None:
    """The seed is a number, and it is not the seed of the fault schedule."""
    from harness import FAULT_SEED_V3

    assert isinstance(TASK_GENERATOR_SEED, int)
    assert TASK_GENERATOR_SEED != FAULT_SEED_V3


def test_the_tasks_of_a_prefix_do_not_depend_on_the_length() -> None:
    """A task keeps its subject when the grid grows."""
    short = build_generated_tasks(count=10)
    long = build_generated_tasks(count=20)
    assert [task.name for task in short] == [task.name for task in long[:10]]


# ----------------------------------------------------------------------
# the shape of the set
# ----------------------------------------------------------------------
def test_the_grid_has_sixty_tasks() -> None:
    """The grid of the protocol needs sixty tasks per cell."""
    assert len(TASKS_V3) == 20
    assert GENERATED_TASK_COUNT == 40
    assert len(TASKS_V3_FULL) == 60


def test_the_hand_written_tasks_are_untouched() -> None:
    """The first twenty tasks of the grid are the hand-written ones."""
    for index, task in enumerate(TASKS_V3):
        assert TASKS_V3_FULL[index] == task
        assert TASKS_V3_FULL[index].name == task.name


def test_the_generated_tasks_are_distinct() -> None:
    """No two tasks of the grid have the same name or the same subject."""
    names = [task.name for task in TASKS_V3_FULL]
    assert len(set(names)) == len(names)
    subjects = [name.split("-", 1)[1] for name in names]
    assert len(set(subjects)) == len(subjects)


def test_the_generated_tasks_do_not_reuse_a_subject_of_another_run() -> None:
    """A task of the grid is never a task of the v2 or of the v3."""
    from tasks import TASKS

    old_subjects = {task.name.split("-", 1)[1] for task in TASKS}
    v3_subjects = {task.name.split("-", 1)[1] for task in TASKS_V3}
    generated = {task.name.split("-", 1)[1] for task in build_generated_tasks()}
    assert not (generated & old_subjects)
    assert not (generated & v3_subjects)


def test_the_generated_tasks_have_the_same_shape_as_the_hand_written_ones() -> None:
    """Three or four steps, the same number of checks, the same kind of files."""
    for task in build_generated_tasks():
        assert 3 <= len(task.steps) <= 4
        assert len(task.checks) in (13, 16)
        assert len(task.expected_files) in (4, 5)


def test_the_mix_of_the_steps_is_the_mix_of_the_hand_written_tasks() -> None:
    """Half of the tasks have a report step, like the hand-written ones."""
    hand = [len(task.steps) for task in TASKS_V3]
    generated = [len(task.steps) for task in build_generated_tasks()]
    assert hand.count(3) == hand.count(4)
    assert generated.count(3) == generated.count(4)


def test_the_subject_pool_is_long_enough_for_the_grid() -> None:
    """The pool can be cut at any length without changing the tasks."""
    assert len(SUBJECT_POOL) >= 60
    assert len(set(SUBJECT_POOL)) == len(SUBJECT_POOL)


# ----------------------------------------------------------------------
# the ground truth
# ----------------------------------------------------------------------
@pytest.mark.parametrize("index", [0, 1, 17, 38, 39])
def test_the_ground_truth_passes_on_a_correct_solution(tmp_path: Path, index: int) -> None:
    """A task that does what it says passes its own ground truth."""
    task = build_generated_tasks()[index]
    sandbox = tmp_path / task.name
    sandbox.mkdir()
    write_correct_solution(task, sandbox)
    assert task_is_correct(task, sandbox) is True
    assert asyncio.run(expectations_hold(task, sandbox)) is True


def test_the_ground_truth_fails_on_a_missing_file(tmp_path: Path) -> None:
    """A task that does not produce every file fails its ground truth."""
    task = build_generated_tasks()[0]
    sandbox = tmp_path / task.name
    sandbox.mkdir()
    write_correct_solution(task, sandbox)
    missing = task.expected_files[-1]
    (sandbox / missing).unlink()
    assert task_is_correct(task, sandbox) is False
    assert asyncio.run(expectations_hold(task, sandbox)) is False


def test_the_ground_truth_fails_on_a_wrong_content(tmp_path: Path) -> None:
    """A task whose file holds the wrong content fails its ground truth."""
    task = build_generated_tasks()[1]
    sandbox = tmp_path / task.name
    sandbox.mkdir()
    write_correct_solution(task, sandbox)
    target = sandbox / "README.md"
    if not target.exists():
        target = sandbox / "GUIDE.md"
    target.write_text("nothing useful here\n", encoding="utf-8")
    assert task_is_correct(task, sandbox) is False
    assert asyncio.run(expectations_hold(task, sandbox)) is False


def test_the_ground_truth_fails_on_a_broken_script(tmp_path: Path) -> None:
    """A script that does not compile fails its ground truth."""
    task = build_generated_tasks()[2]
    sandbox = tmp_path / task.name
    sandbox.mkdir()
    write_correct_solution(task, sandbox)
    script = next(sandbox / path for path in task.expected_files if path.endswith(".py"))
    script.write_text("def broken(:\n", encoding="utf-8")
    assert task_is_correct(task, sandbox) is False
    assert asyncio.run(expectations_hold(task, sandbox)) is False


def test_every_generated_task_has_a_solvable_ground_truth(tmp_path: Path) -> None:
    """Every task of the generated set can be solved."""
    for task in build_generated_tasks():
        sandbox = tmp_path / task.name
        sandbox.mkdir()
        write_correct_solution(task, sandbox)
        assert task_is_correct(task, sandbox) is True, task.name


# ----------------------------------------------------------------------
# the expectations are as strong as the ground truth
# ----------------------------------------------------------------------
def test_the_visible_specification_says_what_the_ground_truth_checks() -> None:
    """The expectation of a generated task is as strong as its ground truth."""
    for task in build_generated_tasks():
        declared = {
            expectation.path: expectation
            for step in task.steps
            for expectation in expectations_of(step)
        }
        checked = {check.path for check in task.checks}
        assert checked == set(declared), task.name
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
