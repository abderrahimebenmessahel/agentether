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
REPORT = ROOT / "docs" / "final-report-2026-10-20.md"

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


def test_the_report_totals_are_the_totals_of_the_raw_cells() -> None:
    """The final report does not contradict the raw data."""
    report = REPORT.read_text(encoding="utf-8")
    cells: list[dict[str, Any]] = []
    for run in _manifest()["runs"]:
        cells.extend(_cells_of(run))
    requests = sum(int(cell.get("requests", 0) or 0) for cell in cells)
    tokens = sum(int(cell.get("tokens", 0) or 0) for cell in cells)
    assert f"{requests} model calls" in report or f"{requests} requests" in report
    assert f"{tokens:,}".replace(",", " ") in report or str(tokens) in report


def test_the_wrong_totals_of_the_first_report_are_only_quoted_in_the_erratum() -> None:
    """The erratum is in the report and the old numbers are not asserted.

    The old numbers may be *quoted* by the erratum (that is the point of an
    erratum), but a line that quotes them must carry the corrected number
    next to them.
    """
    report = REPORT.read_text(encoding="utf-8")
    assert "Erratum" in report or "erratum" in report
    for line in report.splitlines():
        if "450 000 tokens" in line or "450000 tokens" in line:
            assert "394 951" in line, f"the old total is asserted without the new one: {line}"
    # The old claim about the Google model is gone, and its correction is
    # in the report.
    assert "token count of the Google model of\n  this report is therefore **0**" not in report
    assert "188 346" in report


@pytest.mark.parametrize("name", ["evidence.md", "final-report-2026-10-20.md"])
def test_the_documents_state_the_sign_convention(name: str) -> None:
    """Every document that shows a paired difference states the convention."""
    text = (ROOT / "docs" / name).read_text(encoding="utf-8")
    assert "sign convention" in text.lower()
    assert "agentether minus" in text.lower() or "guarded arm minus" in text.lower()
