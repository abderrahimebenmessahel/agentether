"""A 60 second demo, without an API key.

The "agent" below is a fake that claims to have written a file it never
wrote.  AgenTether catches the claim, shows the agent why, and the second
attempt does the work for real.

    python examples/demo.py
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from agentether import AutoOrchestrator, StepContext, artifacts_exist, file_contains


async def main() -> None:
    """Run the demo."""
    root = Path(tempfile.mkdtemp())
    memory = root / "memory"
    work = root / "work"
    memory.mkdir()
    work.mkdir()

    orch = AutoOrchestrator(
        roadmap=["notes"],
        memory_dir=str(memory),
        timeout_seconds=30,
        max_retries=3,
        workdir=str(work),
    )
    attempt = 0

    @orch.guard_step("notes", verify=[artifacts_exist(), file_contains("notes.md", "## Findings")])
    async def notes(ctx: StepContext) -> str:
        """A worker that lies on the first attempt and works on the second."""
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            # It claims the work is done, but it writes nothing.
            return json.dumps(
                {
                    "step": "notes",
                    "status": "completed",
                    "summary": "I wrote the notes.",
                    "progress": 100,
                    "next_step": None,
                    "artifacts": ["notes.md"],
                }
            )
        (work / "notes.md").write_text(
            "# Notes\n\n## Findings\n\nThree credible sources.\n", encoding="utf-8"
        )
        return json.dumps(
            {
                "step": "notes",
                "status": "completed",
                "summary": "I wrote the notes for real.",
                "progress": 100,
                "next_step": None,
                "artifacts": ["notes.md"],
            }
        )

    try:
        result = await notes()
    except Exception as exc:  # the run may end with the breaker
        print(f"the run stopped: {type(exc).__name__}: {exc}")
        return

    print(f"step      : {result.step}")
    print(f"status    : {result.telemetry.status}")
    print(f"attempts  : {result.attempts}")
    print(f"summary   : {result.telemetry.summary}")
    print(f"the file  : {(work / 'notes.md').exists()}")
    print("the first claim was rejected: the file did not exist yet")
    print(f"the memory file: {memory / 'PROJECT_MEMORY.md'}")


if __name__ == "__main__":
    asyncio.run(main())
