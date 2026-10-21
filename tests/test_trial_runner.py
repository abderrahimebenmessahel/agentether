"""The accounting of the trial runner.

Run 1 recorded ``tokens: 0`` next to ``requests: 291``: the runner that
produced it had ``tokens = 0`` hard-coded, and the wall clock of the
committed payload was 0 as well.  These tests pin the accounting down.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))

from harness import Caller
from tasks import TASKS, Check, FileSpec, StepSpec, TaskSpec
from trial import ModelStats, _read_progress, _seed_stats, run_trial

from agentether import Usage, WorkerOutput
from agentether.adapters.openai_compatible import TokenBucketLimiter


class CountingCaller:
    """A caller that accounts for its requests and its tokens."""

    def __init__(self, stats: ModelStats, text: str) -> None:
        self.stats = stats
        self.text = text

    async def call(self, prompt: str) -> WorkerOutput:
        """One counted request."""
        # The call takes a little time, so that the measured duration of
        # the cell is not rounded away to zero.  The wait is long enough
        # for the coarse clock of Windows before Python 3.13 (the
        # resolution of ``time.monotonic`` is 15.6 ms there).
        await asyncio.sleep(0.02)
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

    def _make(model: str, limiter: TokenBucketLimiter, stats: ModelStats, cap: int) -> Caller:
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
    assert cell["seconds"] >= 0.0
    # The measured time is the sum of the cells, and it is not zero.
    assert payload["measured_seconds"] == pytest.approx(
        sum(float(c["seconds"]) for c in payload["cells"])
    )
    assert payload["measured_seconds"] > 0.0


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


def test_the_seeding_carries_the_tokens_of_the_cells() -> None:
    """A resumed run must not report zero tokens.

    The cells carry a single ``tokens`` field and not the split between the
    input and the output, so the seeding has to read that field.  It read
    ``input_tokens`` and ``output_tokens`` before, and the summary of the
    resumed run of the trial v2 reported 0 tokens next to 189 requests.
    """
    stats = {"fake/model": ModelStats("fake/model")}
    cells = [
        {"model": "fake/model", "requests": 3, "tokens": 3000},
        {"model": "fake/model", "requests": 2, "tokens": 2000},
    ]
    _seed_stats(stats, cells)
    assert stats["fake/model"].tokens == 5000
    assert stats["fake/model"].to_dict()["tokens"] == 5000


async def test_a_resumed_run_reports_the_tokens_of_the_earlier_cells(tmp_path: Path) -> None:
    """The payload of a resumed run carries the tokens of the past cells."""
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
    assert first["model_stats"]["fake/model"]["tokens"] == 18

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
    # The cell is not run again, but its tokens are still in the summary.
    assert second["model_stats"]["fake/model"]["tokens"] == 18


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


def test_a_cell_without_a_request_is_not_a_measurement(tmp_path: Path) -> None:
    """The empty cells of a run that swallowed a stop are done again.

    The first run of the trial v3 wrote 136 cells without a request when
    the arms swallowed the stop of the daily cap.  A resumed run that
    took them for done would skip them for ever, and the natural
    condition of the Cerebras model (80 cells) would never have been run.
    """
    progress = tmp_path / "progress.jsonl"
    records = [
        {
            "model": "m",
            "arm": "naive",
            "condition": "injected",
            "task": "t1",
            "requests": 0,
            "tokens": 0,
        },
        {
            "model": "m",
            "arm": "naive",
            "condition": "injected",
            "task": "t2",
            "requests": 3,
            "tokens": 100,
        },
    ]
    progress.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )

    cells = _read_progress(progress)

    assert [cell["task"] for cell in cells] == ["t2"]


def test_the_collector_drops_the_cells_without_a_request() -> None:
    """The collector and the resume apply the same rule.

    A cell without a request is not a measurement: the collector drops
    it, and the next run does it again.  If the two disagreed, a cell
    could be dropped from the evidence document and never be run.
    """
    from collect_cells import collect

    cells = [
        {"task": "t1", "requests": 0, "attempts": 0},
        {"task": "t2", "requests": 3, "attempts": 1},
    ]
    kept, dropped = collect(cells)
    assert [cell["task"] for cell in kept] == ["t2"]
    assert dropped == 1
