"""Using the Anthropic adapter.

The adapter is an optional extra::

    pip install "agentether[anthropic]"
    export ANTHROPIC_API_KEY=...      # the SDK reads it from the environment

The core package never imports a provider SDK, and this example has **not
been tested against live APIs** unless ``AGENTETHER_LIVE_TESTS=1`` is set
and the live test in ``tests/test_adapters.py`` was run.

    python examples/anthropic_agent.py
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from agentether import AutoOrchestrator, StepContext, configure_logging


async def main() -> None:
    configure_logging()
    try:
        from agentether.adapters import anthropic_worker
    except ImportError as exc:  # pragma: no cover - depends on the environment
        print(exc)
        print('install it with: pip install "agentether[anthropic]"')
        return

    try:
        worker = anthropic_worker(model="claude-3-5-sonnet-latest", max_tokens=1024)
    except ImportError as exc:
        print(exc)
        return

    memory_dir = Path(tempfile.mkdtemp()) / "project-memory"
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=120,
        max_retries=3,
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        # The adapter returns a WorkerOutput, so the token and cost budgets
        # of the orchestrator see the usage reported by the provider.
        result = await worker(ctx)
        print("usage:", result.usage)
        text: str = result.text
        return text

    try:
        result = await research()
    except Exception as exc:
        print("the call failed:", type(exc).__name__, exc)
        print("(this example needs a real ANTHROPIC_API_KEY to work)")
        return

    print("status:", result.telemetry.status)
    print("summary:", result.telemetry.summary)


if __name__ == "__main__":
    asyncio.run(main())
