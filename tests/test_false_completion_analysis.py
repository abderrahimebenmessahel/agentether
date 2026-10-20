"""The classification of the false completions.

The analysis of the trial v2 (``docs/false-completions.md``) says **why**
each false completion happened.  The document is generated from the sandboxes
of the run, and the sandboxes are not in the repository (they are the
runtime data of the trial), so these tests check two things:

* the classifier itself, on synthetic sandboxes where the cause is known;
* the numbers of the committed document against the raw cells, which are
  in the repository.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))

from analyze_false import CellAnalysis, Finding, classify_cell  # noqa: E402
from tasks import TASKS, Check, FileSpec, StepSpec, TaskSpec  # noqa: E402

CELLS = (
    ROOT / "benchmarks" / "results" / "trial-v2-cerebras-cells.jsonl",
    ROOT / "benchmarks" / "results" / "trial-v2-google-cells.jsonl",
)
DOCUMENT = ROOT / "docs" / "false-completions.md"


def _task() -> TaskSpec:
    """A task with one step and one file."""
    step = StepSpec(
        name="data",
        instruction="Write the file data.json.",
        files=(FileSpec(path="data.json"),),
    )
    return TaskSpec(
        name="t1",
        steps=(step,),
        checks=(Check("file_exists", "data.json"),),
    )


def _two_step_task() -> TaskSpec:
    """A task whose second step owns the file."""
    first = StepSpec(name="notes", instruction="Write notes.md.")
    second = StepSpec(
        name="data",
        instruction="Write the file data.json.",
        files=(FileSpec(path="data.json"),),
    )
    return TaskSpec(
        name="t1",
        steps=(first, second),
        checks=(Check("json_keys", "data.json", value="a,b,c"),),
    )


def _cell(arm: str, condition: str, task_index: int = 0) -> dict[str, Any]:
    return {
        "model": "fake/model",
        "condition": condition,
        "arm": arm,
        "task": "t1",
        "task_index": task_index,
        "false_completion": True,
    }


def _write(sandbox: Path, name: str, content: str) -> None:
    sandbox.mkdir(parents=True, exist_ok=True)
    (sandbox / name).write_text(content, encoding="utf-8")


def test_a_missing_file_without_a_fault_is_the_second_cause(tmp_path: Path) -> None:
    """A file that the model never produced is the cause (ii)."""
    analysis = classify_cell(_cell("naive", "natural"), _task(), tmp_path, tmp_path / "memory")
    assert [finding.cause for finding in analysis.findings] == ["ii"]


def test_a_file_damaged_by_a_fault_is_the_first_cause(tmp_path: Path) -> None:
    """A file that exists but is cut in the middle is the cause (i).

    The schedule of the task 6 (the task 07 of the trial), step 1 and
    attempt 1 is the fault ``truncate_file``: the file is cut in the
    middle, it still exists, and the existence check of the library cannot
    see the damage.
    """
    _write(tmp_path, "data.json", '{"a": 1, "b": "x')
    analysis = classify_cell(
        _cell("naive", "injected", task_index=6),
        _two_step_task(),
        tmp_path,
        tmp_path / "memory",
    )
    assert analysis.findings
    assert analysis.findings[0].cause == "i"
    assert analysis.findings[0].fault == "truncate_file"


def test_the_classifier_reports_the_failing_check(tmp_path: Path) -> None:
    """The finding names the check that failed and the step that owns it."""
    analysis = classify_cell(_cell("naive", "natural"), _task(), tmp_path, tmp_path / "memory")
    finding = analysis.findings[0]
    assert finding.check == "file_exists"
    assert finding.path == "data.json"
    assert finding.step == "data"
    assert finding.arm == "naive"
    assert finding.condition == "natural"


def test_the_cause_of_a_cell_is_the_cause_of_its_findings() -> None:
    """The cause of the cell is the most frequent cause of its findings."""
    analysis = CellAnalysis(cell={"arm": "naive"})
    assert analysis.cause == "?"
    analysis.findings = [
        Finding(
            task="t1",
            model="m",
            condition="natural",
            arm="naive",
            step="data",
            path="data.json",
            check="file_exists",
            detail="",
            cause="i",
        ),
        Finding(
            task="t1",
            model="m",
            condition="natural",
            arm="naive",
            step="data",
            path="data.json",
            check="file_exists",
            detail="",
            cause="iii",
        ),
        Finding(
            task="t1",
            model="m",
            condition="natural",
            arm="naive",
            step="data",
            path="data.json",
            check="file_exists",
            detail="",
            cause="iii",
        ),
    ]
    assert analysis.cause == "iii"


def _false_completions() -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for path in CELLS:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cells.append(json.loads(line))
    return [cell for cell in cells if cell.get("false_completion")]


def test_the_document_counts_the_false_completions_of_the_raw_cells() -> None:
    """The number of the false completions of the document is the raw one."""
    text = DOCUMENT.read_text(encoding="utf-8")
    cells = _false_completions()
    assert len(cells) == 17
    counts: dict[str, int] = {}
    for cell in cells:
        arm = str(cell["arm"])
        counts[arm] = counts.get(arm, 0) + 1
    for arm, count in counts.items():
        marker = f"### The arm {arm}\n"
        assert marker in text
        section = text.split(marker, 1)[1]
        # Only the table of the arm, not the sections that follow it.
        section = section.split("\n## ", 1)[0].split("\n### ", 1)[0]
        # The table of the arm holds one row per failing check; the number
        # of the (model, task) pairs of the table is the number of the
        # cells of the arm.
        pairs = set(
            re.findall(r"\| ([a-z0-9.\-]+) \| (natural|injected) \| (task\d\d-[a-z]+) \|", section)
        )
        assert len(pairs) == count, f"the table of the arm {arm} has the wrong tasks"


def test_the_document_states_the_two_mechanisms() -> None:
    """The document explains why the guarded arm caught what it caught."""
    text = DOCUMENT.read_text(encoding="utf-8")
    assert "Why the guarded arm caught" in text
    assert "artifacts_exist()" in text
    assert "the harness cut the file" in text


def test_the_task_set_is_the_committed_one() -> None:
    """The analysis uses the task set of the trial."""
    assert len(TASKS) == 20
    assert {task.name for task in TASKS} >= {"task02-orchard", "task07-trellis"}


@pytest.mark.parametrize("name", ["false-completions.md"])
def test_the_document_is_not_empty(name: str) -> None:
    """The document exists and is not a stub."""
    text = (ROOT / "docs" / name).read_text(encoding="utf-8")
    assert len(text) > 2000
