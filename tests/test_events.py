"""Tests for the event hooks and the event log."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agentether.events import EVENT_NAMES, EventBus, EventLog


async def test_event_bus_calls_the_callbacks() -> None:
    bus = EventBus()
    seen: list[dict[str, Any]] = []
    bus.on("step_completed", seen.append)
    await bus.emit("step_completed", {"step": "research"})
    assert seen == [{"step": "research"}]


async def test_event_bus_supports_async_callbacks() -> None:
    bus = EventBus()
    seen: list[dict[str, Any]] = []

    async def callback(payload: dict[str, Any]) -> None:
        seen.append(payload)

    bus.on("attempt_failed", callback)
    await bus.emit("attempt_failed", {"step": "research"})
    assert len(seen) == 1


async def test_a_throwing_callback_does_not_break_the_run() -> None:
    bus = EventBus()
    seen: list[dict[str, Any]] = []

    def broken(payload: dict[str, Any]) -> None:
        raise RuntimeError("callback is broken")

    bus.on("attempt_failed", broken)
    bus.on("attempt_failed", seen.append)
    await bus.emit("attempt_failed", {"step": "research"})
    assert len(seen) == 1


def test_unknown_events_are_rejected() -> None:
    bus = EventBus()
    with pytest.raises(ValueError):
        bus.on("not_an_event", lambda payload: None)


async def test_disabled_bus_does_nothing() -> None:
    bus = EventBus(enabled=False)
    seen: list[dict[str, Any]] = []
    bus.on("step_completed", seen.append)
    await bus.emit("step_completed")
    assert seen == []


def test_event_log_appends_json_lines(tmp_path: Path) -> None:
    log = EventLog(tmp_path)
    log.append("attempt_started", step="research", attempt=1)
    log.append("step_completed", step="research")
    lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["seq"] == 1
    assert first["event"] == "attempt_started"
    assert first["step"] == "research"
    assert first["ts"].endswith("Z")
    assert json.loads(lines[1])["seq"] == 2


def test_event_log_continues_the_sequence(tmp_path: Path) -> None:
    EventLog(tmp_path).append("attempt_started", step="a")
    second = EventLog(tmp_path)
    record = second.append("attempt_started", step="b")
    assert record["seq"] == 2


def test_event_log_rotates_and_keeps_one_previous_file(tmp_path: Path) -> None:
    log = EventLog(tmp_path, max_bytes=400)
    for index in range(20):
        log.append("attempt_started", step="research", attempt=index, filler="x" * 40)
    assert (tmp_path / "events.jsonl.1").exists()
    # The file never grows much past the limit: it is rotated before a line
    # that would push it over.
    assert (tmp_path / "events.jsonl").stat().st_size < 400 + 200


def test_event_log_can_be_disabled(tmp_path: Path) -> None:
    log = EventLog(tmp_path, enabled=False)
    record = log.append("attempt_started", step="research")
    assert record["seq"] == 1
    assert not (tmp_path / "events.jsonl").exists()


def test_every_documented_event_name_is_known() -> None:
    assert set(EVENT_NAMES) == {
        "attempt_started",
        "attempt_failed",
        "step_completed",
        "breaker_opened",
        "loop_detected",
        "budget_exceeded",
        "verification_failed",
    }
