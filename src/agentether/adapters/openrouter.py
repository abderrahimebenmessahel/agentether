"""OpenRouter adapter (optional, standard library only).

OpenRouter speaks the OpenAI dialect, so the work is done by
:mod:`agentether.adapters.openai_compatible`.  This module is the OpenRouter
preset: the endpoint, the names of the environment variables that may hold
the key, and the error types the rest of the code already catches.

.. warning::
   Untested against live APIs unless ``AGENTETHER_LIVE_TESTS=1`` is set.

**Secrets.**  The API key is read from the environment only.  It is never
written to a file, never passed on a command line, never logged and never
in an error message: every message that could echo the server response is
passed through a redaction step first.
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable

from ..exceptions import ConfigurationError
from ..models import StepContext, WorkerOutput
from .openai_compatible import (
    MAX_RESPONSE_BYTES,
    OpenAICompatibleError,
    OpenAICompatibleTransientError,
    ProviderSpec,
    openai_compatible_complete,
    openai_compatible_worker,
)

__all__ = [
    "DEFAULT_ENDPOINT",
    "DEFAULT_MODEL",
    "KEY_ENVIRONMENT_VARIABLES",
    "OPENROUTER",
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


class OpenRouterError(OpenAICompatibleError):
    """An error reported by the OpenRouter API.

    ``retryable`` tells the orchestrator whether another attempt can help.
    A bad key (401/403) never can; a rate limit or a server error sometimes
    can.
    """


class OpenRouterTransientError(OpenRouterError):
    """A temporary OpenRouter failure (rate limit, server error, network)."""

    retryable = True

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


#: The preset of OpenRouter.  The model ids are not hard-coded: they are
#: discovered with :func:`agentether.adapters.openai_compatible.list_free_models`.
OPENROUTER = ProviderSpec(
    name="OpenRouter",
    base_url="https://openrouter.ai/api/v1",
    api_key_env=None,
    chat_path="/chat/completions",
    models_path="/models",
    requests_per_minute=20,
    requests_per_day=50,
    docs_url="https://openrouter.ai/docs/api-reference/limits",
    verified_on="2026-10-20",
    notes=(
        "The key may be in any of the names of KEY_ENVIRONMENT_VARIABLES, so the "
        "preset itself has no single environment variable."
    ),
)


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


def provider_key_resolver(api_key_env: str | None = None) -> Callable[[], str]:
    """A callable that returns the key of OpenRouter, read at every call.

    The key is read when the worker runs, not when it is built, so a test
    (or a run that reads the key from the user scope of Windows) can set
    the environment after the worker exists.
    """

    def _resolve() -> str:
        return resolve_api_key(api_key_env)

    return _resolve


def _split_endpoint(endpoint: str) -> tuple[str, str]:
    """Split a full endpoint into the base of the API and the path."""
    for path in ("/chat/completions", "/v1/chat/completions"):
        if endpoint.endswith(path):
            return endpoint[: -len(path)], path
    return endpoint, "/chat/completions"


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
    prompt from a :class:`~agentether.models.StepContext` and calls it.

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
    base, path = _split_endpoint(endpoint)
    headers: dict[str, str] = {}
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-Title"] = title
    spec = ProviderSpec(
        name=OPENROUTER.name,
        base_url=base,
        api_key_env=None,
        chat_path=path,
        models_path=OPENROUTER.models_path,
        requests_per_minute=OPENROUTER.requests_per_minute,
        requests_per_day=OPENROUTER.requests_per_day,
        docs_url=OPENROUTER.docs_url,
        verified_on=OPENROUTER.verified_on,
        notes=OPENROUTER.notes,
    )
    try:
        return await openai_compatible_complete(
            prompt,
            spec=spec,
            model=model,
            api_key=resolve_api_key(api_key_env),
            timeout=timeout,
            max_retries=max_retries,
            backoff_base=backoff_base,
            backoff_max=backoff_max,
            extra_headers=headers or None,
            system_prompt=system_prompt,
            temperature=temperature,
            max_response_bytes=max_response_bytes,
        )
    except OpenAICompatibleTransientError as exc:
        raise OpenRouterTransientError(str(exc), retry_after=exc.retry_after) from exc
    except OpenAICompatibleError as exc:
        raise OpenRouterError(str(exc)) from exc


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
        api_key_env: The environment variable that holds the key.  When it
            is ``None``, :data:`KEY_ENVIRONMENT_VARIABLES` are tried.
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
       Untested against live APIs unless ``AGENTETHER_LIVE_TESTS=1`` is set.
    """
    base, path = _split_endpoint(endpoint)
    spec = ProviderSpec(
        name=OPENROUTER.name,
        base_url=base,
        api_key_env=None,
        chat_path=path,
        models_path=OPENROUTER.models_path,
        requests_per_minute=OPENROUTER.requests_per_minute,
        requests_per_day=OPENROUTER.requests_per_day,
        docs_url=OPENROUTER.docs_url,
        verified_on=OPENROUTER.verified_on,
        notes=OPENROUTER.notes,
    )
    headers: dict[str, str] = {}
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-Title"] = title
    inner = openai_compatible_worker(
        spec=spec,
        model=model,
        api_key_resolver=lambda: resolve_api_key(api_key_env),
        timeout=timeout,
        max_retries=max_retries,
        backoff_base=backoff_base,
        backoff_max=backoff_max,
        extra_headers=headers or None,
        system_prompt=system_prompt,
        temperature=temperature,
        max_response_bytes=max_response_bytes,
    )

    async def worker(ctx: StepContext) -> WorkerOutput:
        """One call to OpenRouter, with the errors of OpenRouter."""
        try:
            return await inner(ctx)
        except OpenAICompatibleTransientError as exc:
            raise OpenRouterTransientError(str(exc), retry_after=exc.retry_after) from exc
        except OpenAICompatibleError as exc:
            raise OpenRouterError(str(exc)) from exc

    return worker
