"""Verifying what the agent claims.

The agent reports ``status: "completed"``.  That is a claim.  A *verifier*
checks the claim against reality: does the file exist, is the JSON valid, did
the command succeed?

The example below lies on the first attempt (it claims a file it never
wrote) and the verifier catches it, so the step is retried with a corrective
hint.

    python examples/verified_step.py
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from context_guard import (
    AutoOrchestrator,
    StepContext,
    VerificationFailedError,
    artifacts_exist,
    file_contains,
    json_file_valid,
)


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

    attempts = 0

    @orch.guard_step(
        "report",
        verify=[
            file_contains("report.md", r"## Findings"),
            json_file_valid("report.json", required_keys=["findings"]),
            artifacts_exist(),
        ],
    )
    async def report(ctx: StepContext) -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            # The agent claims success but writes nothing at all.
            return json.dumps(
                {
                    "step": "report",
                    "status": "completed",
                    "summary": "wrote the report",
                    "progress": 100,
                    "next_step": None,
                    "artifacts": ["report.md", "report.json"],
                }
            )
        # This time it really writes the files.
        (work_dir / "report.md").write_text("## Findings\nthree sources\n", encoding="utf-8")
        (work_dir / "report.json").write_text(json.dumps({"findings": 3}), encoding="utf-8")
        return json.dumps(
            {
                "step": "report",
                "status": "completed",
                "summary": "wrote the report and the data file",
                "progress": 100,
                "next_step": None,
                "artifacts": ["report.md", "report.json"],
            }
        )

    result = await report()
    print("attempts the agent needed:", result.attempts)
    print("status:", result.telemetry.status)
    print("summary:", result.telemetry.summary)
    print("the first attempt was rejected by the verifier, the second passed")

    # A failing verification raises a retryable error.  With enough attempts
    # it ends up in the circuit breaker:
    failing = AutoOrchestrator(
        roadmap=["report"],
        memory_dir=str(root / "memory2"),
        timeout_seconds=30,
        max_retries=1,
        workdir=str(work_dir),
    )

    @failing.guard_step("report", verify=[artifacts_exist()])
    async def liar(ctx: StepContext) -> str:
        return json.dumps(
            {
                "step": "report",
                "status": "completed",
                "summary": "trust me",
                "progress": 100,
                "next_step": None,
                "artifacts": ["never-written.md"],
            }
        )

    try:
        await liar()
    except VerificationFailedError as exc:
        print("verification error:", exc)
    except Exception as exc:  # the breaker error carries it as __cause__
        print("the run was stopped:", type(exc).__name__)
        print("cause:", type(exc.__cause__).__name__, exc.__cause__)


if __name__ == "__main__":
    asyncio.run(main())
