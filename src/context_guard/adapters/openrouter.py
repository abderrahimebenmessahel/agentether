"""OpenRouter adapter (optional, standard library only).

Talks to the OpenRouter OpenAI compatible endpoint with ``urllib``.  No third
party dependency is needed.

.. warning::
   Untested against live APIs unless ``CONTEXTGUARD_LIVE_TESTS=1`` is set.

**Secrets.**  The API key is read from the environment only.  It is never
written to a file, never passed on a command line, never logged and never
included in an error message: every message that could echo the server
response is passed through a redaction step first.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import random
import urllib.error
import urllib.request
from collections.abc import Awaitable, Callable
from typing import Any

from ..exceptions import ConfigurationError
from ..models import StepContext, Usage, WorkerOutput

__all__ = [
    "DEFAULT_MODEL",
    "KEY_ENVIRONMENT_VARIABLES",
    "OpenRouterError",
    "OpenRouterTransientError",
    "openrouter_complete",
    "openrouter_worker",
    "resolve_api_key",
]

#: The default model of the free tier.
DEFAULT_MODEL = "minimax/minimax-m3.1-flash:free"

#: The endpoint of the OpenAI compatible API of OpenRouter.
DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

#: The environment variables that are searched for the key, in this order.
KEY_ENVIRONMENT_VARIABLES: tuple[str, ...] = (
    "minimax",
    "MINIMAX",
    "MINIMAX_API_KEY",
    "OPENROUTER_API_KEY",
)

#: The default cap of the response body that is read.
MAX_RESPONSE_BYTES = 4 * 1024 * 1024

#: The HTTP status codes that are worth another attempt.
RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


class OpenRouterError(RuntimeError):
    """An error reported by the OpenRouter API.

    ``retryable`` tells the orchestrator whether another attempt can help.
    A bad key (401/403) never can; a rate limit or a server error sometimes
    can.
    """

    retryable = False


class OpenRouterTransientError(OpenRouterError):
    """A temporary OpenRouter failure (rate limit, server error, network)."""

    retryable = True

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def resolve_api_key(api_key_env: str | None = None) -> str:
    """Find the API key in the environment.

    Args:
        api_key_env: The name of the environment variable to read.  When it
            is ``None``, the variables in :data:`KEY_ENVIRONMENT_VARIABLES`
            are tried, first as written and then case insensitively.

    Returns:
        The key.

    Raises:
        ConfigurationError: If no key was found.  The message names the
            variables that were checked and never contains a value.
    """
    if api_key_env:
        value = os.environ.get(api_key_env)
        if not value:
            raise ConfigurationError(
                f"the environment variable {api_key_env!r} is not set or empty"
            )
        return value
    for name in KEY_ENVIRONMENT_VARIABLES:
        value = os.environ.get(name)
        if value:
            return value
    lowered = {key.lower(): value for key, value in os.environ.items()}
    for name in KEY_ENVIRONMENT_VARIABLES:
        value = lowered.get(name.lower())
        if value:
            return value
    raise ConfigurationError(
        "no OpenRouter API key found: set one of "
        + ", ".join(KEY_ENVIRONMENT_VARIABLES)
        + " in the environment (the key is never read from a file or a command line)"
    )


def _redact(text: str, secret: str) -> str:
    """Remove the key from a text that is about to be shown or logged."""
    if secret and secret in text:
        return text.replace(secret, "***redacted***")
    return text


def _retry_after_seconds(headers: Any) -> float | None:
    """Read the ``Retry-After`` header, if it is a number of seconds."""
    if headers is None:
        return None
    try:
        raw = headers.get("Retry-After")
    except AttributeError:  # pragma: no cover - a header object without get()
        return None
    if raw is None:
        return None
    try:
        return max(0.0, float(str(raw).strip()))
    except ValueError:
        return None


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
    max_bytes: int,
    secret: str,
) -> dict[str, Any]:
    """Send one request and return the decoded JSON body.

    Raises:
        OpenRouterTransientError: On a rate limit, a server error or a
            network failure.  The message never contains the key.
        OpenRouterError: On a rejected request or a broken answer.
    """
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        body = b""
        with contextlib.suppress(Exception):  # the body is best effort
            body = exc.read(4096)
        detail = _redact(body.decode("utf-8", errors="replace"), secret)[:500]
        message = f"OpenRouter returned HTTP {exc.code}"
        if detail:
            message = f"{message}: {detail}"
        if exc.code in (401, 403):
            raise OpenRouterError(
                f"{message} (the API key was rejected; check the key and its access to the model)"
            ) from exc
        if exc.code in RETRYABLE_STATUS:
            raise OpenRouterTransientError(
                message, retry_after=_retry_after_seconds(exc.headers)
            ) from exc
        raise OpenRouterError(message) from exc
    except urllib.error.URLError as exc:
        reason = _redact(str(getattr(exc, "reason", exc)), secret)
        raise OpenRouterTransientError(f"could not reach OpenRouter: {reason}") from exc
    except (TimeoutError, OSError) as exc:
        reason = _redact(str(exc), secret)
        raise OpenRouterTransientError(f"the OpenRouter request failed: {reason}") from exc

    if len(raw) > max_bytes:
        raise OpenRouterError(f"the OpenRouter response was larger than {max_bytes} bytes")
    try:
        decoded = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise OpenRouterError("the OpenRouter response was not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise OpenRouterError("the OpenRouter response was not a JSON object")
    return decoded


def openrouter_worker(
    *,
    model: str = DEFAULT_MODEL,
    api_key_env: str | None = None,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: float = 60.0,
    max_retries: int = 4,
    backoff_base: float = 1.0,
    backoff_max: float = 20.0,
    referer: str | None = None,
    title: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.0,
    max_response_bytes: int = MAX_RESPONSE_BYTES,
) -> Callable[[StepContext], Awaitable[WorkerOutput]]:
    """Create a worker that calls OpenRouter.

    Args:
        model: The model id, for example
            ``"minimax/minimax-m3.1-flash:free"``.
        api_key_env: The environment variable that holds the key.  When it is
            ``None``, :data:`KEY_ENVIRONMENT_VARIABLES` are tried.
        endpoint: The chat completions endpoint.
        timeout: The HTTP timeout in seconds.
        max_retries: How many extra attempts a rate limit or a server error
            gets.
        backoff_base: The base of the exponential backoff.
        backoff_max: The cap of a single backoff delay.
        referer: The optional ``HTTP-Referer`` header.
        title: The optional ``X-Title`` header.
        system_prompt: An optional system message.
        temperature: The sampling temperature.
        max_response_bytes: The cap of the response body that is read.

    Returns:
        A worker that can be used with ``@orch.guard_step("name")``.

    .. warning::
       Untested against live APIs unless ``CONTEXTGUARD_LIVE_TESTS=1`` is set.
    """

    async def worker(ctx: StepContext) -> WorkerOutput:
        return await openrouter_complete(
            ctx.build_prompt(ctx.step_name),
            model=model,
            api_key_env=api_key_env,
            endpoint=endpoint,
            timeout=timeout,
            max_retries=max_retries,
            backoff_base=backoff_base,
            backoff_max=backoff_max,
            referer=referer,
            title=title,
            system_prompt=system_prompt,
            temperature=temperature,
            max_response_bytes=max_response_bytes,
        )

    return worker


async def openrouter_complete(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    api_key_env: str | None = None,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: float = 60.0,
    max_retries: int = 4,
    backoff_base: float = 1.0,
    backoff_max: float = 20.0,
    referer: str | None = None,
    title: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.0,
    max_response_bytes: int = MAX_RESPONSE_BYTES,
) -> WorkerOutput:
    """Send one prompt to OpenRouter and return the answer.

    This is the low level entry point; :func:`openrouter_worker` builds the
    prompt from a :class:`~context_guard.models.StepContext` and calls it.

    Args:
        prompt: The user prompt.
        model: The model id.
        api_key_env: The environment variable that holds the key.
        endpoint: The chat completions endpoint.
        timeout: The HTTP timeout in seconds.
        max_retries: How many extra attempts a rate limit or a server error
            gets.
        backoff_base: The base of the exponential backoff.
        backoff_max: The cap of a single backoff delay.
        referer: The optional ``HTTP-Referer`` header.
        title: The optional ``X-Title`` header.
        system_prompt: An optional system message.
        temperature: The sampling temperature.
        max_response_bytes: The cap of the response body that is read.

    Returns:
        The answer and the usage reported by the server.

    Raises:
        OpenRouterError: On a rejected request or a broken answer.
        OpenRouterTransientError: When the failure may be temporary.
        ConfigurationError: When no API key was found.
    """
    secret = resolve_api_key(api_key_env)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {secret}",
    }
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-Title"] = title
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    attempt = 0
    while True:
        try:
            data = await asyncio.to_thread(
                _post_json,
                endpoint,
                payload,
                headers,
                timeout,
                max_response_bytes,
                secret,
            )
            break
        except OpenRouterTransientError as exc:
            if attempt >= max_retries:
                raise
            attempt += 1
            delay = exc.retry_after
            if delay is None:
                cap = min(backoff_max, backoff_base * (2 ** (attempt - 1)))
                delay = random.uniform(0.0, cap)
            await asyncio.sleep(min(delay, backoff_max))
    return _to_worker_output(data, secret)


def _to_worker_output(data: dict[str, Any], secret: str) -> WorkerOutput:
    """Turn the decoded answer into a :class:`WorkerOutput`."""
    reported = data.get("error")
    if isinstance(reported, dict) and reported.get("message"):
        detail = _redact(str(reported["message"]), secret)
        raise OpenRouterError(f"OpenRouter reported an error: {detail}")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise OpenRouterError("the OpenRouter response contained no choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise OpenRouterError("the OpenRouter response contained a malformed choice")
    payload_message = first.get("message")
    text = ""
    if isinstance(payload_message, dict):
        content = payload_message.get("content")
        if isinstance(content, str):
            text = content
    usage = data.get("usage")
    input_tokens = 0
    output_tokens = 0
    cost: float | None = None
    if isinstance(usage, dict):
        input_tokens = int(usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or 0)
        raw_cost = usage.get("cost")
        if isinstance(raw_cost, (int, float)):
            cost = float(raw_cost)
    return WorkerOutput(
        text=text,
        usage=Usage(input_tokens=input_tokens, output_tokens=output_tokens, cost=cost),
    )
