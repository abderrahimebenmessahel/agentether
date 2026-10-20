"""Anthropic adapter (optional extra).

.. warning::
   Untested against live APIs unless ``CONTEXTGUARD_LIVE_TESTS=1`` is set.
   The API key is read from the environment by the SDK; never hard code it
   and never log it.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ..models import StepContext, Usage, WorkerOutput

__all__ = ["anthropic_worker"]


def _require_anthropic() -> Any:
    import importlib

    try:
        return importlib.import_module("anthropic")
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise ImportError(
            "the 'anthropic' package is required for this adapter; "
            "install it with: pip install 'contextguard[anthropic]'"
        ) from exc


def anthropic_worker(
    *,
    model: str = "claude-3-5-sonnet-latest",
    max_tokens: int = 2048,
    system: str | None = None,
    client: Any | None = None,
    **client_kwargs: Any,
) -> Callable[[StepContext], Awaitable[WorkerOutput]]:
    """Create a worker that calls the Anthropic Messages API.

    Args:
        model: The model id.
        max_tokens: Maximum number of tokens to generate.
        system: Optional system prompt.
        client: An existing client instance (useful for tests).  When it is
            not given, ``anthropic.AsyncAnthropic()`` is created lazily.
        **client_kwargs: Passed to the client constructor.

    Returns:
        A worker that can be used with ``@orch.guard_step("name")``.
    """
    if client is None:
        sdk = _require_anthropic()
        client = sdk.AsyncAnthropic(**client_kwargs)

    api = client

    async def worker(ctx: StepContext) -> WorkerOutput:
        message = await api.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": ctx.build_prompt(ctx.step_name)}],
        )
        parts = []
        for block in getattr(message, "content", []) or []:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        text = "".join(parts)
        usage = getattr(message, "usage", None)
        reported = Usage(
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        )
        return WorkerOutput(text=text, usage=reported)

    return worker
