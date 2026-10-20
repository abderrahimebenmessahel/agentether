"""The natural frequency of the false completions of the kind (ii).

The primary endpoint of the trial v3 is the false completion rate **under
the injected faults**.  The faults are designed, and one of them
(``hide_file``) is designed to be caught **only** by the declarative
expectations.  The evidence for the real-world value of ``expects`` must
therefore not rest on that fault alone.

This tool answers the other half of the question: **how often does the
failure happen on its own?**  It reads the raw cells of a run, keeps the
**natural** condition (no fault is injected), classifies every false
completion with the same code as the analysis of the false completions
(:func:`analyze_false.classify_cell`) and reports the rate of the false
completions of the kind **(ii)** -- "a required file was never produced
and the claim did not mention it" -- with its Wilson interval.

    python benchmarks/natural_frequency.py \\
        --progress benchmarks/results/trial-v3-cerebras-cells.jsonl \\
        --workdir logs/trial-v3-cerebras --out docs/natural-frequency.md

No model is called: the tool reads the cells, the sandboxes and the
attempt logs of a run that is already over.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyze_false import FAULTS as FAULTS_V2
from analyze_false import _memory_of, _provider_of, _sandbox_of, classify_cell
from harness import FAULT_SEED, FAULT_SEED_V3, FAULTS_V3
from tasks import TASKS, TaskSpec
from trial import common_task_set, wilson_interval

#: The kind of a false completion that the tool counts.
KIND = "ii"


def _tasks_of(task_set: str) -> list[TaskSpec]:
    """The task set of a run."""
    if task_set == "v3":
        from tasks_v3_gen import TASKS_V3_FULL

        return TASKS_V3_FULL
    if task_set == "v3-20":
        from tasks_v3 import TASKS_V3

        return TASKS_V3
    return TASKS


def _read_cells(paths: Sequence[Path]) -> list[dict[str, Any]]:
    """The cells of the progress files."""
    cells: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (
                str(record.get("model", "")),
                str(record.get("arm", "")),
                str(record.get("condition", "")),
                str(record.get("task", "")),
            )
            if key in seen:
                continue
            seen.add(key)
            cells.append(record)
    return cells


def _rate(value: float) -> str:
    return f"{value:.3f}"


def _ci(low: float, high: float) -> str:
    return f"[{low:.3f}, {high:.3f}]"


def build_document(
    cells: list[dict[str, Any]],
    workdirs: dict[str, Path],
    tasks: list[TaskSpec],
    fault_seed: int | None,
    faults: Sequence[str],
    title: str,
) -> str:
    """Build the document of the natural frequency."""
    by_name = {task.name: task for task in tasks}
    models = sorted({str(cell.get("model", "")) for cell in cells})
    conditions = sorted({str(cell.get("condition", "")) for cell in cells})
    lines = [
        f"# {title}",
        "",
        "> The **natural** frequency of the false completions of the kind (ii):",
        "> *a required file was never produced and the claim did not mention it*.",
        "> No fault is injected in the natural condition, so every failure is the",
        "> failure of the model.  The primary endpoint of the trial v3 is the",
        "> false completion rate under the **injected** faults; the two numbers",
        "> are reported **separately**, and the evidence for the value of the",
        "> declarative expectations does not rest on a fault that only they can",
        "> catch.",
        "",
        "Every rate is computed on the **common set** of the tasks of the cell:",
        "the tasks that every arm of that model and of that condition completed.",
        "",
    ]
    for model in models:
        for condition in conditions:
            key = f"{model}|{condition}"
            common = set(common_task_set(cells, key))
            if not common:
                continue
            arms = sorted({str(cell.get("arm", "")) for cell in cells if cell.get("key") == key})
            lines.extend(
                [
                    f"## {model} -- {condition}",
                    "",
                    "| Arm | N | False completions | Of which (ii) | Rate of (ii) (95% CI) |",
                    "| --- | --- | --- | --- | --- |",
                ]
            )
            for arm in arms:
                rows = [
                    cell
                    for cell in cells
                    if cell.get("key") == key
                    and cell.get("arm") == arm
                    and str(cell.get("task", "")) in common
                ]
                total = len(rows)
                if not total:
                    continue
                false_cells = [cell for cell in rows if cell.get("false_completion")]
                of_kind = 0
                for cell in false_cells:
                    task = by_name.get(str(cell.get("task", "")))
                    if task is None:
                        continue
                    provider = _provider_of(workdirs, model)
                    workdir = workdirs.get(provider)
                    if workdir is None:
                        continue
                    sandbox = _sandbox_of(workdir, model, arm, condition, task.name)
                    memory = _memory_of(workdir, model, condition, task.name)
                    analysis = classify_cell(cell, task, sandbox, memory, fault_seed, faults)
                    if analysis.cause == KIND:
                        of_kind += 1
                low, high = wilson_interval(of_kind, total)
                rate = _rate(of_kind / total)
                interval = _ci(low, high)
                lines.append(
                    f"| {arm} | {total} | {len(false_cells)} | {of_kind} | {rate} {interval} |"
                )
            lines.append("")
    lines.extend(
        [
            "## What this shows and what it does not",
            "",
            "**It shows** how often a model of the trial failed to produce a file",
            "it claimed to have produced, with nothing injected: the frequency of",
            "the failure that the declarative expectations exist for.",
            "",
            "**It does not show** that the library fixes it.  The rate of the",
            "guarded arm in the same table is the answer to that question, and the",
            "verdicts of the trial (with the Wilson intervals and the McNemar",
            "tests) are in `docs/evidence.md`.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Read the cells and write the document."""
    parser = argparse.ArgumentParser(description="The natural frequency of the kind (ii).")
    parser.add_argument("--progress", nargs="+", required=True, help="the progress files")
    parser.add_argument(
        "--workdir",
        nargs="+",
        required=True,
        help="the work directories of the providers",
    )
    parser.add_argument("--out", default="docs/natural-frequency.md")
    parser.add_argument("--task-set", choices=("v2", "v3", "v3-20"), default="v3")
    parser.add_argument("--title", default="The natural frequency of the false completions")
    parser.add_argument("--fault-seed", type=int, default=None)
    parser.add_argument("--faults", nargs="*", default=None)
    args = parser.parse_args(argv)

    cells = _read_cells([Path(name) for name in args.progress])
    workdirs: dict[str, Path] = {}
    for name in args.workdir:
        provider, _, path = name.partition("=")
        if not path:
            provider = Path(name).name.replace("trial-v2-", "").replace("trial-v3-", "")
            path = name
        workdirs[provider] = Path(path)
    if args.faults is not None:
        faults: Sequence[str] = args.faults
    elif args.task_set == "v2":
        faults = FAULTS_V2
    else:
        faults = FAULTS_V3
    if args.fault_seed is not None:
        seed: int | None = args.fault_seed
    elif args.task_set == "v2":
        seed = FAULT_SEED
    else:
        seed = FAULT_SEED_V3
    document = build_document(
        cells=cells,
        workdirs=workdirs,
        tasks=_tasks_of(args.task_set),
        fault_seed=seed,
        faults=faults,
        title=args.title,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(document, encoding="utf-8")
    print(f"cells: {len(cells)}")
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
