"""The accounting of the trial runner.

Run 1 recorded ``tokens: 0`` next to ``requests: 291``: the runner that
produced it had ``tokens = 0`` hard-coded, and the wall clock of the
committed payload was 0 as well.  These tests pin the accounting down.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))

from harness import Caller
from tasks import TASKS, Check, FileSpec, StepSpec, TaskSpec
from trial import ModelStats, RateLimiter, _read_progress, _seed_stats, run_trial

from agentether import Usage, WorkerOutput


class CountingCaller:
    """A caller that accounts for its requests and its tokens."""

    def __init__(self, stats: ModelStats, text: str) -> None:
        self.stats = stats
        self.text = text

    async def call(self, prompt: str) -> WorkerOutput:
        """One counted request."""
        self.stats.requests += 1
        self.stats.input_tokens += 11
        self.stats.output_tokens += 7
        return WorkerOutput(text=self.text, usage=Usage(input_tokens=11, output_tokens=7))


def make_task() -> TaskSpec:
    """A one step task with a ground truth the arms never see."""
    step = StepSpec(
        name="notes",
        instruction="Write the file notes.md with the heading '## Context'.",
        files=(FileSpec(path="notes.md"),),
    )
    return TaskSpec(
        name="t1",
        steps=(step,),
        checks=(Check("file_exists", "notes.md"),),
    )


def answer(step: str = "notes") -> str:
    """A raw model answer."""
    return "```\nFILE: notes.md\n# Notes\n## Context\nhello\n```\n" + json.dumps(
        {
            "step": step,
            "status": "completed",
            "summary": "did the work",
            "progress": 100,
            "next_step": None,
            "artifacts": ["notes.md"],
        }
    )


def factory(text: str) -> Any:
    """A caller factory for the fake model."""

    def _make(model: str, limiter: RateLimiter, stats: ModelStats, cap: int) -> Caller:
        return CountingCaller(stats, text)

    return _make


async def test_the_runner_counts_the_tokens_of_the_model(tmp_path: Path) -> None:
    """The tokens of the answers must end up in the payload.

    Run 1 recorded zero tokens for 291 requests.
    """
    payload = await run_trial(
        models=("fake/model",),
        arms=("naive",),
        conditions=("natural",),
        tasks=[make_task()],
        per_cell=1,
        rate_limit=1000,
        model_cap=100,
        workdir=tmp_path / "work",
        progress_path=tmp_path / "progress.jsonl",
        caller_factory=factory(answer()),
    )

    stats = payload["model_stats"]["fake/model"]
    assert stats["requests"] == 1
    assert stats["input_tokens"] == 11
    assert stats["output_tokens"] == 7

    cell = payload["cells"][0]
    assert cell["tokens"] == 18
    assert cell["requests"] == 1
    assert cell["seconds"] > 0.0
    assert payload["measured_seconds"] == pytest.approx(
        sum(float(c["seconds"]) for c in payload["cells"])
    )


async def test_a_resumed_run_counts_the_cells_of_the_earlier_runs(tmp_path: Path) -> None:
    """A resumed run must not forget the requests of the past sessions.

    The counters of a resumed run start at zero; without the seeding they
    would only count the cells of the last session.
    """
    progress = tmp_path / "progress.jsonl"
    first = await run_trial(
        models=("fake/model",),
        arms=("naive",),
        conditions=("natural",),
        tasks=[make_task()],
        per_cell=1,
        rate_limit=1000,
        model_cap=100,
        workdir=tmp_path / "work",
        progress_path=progress,
        caller_factory=factory(answer()),
    )
    assert first["model_stats"]["fake/model"]["requests"] == 1

    # The same cell is not run again, but the totals must still be there.
    second = await run_trial(
        models=("fake/model",),
        arms=("naive",),
        conditions=("natural",),
        tasks=[make_task()],
        per_cell=1,
        rate_limit=1000,
        model_cap=100,
        workdir=tmp_path / "work",
        progress_path=progress,
        caller_factory=factory(answer()),
    )
    assert second["model_stats"]["fake/model"]["requests"] == 1
    assert len(second["cells"]) == 1


def test_the_seeding_adds_the_cells_of_the_past_runs() -> None:
    """The seeding is a plain sum over the cells."""
    stats = {"fake/model": ModelStats("fake/model")}
    cells = [
        {"model": "fake/model", "requests": 3, "input_tokens": 30, "output_tokens": 7},
        {"model": "fake/model", "requests": 2, "input_tokens": 20, "output_tokens": 3},
    ]
    _seed_stats(stats, cells)
    assert stats["fake/model"].requests == 5
    assert stats["fake/model"].input_tokens == 50
    assert stats["fake/model"].output_tokens == 10


def test_the_progress_file_is_read_once_per_cell(tmp_path: Path) -> None:
    """A cell that was written twice is counted once."""
    progress = tmp_path / "progress.jsonl"
    record = {
        "model": "fake/model",
        "arm": "naive",
        "condition": "natural",
        "task": "t1",
        "requests": 1,
    }
    with progress.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
        handle.write(json.dumps(record) + "\n")
    cells = _read_progress(progress)
    assert len(cells) == 1


def test_the_task_set_of_the_trial_is_the_committed_one() -> None:
    """The task set is not changed behind the back of the results."""
    assert len(TASKS) == 20
    assert all(len(task.checks) >= 10 for task in TASKS)
    assert all(3 <= len(task.steps) <= 4 for task in TASKS)
