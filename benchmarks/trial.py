"""The runner of the evidence trial.

Three arms (naive, simple-retry, agentether), two conditions (natural,
injected), several models.  Every arm sees the same tasks, the same prompts
and the same fault schedule; the arms themselves live in
:mod:`benchmarks.harness`.

The runner is **resumable**: it appends one JSON line per call to a progress
file, so a run that stops (a daily cap, a rate limit) can be continued later
with the same command.

.. warning::
   The benchmark in :mod:`agentether.benchmark` is a *simulation* of policies.
   This module talks to a *real* model through OpenRouter.  Neither is a
   measure of real world effectiveness; see ``docs/trial-protocol.md``.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import (
    ATTEMPT_CAP,
    FAULT_RATE,
    FAULT_SEED,
    Caller,
    artifacts_present,
    run_arm_agentether,
    run_arm_naive,
    run_arm_simple_retry,
    task_is_correct,
)
from tasks import TASKS, TaskSpec

from agentether.adapters.openai_compatible import (
    DailyCounter,
    OpenAICompatibleError,
    OpenAICompatibleTransientError,
    ProviderSpec,
    TokenBucketLimiter,
    openai_compatible_complete,
    provider_for,
    resolve_provider_key,
)

#: The models of the trial (different families, all free tier).  The ids are
#: checked against the live catalogue of OpenRouter before a run.
MODELS: tuple[str, ...] = (
    "minimax/minimax-m3.1-flash:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
)

#: The arms of the trial.
ARMS: tuple[str, ...] = ("naive", "simple-retry", "agentether")

#: The conditions of the trial.
CONDITIONS: tuple[str, ...] = ("natural", "injected")

#: The hard cap of HTTP requests per model per day.
DEFAULT_MODEL_CAP = 400

#: The global rate limit in requests per minute.
DEFAULT_RATE_LIMIT = 15


class TrialHalt(Exception):
    """Raised when the trial must stop."""


def _usage_path(provider: str) -> Path:
    """Where the daily counter of a provider lives."""
    base = os.environ.get("AGENTETHER_USAGE_DIR")
    root = Path(base) if base else Path.home() / ".cache" / "agentether" / "usage"
    return root / f"{provider}.json"


# ----------------------------------------------------------------------
# the model call
# ----------------------------------------------------------------------
@dataclass
class ModelStats:
    """The request accounting of one model."""

    model: str
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    consecutive_429: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable copy."""
        return {
            "model": self.model,
            "requests": self.requests,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


class ModelCaller:
    """Calls a model with a rate limit, a cap and 429 handling."""

    def __init__(
        self,
        model: str,
        spec: ProviderSpec,
        limiter: TokenBucketLimiter,
        stats: ModelStats,
        cap: int,
        counter: DailyCounter | None = None,
    ) -> None:
        self.model = model
        self.spec = spec
        self.limiter = limiter
        self.stats = stats
        self.cap = cap
        self.counter = counter

    async def call(self, prompt: str) -> Any:
        """One request.  Raises ``TrialHalt`` when the cap is reached."""
        if self.stats.requests >= self.cap:
            raise TrialHalt(f"the request cap of {self.cap} was reached for {self.model}")
        self.stats.requests += 1
        try:
            output = await openai_compatible_complete(
                prompt,
                spec=self.spec,
                model=self.model,
                api_key_resolver=lambda: resolve_provider_key(self.spec),
                max_retries=0,
                limiter=self.limiter,
                counter=self.counter,
            )
        except OpenAICompatibleTransientError as exc:
            self.stats.consecutive_429 += 1
            if self.stats.consecutive_429 >= 5:
                raise TrialHalt(f"{self.model} kept returning a temporary error: {exc}") from exc
            await asyncio.sleep(min(exc.retry_after or 5.0, 60.0))
            raise
        except OpenAICompatibleError as exc:
            # A rejected key or a request that needs money: the run must
            # stop, and the message must say why.
            raise TrialHalt(f"{self.model} was refused by the provider: {exc}") from exc
        self.stats.consecutive_429 = 0
        usage = output.usage
        if usage is not None:
            self.stats.input_tokens += usage.input_tokens
            self.stats.output_tokens += usage.output_tokens
        return output


# ----------------------------------------------------------------------
# the statistics
# ----------------------------------------------------------------------
def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """The Wilson score interval of a proportion.

    Args:
        successes: The number of successes.
        total: The number of trials.
        z: The z value of the confidence level (1.96 is 95%).

    Returns:
        ``(low, high)``.  ``(0.0, 1.0)`` when there is no trial at all.
    """
    if total <= 0:
        return 0.0, 1.0
    proportion = successes / total
    denominator = 1 + z**2 / total
    centre = proportion + z**2 / (2 * total)
    margin = z * ((proportion * (1 - proportion) / total + z**2 / (4 * total**2)) ** 0.5)
    return (max(0.0, (centre - margin) / denominator), min(1.0, (centre + margin) / denominator))


def summarise(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate the cells into the tables of the report.

    The models and the conditions are taken from the cells themselves and
    not from a fixed list, so a trial with the models of several providers
    is summarised like any other.
    """
    out: dict[str, Any] = {}
    models = sorted({str(cell.get("model", "")) for cell in cells})
    conditions = sorted({str(cell.get("condition", "")) for cell in cells})
    for model in models:
        for condition in conditions:
            key = f"{model}|{condition}"
            rows = [cell for cell in cells if cell["key"] == key]
            if not rows:
                continue
            for arm in sorted({str(row.get("arm", "")) for row in rows}):
                arm_rows = [row for row in rows if row["arm"] == arm]
                if not arm_rows:
                    continue
                total = len(arm_rows)
                correct = sum(1 for row in arm_rows if row["correct"])
                false = sum(1 for row in arm_rows if row["false_completion"])
                reported = sum(1 for row in arm_rows if row["reported_complete"])
                requests = sum(row.get("requests", 0) for row in arm_rows)
                tokens = sum(row.get("tokens", 0) for row in arm_rows)
                seconds = sum(row.get("seconds", 0.0) for row in arm_rows)
                rejections = sum(row.get("verifier_rejections", 0) for row in arm_rows)
                loops = sum(row.get("loop_detections", 0) for row in arm_rows)
                retries = sum(max(0, row.get("attempts", 1) - 1) for row in arm_rows)
                out[f"{key}|{arm}"] = {
                    "n": total,
                    "correct": correct,
                    "correct_rate": correct / total,
                    "correct_ci": wilson_interval(correct, total),
                    "false_completions": false,
                    "false_rate": false / total,
                    "false_ci": wilson_interval(false, total),
                    "reported": reported,
                    "requests": requests,
                    "tokens": tokens,
                    "seconds": round(seconds, 2),
                    "verifier_rejections": rejections,
                    "loop_detections": loops,
                    "retries": retries,
                }
    return out


def paired_difference(
    cells: list[dict[str, Any]], key: str, arm_a: str, arm_b: str, field_name: str
) -> dict[str, Any]:
    """The paired difference of two arms over the same tasks.

    Args:
        cells: The cells of the run.
        key: The cell key (model and condition).
        arm_a: The first arm.
        arm_b: The second arm.
        field_name: The boolean field to compare.

    Returns:
        The counts and the interval of the difference.
    """
    rows_a = {row["task"]: row for row in cells if row["key"] == key and row["arm"] == arm_a}
    rows_b = {row["task"]: row for row in cells if row["key"] == key and row["arm"] == arm_b}
    shared = sorted(set(rows_a) & set(rows_b))
    only_a = sum(1 for task in shared if rows_a[task][field_name] and not rows_b[task][field_name])
    only_b = sum(1 for task in shared if rows_b[task][field_name] and not rows_a[task][field_name])
    both = sum(1 for task in shared if rows_a[task][field_name] and rows_b[task][field_name])
    neither = len(shared) - only_a - only_b - both
    total = len(shared)
    difference = (only_a - only_b) / total if total else 0.0
    return {
        "n": total,
        "only_" + arm_a: only_a,
        "only_" + arm_b: only_b,
        "both": both,
        "neither": neither,
        "difference": difference,
        "discordant": only_a + only_b,
    }


# ----------------------------------------------------------------------
# the runner
# ----------------------------------------------------------------------
def _read_progress(progress_path: Path) -> list[dict[str, Any]]:
    """The cells of the previous runs of this work directory."""
    cells: list[dict[str, Any]] = []
    if not progress_path.exists():
        return cells
    seen: set[tuple[str, str, str, str]] = set()
    with progress_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (record["model"], record["arm"], record["condition"], record["task"])
            if key in seen:
                continue
            seen.add(key)
            cells.append(record)
    return cells


def _seed_stats(stats: dict[str, ModelStats], cells: list[dict[str, Any]]) -> None:
    """Seed the counters of a resumed run with the cells of the past runs.

    Without this, the request and token totals of a resumed run would only
    count the cells of the last session.
    """
    for cell in cells:
        stat = stats.get(cell.get("model", ""))
        if stat is None:
            continue
        stat.requests += int(cell.get("requests", 0) or 0)
        stat.input_tokens += int(cell.get("input_tokens", 0) or 0)
        stat.output_tokens += int(cell.get("output_tokens", 0) or 0)


async def run_trial(
    models: tuple[str, ...],
    arms: tuple[str, ...],
    conditions: tuple[str, ...],
    tasks: list[TaskSpec],
    per_cell: int,
    rate_limit: int,
    model_cap: int,
    workdir: Path,
    progress_path: Path,
    provider: str = "openrouter",
    caller_factory: Callable[[str, Any, ModelStats, int], Caller] | None = None,
) -> dict[str, Any]:
    """Run the trial and return the result payload.

    Args:
        models: The model ids to run.
        arms: The arms to run.
        conditions: The conditions to run.
        tasks: The task set.
        per_cell: The number of tasks per cell.
        rate_limit: The requests per minute.
        model_cap: The hard cap of requests per model.
        workdir: The directory of the sandboxes.
        progress_path: The resumable progress file.
        provider: The provider of the models.  The rate and the daily
            limit of the provider are never exceeded: the requests per
            minute are the smallest of the requested rate and the limit of
            the provider, and the daily count is kept on disk.
        caller_factory: Builds the caller of a model.  It is ``None`` in
            the trial (the live model) and a script in the tests.
    """
    spec = provider_for(provider)
    limiter = TokenBucketLimiter(min(rate_limit, spec.requests_per_minute))
    counter = DailyCounter(_usage_path(provider), spec.requests_per_day, spec.name)
    stats = {model: ModelStats(model) for model in models}
    cells: list[dict[str, Any]] = []
    halted = ""
    started = time.monotonic()

    done: set[tuple[str, str, str, str]] = set()
    for record in _read_progress(progress_path):
        key = (record["model"], record["arm"], record["condition"], record["task"])
        done.add(key)
        cells.append(record)
    _seed_stats(stats, cells)

    selected = tasks[:per_cell]
    for model in models:
        if caller_factory is None:
            caller: Caller = ModelCaller(model, spec, limiter, stats[model], model_cap, counter)
        else:
            caller = caller_factory(model, limiter, stats[model], model_cap)
        for condition in conditions:
            for arm in arms:
                for index, task in enumerate(selected):
                    key = (model, arm, condition, task.name)
                    if key in done:
                        continue
                    # A model id contains characters that Windows does not
                    # allow in a path (a colon).
                    safe_model = model.replace("/", "_").replace(":", "_")
                    sandbox = workdir / safe_model / arm / condition / task.name
                    sandbox.mkdir(parents=True, exist_ok=True)
                    memory = sandbox.parent / f"{task.name}-memory"
                    memory.mkdir(parents=True, exist_ok=True)
                    before = stats[model].requests
                    tokens_before = stats[model].input_tokens + stats[model].output_tokens
                    step_started = time.monotonic()
                    try:
                        if arm == "naive":
                            outcome = await run_arm_naive(task, sandbox, caller, condition, index)
                        elif arm == "simple-retry":
                            outcome = await run_arm_simple_retry(
                                task, sandbox, caller, condition, index
                            )
                        else:
                            outcome = await run_arm_agentether(
                                task, sandbox, memory, caller, condition, index
                            )
                    except TrialHalt as exc:
                        halted = str(exc)
                        break
                    requests = stats[model].requests - before
                    tokens = stats[model].input_tokens + stats[model].output_tokens - tokens_before
                    record = {
                        "key": f"{model}|{condition}",
                        "model": model,
                        "condition": condition,
                        "arm": arm,
                        "task": task.name,
                        "task_index": index,
                        "attempts": outcome.attempts,
                        "reported_complete": outcome.believed,
                        "step_verdicts": list(outcome.step_verdicts),
                        "correct": task_is_correct(task, sandbox),
                        "artifacts_present": artifacts_present(task, sandbox),
                        "requests": requests,
                        "tokens": tokens,
                        "seconds": round(time.monotonic() - step_started, 3),
                        "verifier_rejections": outcome.verifier_rejections,
                        "loop_detections": outcome.loop_detections,
                        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    }
                    record["false_completion"] = (
                        record["reported_complete"] and not record["correct"]
                    )
                    cells.append(record)
                    with progress_path.open("a", encoding="utf-8", newline="\n") as handle:
                        handle.write(json.dumps(record, sort_keys=True) + "\n")
                if halted:
                    break
            if halted:
                break
        if halted:
            break

    measured = sum(float(cell.get("seconds", 0.0) or 0.0) for cell in cells)
    payload = {
        "simulated": False,
        "real_model_trial": True,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "protocol": "docs/trial-protocol.md",
        "fault_rate": FAULT_RATE,
        "fault_seed": FAULT_SEED,
        "attempt_cap": ATTEMPT_CAP,
        "rate_limit_per_minute": rate_limit,
        "model_request_cap": model_cap,
        "provider": provider,
        "models": list(models),
        "arms": list(arms),
        "conditions": list(conditions),
        "tasks_per_cell": per_cell,
        "halted": halted,
        # The wall clock of this session, and the time the calls took in
        # total (which also covers the cells of the previous sessions of a
        # resumed run).
        "wall_seconds": round(time.monotonic() - started, 2),
        "measured_seconds": round(measured, 3),
        "model_stats": {model: stat.to_dict() for model, stat in stats.items()},
        "cells": cells,
        "summary": summarise(cells),
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    """Entry point of the trial."""
    parser = argparse.ArgumentParser(description="Run the evidence trial.")
    parser.add_argument("--provider", default="openrouter", help="the provider of the models")
    parser.add_argument("--models", nargs="*", default=list(MODELS))
    parser.add_argument("--arms", nargs="*", default=list(ARMS))
    parser.add_argument("--conditions", nargs="*", default=list(CONDITIONS))
    parser.add_argument("--tasks", type=int, default=10, help="tasks per cell")
    parser.add_argument("--rate-limit", type=int, default=DEFAULT_RATE_LIMIT)
    parser.add_argument("--model-cap", type=int, default=DEFAULT_MODEL_CAP)
    parser.add_argument(
        "--workdir",
        default=str(Path(tempfile.gettempdir()) / "agentether-trial"),
    )
    parser.add_argument(
        "--output",
        default=str(
            Path(__file__).resolve().parent
            / "results"
            / f"trial-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
        ),
    )
    args = parser.parse_args(argv)

    try:
        spec = provider_for(args.provider)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if spec.key_variables():
        try:
            resolve_provider_key(spec)
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 2

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    progress = workdir / "progress.jsonl"
    payload = asyncio.run(
        run_trial(
            models=tuple(args.models),
            arms=tuple(args.arms),
            conditions=tuple(args.conditions),
            tasks=TASKS,
            per_cell=args.tasks,
            rate_limit=args.rate_limit,
            model_cap=args.model_cap,
            workdir=workdir,
            progress_path=progress,
            provider=args.provider,
        )
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"cells: {len(payload['cells'])}")
    print(f"requests: {payload['model_stats']}")
    print(f"halted: {payload['halted'] or 'no'}")
    print(f"results: {output}")
    print(f"resume: python benchmarks/trial.py --workdir {workdir} --output {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
