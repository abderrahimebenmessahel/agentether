"""A runnable AgenTether example.

The example uses a stub ``my_llm`` so it runs offline and deterministically.
Replace ``my_llm`` with a call to your own model -- the contract stays the
same: return text that ends with the telemetry JSON object.

    python examples/quickstart.py
"""

from __future__ import annotations

import asyncio
import json
import re
import tempfile
from pathlib import Path

from agentether import AutoOrchestrator, StepContext, configure_logging


async def my_llm(prompt: str) -> str:
    """Stand-in for a real LLM call.

    A real implementation would send ``prompt`` to the model and return the
    raw answer.  The answer has to end with the telemetry JSON object.
    """
    await asyncio.sleep(0.05)  # pretend this is a network call
    match = re.search(r'You are on step \d+ of \d+: "([^"]+)"', prompt)
    step = match.group(1) if match else "unknown"
    payload = {
        "step": step,
        "status": "completed",
        "summary": f"I completed the {step} step.",
        "progress": 100,
        "next_step": "write" if step == "research" else None,
        "artifacts": [f"notes/{step}.md"],
    }
    return f"Here is what I did for the {step} step.\n{json.dumps(payload)}"


async def main() -> None:
    configure_logging()
    memory_dir = Path(tempfile.mkdtemp()) / "project-memory"

    orch = AutoOrchestrator(
        roadmap=["research", "write"],
        memory_dir=str(memory_dir),
        timeout_seconds=60,
        max_retries=3,
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return await my_llm(ctx.build_prompt("Research X"))

    @orch.guard_step("write")
    async def write(ctx: StepContext) -> str:
        return await my_llm(ctx.build_prompt("Write the summary of X"))

    research_result = await research()
    print("research:", research_result.telemetry.summary)
    print("attempts:", research_result.attempts, "from cache:", research_result.from_cache)

    write_result = await write()
    print("write:", write_result.telemetry.summary)
    print("attempts:", write_result.attempts, "from cache:", write_result.from_cache)

    # Re-running the same step is a no-op: the result comes from the
    # project memory instead of the model.
    cached = await research()
    print("research again from cache:", cached.from_cache)

    # ``rerun()`` ignores the cached result and executes the step again.
    rerun = await research.rerun()
    print("research again with rerun(), from cache:", rerun.from_cache)

    print(f"\nproject memory written to {memory_dir / 'PROJECT_MEMORY.md'}")


if __name__ == "__main__":
    asyncio.run(main())
