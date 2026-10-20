"""A reproducible **simulated** benchmark.

.. warning::
   **This is a simulation, not a real world measurement.**  No LLM is called.
   A seeded random number generator produces a *failure schedule* for a
   synthetic agent, and two runners are compared over the very same
   schedules:

   1. the **naive** runner calls the worker, retries blindly up to a fixed
      cap and trusts whatever the worker claims;
   2. the **guarded** runner is ContextGuard with verifiers, semantic loop
      detection and a circuit breaker.

   The numbers say something about *the policies*, not about how well the
   library performs against a real model.  They must never be quoted as
   evidence of real world effectiveness.

Every parameter of the simulation is documented in
:class:`BenchmarkConfig` and echoed into the result, so a reader can
reproduce or criticise the numbers.

.. versionadded:: 0.2.0
"""

from __future__ import annotations

import asyncio
import json
import random
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .exceptions import ContextGuardError
from .loop_detector import fingerprint, jaccard
from .models import StepContext
from .orchestrator import AutoOrchestrator
from .state_manager import StateManager
from .verifier import artifacts_exist

__all__ = [
    "BenchmarkConfig",
    "BenchmarkResult",
    "FakeClock",
    "RunnerMetrics",
    "run_benchmark",
]

#: Two answers are "the same answer" when their similarity reaches this
#: value.  It is the same threshold the loop detector uses.
REPEAT_THRESHOLD: float = 0.9

#: The failure modes the simulated agent can produce.
FAILURE_MODES: tuple[str, ...] = (
    "ok",
    "malformed",
    "drift",
    "lie",
    "loop",
    "partial",
    "hang",
)


class FakeClock:
    """A monotonic clock that only moves when the simulation says so.

    Attributes:
        now: The current time.
    """

    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        """Move the clock forward."""
        self.now += seconds


@dataclass(frozen=True)
class BenchmarkConfig:
    """Every parameter of the simulation.

    Attributes:
        trials: Number of simulated tasks.
        seed: Seed of the random number generator.
        steps: Number of roadmap steps per task.
        max_attempts: Attempt cap per step, identical for both runners.
        tokens_per_attempt: Simulated token cost of one attempt.
        seconds_per_attempt: Simulated duration of one attempt.
        p_unrecoverable_step: Probability that a step can never be completed
            (the agent never gets it right in the allowed attempts).
        probabilities: Probability of each failure mode for a failing attempt.
    """

    trials: int = 100
    seed: int = 0
    steps: int = 3
    max_attempts: int = 4
    tokens_per_attempt: int = 800
    seconds_per_attempt: float = 2.0
    p_unrecoverable_step: float = 0.15
    probabilities: dict[str, float] = field(
        default_factory=lambda: {
            "malformed": 0.25,
            "drift": 0.15,
            "lie": 0.15,
            "loop": 0.15,
            "partial": 0.10,
            "hang": 0.10,
        }
    )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable copy of the configuration."""
        return {
            "trials": self.trials,
            "seed": self.seed,
            "steps": self.steps,
            "max_attempts": self.max_attempts,
            "tokens_per_attempt": self.tokens_per_attempt,
            "seconds_per_attempt": self.seconds_per_attempt,
            "p_unrecoverable_step": self.p_unrecoverable_step,
            "probabilities": dict(self.probabilities),
        }


@dataclass
class RunnerMetrics:
    """The metrics of one runner.

    Attributes:
        name: Name of the runner.
        tasks: Number of simulated tasks.
        completed: Tasks the runner reported as finished.
        false_completions: Tasks the runner reported as finished although an
            artifact was missing.
        correct_completions: Tasks the runner reported as finished *and* that
            were really done (every artifact present).  This is the headline
            metric.
        total_attempts: Attempts across all tasks.
        total_steps: Steps across all tasks.
        repeated_attempts: Attempts whose answer was near-identical to the
            previous answer of the same step.  The metric is computed the
            same way for both runners, so it is comparable.
        simulated_cost: ``attempts * tokens_per_attempt``.
        halt_seconds: Simulated seconds until the runner gave up, per task.
    """

    name: str
    tasks: int = 0
    completed: int = 0
    false_completions: int = 0
    correct_completions: int = 0
    total_attempts: int = 0
    total_steps: int = 0
    repeated_attempts: int = 0
    simulated_cost: int = 0
    halt_seconds: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable copy of these metrics."""
        return {
            "name": self.name,
            "tasks": self.tasks,
            "completed": self.completed,
            "false_completions": self.false_completions,
            "correct_completions": self.correct_completions,
            "total_attempts": self.total_attempts,
            "total_steps": self.total_steps,
            "repeated_attempts": self.repeated_attempts,
            "simulated_cost": self.simulated_cost,
            "mean_attempts_per_step": (
                self.total_attempts / self.total_steps if self.total_steps else 0.0
            ),
            "completion_rate": (self.completed / self.tasks) if self.tasks else 0.0,
            "false_completion_rate": (self.false_completions / self.tasks if self.tasks else 0.0),
            "correct_completion_rate": (
                self.correct_completions / self.tasks if self.tasks else 0.0
            ),
            "mean_time_to_halt_seconds": (
                sum(self.halt_seconds) / len(self.halt_seconds) if self.halt_seconds else 0.0
            ),
        }


@dataclass
class BenchmarkResult:
    """The result of a benchmark run.

    Attributes:
        config: The configuration that produced this result.
        naive: Metrics of the naive runner.
        guarded: Metrics of the guarded runner.
    """

    config: BenchmarkConfig
    naive: RunnerMetrics
    guarded: RunnerMetrics

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable copy of the result."""
        return {
            "simulated": True,
            "warning": (
                "SIMULATED benchmark: no LLM was called, the failure schedules are "
                "produced by a seeded random number generator."
            ),
            "config": self.config.to_dict(),
            "runners": {
                "naive": self.naive.to_dict(),
                "guarded": self.guarded.to_dict(),
            },
        }

    def to_markdown(self) -> str:
        """Render the result as a Markdown report."""
        data = self.to_dict()
        naive = data["runners"]["naive"]
        guarded = data["runners"]["guarded"]
        lines = [
            "# Simulated benchmark (not a real-world measurement)",
            "",
            "> **This is a simulation.** No LLM was called. A seeded random number",
            "> generator produces a failure schedule for a synthetic agent and both",
            "> runners are compared over the very same schedules. The numbers",
            "> describe the *policies*, not the real-world behaviour of any model.",
            "",
            "## Parameters",
            "",
            "| Parameter | Value |",
            "| --- | --- |",
        ]
        for key, value in sorted(self.config.to_dict().items()):
            lines.append(f"| `{key}` | `{value}` |")
        lines.extend(
            [
                "",
                "## Results",
                "",
                "| Metric | naive | guarded |",
                "| --- | --- | --- |",
            ]
        )
        rows = [
            ("tasks", "tasks"),
            ("**correct completion rate** (done *and* really finished)", "correct_completion_rate"),
            ("reported completion rate (claims only)", "completion_rate"),
            ("false completion rate (claimed, not done)", "false_completion_rate"),
            ("mean attempts per step", "mean_attempts_per_step"),
            ("total attempts", "total_attempts"),
            ("repeated attempts (answer ~ previous answer)", "repeated_attempts"),
            ("simulated cost (tokens)", "simulated_cost"),
            ("mean time to halt (s)", "mean_time_to_halt_seconds"),
        ]
        for label, key in rows:
            naive_value = naive[key]
            guarded_value = guarded[key]
            if isinstance(naive_value, float):
                naive_text = f"{naive_value:.3f}"
                guarded_text = f"{guarded_value:.3f}"
            else:
                naive_text = str(naive_value)
                guarded_text = str(guarded_value)
            lines.append(f"| {label} | {naive_text} | {guarded_text} |")
        lines.extend(
            [
                "",
                "## What this does and does not show",
                "",
                "- It shows how the two *policies* behave on the same failure",
                "  schedule: the naive runner trusts the agent, the guarded runner",
                "  checks the claim.",
                "- It does **not** show that the library works with a real model,",
                "  that a real agent fails this way, or that these numbers",
                "  generalise beyond the documented parameters.",
                "- The guarded runner can use *more* attempts than the naive one:",
                "  it refuses to accept a claim that a verifier rejected, and that",
                "  is a deliberate trade-off, not a win.",
                "- The headline metric is the *correct* completion rate: a task",
                "  counts only when the runner finished it **and** every artifact",
                "  is really there.  The naive runner's higher reported completion",
                "  rate is made of tasks that were never really done.",
                "",
            ]
        )
        return "\n".join(lines)


def _make_schedule(
    rng: random.Random, config: BenchmarkConfig, steps: list[str]
) -> dict[str, list[str]]:
    """Build the failure schedule of one simulated task."""
    schedule: dict[str, list[str]] = {}
    for step in steps:
        if rng.random() < config.p_unrecoverable_step:
            modes = [rng.choices(FAILURE_MODES[:-1], weights=_weights(config))[0]]
            modes = [modes[0]] * config.max_attempts
        else:
            modes = []
            for _ in range(config.max_attempts):
                if rng.random() < 0.45:
                    modes.append("ok")
                else:
                    modes.append(rng.choices(FAILURE_MODES[:-1], weights=_weights(config))[0])
        schedule[step] = modes
    return schedule


def _weights(config: BenchmarkConfig) -> list[float]:
    return [config.probabilities.get(mode, 0.0) for mode in FAILURE_MODES[:-1]]


def _artifact_name(step: str) -> str:
    return f"{step}.out"


def _answer_for(mode: str, step: str, attempt: int) -> str:
    """The answer the simulated agent produces for one mode.

    The same function is used by both runners, so the answers of the naive
    and the guarded run can be compared.
    """
    if mode == "malformed":
        return "I could not produce the report in the expected format."
    if mode == "drift":
        return json.dumps(
            {
                "step": "some_other_step",
                "status": "completed",
                "summary": "finished something else",
                "progress": 100,
            }
        )
    if mode == "lie":
        # Claims success but produces no artifact at all.
        return json.dumps(
            {
                "step": step,
                "status": "completed",
                "summary": "all done",
                "progress": 100,
                "artifacts": [_artifact_name(step)],
            }
        )
    if mode == "loop":
        token = f"{attempt:04x}{abs(hash(step)) % 9973:04x}"
        return f"I am still working on the task, token {token}. " + (
            "the same summary text repeated verbatim " * 4
        )
    if mode == "partial":
        return json.dumps(
            {
                "step": step,
                "status": "in_progress",
                "summary": "halfway there",
                "progress": min(90, 10 * attempt),
            }
        )
    return json.dumps(
        {
            "step": step,
            "status": "completed",
            "summary": f"completed {step}",
            "progress": 100,
            "artifacts": [_artifact_name(step)],
        }
    )


def _count_repeated_answers(answers: list[str]) -> int:
    """Count the answers that are near-identical to the previous one.

    The metric does not depend on the runner: it is computed from the
    answers themselves, so the naive runner (which keeps retrying) and the
    guarded runner (which stops) are compared on the same scale.
    """
    repeats = 0
    previous: frozenset[str] | None = None
    for answer in answers:
        current = fingerprint(answer)
        if previous is not None and jaccard(current, previous) >= REPEAT_THRESHOLD:
            repeats += 1
        previous = current
    return repeats


def _answers_for_attempts(schedule: dict[str, list[str]], step: str, count: int) -> list[str]:
    """The answers the agent would have produced in ``count`` attempts."""
    modes = schedule.get(step, [])
    answers: list[str] = []
    for attempt in range(1, count + 1):
        mode = modes[min(attempt - 1, len(modes) - 1)] if modes else "ok"
        if mode == "hang":
            answers.append("")
            continue
        answers.append(_answer_for(mode, step, attempt))
    return answers


async def _simulated_agent(
    ctx: StepContext,
    schedule: dict[str, list[str]],
    workdir: Path,
    clock: FakeClock,
    config: BenchmarkConfig,
) -> str:
    """The synthetic agent: it fails in the ways the schedule says."""
    modes = schedule.get(ctx.step_name, [])
    index = min(ctx.attempt - 1, len(modes) - 1) if modes else 0
    mode = modes[index] if modes else "ok"
    clock.advance(config.seconds_per_attempt)

    if mode == "hang":
        # A hang is simulated by jumping the fake clock past the timeout and
        # raising the same exception the event loop would raise.  Nothing
        # really sleeps.
        clock.advance(config.seconds_per_attempt * 10)
        raise asyncio.TimeoutError

    answer = _answer_for(mode, ctx.step_name, ctx.attempt)
    if mode == "ok":
        artifact = workdir / _artifact_name(ctx.step_name)
        artifact.write_text(f"result of {ctx.step_name}" + chr(10), encoding="utf-8")
    return answer


def _naive_runner(
    schedule: dict[str, list[str]],
    steps: list[str],
    workdir: Path,
    clock: FakeClock,
    config: BenchmarkConfig,
) -> tuple[bool, int, dict[str, int]]:
    """The naive runner: call, retry blindly, trust the claim.

    Returns:
        ``(reported_complete, attempts, attempts_per_step)``.
    """
    attempts = 0
    per_step: dict[str, int] = {}
    for step in steps:
        reported = False
        step_attempts = 0
        for attempt in range(1, config.max_attempts + 1):
            attempts += 1
            step_attempts += 1
            clock.advance(config.seconds_per_attempt)
            modes = schedule.get(step, [])
            mode = modes[min(attempt - 1, len(modes) - 1)] if modes else "ok"
            if mode in ("hang", "malformed", "drift", "loop", "partial"):
                continue
            if mode == "lie":
                # The naive runner believes the claim -- and no artifact
                # appears, because the agent did not do the work.
                reported = True
                break
            (workdir / _artifact_name(step)).write_text(
                f"result of {step}" + chr(10), encoding="utf-8"
            )
            reported = True
            break
        per_step[step] = step_attempts
        if not reported:
            return False, attempts, per_step
    return True, attempts, per_step


async def _guarded_runner(
    schedule: dict[str, list[str]],
    steps: list[str],
    workdir: Path,
    memory_dir: Path,
    clock: FakeClock,
    config: BenchmarkConfig,
) -> tuple[bool, int, dict[str, int]]:
    """The guarded runner: ContextGuard with verifiers and a breaker.

    Returns:
        ``(reported_complete, attempts, attempts_per_step)``.
    """
    orchestrator = AutoOrchestrator(
        roadmap=list(steps),
        memory_dir=str(memory_dir),
        timeout_seconds=config.seconds_per_attempt,
        max_retries=config.max_attempts,
        workdir=str(workdir),
        clock=clock,
        events_enabled=False,
        resume=False,
        backoff_base=0.0,
    )
    reported = True
    for step in steps:

        @orchestrator.guard_step(step, verify=[artifacts_exist()])
        async def _worker(ctx: StepContext, _step: str = step) -> str:
            return await _simulated_agent(ctx, schedule, workdir, clock, config)

        try:
            result = await _worker()
        except ContextGuardError:
            reported = False
            break
        except Exception:
            reported = False
            break
        if result.telemetry.status != "completed":
            reported = False
            break
    # Count the attempts from the attempt log: it is the same number the
    # orchestrator actually used.
    attempts, per_step = await _count_attempts(memory_dir)
    return reported, attempts, per_step


def _repeats(schedule: dict[str, list[str]], per_step: dict[str, int]) -> int:
    """Count the repeated answers over all the steps of one task."""
    repeats = 0
    for step, count in per_step.items():
        answers = _answers_for_attempts(schedule, step, count)
        repeats += _count_repeated_answers(answers)
    return repeats


def _missing_artifacts(steps: list[str], workdir: Path) -> list[str]:
    """Return the steps whose artifact is missing on disk (the ground truth)."""
    return [step for step in steps if not (workdir / _artifact_name(step)).exists()]


async def _count_attempts(memory_dir: Path) -> tuple[int, dict[str, int]]:
    """Count the attempt records written by the guarded runner.

    Returns:
        ``(total_attempts, attempts_per_step)``.
    """
    manager = StateManager(memory_dir)
    state = await manager.load()
    per_step: dict[str, int] = {}
    total = 0
    for step, records in (state.get("attempts") or {}).items():
        count = len(records)
        per_step[str(step)] = count
        total += count
    return total, per_step


async def _run_trial(
    trial: int, config: BenchmarkConfig, rng: random.Random
) -> tuple[RunnerMetrics, RunnerMetrics]:
    """Run one simulated task with both runners."""
    steps = [f"step{index + 1}" for index in range(config.steps)]
    schedule = _make_schedule(rng, config, steps)
    root = Path(tempfile.mkdtemp(prefix="contextguard-bench-"))
    try:
        naive_work = root / "naive"
        guarded_work = root / "guarded"
        naive_work.mkdir()
        guarded_work.mkdir()
        guarded_memory = root / "memory"
        guarded_memory.mkdir()

        naive_clock = FakeClock()
        naive_complete, naive_attempts, naive_per_step = _naive_runner(
            schedule, steps, naive_work, naive_clock, config
        )
        naive_missing = _missing_artifacts(steps, naive_work)
        naive_false = int(naive_complete and bool(naive_missing))
        naive_correct = int(naive_complete and not naive_missing)
        naive_repeats = _repeats(schedule, naive_per_step)

        guarded_clock = FakeClock()
        guarded_complete, guarded_attempts, guarded_per_step = await _guarded_runner(
            schedule, steps, guarded_work, guarded_memory, guarded_clock, config
        )
        guarded_missing = _missing_artifacts(steps, guarded_work)
        guarded_false = int(guarded_complete and bool(guarded_missing))
        guarded_correct = int(guarded_complete and not guarded_missing)
        guarded_repeats = _repeats(schedule, guarded_per_step)

        naive = RunnerMetrics(name="naive")
        guarded = RunnerMetrics(name="guarded")
        for metrics, complete, attempts, false_completion, correct, repeats, clock in (
            (
                naive,
                naive_complete,
                naive_attempts,
                naive_false,
                naive_correct,
                naive_repeats,
                naive_clock,
            ),
            (
                guarded,
                guarded_complete,
                guarded_attempts,
                guarded_false,
                guarded_correct,
                guarded_repeats,
                guarded_clock,
            ),
        ):
            metrics.tasks = 1
            metrics.total_steps = config.steps
            metrics.total_attempts = attempts
            metrics.repeated_attempts = repeats
            metrics.simulated_cost = attempts * config.tokens_per_attempt
            if complete:
                metrics.completed = 1
            if false_completion:
                metrics.false_completions = 1
            if correct:
                metrics.correct_completions = 1
            metrics.halt_seconds.append(clock.now)
        return naive, guarded
    finally:
        shutil.rmtree(root, ignore_errors=True)


async def _run_trials(config: BenchmarkConfig) -> BenchmarkResult:
    """Run every trial and aggregate the metrics."""
    rng = random.Random(config.seed)
    naive = RunnerMetrics(name="naive")
    guarded = RunnerMetrics(name="guarded")
    for trial in range(config.trials):
        trial_naive, trial_guarded = await _run_trial(trial, config, rng)
        for total, part in ((naive, trial_naive), (guarded, trial_guarded)):
            total.tasks += part.tasks
            total.completed += part.completed
            total.false_completions += part.false_completions
            total.correct_completions += part.correct_completions
            total.total_attempts += part.total_attempts
            total.total_steps += part.total_steps
            total.repeated_attempts += part.repeated_attempts
            total.simulated_cost += part.simulated_cost
            total.halt_seconds.extend(part.halt_seconds)
    return BenchmarkResult(config=config, naive=naive, guarded=guarded)


def run_benchmark(trials: int = 100, seed: int = 0, **overrides: Any) -> BenchmarkResult:
    """Run the simulated benchmark.

    Args:
        trials: Number of simulated tasks.
        seed: Seed of the random number generator.  The same seed always
            produces the same result.
        **overrides: Additional :class:`BenchmarkConfig` fields.

    Returns:
        The aggregated result.
    """
    config = BenchmarkConfig(trials=trials, seed=seed, **overrides)
    return asyncio.run(_run_trials(config))
