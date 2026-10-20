"""Tests for the simulated benchmark."""

from __future__ import annotations

import json
from pathlib import Path

from agentether.benchmark import BenchmarkConfig, run_benchmark


def test_the_same_seed_produces_the_same_result() -> None:
    first = run_benchmark(trials=5, seed=0)
    second = run_benchmark(trials=5, seed=0)
    assert first.to_dict() == second.to_dict()


def test_a_different_seed_produces_a_different_result() -> None:
    first = run_benchmark(trials=5, seed=0)
    second = run_benchmark(trials=5, seed=1)
    assert first.to_dict() != second.to_dict()


def test_the_result_is_labelled_as_simulated() -> None:
    result = run_benchmark(trials=2, seed=0)
    data = result.to_dict()
    assert data["simulated"] is True
    assert "SIMULATED" in data["warning"]


def test_the_result_contains_both_runners() -> None:
    result = run_benchmark(trials=3, seed=0)
    data = result.to_dict()
    assert set(data["runners"]) == {"naive", "guarded"}
    for runner in data["runners"].values():
        assert runner["tasks"] == 3
        assert "completion_rate" in runner
        assert "false_completion_rate" in runner
        assert "correct_completion_rate" in runner
        assert "mean_attempts_per_step" in runner
        assert "repeated_attempts" in runner
        assert "simulated_cost" in runner
        assert "mean_time_to_halt_seconds" in runner


def test_the_guarded_runner_never_reports_a_false_completion() -> None:
    # The whole point of the verifier: the guarded runner must not claim a
    # step is done when the artifact is missing.
    result = run_benchmark(trials=25, seed=0)
    assert result.guarded.false_completions == 0


def test_the_correct_completion_rate_is_the_headline_metric() -> None:
    # The naive runner completes more tasks, but 30% of them are not really
    # done: the correct completion rate tells the two apart.
    result = run_benchmark(trials=50, seed=0)
    naive = result.naive.to_dict()
    guarded = result.guarded.to_dict()
    assert naive["correct_completion_rate"] < naive["completion_rate"]
    assert guarded["correct_completion_rate"] == guarded["completion_rate"]
    assert guarded["correct_completion_rate"] > naive["correct_completion_rate"]


def test_the_repeated_attempts_metric_is_not_zero_by_construction() -> None:
    # The metric is computed from the answers, not from the loop detector, so
    # the naive runner also shows the repeated work it does.
    result = run_benchmark(trials=50, seed=0)
    assert result.naive.repeated_attempts > 0


def test_the_markdown_report_leads_with_the_correct_completion_rate() -> None:
    result = run_benchmark(trials=2, seed=0)
    markdown = result.to_markdown()
    assert "correct completion rate" in markdown
    assert markdown.index("correct completion rate") < markdown.index("reported completion rate")


def test_the_markdown_report_contains_the_numbers() -> None:
    result = run_benchmark(trials=2, seed=0)
    markdown = result.to_markdown()
    assert "Simulated benchmark (not a real-world measurement)" in markdown
    assert "| Metric | naive | guarded |" in markdown
    assert "false completion rate" in markdown


def test_the_configuration_is_echoed() -> None:
    result = run_benchmark(trials=2, seed=0, steps=2, max_attempts=3)
    data = result.to_dict()
    assert data["config"]["steps"] == 2
    assert data["config"]["max_attempts"] == 3
    assert data["config"]["seed"] == 0


def test_the_benchmark_can_write_a_json_file(tmp_path: Path) -> None:
    from agentether.cli import main

    target = tmp_path / "result.json"
    assert main(["benchmark", "--trials", "2", "--seed", "0", "--output", str(target)]) == 0
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["simulated"] is True


def test_the_default_configuration_is_documented() -> None:
    config = BenchmarkConfig()
    assert config.trials == 100
    assert config.seed == 0
    assert config.steps == 3
    assert config.max_attempts == 4
    assert sum(config.probabilities.values()) < 1.0
