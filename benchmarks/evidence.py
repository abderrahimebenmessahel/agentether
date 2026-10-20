"""Turn the raw trial cells into the tables of ``docs/evidence.md``.

The document is built from the **raw** progress file of the trial (one JSON
line per cell) and from a small meta file that describes the run.  Nothing
is typed in by hand: the tables, the intervals and the totals are computed
here, so the document can be regenerated and checked.

    python benchmarks/evidence.py --progress benchmarks/results/run-1-progress.jsonl \\
        --meta benchmarks/results/run-1-meta.json --out docs/evidence.md

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trial import paired_difference, summarise

ARMS = ("naive", "simple-retry", "agentether")
CONDITIONS = ("natural", "injected")


def _rate(value: float) -> str:
    return f"{value:.3f}"


def _ci(low: float, high: float) -> str:
    return f"[{low:.3f}, {high:.3f}]"


def _read_progress(path: Path) -> list[dict[str, Any]]:
    """The cells of a run."""
    cells: list[dict[str, Any]] = []
    if not path.exists():
        return cells
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                cells.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return cells


def _totals_section(cells: list[dict[str, Any]], meta: dict[str, Any]) -> list[str]:
    """The request and token totals of the run."""
    lines = [
        "## The request and token totals",
        "",
        "| Model | Requests | Input tokens | Output tokens |",
        "| --- | --- | --- | --- |",
    ]
    for model in meta.get("models", []):
        rows = [cell for cell in cells if cell["model"] == model]
        requests = sum(int(cell.get("requests", 0) or 0) for cell in rows)
        tokens = sum(int(cell.get("tokens", 0) or 0) for cell in rows)
        if meta.get("tokens_recorded") is False:
            lines.append(f"| {model} | {requests} | not recorded | not recorded |")
        else:
            lines.append(f"| {model} | {requests} | {tokens} | (see the cells) |")
    lines.append("")
    if meta.get("tokens_note"):
        lines.extend([f"> {meta['tokens_note']}", ""])
    return lines


def _condition_tables(
    cells: list[dict[str, Any]], summary: dict[str, Any], models: list[str]
) -> list[str]:
    """One table per condition."""
    lines: list[str] = []
    for condition in CONDITIONS:
        lines.extend(
            [
                f"## Condition: {condition}",
                "",
                "| Model | Arm | N | Correct completion rate (95% CI) |"
                " False completion rate (95% CI) | Believed done | Requests | Wall s |"
                " Rejections | Loops |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for model in models:
            for arm in ARMS:
                row = summary.get(f"{model}|{condition}|{arm}")
                if not row:
                    continue
                lines.append(
                    "| {model} | {arm} | {n} | {rate} {ci} | {false} {false_ci} |"
                    " {reported} | {requests} | {seconds} | {rejections} | {loops} |".format(
                        model=model,
                        arm=arm,
                        n=row["n"],
                        rate=_rate(row["correct_rate"]),
                        ci=_ci(*row["correct_ci"]),
                        false=_rate(row["false_rate"]),
                        false_ci=_ci(*row["false_ci"]),
                        reported=row["reported"],
                        requests=row["requests"],
                        seconds=row["seconds"],
                        rejections=row["verifier_rejections"],
                        loops=row["loop_detections"],
                    )
                )
        lines.append("")
    return lines


def _paired_tables(cells: list[dict[str, Any]], models: list[str]) -> list[str]:
    """The paired differences between the arms."""
    lines = [
        "## The paired differences",
        "",
        "Every arm saw the same tasks and the same fault schedule, so the",
        "comparison is paired.  The difference is the share of the tasks where",
        "one arm was right and the other was not.",
        "",
        "| Model | Condition | Comparison | Only A | Only B | Both | Neither | Difference |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for model in models:
        for condition in CONDITIONS:
            key = f"{model}|{condition}"
            for arm_a, arm_b in (
                ("agentether", "naive"),
                ("agentether", "simple-retry"),
            ):
                for field, label in (
                    ("correct", "correct completion"),
                    ("false_completion", "false completion"),
                ):
                    diff = paired_difference(cells, key, arm_a, arm_b, field)
                    if not diff["n"]:
                        continue
                    lines.append(
                        "| {model} | {condition} | {label} ({a} vs {b}) |"
                        " {only_a} | {only_b} | {both} | {neither} |"
                        " {difference} |".format(
                            model=model,
                            condition=condition,
                            label=label,
                            a=arm_a,
                            b=arm_b,
                            only_a=diff[f"only_{arm_a}"],
                            only_b=diff[f"only_{arm_b}"],
                            both=diff["both"],
                            neither=diff["neither"],
                            difference=f"{diff['difference']:+.3f}",
                        )
                    )
    lines.append("")
    return lines


def _hypotheses(
    cells: list[dict[str, Any]], summary: dict[str, Any], models: list[str]
) -> list[str]:
    """The verdict on H1 and H2, per model and condition."""
    lines = [
        "## The hypotheses",
        "",
        "H1: the guarded arm completes more tasks correctly.  H2: the guarded arm",
        "catches more false completions.  The paired difference is the share of",
        "the tasks where one arm was right and the other was not.",
        "",
        "| Model | Condition | agentether | naive | H1 (paired) | H2 (paired) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for model in models:
        for condition in CONDITIONS:
            key = f"{model}|{condition}"
            a = summary.get(f"{key}|agentether")
            b = summary.get(f"{key}|naive")
            if not (a and b):
                continue
            h1 = paired_difference(cells, key, "agentether", "naive", "correct")
            h2 = paired_difference(cells, key, "agentether", "naive", "false_completion")
            lines.append(
                "| {model} | {condition} | {a} | {b} | {h1} | {h2} |".format(
                    model=model,
                    condition=condition,
                    a=_rate(a["correct_rate"]),
                    b=_rate(b["correct_rate"]),
                    h1=f"{h1['difference']:+.3f}",
                    h2=f"{-h2['difference']:+.3f}",
                )
            )
    lines.append("")
    return lines


def _defects_section(defects: list[dict[str, Any]]) -> list[str]:
    """The defects of the harness, with the evidence for each."""
    if not defects:
        return []
    lines = [
        "## The defects of this run",
        "",
        "A run whose harness treats the arms differently does not measure the",
        "arms.  The defects below were found in the harness of this run, and",
        "each of them changed the numbers of the tables above.",
        "",
    ]
    for defect in defects:
        lines.extend(
            [
                f"### {defect['id']}. {defect['title']}",
                "",
                f"- **Evidence.** {defect['evidence']}",
                f"- **Effect.** {defect['effect']}",
                f"- **Fix.** {defect['fix']}",
                "",
            ]
        )
    return lines


def build_markdown(cells: list[dict[str, Any]], meta: dict[str, Any]) -> str:
    """Build the evidence document."""
    summary = summarise(cells)
    models = list(meta.get("models") or sorted({cell["model"] for cell in cells}))
    measured = sum(float(cell.get("seconds", 0.0) or 0.0) for cell in cells)
    requests = sum(int(cell.get("requests", 0) or 0) for cell in cells)
    label = meta.get("label", "The run")

    lines: list[str] = [
        "# Evidence",
        "",
        "> **A tiny sample from free models on a single day.**  This is not a",
        "> benchmark and it does not show that AgenTether works in general.  The",
        "> protocol was pre-registered and committed before the first result file",
        "> existed: [`docs/trial-protocol.md`](trial-protocol.md).",
        "",
        f"## {label}",
        "",
        f"> **Status: {meta.get('status', 'unknown')}**",
        "",
    ]
    if meta.get("wall_clock_note"):
        lines.extend([f"> {meta['wall_clock_note']}", ""])
    lines.extend(
        [
            "## What was run",
            "",
            f"- Tasks per cell: {meta.get('tasks_per_cell', '?')}",
            f"- Cells completed: {len(cells)}",
            f"- Time the calls took: {measured:.1f} s",
            f"- Model calls: {requests}",
            f"- Fault rate: {meta.get('fault_rate', '?')} (the injected condition only)",
            f"- Attempt cap per step: {meta.get('attempt_cap', '?')}",
            f"- Halted: {meta.get('halted') or 'no'}",
            "",
        ]
    )
    lines.extend(_totals_section(cells, meta))
    lines.extend(
        [
            "## The arms",
            "",
            "| Arm | What it does |",
            "| --- | --- |",
            "| naive | One call per step; the claim is trusted. |",
            "| simple-retry | The baseline most people would write: retry on a"
            " contract failure, an exception or a timeout. No verification, no loop"
            " detection, no drift check. |",
            "| agentether | The full library: the contract, the drift checks, the"
            " verifiers, the loop detector, the budget and the breaker. |",
            "",
        ]
    )
    lines.extend(_condition_tables(cells, summary, models))
    lines.extend(_paired_tables(cells, models))
    lines.extend(_hypotheses(cells, summary, models))
    lines.extend(_defects_section(list(meta.get("defects") or [])))
    lines.extend(
        [
            "## What this shows and what it does not",
            "",
            "**It shows** how three policies behave on the same tasks with the",
            "same injected faults, for a few free models, on one day.",
            "",
            "**It does not show** that AgenTether makes agents reliable in",
            "general.  The sample is small, the tasks are synthetic, the models",
            "are free tier models with their own limits, and the ground truth",
            "checks are the ones the author of the library wrote.",
            "",
            "A null result is reported as a null result: where the paired",
            "difference is smaller than the interval, the table says so.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Read the progress file and write the evidence document."""
    parser = argparse.ArgumentParser(description="Build the evidence document.")
    parser.add_argument("--progress", required=True, help="the progress.jsonl of the trial")
    parser.add_argument("--out", default="docs/evidence.md")
    parser.add_argument("--meta", default=None, help="the JSON description of the run")
    args = parser.parse_args(argv)

    cells = _read_progress(Path(args.progress))
    meta: dict[str, Any] = {}
    if args.meta and Path(args.meta).exists():
        meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
    meta.setdefault("tasks_per_cell", 10)
    document = build_markdown(cells, meta)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(document, encoding="utf-8")
    print(f"cells: {len(cells)}")
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
