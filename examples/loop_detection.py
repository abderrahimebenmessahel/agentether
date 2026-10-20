"""Detecting a loop of death.

An agent that keeps producing *different looking but equivalent* output is
the dangerous case: every answer looks new, but the agent is going in
circles.  AgenTether normalises the answer (numbers, ids and timestamps are
masked), hashes it into shingles and compares the answers with the Jaccard
similarity.  When three consecutive answers are alike, the loop is detected.

    python examples/loop_detection.py
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from agentether import (
    AutoOrchestrator,
    CircuitBreakerOpenError,
    LoopDetector,
    LoopPolicy,
    StepContext,
    configure_logging,
)
from agentether.loop_detector import fingerprint, jaccard


def show_the_fingerprints() -> None:
    """Show how two answers that look different get the same fingerprint."""
    first = "Processed 42 records, see run a1b2c3d4 for details."
    second = "Processed 43 records, see run e5f6a7b8 for details."
    print("normalized:", fingerprint(first) == fingerprint(second))
    print("similarity:", round(jaccard(fingerprint(first), fingerprint(second)), 3))


async def main() -> None:
    configure_logging()
    root = Path(tempfile.mkdtemp())
    memory_dir = root / "memory"
    memory_dir.mkdir()

    detector = LoopDetector(LoopPolicy(repeat_window=3, similarity_threshold=0.9))
    for token in ("a1b2c3d4", "e5f6a7b8", "09182736"):
        verdict = detector.record("research", f"still working, token {token}, same text")
        print(f"token {token}: loop={verdict.loop} similarity={verdict.similarity:.2f}")

    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=30,
        max_retries=5,
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        # Every answer looks slightly different (a new token every time) but
        # says exactly the same thing.
        return (
            f"I am still working on the report, token {ctx.attempt:08x}. "
            "The summary stays the same. " * 3
        )

    try:
        await research()
    except CircuitBreakerOpenError as exc:
        print("\nthe run was stopped by the circuit breaker")
        print("reason:", exc.reason)
        print("last error:", exc.last_error)
        print("the original error is chained:", type(exc.__cause__).__name__)


if __name__ == "__main__":
    asyncio.run(main())
