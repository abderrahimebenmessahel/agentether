"""The numbers of the report must be the numbers of the raw cells.

The report of the audit contradicted the evidence document: it announced
"450 000 tokens" where the raw cells hold 394 951, and it said that the
token count of the Google model was 0 while the evidence document showed
188 346.  Nothing stopped the two documents from drifting apart, because
nothing compared them with the raw data.

These tests are that comparison.  They fail when:

* a total of ``docs/evidence.md`` is not the sum of the raw cells;
* ``docs/evidence.md`` is not what the generator produces (it was edited
  by hand);
* a total of the final report is not the sum of the raw cells;
* a wrong total of the report is still there.

**The common set of the tasks.**  A run that stops in the middle of a task
can leave the arms of a cell with a different number of tasks.  A rate
computed on two different sets of tasks is not comparable, so every rate of
a cell is computed on the tasks that **every** arm of the cell completed,
and the tasks that were dropped are reported.  The tests of the section
below fail when a table mixes two different numbers of tasks.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "benchmarks" / "results" / "evidence-manifest.json"
EVIDENCE = ROOT / "docs" / "evidence.md"

#: Every report of the audit, the oldest first.  A report is a snapshot of
#: the state of its day, and a run that continues after a report was
#: written has more cells than the report could know: the report that is
#: checked against the raw cells is the **newest** one.
REPORTS: list[Path] = sorted((ROOT / "docs").glob("final-report-*.md"))
REPORT = REPORTS[-1]

sys_path = str(ROOT / "benchmarks")
if sys_path not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path)


def _manifest() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return data


def _cells_of(run: dict[str, Any]) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for name in run.get("progress") or []:
        path = ROOT / name
        assert path.exists(), f"the raw cell file {name} is missing"
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            cells.append(json.loads(line))
    return cells


def _totals(cells: list[dict[str, Any]]) -> dict[str, tuple[int, int, float]]:
    """The request, token and second totals of a set of cells, per model."""
    out: dict[str, tuple[int, int, float]] = {}
    for model in sorted({str(cell.get("model", "")) for cell in cells}):
        rows = [cell for cell in cells if str(cell.get("model", "")) == model]
        out[model] = (
            sum(int(cell.get("requests", 0) or 0) for cell in rows),
            sum(int(cell.get("tokens", 0) or 0) for cell in rows),
            round(sum(float(cell.get("seconds", 0.0) or 0.0) for cell in rows), 1),
        )
    return out


def _section(text: str, title: str) -> str:
    """The section of the document that starts with the title."""
    marker = f"## {title}"
    start = text.index(marker)
    rest = text[start + len(marker) :]
    end = rest.find("\n## ")
    return rest[:end] if end >= 0 else rest


def _totals_table(section: str) -> dict[str, tuple[int, int, float]]:
    """The rows of the totals table of a section, per model."""
    rows: dict[str, tuple[int, int, float]] = {}
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip().strip("*") for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4:
            continue
        model = cells[0]
        if model in ("Model", "total"):
            continue
        try:
            rows[model] = (int(cells[1]), int(cells[2]), float(cells[3]))
        except ValueError:
            continue
    return rows


def _total_row(section: str) -> tuple[int, int, float]:
    """The grand total row of the totals table of a section."""
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip().strip("*") for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] != "total":
            continue
        return int(cells[1]), int(cells[2]), float(cells[3])
    raise AssertionError("the totals table has no total row")


def test_the_manifest_lists_the_raw_cell_files() -> None:
    """The document is built from raw cells, and they are all there."""
    manifest = _manifest()
    assert manifest.get("runs"), "the manifest lists no run"
    for run in manifest["runs"]:
        assert run.get("progress"), f"the run {run.get('label')} lists no cell file"
        assert run.get("meta"), f"the run {run.get('label')} lists no meta file"
        assert (ROOT / run["meta"]).exists()


def test_the_totals_of_the_evidence_are_the_totals_of_the_raw_cells() -> None:
    """Every total of the evidence document is the sum of the raw cells."""
    document = EVIDENCE.read_text(encoding="utf-8")
    for run in _manifest()["runs"]:
        cells = _cells_of(run)
        section = _section(document, run["label"])
        expected = _totals(cells)
        assert _totals_table(section) == expected, f"the totals of {run['label']} are wrong"
        grand = (
            sum(value[0] for value in expected.values()),
            sum(value[1] for value in expected.values()),
            round(sum(value[2] for value in expected.values()), 1),
        )
        assert _total_row(section) == grand, f"the total of {run['label']} is wrong"
        # The two numbers of the header of the section.
        assert f"- Cells completed: {len(cells)}" in section
        assert f"- Model calls: {grand[0]}" in section


def test_the_evidence_document_is_generated_and_not_hand_edited() -> None:
    """The committed document is what the generator produces."""
    from evidence import build_markdown, load_manifest

    document = build_markdown(load_manifest(MANIFEST))
    assert document == EVIDENCE.read_text(encoding="utf-8"), (
        "docs/evidence.md is not what benchmarks/evidence.py produces: "
        "regenerate it instead of editing it"
    )


def _spaced(number: int) -> str:
    """The number with the thin spaces of the report (1 234 567)."""
    return f"{number:,}".replace(",", " ")


def test_the_report_totals_are_the_totals_of_the_raw_cells() -> None:
    """The final report does not contradict the raw data.

    The report states the requests and the tokens of every run and of the
    two runs together; the numbers of the raw cells must be among them.

    The report that is checked is the **newest** one: a report is a
    snapshot of the state of its day, and a run that continues after a
    report was written has more cells than the report could know.
    """
    report = REPORT.read_text(encoding="utf-8")
    cells: list[dict[str, Any]] = []
    for run in _manifest()["runs"]:
        run_cells = _cells_of(run)
        cells.extend(run_cells)
        requests = sum(int(cell.get("requests", 0) or 0) for cell in run_cells)
        tokens = sum(int(cell.get("tokens", 0) or 0) for cell in run_cells)
        assert _spaced(requests) in report or str(requests) in report, (
            f"the report does not state the {requests} requests of the run"
        )
        assert _spaced(tokens) in report or str(tokens) in report, (
            f"the report does not state the {tokens} tokens of the run"
        )
    requests = sum(int(cell.get("requests", 0) or 0) for cell in cells)
    tokens = sum(int(cell.get("tokens", 0) or 0) for cell in cells)
    assert _spaced(requests) in report or str(requests) in report
    assert _spaced(tokens) in report or str(tokens) in report


def test_the_wrong_totals_of_the_first_report_are_only_quoted_in_the_erratum() -> None:
    """The erratum is in the report and the old numbers are not asserted.

    The old numbers may be *quoted* by the erratum (that is the point of an
    erratum), but a line that quotes them must carry the corrected number
    next to them.
    """
    for path in REPORTS:
        report = path.read_text(encoding="utf-8")
        assert "Erratum" in report or "erratum" in report
        for line in report.splitlines():
            if "450 000 tokens" in line or "450000 tokens" in line:
                assert "394 951" in line, f"the old total is asserted without the new one: {line}"
        # The old claim about the Google model is gone, and its correction
        # is in the report.
        assert "token count of the Google model of\n  this report is therefore **0**" not in report
        assert "188 346" in report


@pytest.mark.parametrize("name", ["evidence.md", "final-report-2026-10-20.md"])
def test_the_documents_state_the_sign_convention(name: str) -> None:
    """Every document that shows a paired difference states the convention."""
    text = (ROOT / "docs" / name).read_text(encoding="utf-8")
    assert "sign convention" in text.lower()
    assert "agentether minus" in text.lower() or "guarded arm minus" in text.lower()


# ----------------------------------------------------------------------
# the common set of the tasks
# ----------------------------------------------------------------------
def _cell(
    model: str,
    condition: str,
    arm: str,
    task: str,
    *,
    correct: bool = True,
    reported: bool = True,
    requests: int = 1,
    tokens: int = 10,
) -> dict[str, Any]:
    """One synthetic cell."""
    return {
        "key": f"{model}|{condition}",
        "model": model,
        "condition": condition,
        "arm": arm,
        "task": task,
        "correct": correct,
        "reported_complete": reported,
        "false_completion": reported and not correct,
        "requests": requests,
        "tokens": tokens,
        "seconds": 1.0,
        "verifier_rejections": 0,
        "loop_detections": 0,
        "attempts": 1,
    }


def test_the_common_set_is_the_tasks_of_every_arm() -> None:
    """The common set of a cell is the intersection of the tasks of its arms."""
    from trial import common_task_set

    cells = [
        _cell("m", "injected", "naive", "t1"),
        _cell("m", "injected", "naive", "t2"),
        _cell("m", "injected", "naive", "t3"),
        _cell("m", "injected", "simple-retry", "t1"),
        _cell("m", "injected", "simple-retry", "t2"),
    ]
    assert common_task_set(cells, "m|injected") == ("t1", "t2")


def test_the_rates_are_computed_on_the_common_set() -> None:
    """An arm with more tasks does not get a rate on more tasks.

    The naive arm has three tasks and the baseline two: the rate of the
    naive arm is computed on the two tasks the two arms share, and the
    task that was dropped is reported.
    """
    from trial import summarise

    cells = [
        _cell("m", "injected", "naive", "t1", correct=True),
        _cell("m", "injected", "naive", "t2", correct=False, reported=False),
        _cell("m", "injected", "naive", "t3", correct=False, reported=False),
        _cell("m", "injected", "simple-retry", "t1", correct=True),
        _cell("m", "injected", "simple-retry", "t2", correct=True),
    ]
    summary = summarise(cells)
    naive = summary["m|injected|naive"]
    baseline = summary["m|injected|simple-retry"]
    assert naive["n"] == baseline["n"] == 2
    assert naive["n_dropped"] == 1
    assert baseline["n_dropped"] == 0
    # The rate of the naive arm is the rate of the two common tasks only.
    assert naive["correct"] == 1
    assert naive["correct_rate"] == 0.5


def test_the_paired_difference_uses_the_common_set() -> None:
    """The paired comparison is made on the common set too."""
    from trial import paired_difference

    cells = [
        _cell("m", "injected", "agentether", "t1", correct=True, reported=True),
        _cell("m", "injected", "agentether", "t2", correct=False, reported=True),
        _cell("m", "injected", "agentether", "t3", correct=True, reported=True),
        _cell("m", "injected", "naive", "t1", correct=True, reported=True),
        _cell("m", "injected", "naive", "t2", correct=True, reported=True),
    ]
    diff = paired_difference(cells, "m|injected", "agentether", "naive", "correct")
    assert diff["n"] == 2
    assert diff["only_agentether"] == 0
    assert diff["only_naive"] == 1
    assert diff["difference"] == -0.5


def _condition_table(section: str, condition: str) -> list[list[str]]:
    """The rows of the table of a condition of a section."""
    marker = f"### Condition: {condition}"
    start = section.index(marker)
    rest = section[start:]
    end = rest.find("\n### ")
    if end >= 0:
        rest = rest[:end]
    rows: list[list[str]] = []
    for line in rest.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells[0] in ("Model", "---") or set(cells[0]) == {"-"}:
            continue
        rows.append(cells)
    return rows


@pytest.mark.parametrize("run_label", ["Trial v3 (2026-10-20)", "Trial v2 (2026-10-20)"])
def test_no_table_of_the_evidence_mixes_two_numbers_of_tasks(run_label: str) -> None:
    """Every row of a cell of a table has the same N.

    A table that shows 6 for one arm and 7 for another compares two
    different sets of tasks, and the comparison is not the one the
    document claims to make.
    """
    document = EVIDENCE.read_text(encoding="utf-8")
    for run in _manifest()["runs"]:
        if run["label"] != run_label:
            continue
        section = _section(document, run["label"])
        conditions = {str(cell.get("condition", "")) for cell in _cells_of(run)}
        for condition in sorted(conditions):
            rows = _condition_table(section, condition)
            by_cell: dict[tuple[str, str], set[int]] = {}
            for cells in rows:
                if len(cells) < 4:
                    continue
                try:
                    n = int(cells[2])
                except ValueError:
                    continue
                by_cell.setdefault((cells[0], condition), set()).add(n)
            for key, values in by_cell.items():
                assert len(values) == 1, (
                    f"the table of {key} mixes the numbers of tasks {sorted(values)}"
                )


@pytest.mark.parametrize("run_label", ["Trial v3 (2026-10-20)", "Trial v2 (2026-10-20)"])
def test_the_n_of_the_tables_is_the_common_set_of_the_raw_cells(run_label: str) -> None:
    """The N of a table is the number of the tasks every arm completed."""
    from trial import common_task_set

    document = EVIDENCE.read_text(encoding="utf-8")
    for run in _manifest()["runs"]:
        if run["label"] != run_label:
            continue
        cells = _cells_of(run)
        section = _section(document, run["label"])
        conditions = {str(cell.get("condition", "")) for cell in cells}
        for condition in sorted(conditions):
            rows = _condition_table(section, condition)
            for row in rows:
                if len(row) < 4:
                    continue
                try:
                    n = int(row[2])
                except ValueError:
                    continue
                key = f"{row[0]}|{condition}"
                expected = len(common_task_set(cells, key))
                assert n == expected, (
                    f"the table shows N = {n} for {key} and the common set holds {expected} tasks"
                )
