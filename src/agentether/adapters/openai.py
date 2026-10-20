"""OpenAI adapter (optional extra).

.. warning::
   Untested against live APIs unless ``AGENTETHER_LIVE_TESTS=1`` is set.
   The API key is read from the environment by the SDK; never hard code it
   and never log it.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ..models import StepContext, Usage, WorkerOutput

__all__ = ["openai_worker"]


def _require_openai() -> Any:
    import importlib

    try:
        return importlib.import_module("openai")
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise ImportError(
            "the 'openai' package is required for this adapter; "
            "install it with: pip install 'agentether[openai]'"
        ) from exc


def openai_worker(
    *,
    model: str = "gpt-4o-mini",
    max_tokens: int | None = None,
    system: str | None = None,
    client: Any | None = None,
    **client_kwargs: Any,
) -> Callable[[StepContext], Awaitable[WorkerOutput]]:
    """Create a worker that calls the OpenAI Chat Completions API.

    Args:
        model: The model id.
        max_tokens: Optional cap on the generated tokens.
        system: Optional system message.
        client: An existing client instance (useful for tests).  When it is
            not given, ``openai.AsyncOpenAI()`` is created lazily.
        **client_kwargs: Passed to the client constructor.

    Returns:
        A worker that can be used with ``@orch.guard_step("name")``.
    """
    if client is None:
        sdk = _require_openai()
        client = sdk.AsyncOpenAI(**client_kwargs)

    api = client

    async def worker(ctx: StepContext) -> WorkerOutput:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": ctx.build_prompt(ctx.step_name)})
        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        response = await api.chat.completions.create(**kwargs)
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        reported = Usage(
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        )
        return WorkerOutput(text=text, usage=reported)

    return worker
