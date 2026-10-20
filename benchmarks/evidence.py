"""Turn the raw trial cells into the tables of ``docs/evidence.md``.

The document is built from the **raw** progress files of the trial (one
JSON line per cell) and from small meta files that describe the runs.
Nothing is typed in by hand: the tables, the intervals, the totals and the
verdicts are computed here, so the document can be regenerated and checked.

The document may carry **several runs** (the supplementary run of the
protocol v2 and the confirmatory run of the protocol v3).  Every run has its
own section and its own tables, and they are never mixed.

    python benchmarks/evidence.py --manifest benchmarks/results/evidence-manifest.json \\
        --out docs/evidence.md

    python benchmarks/evidence.py --progress benchmarks/results/run-1-progress.jsonl \\
        --meta benchmarks/results/run-1-meta.json --out docs/evidence.md

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trial import paired_difference, summarise

#: What every arm of the trial does.  The table is built from this map, so
#: an arm that is added to the trial appears in the document without a
#: hand-written line.
ARM_DESCRIPTIONS: dict[str, str] = {
    "naive": "One call per step; the claim is trusted.",
    "simple-retry": (
        "The baseline most people would write: retry on a contract failure, an"
        " exception or a timeout. No verification, no loop detection, no drift check."
    ),
    "agentether": (
        "The full library with the declarative expectations of the step: the"
        " contract, the drift checks, the verifiers, the loop detector, the budget"
        " and the breaker."
    ),
    "agentether-claims-only": (
        "The full library, but the step declares no expectation: only the files"
        " the agent claims are checked. It isolates the contribution of the"
        " declarative expectations."
    ),
}


@dataclass
class Run:
    """One run of the trial, with its raw cells and its description."""

    label: str
    cells: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    status: str = ""
    protocol: str = "trial-protocol-v2.md"

    @property
    def title(self) -> str:
        """The title of the section of the run."""
        label = self.meta.get("label")
        return str(label) if label else self.label


def _rate(value: float) -> str:
    return f"{value:.3f}"


def _plural(count: int, word: str) -> str:
    """The word with the right number: ``1 task``, ``0 tasks``."""
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


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


def _totals_section(run: Run, level: int) -> list[str]:
    """The request and token totals of a run.

    The totals are summed from the raw cells, and the grand total is a row
    of its own: a reader must be able to add the rows of the table and find
    the same number.
    """
    cells = run.cells
    meta = run.meta
    head = "#" * level
    lines = [
        f"{head} The request and token totals",
        "",
        "| Model | Requests | Tokens | Wall clock (s) |",
        "| --- | --- | --- | --- |",
    ]
    total_requests = 0
    total_tokens = 0
    # The total of the wall clock is the sum of the **rounded** rows of the
    # table: a reader must be able to add the rows of the table and find the
    # same number.
    total_seconds = 0.0
    for model in sorted({str(cell.get("model", "")) for cell in cells}):
        rows = [cell for cell in cells if cell.get("model") == model]
        requests = sum(int(cell.get("requests", 0) or 0) for cell in rows)
        tokens = sum(int(cell.get("tokens", 0) or 0) for cell in rows)
        seconds = round(sum(float(cell.get("seconds", 0.0) or 0.0) for cell in rows), 1)
        total_requests += requests
        total_tokens += tokens
        total_seconds += seconds
        if meta.get("tokens_recorded") is False:
            lines.append(f"| {model} | {requests} | not recorded | {seconds:.1f} |")
        else:
            lines.append(f"| {model} | {requests} | {tokens} | {seconds:.1f} |")
    if meta.get("tokens_recorded") is False:
        lines.append(
            f"| **total** | **{total_requests}** | not recorded | **{total_seconds:.1f}** |"
        )
    else:
        lines.append(
            f"| **total** | **{total_requests}** | **{total_tokens}** | **{total_seconds:.1f}** |"
        )
    lines.append("")
    if meta.get("tokens_note"):
        lines.extend([f"> {meta['tokens_note']}", ""])
    return lines


def _condition_tables(run: Run, level: int) -> list[str]:
    """One table per condition."""
    cells = run.cells
    summary = summarise(cells)
    models = sorted({str(cell.get("model", "")) for cell in cells})
    head = "#" * level
    lines: list[str] = []
    conditions = sorted({str(cell.get("condition", "")) for cell in cells})
    for condition in conditions:
        lines.extend(
            [
                f"{head} Condition: {condition}",
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


def _arms_section(run: Run, level: int) -> list[str]:
    """What every arm of the run does."""
    head = "#" * level
    arms = sorted({str(cell.get("arm", "")) for cell in run.cells})
    lines = [
        f"{head} The arms",
        "",
        "| Arm | What it does |",
        "| --- | --- |",
    ]
    for arm in arms:
        lines.append(f"| {arm} | {ARM_DESCRIPTIONS.get(arm, 'not described')} |")
    lines.append("")
    return lines


def _convention_section() -> list[str]:
    """The sign convention of every paired difference of the document.

    The convention is stated **once** here and every table follows it.  It
    used to differ between the tables of the document (the table of the
    hypotheses showed the *opposite* sign of the table of the paired
    differences for the false completion), which made two numbers of the
    same run contradict each other.
    """
    return [
        "## The sign convention",
        "",
        "Every paired difference of this document is **arm A minus arm B**, and",
        "A is the first arm of the comparison (the guarded arm is always the",
        "first).  What the sign means depends on the metric:",
        "",
        "* for the **correct completion rate**, a **positive** difference is an",
        "  improvement: the first arm completed more tasks correctly;",
        "* for the **false completion rate**, a **NEGATIVE** difference is an",
        "  improvement: the first arm had fewer false completions.",
        "",
        "The same rule applies to the hypotheses, to the verdicts and to the",
        "tables of the report.",
        "",
    ]


def _paired_tables(run: Run, level: int) -> list[str]:
    """The paired differences between the arms."""
    cells = run.cells
    models = sorted({str(cell.get("model", "")) for cell in cells})
    head = "#" * level
    lines = [
        f"{head} The paired differences",
        "",
        "Every arm saw the same tasks and the same fault schedule, so the",
        "comparison is paired.  The difference is the share of the tasks where",
        "one arm was right and the other was not, with the sign convention of",
        "the section above (A minus B).",
        "",
        "| Model | Condition | Comparison | Only A | Only B | Both | Neither | Difference |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    conditions = sorted({str(cell.get("condition", "")) for cell in cells})
    for model in models:
        for condition in conditions:
            key = f"{model}|{condition}"
            for arm_a, arm_b in _comparisons(cells):
                for field_name, label in (
                    ("correct", "correct completion"),
                    ("false_completion", "false completion"),
                ):
                    diff = paired_difference(cells, key, arm_a, arm_b, field_name)
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


def _comparisons(cells: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """The pairs of arms that are compared.

    The guarded arm is always the first arm of a comparison (the sign
    convention says "A minus B"), and it is compared with every other arm
    of the run.
    """
    arms = sorted({str(cell.get("arm", "")) for cell in cells})
    if "agentether" not in arms:
        return []
    return [("agentether", other) for other in arms if other != "agentether"]


def _hypotheses(run: Run, level: int) -> list[str]:
    """The verdict on H1 and H2, per model and condition."""
    cells = run.cells
    summary = summarise(cells)
    models = sorted({str(cell.get("model", "")) for cell in cells})
    head = "#" * level
    lines = [
        f"{head} The hypotheses",
        "",
        "H1: the guarded arm completes more tasks correctly.  H2: the guarded arm",
        "catches more false completions (the primary endpoint).  The paired",
        "differences follow the sign convention of the section above: the",
        "guarded arm minus the naive arm, a **positive** H1 is an improvement",
        "and a **negative** H2 is an improvement.",
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
                    h2=f"{h2['difference']:+.3f}",
                )
            )
    lines.append("")
    return lines


def _runs_section(run: Run, level: int) -> list[str]:
    """The models of the run, with the pilot and the size of the sample."""
    runs = list(run.meta.get("runs") or [])
    if not runs:
        return []
    head = "#" * level
    lines = [
        f"{head} The models of the run",
        "",
        "| Provider | Model | Pilot (naive, natural) | Qualifies | N per cell |"
        " MDE of the paired difference |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in runs:
        pilot = item.get("pilot") or {}
        lines.append(
            "| {provider} | {model} | {pilot} | {qualifies} | {n} | {mde} |".format(
                provider=item.get("provider", "?"),
                model=item.get("model", "?"),
                pilot=(
                    f"{pilot.get('correct', 0)}/{pilot.get('n', 0)} = "
                    f"{_rate(float(pilot.get('rate', 0.0)))}"
                    if pilot
                    else "not run"
                ),
                qualifies=item.get("qualification", "?"),
                n=item.get("n", "?"),
                mde=item.get("mde", "?"),
            )
        )
    lines.append("")
    for item in runs:
        note = item.get("note")
        if note:
            lines.append(f"- **{item.get('model', '?')}**: {note}")
    if any(item.get("note") for item in runs):
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
    return float(math.comb(n, k)) / float(2**n)


def _verdict(difference: float, p_value: float, mde: float, expected: int = 1) -> str:
    """The verdict of a hypothesis.

    The rule is the one of the pre-registration: a difference that is
    smaller than the minimum detectable effect of the sample is
    **inconclusive** (the sample is too small to say anything, which is
    not the same as "no effect"), and a difference that is at least as
    large as the minimum detectable effect is only **supported** when the
    exact McNemar test rejects the null hypothesis.

    Args:
        difference: The observed difference of the paired rates, with the
            sign convention of the document (arm A minus arm B).
        p_value: The exact two sided p value of the discordant pairs.
        mde: The minimum detectable effect of the sample.
        expected: The sign the hypothesis expects: 1 for "more", -1 for
            "less".  The hypothesis of the false completion expects **less**
            (a negative difference is an improvement).
    """
    if abs(difference) < mde:
        return "INCONCLUSIVE (the sample is too small)"
    if expected * difference > 0 and p_value < 0.05:
        return "SUPPORTED"
    return "NOT SUPPORTED"


def _verdicts_section(run: Run, level: int) -> list[str]:
    """The verdict of H1, H2 and H3, per model."""
    cells = run.cells
    summary = summarise(cells)
    models = sorted({str(cell.get("model", "")) for cell in cells})
    mdes: dict[str, float] = {}
    for item in list(run.meta.get("runs") or []):
        try:
            mdes[str(item.get("model"))] = float(item.get("mde", 0.0) or 0.0)
        except (TypeError, ValueError):
            mdes[str(item.get("model"))] = 0.0
    head = "#" * level
    lines = [
        f"{head} The verdicts",
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
                p2 = _mcnemar(h2["discordant"], h2["only_agentether"])
                # The sign convention is the one of the section above: the
                # guarded arm minus the comparator.  A positive H1 is an
                # improvement, a NEGATIVE H2 is an improvement.
                h1_text = (
                    f"{h1['difference']:+.3f} (in {_plural(h1['only_agentether'], 'task')} "
                    f"only the guarded arm completed, in "
                    f"{_plural(h1['only_simple-retry'], 'task')} only the "
                    f"comparator; p = {p1:.3f}): "
                    f"{_verdict(h1['difference'], p1, mde, 1)}"
                )
                h2_text = (
                    f"{h2['difference']:+.3f} (in {_plural(h2['only_agentether'], 'task')} "
                    f"only the guarded arm falsely completed, in "
                    f"{_plural(h2['only_simple-retry'], 'task')} only the "
                    f"comparator; p = {p2:.3f}): "
                    f"{_verdict(h2['difference'], p2, mde, -1)}"
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
    lines.extend(_expectations_section(run, level))
    return lines


def _expectations_section(run: Run, level: int) -> list[str]:
    """The verdict of H4: the contribution of the declarative expectations.

    H4 compares the arm that declares what the step must produce with the
    arm that only checks the claimed files.  It is only computed when both
    arms are in the run.
    """
    cells = run.cells
    summary = summarise(cells)
    models = sorted({str(cell.get("model", "")) for cell in cells})
    arms = {str(cell.get("arm", "")) for cell in cells}
    if "agentether-claims-only" not in arms:
        return []
    mdes: dict[str, float] = {}
    for item in list(run.meta.get("runs") or []):
        try:
            mdes[str(item.get("model"))] = float(item.get("mde", 0.0) or 0.0)
        except (TypeError, ValueError):
            mdes[str(item.get("model"))] = 0.0
    head = "#" * level
    lines = [
        f"{head} The contribution of the declarative expectations (H4)",
        "",
        "H4: the arm that **declares** what the step must produce has fewer",
        "false completions than the arm that only checks the files the agent",
        "claims.  The difference is the false completion rate of the guarded",
        "arm minus the one of the claims-only arm: a **negative** value is an",
        "improvement.",
        "",
        "| Model | Condition | H4 (paired) | The verdict |",
        "| --- | --- | --- | --- |",
    ]
    conditions = sorted({str(cell.get("condition", "")) for cell in cells})
    for model in models:
        for condition in conditions:
            key = f"{model}|{condition}"
            a = summary.get(f"{key}|agentether")
            b = summary.get(f"{key}|agentether-claims-only")
            if not (a and b):
                continue
            diff = paired_difference(
                cells, key, "agentether", "agentether-claims-only", "false_completion"
            )
            if not diff["n"]:
                continue
            p_value = _mcnemar(diff["discordant"], diff["only_agentether"])
            verdict = _verdict(diff["difference"], p_value, mdes.get(model, 0.0), -1)
            lines.append(
                "| {model} | {condition} | {difference:+.3f} (in {n} tasks only the "
                "guarded arm falsely completed, in {other} only the claims-only arm; "
                "p = {p:.3f}) | {verdict} |".format(
                    model=model,
                    condition=condition,
                    difference=diff["difference"],
                    n=diff["only_agentether"],
                    other=diff["only_agentether-claims-only"],
                    p=p_value,
                    verdict=verdict,
                )
            )
    lines.append("")
    return lines


def _defects_section(run: Run, level: int) -> list[str]:
    """The defects of the harness, with the evidence for each."""
    defects = list(run.meta.get("defects") or [])
    if not defects:
        return []
    head = "#" * level
    lines = [
        f"{head} The defects of this run",
        "",
        "A run whose harness treats the arms differently does not measure the",
        "arms.  The defects below were found in the harness of this run, and",
        "each of them changed the numbers of the tables above.",
        "",
    ]
    for defect in defects:
        lines.extend(
            [
                f"{head}# {defect['id']}. {defect['title']}",
                "",
                f"- **Evidence.** {defect['evidence']}",
                f"- **Effect.** {defect['effect']}",
                f"- **Fix.** {defect['fix']}",
                "",
            ]
        )
    return lines


def build_run_section(run: Run, level: int = 2) -> list[str]:
    """The whole section of one run."""
    head = "#" * level
    cells = run.cells
    measured = sum(float(cell.get("seconds", 0.0) or 0.0) for cell in cells)
    requests = sum(int(cell.get("requests", 0) or 0) for cell in cells)
    lines: list[str] = [
        f"{head} {run.title}",
        "",
        f"> **Status: {run.status or run.meta.get('status', 'unknown')}**",
        "",
    ]
    if run.meta.get("wall_clock_note"):
        lines.extend([f"> {run.meta['wall_clock_note']}", ""])
    lines.extend(
        [
            f"{head}# What was run",
            "",
            f"- Cells completed: {len(cells)}",
            f"- Time the calls took: {measured:.1f} s",
            f"- Model calls: {requests}",
            f"- Fault rate: {run.meta.get('fault_rate', '?')} (the injected condition only)",
            f"- Attempt cap per step: {run.meta.get('attempt_cap', '?')}",
            f"- Halted: {run.meta.get('halted') or 'no'}",
            "",
        ]
    )
    lines.extend(_runs_section(run, level + 1))
    lines.extend(_totals_section(run, level + 1))
    lines.extend(_arms_section(run, level + 1))
    lines.extend(_condition_tables(run, level + 1))
    lines.extend(_paired_tables(run, level + 1))
    lines.extend(_hypotheses(run, level + 1))
    lines.extend(_verdicts_section(run, level + 1))
    lines.extend(_defects_section(run, level + 1))
    return lines


def build_markdown(runs: list[Run]) -> str:
    """Build the evidence document."""
    lines: list[str] = [
        "# Evidence",
        "",
        "> **A tiny sample from free models on a single day.**  This is not a",
        "> benchmark and it does not show that AgenTether works in general.  The",
        "> protocol of every run was pre-registered and committed before the",
        "> first result file of that run existed.",
        "",
    ]
    for run in runs:
        lines.extend(
            [
                f"> The protocol of this run: [`docs/{run.protocol}`]({run.protocol}).",
                "",
            ]
        )
    lines.extend(_convention_section())
    for run in runs:
        lines.extend(build_run_section(run, 2))
    lines.extend(
        [
            "## What this shows and what it does not",
            "",
            "**It shows** how a few policies behave on the same tasks with the",
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


# ----------------------------------------------------------------------
# the manifest
# ----------------------------------------------------------------------
def load_manifest(path: Path) -> list[Run]:
    """Read the manifest of the document and return its runs."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    root = path.parent.parent.parent
    runs: list[Run] = []
    for item in manifest.get("runs") or []:
        cells: list[dict[str, Any]] = []
        for name in item.get("progress") or []:
            path = Path(name)
            if not path.is_absolute():
                path = root / path
            cells.extend(_read_progress(path))
        meta: dict[str, Any] = {}
        meta_name = item.get("meta")
        if meta_name:
            meta_path = Path(meta_name)
            if not meta_path.is_absolute():
                meta_path = root / meta_path
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
        runs.append(
            Run(
                label=str(item.get("label", "The run")),
                cells=cells,
                meta=meta,
                status=str(item.get("status", "")),
                protocol=str(item.get("protocol", "trial-protocol-v2.md")),
            )
        )
    return runs


def main(argv: list[str] | None = None) -> int:
    """Read the progress files and write the evidence document."""
    parser = argparse.ArgumentParser(description="Build the evidence document.")
    parser.add_argument("--progress", nargs="*", default=None, help="the progress files")
    parser.add_argument("--out", default="docs/evidence.md")
    parser.add_argument("--meta", default=None, help="the JSON description of the run")
    parser.add_argument(
        "--manifest",
        default=None,
        help="the JSON manifest of the runs of the document (several runs)",
    )
    args = parser.parse_args(argv)

    runs: list[Run] = []
    if args.manifest:
        runs = load_manifest(Path(args.manifest))
    else:
        cells: list[dict[str, Any]] = []
        for name in args.progress or []:
            cells.extend(_read_progress(Path(name)))
        meta: dict[str, Any] = {}
        if args.meta and Path(args.meta).exists():
            meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
        meta.setdefault("tasks_per_cell", 10)
        runs = [Run(label=str(meta.get("label", "The run")), cells=cells, meta=meta)]
    document = build_markdown(runs)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(document, encoding="utf-8")
    for run in runs:
        print(f"run: {run.title} ({len(run.cells)} cells)")
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
