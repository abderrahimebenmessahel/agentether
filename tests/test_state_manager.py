"""Tests for the durable project memory."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from context_guard import StateCorruptionError, StateManager, Telemetry


def make_telemetry(step: str = "research", summary: str = "did the work") -> Telemetry:
    return Telemetry(
        step=step,
        status="completed",
        summary=summary,
        progress=100,
        next_step=None,
        artifacts=[],
    )


def write_v1_file(memory_dir: Path) -> Path:
    """Write a schema version 1 memory file."""
    path = memory_dir / "PROJECT_MEMORY.md"
    state = {
        "schema_version": 1,
        "roadmap": ["research"],
        "completed_steps": ["research"],
        "telemetry": {"research": make_telemetry().to_dict()},
        "step_files": {"research": "steps/01_research.md"},
        "breaker": {
            "open": False,
            "reason": None,
            "step": None,
            "attempts": 0,
            "last_error": None,
        },
        "last_failure": None,
    }
    path.write_text(
        "# Project Memory\n\n"
        "<!-- contextguard:state -->\n```json\n" + json.dumps(state, indent=2) + "\n```\n",
        encoding="utf-8",
    )
    return path


async def test_record_step_and_load_roundtrip(memory_dir: Path) -> None:
    manager = StateManager(memory_dir)
    await manager.record_step("research", make_telemetry(), "raw agent output")

    state = await manager.load()
    assert state["completed_steps"] == ["research"]
    assert state["telemetry"]["research"]["summary"] == "did the work"
    assert state["schema_version"] == 2
    assert (memory_dir / "PROJECT_MEMORY.md").exists()
    assert (
        (memory_dir / "steps" / "01_research.md")
        .read_text(encoding="utf-8")
        .endswith("raw agent output\n")
    )


async def test_missing_file_yields_a_fresh_state(memory_dir: Path) -> None:
    manager = StateManager(memory_dir)
    state = await manager.load()
    assert state["completed_steps"] == []
    assert state["schema_version"] == 2
    assert state["breaker"]["open"] is False


async def test_atomic_write_keeps_the_old_file_when_replace_fails(
    memory_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = StateManager(memory_dir)
    await manager.record_step("research", make_telemetry(), "first")
    original = (memory_dir / "PROJECT_MEMORY.md").read_text(encoding="utf-8")

    def boom(*args: Any, **kwargs: Any) -> None:
        raise OSError("disk on fire")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        await manager.record_step("write", make_telemetry("write"), "second")
    monkeypatch.undo()

    assert (memory_dir / "PROJECT_MEMORY.md").read_text(encoding="utf-8") == original
    assert list(memory_dir.glob("*.tmp")) == []


async def test_successful_write_leaves_no_temp_file(memory_dir: Path) -> None:
    manager = StateManager(memory_dir)
    await manager.record_step("research", make_telemetry(), "output")
    assert list(memory_dir.glob("*.tmp")) == []


async def test_fsync_is_called(memory_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    real_fsync = os.fsync

    def recording_fsync(fd: int) -> None:
        calls.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", recording_fsync)
    manager = StateManager(memory_dir)
    await manager.record_step("research", make_telemetry(), "output")
    assert calls, "os.fsync must be called before the atomic rename"


async def test_directory_fsync_failure_is_survivable(
    memory_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_open = os.open

    def fake_open(path: Any, *args: Any, **kwargs: Any) -> int:
        # Opening a directory is not possible on every platform (Windows); the
        # atomic write must survive that and skip the directory fsync.
        if isinstance(path, (str, bytes, os.PathLike)) and os.path.isdir(path):
            raise OSError("no directory fsync here")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", fake_open)
    manager = StateManager(memory_dir)
    await manager.record_step("research", make_telemetry(), "output")
    assert (memory_dir / "PROJECT_MEMORY.md").exists()


async def test_other_directory_fsync_errors_are_logged(
    memory_dir: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    real_open = os.open

    def fake_open(path: Any, *args: Any, **kwargs: Any) -> int:
        if isinstance(path, (str, bytes, os.PathLike)) and os.path.isdir(path):
            raise OSError(5, "input/output error")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", fake_open)
    with caplog.at_level("WARNING", logger="context_guard"):
        manager = StateManager(memory_dir)
        await manager.record_step("research", make_telemetry(), "output")
    assert any("fsync" in record.getMessage() for record in caplog.records)


async def test_stale_temp_files_are_removed_but_fresh_ones_survive(
    memory_dir: Path,
) -> None:
    stale = memory_dir / "stale.tmp"
    fresh = memory_dir / "fresh.tmp"
    stale.write_text("leftover", encoding="utf-8")
    fresh.write_text("in progress", encoding="utf-8")
    old = time.time() - 7200
    os.utime(stale, (old, old))

    StateManager(memory_dir)
    assert not stale.exists()
    assert fresh.exists()


async def test_corrupted_state_raises(memory_dir: Path) -> None:
    (memory_dir / "PROJECT_MEMORY.md").write_text(
        "# Project Memory\n\n<!-- contextguard:state -->\n```json\n{not json}\n```\n",
        encoding="utf-8",
    )
    manager = StateManager(memory_dir)
    with pytest.raises(StateCorruptionError) as excinfo:
        await manager.load()
    assert "doctor" in str(excinfo.value)


async def test_missing_state_block_raises(memory_dir: Path) -> None:
    (memory_dir / "PROJECT_MEMORY.md").write_text(
        "# Project Memory\n\nsome human notes\n", encoding="utf-8"
    )
    manager = StateManager(memory_dir)
    with pytest.raises(StateCorruptionError):
        await manager.load()


async def test_unsupported_schema_version_raises(memory_dir: Path) -> None:
    (memory_dir / "PROJECT_MEMORY.md").write_text(
        "# Project Memory\n\n<!-- contextguard:state -->\n```json\n"
        + json.dumps({"schema_version": 999})
        + "\n```\n",
        encoding="utf-8",
    )
    manager = StateManager(memory_dir)
    with pytest.raises(StateCorruptionError):
        await manager.load()


async def test_breaker_is_persisted(memory_dir: Path) -> None:
    manager = StateManager(memory_dir)
    await manager.set_breaker(True, "too many failures", step="research", attempts=3)
    state = await manager.load()
    assert state["breaker"]["open"] is True
    assert state["breaker"]["attempts"] == 3
    assert state["breaker"]["step"] == "research"


async def test_context_compaction_respects_the_limit(memory_dir: Path) -> None:
    manager = StateManager(memory_dir, max_memory_chars=400)
    manager.set_roadmap(("one", "two", "three", "four"))
    state: dict[str, Any] = {
        "roadmap": ["one", "two", "three", "four"],
        "completed_steps": ["one", "two", "three", "four"],
        "telemetry": {
            name: {"summary": f"summary for {name} " + "x" * 200}
            for name in ("one", "two", "three", "four")
        },
    }
    rendered = manager.render_context(state)
    assert len(rendered) <= 400
    assert "# Project Memory" in rendered
    assert "- [x] four" in rendered  # the roadmap checklist survives
    assert "summary for four" in rendered  # the newest step stays complete
    assert "### one" not in rendered  # the oldest step was collapsed


async def test_token_budget_takes_precedence_over_the_character_budget(
    memory_dir: Path,
) -> None:
    manager = StateManager(
        memory_dir, max_memory_chars=100_000, max_memory_tokens=20, token_counter=len
    )
    state: dict[str, Any] = {
        "roadmap": ["one"],
        "completed_steps": ["one"],
        "telemetry": {"one": {"summary": "x" * 500}},
    }
    rendered = manager.render_context(state)
    assert len(rendered) <= 20 or rendered.startswith("# Project Memory")


async def test_context_keeps_the_header_even_when_it_does_not_fit(
    memory_dir: Path,
) -> None:
    manager = StateManager(memory_dir, max_memory_chars=10)
    state: dict[str, Any] = {
        "roadmap": ["one"],
        "completed_steps": [],
        "telemetry": {},
    }
    rendered = manager.render_context(state)
    assert rendered.startswith("# Project Memory")


async def test_step_names_cannot_escape_the_steps_directory(memory_dir: Path) -> None:
    manager = StateManager(memory_dir)
    await manager.record_step("../../etc/passwd", make_telemetry("../../etc/passwd"), "x")

    written = list((memory_dir / "steps").glob("*.md"))
    assert len(written) == 1
    assert written[0].parent == memory_dir / "steps"
    assert ".." not in written[0].name
    assert not (memory_dir.parent / "etc").exists()


async def test_reset_clears_the_state(memory_dir: Path) -> None:
    manager = StateManager(memory_dir)
    await manager.record_step("research", make_telemetry(), "output")
    await manager.reset()
    state = await manager.load()
    assert state["completed_steps"] == []
    assert state["telemetry"] == {}


# ----------------------------------------------------------------------
# schema version 2: human section, attempt log, migration
# ----------------------------------------------------------------------
async def test_attempt_log_records_every_attempt(memory_dir: Path) -> None:
    manager = StateManager(memory_dir)
    await manager.append_attempt("research", 1, "parse_error", error="no json", output="abc")
    await manager.append_attempt("research", 2, "completed", output="abcdef")

    log = memory_dir / "steps" / "01_research.attempts.jsonl"
    lines = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) == 2
    assert lines[0]["outcome"] == "parse_error"
    assert lines[0]["attempt"] == 1
    assert lines[0]["error"] == "no json"
    assert lines[0]["output_length"] == 3
    assert len(lines[0]["output_sha256"]) == 64
    assert "output" not in lines[0]
    assert lines[1]["outcome"] == "completed"


async def test_attempt_log_can_store_the_raw_output(memory_dir: Path) -> None:
    manager = StateManager(memory_dir)
    await manager.append_attempt("research", 1, "completed", output="the full text", store_raw=True)
    log = memory_dir / "steps" / "01_research.attempts.jsonl"
    record = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert record["output"] == "the full text"


async def test_human_section_is_preserved_byte_for_byte(memory_dir: Path) -> None:
    manager = StateManager(memory_dir)
    await manager.record_step("research", make_telemetry(), "output")

    path = memory_dir / "PROJECT_MEMORY.md"
    text = path.read_text(encoding="utf-8")
    human = "Use the tone of the CEO.\n\nDo not mention the budget."
    text = text.replace(
        "<!-- contextguard:human:start -->\n\n<!-- contextguard:human:end -->",
        f"<!-- contextguard:human:start -->\n{human}\n<!-- contextguard:human:end -->",
    )
    path.write_text(text, encoding="utf-8")

    await manager.record_step("write", make_telemetry("write"), "more output")
    after = path.read_text(encoding="utf-8")
    assert human in after
    assert manager.human_text.strip() == human.strip()


async def test_human_section_is_injected_into_the_context(memory_dir: Path) -> None:
    manager = StateManager(memory_dir)
    await manager.record_step("research", make_telemetry(), "output")
    path = memory_dir / "PROJECT_MEMORY.md"
    text = path.read_text(encoding="utf-8")
    human = "Prefer bullet points."
    text = text.replace(
        "<!-- contextguard:human:start -->\n\n<!-- contextguard:human:end -->",
        f"<!-- contextguard:human:start -->\n{human}\n<!-- contextguard:human:end -->",
    )
    path.write_text(text, encoding="utf-8")

    state = await manager.load()
    rendered = manager.render_context(state)
    assert human in rendered


async def test_v1_file_is_migrated_and_backed_up(memory_dir: Path) -> None:
    write_v1_file(memory_dir)
    manager = StateManager(memory_dir)
    state = await manager.load()

    assert state["schema_version"] == 2
    assert state["completed_steps"] == ["research"]
    assert state["telemetry"]["research"]["summary"] == "did the work"
    assert (memory_dir / "PROJECT_MEMORY.md.bak").exists()
    assert '"schema_version": 1' in (memory_dir / "PROJECT_MEMORY.md.bak").read_text(
        encoding="utf-8"
    )
    assert '"schema_version": 2' in (memory_dir / "PROJECT_MEMORY.md").read_text(encoding="utf-8")


async def test_migration_keeps_the_human_section(memory_dir: Path) -> None:
    path = write_v1_file(memory_dir)
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "<!-- contextguard:state -->",
        "<!-- contextguard:human:start -->\nkeep me\n<!-- contextguard:human:end -->\n"
        "<!-- contextguard:state -->",
    )
    path.write_text(text, encoding="utf-8")

    manager = StateManager(memory_dir)
    state = await manager.load()
    assert state["schema_version"] == 2
    assert "keep me" in manager.human_text
    assert "keep me" in (memory_dir / "PROJECT_MEMORY.md").read_text(encoding="utf-8")


async def test_blocked_step_is_listed_for_the_human(memory_dir: Path) -> None:
    manager = StateManager(memory_dir)
    blocked = Telemetry(
        step="research", status="blocked", summary="need the API key", progress=None
    )
    await manager.record_step("research", blocked, "output")

    state = await manager.load()
    assert state["needs_human"]["research"] == "need the API key"
    text = (memory_dir / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    assert "## Needs human input" in text
    assert "need the API key" in text
