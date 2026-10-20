"""Ollama adapter (optional, standard library only).

Talks to a local Ollama server over HTTP using ``urllib`` -- no third party
dependency is needed.

.. warning::
   Untested against live APIs unless ``AGENTETHER_LIVE_TESTS=1`` is set.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Awaitable, Callable
from typing import Any

from ..models import StepContext, Usage, WorkerOutput

__all__ = ["DEFAULT_OLLAMA_URL", "ollama_worker"]

#: The default endpoint of a local Ollama server.
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


def ollama_worker(
    *,
    model: str = "llama3.2",
    url: str = DEFAULT_OLLAMA_URL,
    system: str | None = None,
    timeout: float = 120.0,
    temperature: float = 0.0,
) -> Callable[[StepContext], Awaitable[WorkerOutput]]:
    """Create a worker that calls a local Ollama server.

    Args:
        model: The model name known to the server.
        url: Base URL of the server.
        system: Optional system prompt.
        timeout: HTTP timeout in seconds.
        temperature: Sampling temperature.

    Returns:
        A worker that can be used with ``@orch.guard_step("name")``.
    """

    async def worker(ctx: StepContext) -> WorkerOutput:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": ctx.build_prompt(ctx.step_name),
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        request = urllib.request.Request(
            f"{url.rstrip('/')}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"the Ollama server at {url} could not be reached: {exc}") from exc
        text = str(body.get("response", ""))
        prompt_tokens = int(body.get("prompt_eval_count", 0) or 0)
        output_tokens = int(body.get("eval_count", 0) or 0)
        return WorkerOutput(
            text=text,
            usage=Usage(input_tokens=prompt_tokens, output_tokens=output_tokens),
        )

    return worker
