"""Shared fixtures.

No test touches the network and no test uses a real LLM: the "agent" is a
plain Python function that returns a canned answer.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest

from context_guard import StepContext


def telemetry_answer(
    step: str,
    status: str = "completed",
    summary: str = "did the work",
    progress: float | None = None,
    next_step: str | None = None,
    artifacts: list[str] | None = None,
    prefix: str = "",
) -> str:
    """Build a raw agent answer that ends with a valid telemetry object."""
    payload: dict[str, Any] = {
        "step": step,
        "status": status,
        "summary": summary,
        "progress": progress,
        "next_step": next_step,
        "artifacts": artifacts or [],
    }
    body = json.dumps(payload)
    return f"{prefix}Here is my report.\n{body}" if prefix else body


@pytest.fixture()
def memory_dir(tmp_path: Path) -> Path:
    """An empty directory for the project memory."""
    target = tmp_path / "memory"
    target.mkdir(parents=True, exist_ok=True)
    return target


@pytest.fixture()
def work_dir(tmp_path: Path) -> Path:
    """An empty working directory for the agent."""
    target = tmp_path / "work"
    target.mkdir(parents=True, exist_ok=True)
    return target


@pytest.fixture()
def recording_sleep() -> tuple[list[float], Callable[[float], Awaitable[None]]]:
    """A sleep replacement that records the requested delays."""
    delays: list[float] = []

    async def _sleep(delay: float) -> None:
        delays.append(delay)

    return delays, _sleep


class FakeClock:
    """A monotonic clock that only moves when a test says so."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        """Move the clock forward."""
        self.now += seconds


@pytest.fixture()
def fake_clock() -> FakeClock:
    """A controllable monotonic clock."""
    return FakeClock()


@pytest.fixture()
def context_factory() -> Callable[..., StepContext]:
    """Build a :class:`StepContext` without running an orchestrator."""

    def _make(**overrides: Any) -> StepContext:
        defaults: dict[str, Any] = {
            "step_name": "research",
            "step_index": 0,
            "attempt": 1,
            "max_attempts": 3,
            "memory": "# Project Memory\n",
            "last_error": None,
            "roadmap": ("research", "write"),
        }
        defaults.update(overrides)
        return StepContext(**defaults)

    return _make
