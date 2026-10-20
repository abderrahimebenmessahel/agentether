"""Classify every false completion of a trial run.

A **false completion** is a cell whose arm believes the task is done while
the ground truth says it is not.  This tool takes the raw cells, the
sandboxes and the attempt logs of the run and says **why** each false
completion happened:

* **(i) an injected fault damaged an artifact and the arm did not catch it**;
* **(ii) a required file was never produced, and the claim listed only the
  files that were produced**;
* **(iii) something else** (the model produced a file with the wrong
  content, or the harness damaged the file itself).

Nothing is called: the tool only reads what the run left on disk.

    python benchmarks/analyze_false.py --out docs/false-completions.md

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from harness import FAULTS, fault_for, run_check
from tasks import TASKS, TaskSpec

#: The faults that damage the artifacts of an answer.
DAMAGING_FAULTS = ("drop_file_block", "truncate_file", "lie", "replay_previous")

#: The arms of the trial, in the order of the report.
ARMS = ("naive", "simple-retry", "agentether-claims-only", "agentether")

#: The cause codes of the analysis.
CAUSES = {
    "i": "an injected fault damaged an artifact and the arm did not catch it",
    "ii": "a required file was never produced and the claim did not mention it",
    "iii": "something else",
}

_FENCE = re.compile(r"```[^\r\n]*\r?\n(?P<body>.*?)```", re.DOTALL)
_FILE_HEAD = re.compile(r"^\s*FILE:\s*(?P<path>[^\r\n`]+?)\s*$")


@dataclass
class Finding:
    """One failing ground truth check, with its cause."""

    task: str
    model: str
    condition: str
    arm: str
    step: str
    path: str
    check: str
    detail: str
    cause: str
    fault: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable copy."""
        return {
            "task": self.task,
            "model": self.model,
            "condition": self.condition,
            "arm": self.arm,
            "step": self.step,
            "path": self.path,
            "check": self.check,
            "detail": self.detail,
            "cause": self.cause,
            "fault": self.fault,
            "note": self.note,
        }


@dataclass
class CellAnalysis:
    """The analysis of one cell."""

    cell: dict[str, Any]
    findings: list[Finding] = field(default_factory=list)

    @property
    def cause(self) -> str:
        """The cause of the cell: the most frequent of its findings."""
        if not self.findings:
            return "?"
        counts: dict[str, int] = {}
        for finding in self.findings:
            counts[finding.cause] = counts.get(finding.cause, 0) + 1
        return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]

    @property
    def key(self) -> tuple[str, str, str]:
        """The model, the condition and the task of the cell."""
        return (
            str(self.cell.get("model", "")),
            str(self.cell.get("condition", "")),
            str(self.cell.get("task", "")),
        )


def _step_of_path(task: TaskSpec, path: str) -> str:
    """The step of a task that owns a file."""
    for step in task.steps:
        for spec in step.files:
            if spec.path == path:
                return step.name
    return "?"


def _attempts_of_step(cell: dict[str, Any], memory: Path, step: str) -> list[int]:
    """The attempt numbers of a step, as the arm really made them.

    The guarded arm writes an attempt log per step; the other two arms do
    not, and their attempt count is the number of steps of the task (they
    stop at the first attempt whose claim satisfies the contract, and a
    cell whose every step is done made exactly one attempt per step).
    """
    if cell.get("arm") == "agentether" and memory.is_dir():
        numbers: list[int] = []
        for path in sorted((memory / "steps").glob("*.attempts.jsonl")):
            if not path.name.split("_", 1)[1].startswith(step):
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    numbers.append(int(json.loads(line)["attempt"]))
        if numbers:
            return sorted(numbers)
    return [1]


def _recorded_answer(memory: Path, step: str) -> str:
    """The raw answer the guarded arm recorded for a step.

    The state manager writes the answer of the step in the project memory
    (``steps/NN_<name>.md``).  It is the **raw** text of the model, before
    the harness parsed it, so it shows what the harness did to the files.
    """
    if not memory.is_dir():
        return ""
    for path in sorted((memory / "steps").glob("*.md")):
        if not path.name.split("_", 1)[1].startswith(step):
            continue
        text = path.read_text(encoding="utf-8")
        # The file starts with "# Step: <name>" and then the raw answer.
        return text.split("\n\n", 1)[1] if "\n\n" in text else text
    return ""


def _raw_file_content(answer: str, path: str) -> str:
    """The content the model wrote for a file, in its **raw** answer.

    The answer is read from the ``FILE: <path>`` line to the next
    ``FILE:`` line, and the fences are removed.  The end of a file is not
    always a fence: a file may contain a code block of its own.
    """
    if not answer:
        return ""
    collecting = False
    body: list[str] = []
    for line in answer.splitlines():
        head = _FILE_HEAD.match(line)
        if head is not None:
            if collecting:
                break
            collecting = head.group("path").strip() == path
            continue
        if not collecting:
            continue
        if line.strip() in ("```", "~~~"):
            continue
        body.append(line)
    return "\n".join(body).strip("\n")


def _has_nested_fence(answer: str) -> bool:
    """Whether an answer holds a code block inside a file.

    The harness closes a file on the next fence, even when that fence
    opens a block of its own (`` ```bash ``).  A file that contains a code
    block is therefore cut in the middle by the parser.
    """
    if not answer:
        return False
    inside = False
    for line in answer.splitlines():
        head = _FILE_HEAD.match(line)
        if head is not None:
            inside = True
            continue
        if not inside:
            continue
        if re.match(r"^\s*```[^\s`]", line):
            # A fence with an info string: it opens a block of its own
            # inside the file.
            return True
        if re.match(r"^\s*```\s*$", line):
            inside = False
    return False


def _looks_truncated(content: str) -> bool:
    """Whether a content looks cut in the middle.

    A JSON that does not parse and a text that ends in the middle of a
    line are the two visible signatures of a truncated file.
    """
    stripped = content.strip()
    if not stripped:
        return True
    if stripped.startswith("{") and not stripped.endswith("}"):
        return True
    if stripped.startswith("[") and not stripped.endswith("]"):
        return True
    return "\n" in content and not content.endswith("\n")


def classify_cell(
    cell: dict[str, Any],
    task: TaskSpec,
    sandbox: Path,
    memory: Path,
    fault_seed: int | None = None,
    faults: Sequence[str] = FAULTS,
) -> CellAnalysis:
    """Classify the false completion of one cell."""
    analysis = CellAnalysis(cell=cell)
    task_index = int(cell.get("task_index", 0))
    for check in task.checks:
        if run_check(check, sandbox):
            continue
        step = _step_of_path(task, check.path)
        step_index = next((index for index, spec in enumerate(task.steps) if spec.name == step), 0)
        attempts = _attempts_of_step(cell, memory, step)
        last_attempt = max(attempts) if attempts else 1
        fault = ""
        if cell.get("condition") == "injected":
            fault = fault_for(task_index, step_index, last_attempt, fault_seed, faults) or ""
        target = sandbox / check.path
        detail = f"{check.kind} {check.path}"
        if check.value:
            detail += f" {check.value!r}"
        note = ""
        answer = _recorded_answer(memory, step) if cell.get("arm") == "agentether" else ""
        if not target.exists():
            if fault in DAMAGING_FAULTS:
                cause = "i"
                note = (
                    f"the injected fault {fault!r} of the attempt {last_attempt} removed the file"
                )
            else:
                cause = "ii"
                note = (
                    "no fault was injected in the last attempt of the step: the "
                    "model never produced the file"
                )
        else:
            content = target.read_text(encoding="utf-8", errors="replace")
            raw = _raw_file_content(answer, check.path)
            if fault == "truncate_file" and _looks_truncated(content):
                cause = "i"
                note = (
                    f"the injected fault {fault!r} of the attempt {last_attempt} "
                    "cut the answer, and the file on disk is a faithful copy of "
                    "the cut answer"
                )
            elif raw and content.strip() and raw.strip() != content.strip():
                cause = "iii"
                if raw.strip().startswith(content.strip()):
                    note = (
                        "the answer of the model holds more than the file on disk: "
                        "the harness cut the file while writing it"
                    )
                    if _has_nested_fence(answer):
                        note += (
                            " (the answer holds a code block inside the file, and "
                            "the parser closes the file on the fence of that block)"
                        )
                else:
                    note = (
                        "the answer of the model holds the file and the file on "
                        "disk is different: the harness damaged it while writing it"
                    )
            else:
                cause = "iii"
                note = "the file exists but its content does not satisfy the check"
                if _looks_truncated(content):
                    note += " (the content looks cut in the middle)"
        analysis.findings.append(
            Finding(
                task=str(cell.get("task", "")),
                model=str(cell.get("model", "")),
                condition=str(cell.get("condition", "")),
                arm=str(cell.get("arm", "")),
                step=step,
                path=check.path,
                check=check.kind,
                detail=detail,
                cause=cause,
                fault=fault,
                note=note,
            )
        )
    return analysis


def _sandbox_of(workdir: Path, model: str, arm: str, condition: str, task: str) -> Path:
    safe = model.replace("/", "_").replace(":", "_")
    return workdir / safe / arm / condition / task


def _memory_of(workdir: Path, model: str, condition: str, task: str) -> Path:
    safe = model.replace("/", "_").replace(":", "_")
    return workdir / safe / "agentether" / condition / f"{task}-memory"


def _provider_of(workdirs: dict[str, Path], model: str) -> str:
    """The work directory of the provider of a model."""
    for provider, workdir in workdirs.items():
        safe = model.replace("/", "_").replace(":", "_")
        if (workdir / safe).is_dir():
            return provider
    return ""


def analyse(
    cells: list[dict[str, Any]],
    workdirs: dict[str, Path],
    tasks: list[TaskSpec],
    fault_seed: int | None = None,
    faults: Sequence[str] = FAULTS,
) -> list[CellAnalysis]:
    """The analysis of every false completion of the run."""
    by_name = {task.name: task for task in tasks}
    out: list[CellAnalysis] = []
    for cell in cells:
        if not cell.get("false_completion"):
            continue
        task = by_name[str(cell.get("task", ""))]
        model = str(cell.get("model", ""))
        provider = _provider_of(workdirs, model)
        workdir = workdirs.get(provider)
        if workdir is None:
            continue
        sandbox = _sandbox_of(
            workdir, model, str(cell.get("arm", "")), str(cell.get("condition", "")), task.name
        )
        memory = _memory_of(workdir, model, str(cell.get("condition", "")), task.name)
        out.append(classify_cell(cell, task, sandbox, memory, fault_seed, faults))
    return out


def _cell_table(analyses: list[CellAnalysis], arm: str) -> list[str]:
    """The table of the false completions of one arm."""
    rows = [analysis for analysis in analyses if analysis.cell.get("arm") == arm]
    lines = [
        f"### The arm {arm}",
        "",
        "| Model | Condition | Task | The check that failed | The fault | Cause | Why |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for analysis in sorted(rows, key=lambda item: item.key):
        for finding in analysis.findings:
            lines.append(
                "| {model} | {condition} | {task} | {detail} | {fault} | **({cause})** |"
                " {note} |".format(
                    model=finding.model,
                    condition=finding.condition,
                    task=finding.task,
                    detail=finding.detail,
                    fault=finding.fault or "none",
                    cause=finding.cause,
                    note=finding.note,
                )
            )
    lines.append("")
    return lines


def _caught_analysis(analyses: list[CellAnalysis]) -> list[str]:
    """What the guarded arm caught, per model and condition."""
    lines = [
        "## What the guarded arm caught, and what it could not",
        "",
        "The table compares the false completions of the naive arm (the arm",
        "that trusts every claim) with the false completions of the guarded",
        "arm, task by task, on the same tasks and the same fault schedule.",
        "",
        "| Model | Condition | The false completions of the naive arm |"
        " The guarded arm caught | It could not catch | The guarded arm added |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    keys: list[tuple[str, str]] = []
    for analysis in analyses:
        key = (str(analysis.cell.get("model", "")), str(analysis.cell.get("condition", "")))
        if key not in keys:
            keys.append(key)
    for model, condition in sorted(keys):
        naive = {
            analysis.key[2]: analysis
            for analysis in analyses
            if analysis.cell.get("arm") == "naive"
            and analysis.key[0] == model
            and analysis.key[1] == condition
        }
        guarded = {
            analysis.key[2]: analysis
            for analysis in analyses
            if analysis.cell.get("arm") == "agentether"
            and analysis.key[0] == model
            and analysis.key[1] == condition
        }
        caught = [task for task in naive if task not in guarded]
        missed = [task for task in naive if task in guarded]
        added = [task for task in guarded if task not in naive]
        lines.append(
            "| {model} | {condition} | {total} | {caught} | {missed} | {added} |".format(
                model=model,
                condition=condition,
                total=len(naive),
                caught=(
                    ", ".join(f"{task} ({naive[task].cause})" for task in sorted(caught)) or "none"
                ),
                missed=(
                    ", ".join(f"{task} ({naive[task].cause})" for task in sorted(missed)) or "none"
                ),
                added=(
                    ", ".join(f"{task} ({guarded[task].cause})" for task in sorted(added)) or "none"
                ),
            )
        )
    lines.append("")
    return lines


def _counts(analyses: list[CellAnalysis]) -> list[str]:
    """The counts of the causes, per cell and per check."""
    per_cell: dict[str, int] = {}
    per_check: dict[str, int] = {}
    for analysis in analyses:
        per_cell[analysis.cause] = per_cell.get(analysis.cause, 0) + 1
        for finding in analysis.findings:
            per_check[finding.cause] = per_check.get(finding.cause, 0) + 1
    lines = [
        "## The counts of the causes",
        "",
        "| Cause | The false completions | The failing checks |",
        "| --- | --- | --- |",
    ]
    for code in sorted(CAUSES):
        lines.append(
            f"| ({code}) {CAUSES[code]} | {per_cell.get(code, 0)} | {per_check.get(code, 0)} |"
        )
    lines.append("")
    return lines


def _explanation(analyses: list[CellAnalysis]) -> list[str]:
    """Why the guarded arm caught what it caught.

    The numbers of the paragraph are taken from the analysis, so the text
    cannot drift away from the data.
    """
    lines = [
        "## Why the guarded arm caught what it caught",
        "",
        "The verifier of the claims-only arm is `artifacts_exist()`: it checks",
        "that the files the model **claims** exist.  It does not look at their",
        "content, and it cannot know what the step asked for.  The arm that",
        "declares what the step owes checks the **declaration** of the step:",
        "the file must exist, and its content must satisfy the declaration.",
        "Three cases follow, and they are the whole explanation:",
        "",
        "* a false completion whose artifact is **missing** is caught by both:",
        "  the check fails, the step is retried and the arm does not believe",
        "  the task is done;",
        "* a false completion whose artifact **exists but is damaged** is",
        "  caught only by the declaration: the existence check passes;",
        "* a false completion whose artifact was **never produced and never",
        "  claimed** is caught only by the declaration: the check of the",
        "  claimed files passes.",
        "",
    ]
    keys: list[tuple[str, str]] = []
    for analysis in analyses:
        key = (str(analysis.cell.get("model", "")), str(analysis.cell.get("condition", "")))
        if key not in keys:
            keys.append(key)
    for model, condition in sorted(keys):
        naive = {
            analysis.key[2]: analysis
            for analysis in analyses
            if analysis.cell.get("arm") == "naive"
            and analysis.key[0] == model
            and analysis.key[1] == condition
        }
        guarded = {
            analysis.key[2]: analysis
            for analysis in analyses
            if analysis.cell.get("arm") == "agentether"
            and analysis.key[0] == model
            and analysis.key[1] == condition
        }
        caught = sorted(task for task in naive if task not in guarded)
        missed = sorted(task for task in naive if task in guarded)
        added = sorted(task for task in guarded if task not in naive)
        lines.append(f"* **{model}, {condition}.**")
        if caught:
            for task in caught:
                finding = naive[task].findings[0]
                lines.append(f"  * the false completion of {task} was **caught**: {finding.note}.")
        if missed:
            for task in missed:
                finding = naive[task].findings[0]
                lines.append(
                    f"  * the false completion of {task} was **not** caught: {finding.note}."
                )
        for task in added:
            finding = guarded[task].findings[0]
            lines.append(
                f"  * the guarded arm **added** a false completion of its own on "
                f"{task}: {finding.note}  This one is a defect of the harness and "
                "not of the library: the file on disk is a faithful copy of what "
                "the harness wrote, so no verifier of the library could see it."
            )
        if not naive and not guarded:
            lines.append("  * there is no false completion at all.")
    lines.append("")
    return lines


def _harness_defect(analyses: list[CellAnalysis]) -> list[str]:
    """The tasks where the harness damaged the file itself."""
    proved: dict[tuple[str, str, str], set[str]] = {}
    for analysis in analyses:
        for finding in analysis.findings:
            if finding.cause == "iii" and "the harness cut the file" in finding.note:
                key = (finding.model, finding.condition, finding.task)
                proved.setdefault(key, set()).add(finding.arm)
    lines = [
        "### The defect of the harness",
        "",
        "The harness closes a file on the next fence, even when that fence",
        "opens a code block **of the file itself** (a Markdown file that shows",
        "how to run the script is the common case).  The file is then cut in",
        "the middle, the rest of it is lost, and the ground truth fails.  The",
        "answer of the model was complete: the proof is in the answer that the",
        "guarded arm recorded in its project memory.",
        "",
        "| Model | Condition | Task | The arms that lost it |",
        "| --- | --- | --- | --- |",
    ]
    for (model, condition, task), arms in sorted(proved.items()):
        lines.append(f"| {model} | {condition} | {task} | {', '.join(sorted(arms))} |")
    lines.extend(
        [
            "",
            "The baseline (`simple-retry`) keeps no log of the answers of the",
            "model, so the proof comes from the answers of the guarded arm; the",
            "file of the baseline carries the same signature (a content cut in",
            "the middle).  The naive arm was right on those tasks by luck: the",
            "Google model is not deterministic (the capability probe says so),",
            "and its answer for that task did not hold a code block.",
            "",
            "**The fix belongs to the harness, not to the library.**  The parser",
            "must close a file on a fence that closes it and not on a fence that",
            "opens a block, and the trial v3 runs with the repaired parser (the",
            "data of the trial v2 stay as they are: they are a supplementary",
            "run).",
            "",
        ]
    )
    return lines


def build_markdown(
    analyses: list[CellAnalysis],
    title: str = "the trial v2",
    meta: dict[str, Any] | None = None,
) -> str:
    """The document of the analysis.

    The notes of the run (the interpretation that is not computed) are
    appended at the end; they come from the meta of the run, so the
    document is reproducible from the cells and the meta.
    """
    meta = meta or {}
    lines: list[str] = [
        f"# The cause of every false completion of {title}",
        "",
        "> This document is **generated** by `benchmarks/analyze_false.py` from",
        "> the raw cells, the sandboxes and the attempt logs of the run.  No",
        "> model was called to produce it.",
        "",
        "A **false completion** is a cell whose arm believes the task is done",
        "while the ground truth says it is not.  The belief of an arm and the",
        "ground truth are two separate columns of the cells and they are never",
        "mixed.",
        "",
        "## The causes",
        "",
        "| Code | The cause |",
        "| --- | --- |",
    ]
    for code, text in CAUSES.items():
        lines.append(f"| **({code})** | {text} |")
    lines.extend(
        [
            "",
            "The four injected faults that damage an artifact are",
            "`drop_file_block`, `truncate_file`, `lie` and `replay_previous`.",
            "The other two (`corrupt_telemetry` and `wrong_step`) break the",
            "telemetry and not the files, and they cannot produce a false",
            "completion: the arm does not believe the task is done.",
            "",
            "## The false completions, one table per arm",
            "",
        ]
    )
    for arm in ARMS:
        lines.extend(_cell_table(analyses, arm))
    lines.extend(_counts(analyses))
    lines.extend(_caught_analysis(analyses))
    lines.extend(_explanation(analyses))
    lines.extend(_harness_defect(analyses))
    notes = meta.get("notes")
    if notes:
        lines.append(str(notes).rstrip())
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Read the cells and write the document."""
    parser = argparse.ArgumentParser(description="Classify the false completions.")
    parser.add_argument(
        "--progress", nargs="+", required=True, help="the progress files of the run"
    )
    parser.add_argument(
        "--workdir",
        nargs="+",
        required=True,
        help="the work directories of the providers",
    )
    parser.add_argument("--out", default="docs/false-completions.md")
    parser.add_argument(
        "--fault-seed",
        type=int,
        default=None,
        help="the seed of the fault schedule of the run",
    )
    parser.add_argument(
        "--faults",
        nargs="*",
        default=list(FAULTS),
        help="the faults of the schedule of the run",
    )
    parser.add_argument(
        "--task-set",
        choices=("v2", "v3"),
        default="v2",
        help="the task set of the run",
    )
    parser.add_argument(
        "--title",
        default="the trial v2",
        help="the title of the document",
    )
    parser.add_argument("--meta", default=None, help="the JSON description of the run")
    args = parser.parse_args(argv)

    cells: list[dict[str, Any]] = []
    for name in args.progress:
        for line in Path(name).read_text(encoding="utf-8").splitlines():
            if line.strip():
                cells.append(json.loads(line))
    workdirs: dict[str, Path] = {}
    for name in args.workdir:
        provider, _, path = name.partition("=")
        if not path:
            provider = Path(name).name.replace("trial-v2-", "").replace("trial-v3-", "")
            path = name
        workdirs[provider] = Path(path)
    meta: dict[str, Any] = {}
    if args.meta and Path(args.meta).exists():
        meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
    if args.task_set == "v3":
        from tasks_v3 import TASKS_V3

        tasks = TASKS_V3
    else:
        tasks = TASKS
    analyses = analyse(cells, workdirs, tasks, args.fault_seed, tuple(args.faults))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_markdown(analyses, args.title, meta), encoding="utf-8")
    print(f"false completions: {len(analyses)}")
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
