"""The runner of the evidence trial.

Three arms (naive, simple-retry, agentether), two conditions (natural,
injected), three models.  Every arm sees the same tasks and the same seeded
fault schedule.

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
import random
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tasks import TASKS, Check, TaskSpec

from agentether import (
    AutoOrchestrator,
    StepContext,
    TelemetryParseError,
    WorkerOutput,
    artifacts_exist,
    parse_telemetry,
)
from agentether.adapters.openrouter import (
    OpenRouterError,
    OpenRouterTransientError,
    openrouter_complete,
)

#: The models of the trial (three different families, all free tier).
MODELS: tuple[str, ...] = (
    "minimax/minimax-m3.1-flash:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
)

#: The arms of the trial.
ARMS: tuple[str, ...] = ("naive", "simple-retry", "agentether")

#: The conditions of the trial.
CONDITIONS: tuple[str, ...] = ("natural", "injected")

#: The probability that a fault is injected into an attempt.
FAULT_RATE = 0.20

#: The seed of the fault schedule.
FAULT_SEED = 20261020

#: The hard cap of HTTP requests per model per day.
DEFAULT_MODEL_CAP = 400

#: The global rate limit in requests per minute.
DEFAULT_RATE_LIMIT = 15

#: The attempt cap of the simple-retry and the agentether arms.
ATTEMPT_CAP = 3

PROTOCOL = """\
You are working inside a sandbox. You cannot use tools: you return the content
of every file in a fenced block whose first line is "FILE: <relative path>".

Example:

FILE: notes.md
# Notes
## Context
...

Rules:
- one fenced block per file, and the first line of the block must be
  "FILE: <path>" followed by the content of the file;
- the path must be relative, without ".." and without a drive letter;
- write every file the step asks for, with exactly the content that is asked
  for (the exact headings, the exact keys, the exact numbers);
- end your answer with a single JSON object with the keys "step", "status",
  "summary", "progress", "next_step" and "artifacts" (the list of the files
  you produced, as relative paths);
- the value of "step" must be exactly "{step}";
- report "completed" only when you really produced every file of the step.
"""

_FENCE = re.compile(r"```[^\r\n]*\r?\n(?P<body>.*?)```", re.DOTALL)
_FILE_HEAD = re.compile(r"^\s*FILE:\s*(?P<path>[^\r\n`]+?)\s*$")
_MAX_FILE_BYTES = 64_000
_MAX_SANDBOX_BYTES = 512_000


# ----------------------------------------------------------------------
# the harness protocol
# ----------------------------------------------------------------------
def parse_file_blocks(answer: str) -> list[tuple[str, str]]:
    """Extract the ``FILE: path`` blocks of an answer."""
    found: list[tuple[str, str]] = []
    for match in _FENCE.finditer(answer):
        body = match.group("body")
        lines = body.splitlines()
        if not lines:
            continue
        head = _FILE_HEAD.match(lines[0])
        if head is None:
            continue
        found.append((head.group("path").strip(), "\n".join(lines[1:])))
    return found


def write_answer_files(answer: str, sandbox: Path) -> list[str]:
    """Write the files of an answer into the sandbox (path confined)."""
    written: list[str] = []
    total = 0
    for path, content in parse_file_blocks(answer):
        if not path or path.startswith("/") or ".." in Path(path).parts:
            continue
        encoded = content.encode("utf-8")[:_MAX_FILE_BYTES]
        if total + len(encoded) > _MAX_SANDBOX_BYTES:
            break
        target = sandbox / path
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(encoded)
        except OSError:
            continue
        written.append(path)
        total += len(encoded)
    return written


# ----------------------------------------------------------------------
# the injected faults
# ----------------------------------------------------------------------
def _telemetry_of(answer: str) -> tuple[str, str]:
    """The telemetry JSON of an answer and the text before it."""
    start = answer.rfind("{")
    if start < 0:
        return "", answer
    end = answer.rfind("}")
    if end < start:
        return "", answer
    return answer[start : end + 1], answer[:start]


def inject_fault(answer: str, fault: str, previous: str | None) -> str:
    """Apply one injected fault to an answer.

    Args:
        answer: The answer of the model.
        fault: The name of the fault.
        previous: The previous answer of the same step (for the replay fault).

    Returns:
        The faulty answer.
    """
    if fault == "drop_file_block":
        return re.sub(r"```[^\r\n]*\r?\n.*?```", "", answer, flags=re.DOTALL)
    if fault == "truncate_file":
        blocks = list(_FENCE.finditer(answer))
        if not blocks:
            return answer
        first = blocks[0]
        body = first.group("body")
        half = body[: len(body) // 2]
        new_block = "```\n" + half + "\n```"
        return answer[: first.start()] + new_block + answer[first.end() :]
    if fault == "corrupt_telemetry":
        telemetry, head = _telemetry_of(answer)
        if not telemetry:
            return answer + "\n{not json at all}"
        broken = telemetry.replace('"status"', '"stat us"')
        return head + "\n" + broken
    if fault == "wrong_step":
        telemetry, head = _telemetry_of(answer)
        if not telemetry:
            return answer
        broken = re.sub(r'"step"\s*:\s*"[^"]*"', '"step": "some_other_step"', telemetry)
        return head + "\n" + broken
    if fault == "replay_previous":
        return previous if previous is not None else answer
    if fault == "lie":
        # The claim stays, the file block goes.
        return re.sub(r"```[^\r\n]*\r?\n.*?```", "", answer, flags=re.DOTALL)
    return answer


def fault_for(task_index: int, step_index: int, attempt: int) -> str | None:
    """The fault of one attempt (or ``None``).

    The schedule is seeded and identical for every arm, so the comparison is
    paired.
    """
    rng = random.Random(f"{FAULT_SEED}:{task_index}:{step_index}:{attempt}")
    if rng.random() >= FAULT_RATE:
        return None
    return rng.choice(
        [
            "drop_file_block",
            "truncate_file",
            "corrupt_telemetry",
            "wrong_step",
            "replay_previous",
            "lie",
        ]
    )


# ----------------------------------------------------------------------
# the ground truth
# ----------------------------------------------------------------------
def run_check(check: Check, sandbox: Path) -> bool:
    """Run one ground truth check."""
    target = sandbox / check.path
    if check.kind == "file_exists":
        return target.is_file()
    if not target.is_file():
        return False
    if check.kind in ("contains", "headings"):
        content = target.read_text(encoding="utf-8", errors="replace")
        return bool(check.value in content)
    if check.kind == "python_valid":
        source = target.read_text(encoding="utf-8", errors="replace")
        try:
            compile(source, str(target), "exec")
        except SyntaxError:
            return False
        return True
    if check.kind == "json_keys":
        data = _load_json(target)
        if not isinstance(data, dict):
            return False
        return all(key in data for key in check.value.split(","))
    if check.kind == "json_value":
        data = _load_json(target)
        if not isinstance(data, dict):
            return False
        key, _, expected = check.value.partition("=")
        return bool(str(data.get(key)) == expected)
    return False


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None


def task_is_correct(task: TaskSpec, sandbox: Path) -> bool:
    """Whether every ground truth check of the task passes."""
    return all(run_check(check, sandbox) for check in task.checks)


# ----------------------------------------------------------------------
# the model call
# ----------------------------------------------------------------------
class RateLimiter:
    """A "N requests per minute" limiter."""

    def __init__(self, per_minute: int) -> None:
        self._interval = 60.0 / max(1, per_minute)
        self._last = 0.0

    async def acquire(self) -> None:
        """Wait until the next request may be sent."""
        now = time.monotonic()
        delay = self._last + self._interval - now
        if delay > 0:
            await asyncio.sleep(delay)
        self._last = time.monotonic()


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

    def __init__(self, model: str, limiter: RateLimiter, stats: ModelStats, cap: int) -> None:
        self.model = model
        self.limiter = limiter
        self.stats = stats
        self.cap = cap

    async def call(self, prompt: str) -> WorkerOutput:
        """One request.  Raises ``TrialHalt`` when the cap is reached."""
        await self.limiter.acquire()
        if self.stats.requests >= self.cap:
            raise TrialHalt(f"the request cap of {self.cap} was reached for {self.model}")
        self.stats.requests += 1
        try:
            output = await openrouter_complete(prompt, model=self.model, max_retries=0)
        except OpenRouterTransientError as exc:
            self.stats.consecutive_429 += 1
            if self.stats.consecutive_429 >= 5:
                raise TrialHalt(f"{self.model} kept returning a temporary error: {exc}") from exc
            await asyncio.sleep(min(exc.retry_after or 5.0, 60.0))
            raise
        self.stats.consecutive_429 = 0
        usage = output.usage
        if usage is not None:
            self.stats.input_tokens += usage.input_tokens
            self.stats.output_tokens += usage.output_tokens
        return output


class TrialHalt(Exception):
    """Raised when the trial must stop."""


# ----------------------------------------------------------------------
# the arms
# ----------------------------------------------------------------------
async def run_arm_naive(
    task: TaskSpec,
    sandbox: Path,
    caller: ModelCaller,
    condition: str,
    task_index: int,
) -> dict[str, Any]:
    """Arm A: one call per step, the claim is trusted."""
    attempts = 0
    previous: str | None = None
    believed = False
    for step_index, step in enumerate(task.steps):
        prompt = f"{step.instruction}\n\n{PROTOCOL.format(step=step.name)}"
        output = await caller.call(prompt)
        attempts += 1
        answer = output.text
        if condition == "injected":
            fault = fault_for(task_index, step_index, attempts)
            if fault is not None:
                answer = inject_fault(answer, fault, previous)
        previous = answer
        write_answer_files(answer, sandbox)
        try:
            telemetry = parse_telemetry(answer, step.name)
        except TelemetryParseError:
            continue
        # The belief of the naive arm: the last step claimed "completed".
        believed = telemetry.status == "completed"
    return {"attempts": attempts, "reported_complete": believed}


async def run_arm_simple_retry(
    task: TaskSpec,
    sandbox: Path,
    caller: ModelCaller,
    condition: str,
    task_index: int,
) -> dict[str, Any]:
    """Arm B: retry on a parse failure, an exception or a timeout."""
    attempts = 0
    previous: str | None = None
    believed = False
    for step_index, step in enumerate(task.steps):
        prompt = f"{step.instruction}\n\n{PROTOCOL.format(step=step.name)}"
        for _attempt in range(1, ATTEMPT_CAP + 1):
            try:
                output = await caller.call(prompt)
            except OpenRouterError:
                continue
            except TrialHalt:
                raise
            attempts += 1
            answer = output.text
            if condition == "injected":
                fault = fault_for(task_index, step_index, attempts)
                if fault is not None:
                    answer = inject_fault(answer, fault, previous)
            try:
                telemetry = parse_telemetry(answer, step.name)
            except TelemetryParseError:
                previous = answer
                continue
            if telemetry.status == "completed":
                write_answer_files(answer, sandbox)
                previous = answer
                believed = True
                break
            previous = answer
    return {"attempts": attempts, "reported_complete": believed}


async def run_arm_agentether(
    task: TaskSpec,
    sandbox: Path,
    memory_dir: Path,
    caller: ModelCaller,
    condition: str,
    task_index: int,
) -> dict[str, Any]:
    """Arm C: the full library."""
    orchestrator = AutoOrchestrator(
        roadmap=[step.name for step in task.steps],
        memory_dir=str(memory_dir),
        timeout_seconds=120.0,
        max_retries=ATTEMPT_CAP,
        workdir=str(sandbox),
        backoff_base=0.0,
        events_enabled=True,
        resume=False,
    )
    rejections = 0
    loops = 0
    attempts = 0
    believed = False
    previous: str | None = None

    def on_event(payload: dict[str, Any]) -> None:
        nonlocal rejections, loops
        if payload.get("event") == "verification_failed":
            rejections += 1
        if payload.get("event") == "loop_detected":
            loops += 1

    orchestrator.on("verification_failed", on_event)
    orchestrator.on("loop_detected", on_event)

    for step_index, step in enumerate(task.steps):
        prompt = f"{step.instruction}\n\n{PROTOCOL.format(step=step.name)}"

        @orchestrator.guard_step(step.name, verify=[artifacts_exist()])
        async def _worker(ctx: StepContext, _prompt: str = prompt, _index: int = step_index) -> str:
            nonlocal attempts, previous
            output = await caller.call(_prompt)
            attempts += 1
            answer = output.text
            if condition == "injected":
                fault = fault_for(task_index, _index, attempts)
                if fault is not None:
                    answer = inject_fault(answer, fault, previous)
            previous = answer
            write_answer_files(answer, ctx.workdir)
            return answer

        try:
            outcome = await _worker()
        except TrialHalt:
            raise
        except Exception:
            continue
        believed = outcome.telemetry.status == "completed"
    return {
        "attempts": attempts,
        "reported_complete": believed,
        "verifier_rejections": rejections,
        "loop_detections": loops,
    }


def _artifacts_present(task: TaskSpec, sandbox: Path) -> bool:
    """Whether every expected file is on disk (part of the ground truth)."""
    return bool(task.expected_files) and all(
        (sandbox / path).exists() for path in task.expected_files
    )


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
    """Aggregate the cells into the tables of the report."""
    out: dict[str, Any] = {}
    for model in MODELS:
        for condition in CONDITIONS:
            key = f"{model}|{condition}"
            rows = [cell for cell in cells if cell["key"] == key]
            if not rows:
                continue
            for arm in ARMS:
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
) -> dict[str, Any]:
    """Run the trial and return the result payload."""
    limiter = RateLimiter(rate_limit)
    stats = {model: ModelStats(model) for model in models}
    cells: list[dict[str, Any]] = []
    halted = ""
    started = time.monotonic()

    done: set[tuple[str, str, str, str]] = set()
    if progress_path.exists():
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
                if key in done:
                    continue
                done.add(key)
                cells.append(record)

    selected = tasks[:per_cell]
    for model in models:
        caller = ModelCaller(model, limiter, stats[model], model_cap)
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
                        "attempts": outcome.get("attempts", 0),
                        "reported_complete": bool(outcome.get("reported_complete")),
                        "correct": task_is_correct(task, sandbox),
                        "artifacts_present": _artifacts_present(task, sandbox),
                        "requests": requests,
                        "tokens": tokens,
                        "seconds": round(time.monotonic() - step_started, 3),
                        "verifier_rejections": outcome.get("verifier_rejections", 0),
                        "loop_detections": outcome.get("loop_detections", 0),
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
        "models": list(models),
        "arms": list(arms),
        "conditions": list(conditions),
        "tasks_per_cell": per_cell,
        "halted": halted,
        "wall_seconds": round(time.monotonic() - started, 2),
        "model_stats": {model: stat.to_dict() for model, stat in stats.items()},
        "cells": cells,
        "summary": summarise(cells),
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    """Entry point of the trial."""
    parser = argparse.ArgumentParser(description="Run the evidence trial.")
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

    for name in ("minimax", "MINIMAX", "MINIMAX_API_KEY", "OPENROUTER_API_KEY"):
        if os.environ.get(name):
            break
    else:
        print("no API key found: set MINIMAX (or MINIMAX_API_KEY)", file=sys.stderr)
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
