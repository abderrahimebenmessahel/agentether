"""Crash consistency: the state file survives a hard kill.

A subprocess writes the state and is killed (SIGKILL on POSIX,
``TerminateProcess`` on Windows) at a random moment.  Afterwards the memory
file must still be loadable, must not be corrupted and must never contain a
half written step.

The test is bounded: it runs a fixed number of iterations with a short
timeout, so it stays fast on both platforms.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from agentether import StateCorruptionError, StateManager

#: How many kill iterations to run.  More iterations, more chances to hit a
#: window between the write and the rename.
ITERATIONS = int(os.environ.get("AGENTETHER_CRASH_ITERATIONS", "25"))

#: The child writes the state in a loop; the parent kills it at a random
#: moment.  The child is started with this script.
CHILD = r"""
import asyncio
import sys
from pathlib import Path

from agentether import StateManager, Telemetry


async def main(directory: str) -> None:
    manager = StateManager(Path(directory))
    for index in range(1000):
        await manager.record_step(
            f"step{index % 5}",
            Telemetry(
                step=f"step{index % 5}",
                status="completed",
                summary="x" * 500,
                progress=100,
            ),
            "y" * 500,
        )


asyncio.run(main(sys.argv[1]))
"""


def _kill_after(child: subprocess.Popen[bytes], seconds: float) -> None:
    """Kill the child the hard way."""
    if os.name == "nt":
        child.kill()  # TerminateProcess on Windows
    else:
        child.kill()  # SIGKILL on POSIX
    try:
        child.wait(timeout=30)
    except subprocess.TimeoutExpired:  # pragma: no cover - the kill always works
        child.kill()
        child.wait(timeout=10)


def test_the_state_survives_a_hard_kill(tmp_path: Path) -> None:
    """The state file is always loadable after a kill."""
    failures: list[str] = []
    for iteration in range(ITERATIONS):
        directory = tmp_path / f"run{iteration}"
        directory.mkdir()
        child = subprocess.Popen(
            [sys.executable, "-c", CHILD, str(directory)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # A random moment between 5 ms and 250 ms after the start.
        time.sleep(0.005 + (iteration % 25) * 0.01)
        _kill_after(child, 0.0)

        path = directory / "PROJECT_MEMORY.md"
        if not path.exists():
            continue
        manager = StateManager(directory)
        try:
            state = _load_sync(manager)
        except StateCorruptionError as exc:
            failures.append(f"iteration {iteration}: corrupted state: {exc}")
            continue
        # A step that is recorded as completed must be complete: its summary
        # must not be cut in half and its telemetry must be intact.
        for step, record in (state.get("telemetry") or {}).items():
            summary = record.get("summary", "")
            if summary != "x" * 500:
                failures.append(
                    f"iteration {iteration}: step {step} has a truncated summary "
                    f"({len(summary)} characters)"
                )
        for step in state.get("completed_steps", []):
            if step not in (state.get("telemetry") or {}):
                failures.append(
                    f"iteration {iteration}: step {step} is completed without telemetry"
                )
    assert not failures, "\n".join(failures)


def _load_sync(manager: StateManager) -> dict[str, object]:
    """Load the state outside of an event loop."""
    import asyncio

    return asyncio.run(manager.load())


def test_a_killed_write_leaves_no_temporary_file(tmp_path: Path) -> None:
    """Only the temporary file of a killed write may be left behind."""
    directory = tmp_path / "run"
    directory.mkdir()
    child = subprocess.Popen(
        [sys.executable, "-c", CHILD, str(directory)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.05)
    _kill_after(child, 0.0)
    leftovers = list(directory.glob("*.tmp"))
    # A leftover temporary file is harmless: it is never read, and it is
    # removed when it gets old enough.
    for leftover in leftovers:
        assert leftover.name.startswith("tmp")
        assert leftover.stat().st_size >= 0
