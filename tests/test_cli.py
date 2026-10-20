"""Tests for the ``contextguard`` command line interface."""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from context_guard import AutoOrchestrator, StateManager, Telemetry
from context_guard.cli import main


def read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    """Parse the JSON the CLI printed."""
    out = capsys.readouterr().out
    parsed: dict[str, Any] = json.loads(out)
    return parsed


def build_project(memory_dir: Path) -> None:
    """Create a small project with one completed step."""
    asyncio.run(_build_project(memory_dir))


async def _build_project(memory_dir: Path) -> None:
    orch = AutoOrchestrator(
        roadmap=["research", "write"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
    )

    @orch.guard_step("research")
    async def research(ctx):
        return json.dumps(
            {
                "step": "research",
                "status": "completed",
                "summary": "found three sources",
                "progress": 100,
                "next_step": "write",
                "artifacts": [],
            }
        )

    await research()


def build_project_with_artifact(memory_dir: Path, work_dir: Path) -> None:
    """Create a project whose step claims an artifact in the work directory."""
    asyncio.run(_build_project_with_artifact(memory_dir, work_dir))


async def _build_project_with_artifact(memory_dir: Path, work_dir: Path) -> None:
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
        workdir=str(work_dir),
    )

    @orch.guard_step("research")
    async def research(ctx):
        return json.dumps(
            {
                "step": "research",
                "status": "completed",
                "summary": "done",
                "progress": 100,
                "next_step": None,
                "artifacts": ["result.md"],
            }
        )

    await research()


def test_status_reports_the_progress(memory_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["status", str(memory_dir), "--json"])
    payload = read_json(capsys)
    assert code == 0
    assert payload["ok"] is True
    assert payload["progress"] == {"done": 0, "total": 0}


def test_status_after_a_step(memory_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    build_project(memory_dir)
    code = main(["status", str(memory_dir), "--json"])
    payload = read_json(capsys)
    assert code == 0
    assert payload["completed_steps"] == ["research"]
    assert payload["progress"] == {"done": 1, "total": 2}
    assert payload["breaker"]["open"] is False


def test_reset_breaker(memory_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    async def open_the_breaker() -> None:
        manager = StateManager(memory_dir)
        await manager.set_breaker(True, "timeout", step="research", attempts=3)

    asyncio.run(open_the_breaker())

    code = main(["reset-breaker", str(memory_dir), "--json"])
    payload = read_json(capsys)
    assert code == 0
    assert payload["ok"] is True

    async def read_the_state() -> dict[str, Any]:
        manager = StateManager(memory_dir)
        return await manager.load()

    state = asyncio.run(read_the_state())
    assert state["breaker"]["open"] is False


def test_doctor_finds_a_healthy_project(
    memory_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    build_project(memory_dir)
    code = main(["doctor", str(memory_dir), "--json"])
    payload = read_json(capsys)
    assert code == 0
    assert payload["ok"] is True
    assert payload["problems"] == []


def test_doctor_reports_a_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["doctor", str(tmp_path / "nope"), "--json"])
    payload = read_json(capsys)
    assert code == 1
    assert payload["ok"] is False
    assert any("does not exist" in problem for problem in payload["problems"])


def test_doctor_reports_broken_json(memory_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (memory_dir / "PROJECT_MEMORY.md").write_text(
        "# Project Memory\n\n<!-- contextguard:state -->\n```json\n{not json}\n```\n",
        encoding="utf-8",
    )
    code = main(["doctor", str(memory_dir), "--json"])
    payload = read_json(capsys)
    assert code == 1
    assert payload["ok"] is False
    assert any("malformed" in problem for problem in payload["problems"])


def test_doctor_reports_a_missing_human_end_marker(
    memory_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (memory_dir / "PROJECT_MEMORY.md").write_text(
        "# Project Memory\n\n<!-- contextguard:human:start -->\ntext\n"
        "<!-- contextguard:state -->\n```json\n{}\n```\n",
        encoding="utf-8",
    )
    code = main(["doctor", str(memory_dir), "--json"])
    payload = read_json(capsys)
    assert code == 1
    assert any("end marker" in problem for problem in payload["problems"])


def test_doctor_reports_stale_temp_files(
    memory_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    build_project(memory_dir)
    stale = memory_dir / "old.tmp"
    stale.write_text("leftover", encoding="utf-8")
    old = time.time() - 7200
    os.utime(stale, (old, old))

    code = main(["doctor", str(memory_dir), "--json"])
    payload = read_json(capsys)
    assert code == 0
    assert any("stale .tmp" in note for note in payload["notes"])


def test_verify_checks_the_recorded_artifacts(
    memory_dir: Path, work_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    build_project_with_artifact(memory_dir, work_dir)
    (work_dir / "result.md").write_text("done", encoding="utf-8")

    code = main(["verify", str(memory_dir), "--workdir", str(work_dir), "--json"])
    payload = read_json(capsys)
    assert code == 0
    assert payload["ok"] is True


def test_verify_reports_a_missing_artifact(
    memory_dir: Path, work_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    build_project_with_artifact(memory_dir, work_dir)
    code = main(["verify", str(memory_dir), "--workdir", str(work_dir), "--json"])
    payload = read_json(capsys)
    assert code == 1
    assert payload["ok"] is False
    assert any("missing artifacts" in problem for problem in payload["problems"])


def test_benchmark_command(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["benchmark", "--trials", "3", "--seed", "0", "--json"])
    payload = read_json(capsys)
    assert code == 0
    assert payload["simulated"] is True
    assert payload["config"]["trials"] == 3
    assert "naive" in payload["runners"]
    assert "guarded" in payload["runners"]


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--version"])
    out = capsys.readouterr().out.strip()
    assert code == 0
    assert out == "0.2.0"


def test_no_command_prints_the_help(capsys: pytest.CaptureFixture[str]) -> None:
    code = main([])
    assert code == 2
    assert "usage" in capsys.readouterr().out.lower()


def test_status_reports_a_corrupted_project(
    memory_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (memory_dir / "PROJECT_MEMORY.md").write_text("no state here", encoding="utf-8")
    code = main(["status", str(memory_dir), "--json"])
    payload = read_json(capsys)
    assert code == 1
    assert payload["ok"] is False


def test_telemetry_is_not_lost_by_the_cli(memory_dir: Path) -> None:
    build_project(memory_dir)

    async def read_the_state() -> dict[str, Any]:
        manager = StateManager(memory_dir)
        return await manager.load()

    state = asyncio.run(read_the_state())
    assert state["telemetry"]["research"]["summary"] == "found three sources"
    assert isinstance(state["telemetry"]["research"], dict)
    assert Telemetry.from_dict(state["telemetry"]["research"]).status == "completed"


# ----------------------------------------------------------------------
# the human readable output
# ----------------------------------------------------------------------
def test_status_prints_a_report(memory_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    build_project(memory_dir)
    code = main(["status", str(memory_dir)])
    out = capsys.readouterr().out
    assert code == 0
    assert "roadmap:" in out
    assert "[x] research" in out
    assert "breaker: closed" in out


def test_doctor_prints_a_report(memory_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    build_project(memory_dir)
    code = main(["doctor", str(memory_dir)])
    out = capsys.readouterr().out
    assert code == 0
    assert "no problems found" in out


def test_doctor_prints_the_problems(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["doctor", str(tmp_path / "missing")])
    out = capsys.readouterr().out
    assert code == 1
    assert "problem:" in out


def test_verify_prints_a_report(
    memory_dir: Path, work_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    build_project_with_artifact(memory_dir, work_dir)
    (work_dir / "result.md").write_text("done", encoding="utf-8")
    code = main(["verify", str(memory_dir), "--workdir", str(work_dir)])
    out = capsys.readouterr().out
    assert code == 0
    assert "research: ok" in out
    assert "all recorded artifacts exist" in out


def test_reset_breaker_prints_a_report(
    memory_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["reset-breaker", str(memory_dir)])
    assert code == 0
    assert "circuit breaker closed" in capsys.readouterr().out


def test_benchmark_prints_markdown(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["benchmark", "--trials", "2", "--seed", "0"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Simulated benchmark" in out
    assert "| Metric | naive | guarded |" in out
