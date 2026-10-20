"""A human in the loop.

When a step ends ``blocked``, AgenTether writes a "Needs human input" entry
into ``PROJECT_MEMORY.md`` and refuses to run the step again until the human
answers in their own section of the file.

The human section is never rewritten by the library:

    <!-- agentether:human:start -->
    ... the human writes here ...
    <!-- agentether:human:end -->

    python examples/human_in_the_loop.py
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from agentether import AutoOrchestrator, StepContext, configure_logging

HUMAN_START = "<!-- agentether:human:start -->"
HUMAN_END = "<!-- agentether:human:end -->"


async def main() -> None:
    configure_logging()
    root = Path(tempfile.mkdtemp())
    memory_dir = root / "memory"
    memory_dir.mkdir()

    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=30,
        max_retries=1,
    )
    answered = False

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        if ctx.last_error:
            # The human answered: the hint carries their text.
            print("the agent was told:", ctx.last_error.splitlines()[-1])
            return json.dumps(
                {
                    "step": "research",
                    "status": "completed",
                    "summary": "researched with the credentials the human provided",
                    "progress": 100,
                    "next_step": None,
                }
            )
        return json.dumps(
            {
                "step": "research",
                "status": "blocked",
                "summary": "I need an API key to continue",
                "progress": None,
                "next_step": None,
            }
        )

    try:
        await research()
    except Exception as exc:
        print("the step is blocked:", type(exc).__name__)

    memory_file = memory_dir / "PROJECT_MEMORY.md"
    print("\n--- PROJECT_MEMORY.md (excerpt) ---")
    text = memory_file.read_text(encoding="utf-8")
    start = text.find("## Needs human input")
    print(text[start : start + 120].strip())
    print("...")

    # The human answers in their own section.
    answered = True
    # The human writes right after the start marker; the library never
    # touches the text between the markers.
    text = text.replace(HUMAN_START, f"{HUMAN_START}\nthe API key is sk-example-123")
    memory_file.write_text(text, encoding="utf-8")
    print("\nthe human wrote their answer into the file\n")

    result = await research.rerun()
    print("the step ran again:", result.telemetry.status, "-", result.telemetry.summary)
    assert answered


if __name__ == "__main__":
    asyncio.run(main())
