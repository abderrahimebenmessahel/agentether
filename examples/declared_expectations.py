"""Declaring what a step must produce.

The agent says ``status: "completed"``.  That is a claim, and a claim can
be backed by a file that does not exist.  An **expectation** is the
contract of the step: the files it must produce and what those files must
look like.  The library checks the declaration after every attempt, and the
step cannot complete while one of them is unmet.

The example below lies twice: the first attempt claims to be done without
writing anything, the second one writes a file that is cut in the middle.
The declaration catches both, and the step only completes on the third
attempt, with the real files.

    python examples/declared_expectations.py
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from agentether import (
    AutoOrchestrator,
    Expectation,
    StepContext,
    VerificationFailedError,
)


def telemetry(step: str, **extra: object) -> str:
    """A telemetry answer for the given step."""
    payload: dict[str, object] = {
        "step": step,
        "status": "completed",
        "summary": "done",
        "progress": 100,
        "next_step": None,
        "artifacts": [],
    }
    payload.update(extra)
    return json.dumps(payload)


async def main() -> None:
    root = Path(tempfile.mkdtemp())
    memory_dir = root / "memory"
    work_dir = root / "work"
    memory_dir.mkdir()
    work_dir.mkdir()

    orch = AutoOrchestrator(
        roadmap=["report"],
        memory_dir=str(memory_dir),
        timeout_seconds=30,
        max_retries=3,
        workdir=str(work_dir),
    )

    attempt = 0

    @orch.guard_step(
        "report",
        expects=[
            "report.md",
            Expectation("data.json", json_keys=("a", "b")),
        ],
    )
    async def report(ctx: StepContext) -> str:
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            # The claim is backed by nothing at all.
            return telemetry("report", artifacts=["report.md"])
        if attempt == 2:
            # The file exists, but it is cut in the middle: the existence
            # check passes, the declaration does not.
            (work_dir / "report.md").write_text("# Report\n\nThe number is", encoding="utf-8")
            (work_dir / "data.json").write_text('{"a": 1,', encoding="utf-8")
            return telemetry("report", artifacts=["report.md", "data.json"])
        (work_dir / "report.md").write_text("# Report\n\nThe number is 15.\n", encoding="utf-8")
        (work_dir / "data.json").write_text('{"a": 15, "b": "harbour"}', encoding="utf-8")
        return telemetry("report", artifacts=["report.md", "data.json"])

    result = await report()
    print(f"the step completed after {result.attempts} attempts")
    print(f"the files are there: {sorted(p.name for p in work_dir.iterdir())}")

    # The same declaration, but the agent never writes the file.
    orchestrator = AutoOrchestrator(
        roadmap=["report"],
        memory_dir=str(memory_dir / "second"),
        timeout_seconds=30,
        max_retries=1,
        workdir=str(work_dir),
    )

    @orchestrator.guard_step("report", expects=["missing.md"])
    async def lying(ctx: StepContext) -> str:
        return telemetry("report")

    try:
        await lying()
    except Exception as exc:
        cause = exc.__cause__
        if isinstance(cause, VerificationFailedError):
            print(f"the declaration caught the lie: {cause.reason}")
            print(f"the missing files are named: {cause.evidence['missing']}")


if __name__ == "__main__":
    asyncio.run(main())
