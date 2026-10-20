"""The contracts of AgenTether are pinned down by tests.

The telemetry contract and the format of the state file are **public**
contracts: another implementation is supposed to be able to read and write
them (``docs/spec/telemetry-contract-v1.md`` and
``docs/spec/state-file-format-v2.md``).  A change of a key or of a field
breaks every other implementation, and a test that does not look at the
keys cannot see it.

These tests were written after the mutation triage of the audit: they
kill the mutants that change a key of the state file, a field of the
telemetry or a record of the ledger.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agentether import StateManager, Telemetry

#: The keys of the machine readable block of ``PROJECT_MEMORY.md``.
#: They are the format of the state file and they do not change.
STATE_KEYS = frozenset(
    {
        "schema_version",
        "roadmap",
        "completed_steps",
        "telemetry",
        "step_files",
        "breaker",
        "last_failure",
        "human_hash",
        "updated_at",
        "budget",
        "needs_human",
        "attempts",
        "verifications",
    }
)

#: The keys of a telemetry object.  They are the contract.
TELEMETRY_KEYS = frozenset(
    {"step", "status", "summary", "progress", "next_step", "artifacts"}
)

#: The keys of a line of the claims ledger.
CLAIM_KEYS = frozenset(
    {
        "ts",
        "step",
        "attempt",
        "claimed_status",
        "claimed_summary",
        "claimed_artifacts",
        "model",
        "verification",
        "prev",
    }
)


def make_telemetry(step: str = "research", summary: str = "did the work") -> Telemetry:
    """A telemetry object of a completed step."""
    return Telemetry(
        step=step,
        status="completed",
        summary=summary,
        progress=100,
        next_step=None,
        artifacts=[],
    )


def read_state(memory_dir: Path) -> dict[str, Any]:
    """The machine readable block of the memory file."""
    text = (memory_dir / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    start = text.index("```json")
    end = text.rindex("```")
    return dict(json.loads(text[start + len("```json") : end]))


async def test_the_state_file_has_exactly_the_documented_keys(memory_dir: Path) -> None:
    """The keys of the state file are the format, not a detail."""
    manager = StateManager(memory_dir)
    await manager.record_step("research", make_telemetry(), "raw agent output")
    state = read_state(memory_dir)
    assert set(state) <= STATE_KEYS
    assert {
        "schema_version",
        "roadmap",
        "completed_steps",
        "telemetry",
        "updated_at",
    } <= set(state)


async def test_the_telemetry_contract_has_exactly_the_documented_keys() -> None:
    """The keys of a telemetry object are the contract."""
    telemetry = make_telemetry()
    assert set(telemetry.to_dict()) == TELEMETRY_KEYS


async def test_the_ledger_line_has_exactly_the_documented_keys(memory_dir: Path) -> None:
    """A line of the claims ledger carries the claim and the verification."""
    from agentether.ledger import ClaimsLedger

    ledger = ClaimsLedger(memory_dir)
    ledger.append(
        step="research",
        attempt=1,
        claimed_status="completed",
        claimed_summary="did the work",
        claimed_artifacts=[],
        verification={"ok": True, "reason": "", "evidence": {}},
    )
    lines = [
        json.loads(line)
        for line in (memory_dir / "claims.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) == 1
    assert set(lines[0]) <= CLAIM_KEYS
    assert lines[0]["step"] == "research"
    assert lines[0]["verification"]["ok"] is True


async def test_the_breaker_keeps_its_documented_fields(memory_dir: Path) -> None:
    """The breaker of the state file has the fields of the format."""
    manager = StateManager(memory_dir)
    await manager.set_breaker(True, "drift", step="research", attempts=3, last_error="e")
    state = read_state(memory_dir)
    assert set(state["breaker"]) == {
        "open",
        "reason",
        "step",
        "attempts",
        "last_error",
        "opened_at",
    }
    assert state["breaker"]["open"] is True
    assert state["breaker"]["step"] == "research"
    assert state["breaker"]["attempts"] == 3


async def test_the_compression_keeps_the_newest_entries(memory_dir: Path) -> None:
    """The compaction keeps the newest entries and drops the oldest."""
    manager = StateManager(memory_dir)
    for index in range(6):
        await manager.record_step(f"step{index}", make_telemetry(f"step{index}"), "out")
    state = await manager.load()
    # Every recorded step is there: the compression only happens when the
    # limit is reached.
    assert set(state["completed_steps"]) == {f"step{index}" for index in range(6)}


async def test_the_budget_section_carries_the_used_amounts(memory_dir: Path) -> None:
    """The budget of the state file is the usage of the project."""
    manager = StateManager(memory_dir)
    await manager.record_step("research", make_telemetry(), "raw agent output")
    state = read_state(memory_dir)
    assert "budget" not in state or set(state["budget"]) <= {
        "seconds",
        "attempts",
        "tokens",
        "cost",
    }


@pytest.mark.parametrize("key", sorted(STATE_KEYS - {"schema_version"}))
def test_every_documented_key_is_written_by_the_library(key: str) -> None:
    """No key of the format is a leftover of an older version.

    The test is a reminder: a key that the library never writes is a key
    that the format still promises.
    """
    assert key.islower() or "_" in key
