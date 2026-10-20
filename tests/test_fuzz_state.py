"""Fuzz the state file parser.

Valid memory files are mutated at random and fed back into the parser.  The
only exception the parser may raise is :class:`StateCorruptionError`: it must
never crash with something else, and it must never *accept* a file whose
machine block it did not understand.

The run is bounded in time.  ``AGENTETHER_FUZZ_SECONDS`` sets the budget
(default 10 seconds, which is plenty for CI; the audit run used 60).
"""

from __future__ import annotations

import os
import random
import time
from pathlib import Path

import pytest

from agentether import StateCorruptionError, StateManager, Telemetry

#: The time budget of the fuzzing run in seconds.
SECONDS = float(os.environ.get("AGENTETHER_FUZZ_SECONDS", "10"))

#: How many mutations are tried per round.
ROUNDS = 200

_ALPHABET = b'{}[]":,\n\\/<>-_ abcXYZ0123\x00\xff'


async def build_valid_file(directory: Path) -> bytes:
    """Write a valid memory file and return its bytes."""
    manager = StateManager(directory)
    await manager.record_step(
        "research",
        Telemetry(
            step="research",
            status="completed",
            summary='a summary with <!-- a marker and a " quote',
            progress=100,
            next_step="write",
            artifacts=["notes.md"],
        ),
        "raw output",
    )
    return (directory / "PROJECT_MEMORY.md").read_bytes()


def mutate(data: bytes, rng: random.Random) -> bytes:
    """Mutate the bytes of a file in a random way."""
    if not data:
        return b"x"
    kind = rng.randrange(6)
    index = rng.randrange(len(data))
    if kind == 0:  # flip a byte
        return data[:index] + bytes([rng.randrange(256)]) + data[index + 1 :]
    if kind == 1:  # delete a chunk
        end = min(len(data), index + rng.randrange(1, 40))
        return data[:index] + data[end:]
    if kind == 2:  # insert noise
        noise = bytes(rng.choice(_ALPHABET) for _ in range(rng.randrange(1, 20)))
        return data[:index] + noise + data[index:]
    if kind == 3:  # truncate
        return data[:index]
    if kind == 4:  # duplicate a chunk
        end = min(len(data), index + rng.randrange(1, 60))
        return data[:index] + data[index:end] + data[index:]
    # replace a chunk with noise
    end = min(len(data), index + rng.randrange(1, 30))
    noise = bytes(rng.choice(_ALPHABET) for _ in range(rng.randrange(1, 30)))
    return data[:index] + noise + data[end:]


async def test_the_parser_survives_mutated_files(tmp_path: Path) -> None:
    """Mutated files may only lead to a StateCorruptionError.

    The test is **async** and not a loop of ``asyncio.run``: an event
    loop per round opens a socket pair on Windows, and a few hundred of
    them exhaust the buffer of the machine (the CI cell of Windows
    failed with ``WinError 10055``).
    """
    source = tmp_path / "source"
    source.mkdir()
    original = await build_valid_file(source)

    rng = random.Random(20261020)
    deadline = time.monotonic() + SECONDS
    rounds = 0
    while time.monotonic() < deadline and rounds < ROUNDS * 20:
        rounds += 1
        data = mutate(original, rng)
        target = tmp_path / f"case{rounds % 4}"
        target.mkdir(exist_ok=True)
        (target / "PROJECT_MEMORY.md").write_bytes(data)
        manager = StateManager(target)
        try:
            state = await manager.load()
        except StateCorruptionError:
            continue
        except Exception as exc:
            raise AssertionError(
                f"the parser raised {type(exc).__name__} for a mutated file: {exc}"
            ) from exc
        # If it parsed, the machine block must be a state we understand.
        assert isinstance(state, dict)
        assert state.get("schema_version") in (1, 2)
    assert rounds > 0, "the fuzzer did not run"


async def test_a_file_that_is_not_utf8_is_a_corruption_not_a_crash(tmp_path: Path) -> None:
    """A file edited with another encoding must not raise UnicodeDecodeError."""
    (tmp_path / "PROJECT_MEMORY.md").write_bytes(b"# Project Memory\n\xff\xfe not utf-8\n")
    manager = StateManager(tmp_path)
    with pytest.raises(StateCorruptionError) as excinfo:
        await manager.load()
    assert "UTF-8" in str(excinfo.value)
    assert "doctor" in str(excinfo.value)
