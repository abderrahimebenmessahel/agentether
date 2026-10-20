"""Turn the raw trial cells into the tables of ``docs/evidence.md``.

The document is built from the **raw** progress files of the trial (one
JSON line per cell) and from a small meta file that describes the run.
Nothing is typed in by hand: the tables, the intervals and the totals are
computed here, so the document can be regenerated and checked.

    python benchmarks/evidence.py --progress benchmarks/results/run-1-progress.jsonl \\
        --meta benchmarks/results/run-1-meta.json --out docs/evidence.md

    python benchmarks/evidence.py --progress a/progress.jsonl b/progress.jsonl \\
        --meta benchmarks/results/trial-v2-meta.json --out docs/evidence.md

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trial import paired_difference, summarise


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
        "| Model | Requests | Tokens | Wall clock (s) |",
        "| --- | --- | --- | --- |",
    ]
    for model in sorted({str(cell.get("model", "")) for cell in cells}):
        rows = [cell for cell in cells if cell.get("model") == model]
        requests = sum(int(cell.get("requests", 0) or 0) for cell in rows)
        tokens = sum(int(cell.get("tokens", 0) or 0) for cell in rows)
        seconds = sum(float(cell.get("seconds", 0.0) or 0.0) for cell in rows)
        if meta.get("tokens_recorded") is False:
            lines.append(f"| {model} | {requests} | not recorded | {seconds:.1f} |")
        else:
            lines.append(f"| {model} | {requests} | {tokens} | {seconds:.1f} |")
    lines.append("")
    if meta.get("tokens_note"):
        lines.extend([f"> {meta['tokens_note']}", ""])
    return lines


def _condition_tables(
    cells: list[dict[str, Any]], summary: dict[str, Any], models: list[str]
) -> list[str]:
    """One table per condition."""
    lines: list[str] = []
    conditions = sorted({str(cell.get("condition", "")) for cell in cells})
    for condition in conditions:
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
            arms = sorted({str(row.get("arm", "")) for row in cells if row.get("model") == model})
            for arm in arms:
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
    conditions = sorted({str(cell.get("condition", "")) for cell in cells})
    for model in models:
        for condition in conditions:
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
        "catches more false completions (the primary endpoint).  The paired",
        "difference is the share of the tasks where one arm was right and the",
        "other was not.",
        "",
        "| Model | Condition | agentether | naive | H1 (paired) | H2 (paired) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    conditions = sorted({str(cell.get("condition", "")) for cell in cells})
    for model in models:
        for condition in conditions:
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


def _runs_section(runs: list[dict[str, Any]]) -> list[str]:
    """The models of the run, with the pilot and the size of the sample."""
    if not runs:
        return []
    lines = [
        "## The models of the run",
        "",
        "| Provider | Model | Pilot (naive, natural) | Qualifies | N per cell |"
        " MDE of the paired difference |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for run in runs:
        pilot = run.get("pilot") or {}
        lines.append(
            "| {provider} | {model} | {pilot} | {qualifies} | {n} | {mde} |".format(
                provider=run.get("provider", "?"),
                model=run.get("model", "?"),
                pilot=(
                    f"{pilot.get('correct', 0)}/{pilot.get('n', 0)} = "
                    f"{_rate(float(pilot.get('rate', 0.0)))}"
                    if pilot
                    else "not run"
                ),
                qualifies=run.get("qualification", "?"),
                n=run.get("n", "?"),
                mde=run.get("mde", "?"),
            )
        )
    lines.append("")
    for run in runs:
        note = run.get("note")
        if note:
            lines.append(f"- **{run.get('model', '?')}**: {note}")
    if any(run.get("note") for run in runs):
        lines.append("")
    return lines


def _mcnemar(discordant: int, favours_a: int) -> float:
    """The exact two sided p value of a McNemar test.

    The null hypothesis is that the discordant pairs are split at random:
    the p value is the probability of a binomial with p = 0.5.
    """
    if discordant <= 0:
        return 1.0
    small = min(favours_a, discordant - favours_a)
    total = 0.0
    for count in range(small + 1):
        total += _binomial(discordant, count)
    return min(1.0, 2.0 * total)


def _binomial(n: int, k: int) -> float:
    """The probability of ``k`` successes in ``n`` trials with p = 0.5."""
    return math.comb(n, k) / (2**n)


def _verdict(difference: float, p_value: float, mde: float, expected: int = 1) -> str:
    """The verdict of a hypothesis.

    The rule is the one of the pre-registration: a difference that is
    smaller than the minimum detectable effect of the sample is
    **inconclusive** (the sample is too small to say anything, which is
    not the same as "no effect"), and a difference that is at least as
    large as the minimum detectable effect is only **supported** when the
    exact McNemar test rejects the null hypothesis.

    Args:
        difference: The observed difference of the paired rates.
        p_value: The exact two sided p value of the discordant pairs.
        mde: The minimum detectable effect of the sample.
        expected: The sign the hypothesis expects: 1 for "more", -1 for
            "less".
    """
    if abs(difference) < mde:
        return "INCONCLUSIVE (the sample is too small)"
    if expected * difference > 0 and p_value < 0.05:
        return "SUPPORTED"
    return "NOT SUPPORTED"


def _verdicts_section(
    cells: list[dict[str, Any]],
    summary: dict[str, Any],
    models: list[str],
    runs: list[dict[str, Any]],
) -> list[str]:
    """The verdict of H1, H2 and H3, per model."""
    mdes: dict[str, float] = {}
    for run in runs:
        try:
            mdes[str(run.get("model"))] = float(run.get("mde", 0.0) or 0.0)
        except (TypeError, ValueError):
            mdes[str(run.get("model"))] = 0.0
    lines = [
        "## The verdicts",
        "",
        "H1: under the injected faults, the guarded arm completes more tasks",
        "correctly than the baseline.  H2 (the primary endpoint): the guarded",
        "arm catches more false completions.  H3: the guarded arm costs more.",
        "",
        "The verdict of a hypothesis is **INCONCLUSIVE** when the difference is",
        "smaller than the minimum detectable effect of the sample: the sample",
        'is then too small to say anything, which is not the same as "no',
        'effect".  The p value is the exact two sided McNemar test of the',
        "discordant pairs.",
        "",
        "| Model | H1: correct completion | H2: false completion (primary) | H3: the overhead |",
        "| --- | --- | --- | --- |",
    ]
    conditions = sorted({str(cell.get("condition", "")) for cell in cells})
    for model in models:
        mde = mdes.get(model, 0.0)
        h1_text = "no data"
        h2_text = "no data"
        h3_text = "no data"
        for condition in conditions:
            if condition != "injected":
                continue
            key = f"{model}|{condition}"
            a = summary.get(f"{key}|agentether")
            b = summary.get(f"{key}|simple-retry")
            if a and b:
                h1 = paired_difference(cells, key, "agentether", "simple-retry", "correct")
                h2 = paired_difference(cells, key, "agentether", "simple-retry", "false_completion")
                p1 = _mcnemar(h1["discordant"], h1["only_agentether"])
                p2 = _mcnemar(h2["discordant"], h2["only_simple-retry"])
                h1_text = (
                    f"{h1['difference']:+.3f} ({h1['only_agentether']} against "
                    f"{h1['only_simple-retry']} discordant pairs, p = {p1:.3f}): "
                    f"{_verdict(h1['difference'], p1, mde, 1)}"
                )
                h2_text = (
                    f"{-h2['difference']:+.3f} ({h2['only_simple-retry']} against "
                    f"{h2['only_agentether']} discordant pairs, p = {p2:.3f}): "
                    f"{_verdict(-h2['difference'], p2, mde, -1)}"
                )
                if b["requests"] and a["requests"]:
                    more = a["requests"] > b["requests"] or a["tokens"] > b["tokens"]
                    h3_text = (
                        f"{a['requests']} against {b['requests']} requests, "
                        f"{a['tokens']} against {b['tokens']} tokens: "
                        f"{'SUPPORTED' if more else 'NOT SUPPORTED'}"
                    )
        lines.append(f"| {model} | {h1_text} | {h2_text} | {h3_text} |")
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
    models = sorted({str(cell.get("model", "")) for cell in cells})
    measured = sum(float(cell.get("seconds", 0.0) or 0.0) for cell in cells)
    requests = sum(int(cell.get("requests", 0) or 0) for cell in cells)
    label = meta.get("label", "The run")

    lines: list[str] = [
        "# Evidence",
        "",
        "> **A tiny sample from free models on a single day.**  This is not a",
        "> benchmark and it does not show that AgenTether works in general.  The",
        "> protocol was pre-registered and committed before the first result file",
        "> existed: [`docs/trial-protocol-v2.md`](trial-protocol-v2.md).",
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
            f"- Cells completed: {len(cells)}",
            f"- Time the calls took: {measured:.1f} s",
            f"- Model calls: {requests}",
            f"- Fault rate: {meta.get('fault_rate', '?')} (the injected condition only)",
            f"- Attempt cap per step: {meta.get('attempt_cap', '?')}",
            f"- Halted: {meta.get('halted') or 'no'}",
            "",
        ]
    )
    lines.extend(_runs_section(list(meta.get("runs") or [])))
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
    lines.extend(_verdicts_section(cells, summary, models, list(meta.get("runs") or [])))
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
    """Read the progress files and write the evidence document."""
    parser = argparse.ArgumentParser(description="Build the evidence document.")
    parser.add_argument("--progress", nargs="+", required=True, help="the progress files")
    parser.add_argument("--out", default="docs/evidence.md")
    parser.add_argument("--meta", default=None, help="the JSON description of the run")
    args = parser.parse_args(argv)

    cells: list[dict[str, Any]] = []
    for name in args.progress:
        cells.extend(_read_progress(Path(name)))
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
