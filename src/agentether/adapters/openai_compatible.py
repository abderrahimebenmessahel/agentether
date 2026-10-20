"""A generic worker for the OpenAI compatible chat completions API.

Many providers speak the same dialect: a ``POST`` to ``{base}/chat/completions``
with a JSON body, an ``Authorization: Bearer`` header and an answer shaped
like ``{"choices": [{"message": {"content": ...}}]}``.  This module is that
dialect, once, with the parts that differ in a :class:`ProviderSpec`.

The module is standard library only and it never imports a provider SDK.

**Secrets.**  The key is read from the environment only.  It is never
written to a file, never passed on a command line, never logged and never
in an error message: every message that could echo the server response is
passed through a redaction step first.

**Quotas.**  Every provider has a free tier with a limit.  A
:class:`TokenBucketLimiter` keeps the requests per minute under the limit
and a :class:`DailyCounter` keeps the requests per day under the limit; the
counter is written to disk with an atomic replace, so a run that is
interrupted and continued does not start the day from zero.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import random
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..exceptions import ConfigurationError
from ..models import StepContext, Usage, WorkerOutput

__all__ = [
    "DEFAULT_MODELS_PATH",
    "MAX_RESPONSE_BYTES",
    "DailyCounter",
    "OpenAICompatibleError",
    "OpenAICompatibleTransientError",
    "ProviderSpec",
    "TokenBucketLimiter",
    "list_free_models",
    "openai_compatible_complete",
    "openai_compatible_worker",
    "provider_for",
    "providers",
    "resolve_provider_key",
]

#: The default cap of the response body that is read.
MAX_RESPONSE_BYTES = 4 * 1024 * 1024

#: The path of the model list of an OpenAI compatible API.
DEFAULT_MODELS_PATH = "/models"

#: The User-Agent of the requests.  Some providers put a robot filter in
#: front of their API that answers the default agent of ``urllib``
#: ("Python-urllib/3.x") with a 403 and the error code 1010 of
#: Cloudflare, so the library sends a name of its own.
USER_AGENT = "agentether/0.3.0a1"

#: The HTTP status codes that are worth another attempt.
RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504})

#: The status codes that mean the key or the account is not allowed to make
#: the call.  They are never retried: another attempt would fail the same
#: way and would burn the quota.
NON_RETRYABLE_STATUS = frozenset({401, 402, 403})


class OpenAICompatibleError(RuntimeError):
    """An error reported by the provider.

    ``retryable`` tells the orchestrator whether another attempt can help.
    A rejected key (401, 403) or a request that needs money (402) never
    can; a rate limit or a server error sometimes can.
    """

    retryable = False


class OpenAICompatibleTransientError(OpenAICompatibleError):
    """A temporary failure of the provider (a rate limit, a server error)."""

    retryable = True

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


@dataclass(frozen=True)
class ProviderSpec:
    """Everything that differs between the providers.

    Attributes:
        name: The name of the provider.
        base_url: The base of the API, without the path of the call.
        api_key_env: The environment variable that holds the key.  It is
            ``None`` for a local provider that needs no key.
        chat_path: The path of the chat completions endpoint.
        models_path: The path of the model list, or ``None`` when the
            provider has none.
        requests_per_minute: The documented rate of the free tier.
        requests_per_day: The daily limit of the free tier.  It is a
            **safety net**: a run stops before the limit is reached.
        seed_parameter: The name of the seed parameter of the provider.
            It is ``None`` when the provider has no seed for the chat
            completions.
        free_marker: A suffix that marks a free model in the catalogue of
            the provider.  It is used when the catalogue has no price
            fields, which is the case of every provider but OpenRouter.
        free_models: The ids of the free models of a provider whose
            catalogue has no price.  They come from the documentation of
            the provider and they are only used when the catalogue still
            lists them, so a model that disappears is never called.
        docs_url: The page the facts come from.
        verified_on: The day the facts were read.
        notes: What could not be verified.
    """

    name: str
    base_url: str
    api_key_env: str | None
    chat_path: str = "/chat/completions"
    models_path: str | None = DEFAULT_MODELS_PATH
    requests_per_minute: int = 15
    requests_per_day: int = 50
    seed_parameter: str | None = "seed"
    free_marker: str | None = None
    key_names: tuple[str, ...] = ()
    free_models: tuple[str, ...] = ()
    docs_url: str = ""
    verified_on: str = ""
    notes: str = ""

    def url(self, path: str) -> str:
        """The full URL of a path of this provider."""
        return self.base_url.rstrip("/") + path

    def key_variables(self) -> tuple[str, ...]:
        """The names of the environment variables that may hold the key."""
        names = list(self.key_names)
        if self.api_key_env and self.api_key_env not in names:
            names.append(self.api_key_env)
        return tuple(names)


# ----------------------------------------------------------------------
# the limits
# ----------------------------------------------------------------------
class TokenBucketLimiter:
    """A limiter of "N requests per minute".

    The bucket is shared by every call of a provider, so two workers of the
    same provider cannot exceed the rate between them.
    """

    def __init__(self, per_minute: int) -> None:
        self._interval = 60.0 / max(1, per_minute)
        self._lock = asyncio.Lock()
        self._next_slot = 0.0

    async def acquire(self) -> None:
        """Wait until the next request may be sent."""
        async with self._lock:
            now = time.monotonic()
            delay = self._next_slot - now
            if delay > 0:
                await asyncio.sleep(delay)
            self._next_slot = time.monotonic() + self._interval


def _today() -> str:
    """The day the counter belongs to (UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _default_counter_path(provider: str) -> Path:
    """Where the daily counter of a provider lives."""
    base = os.environ.get("AGENTETHER_USAGE_DIR")
    root = Path(base) if base else Path.home() / ".cache" / "agentether" / "usage"
    return root / f"{provider}.json"


class DailyCounter:
    """A counter of the requests of one day, persisted on disk.

    The counter is written with an atomic replace, so a run that is killed
    in the middle of the write keeps the previous value instead of a
    truncated file.  A resumed run continues on the same counter, so the
    daily limit of the provider is not exceeded by running the trial twice.
    """

    def __init__(self, path: Path, limit: int, provider: str = "the provider") -> None:
        self._path = Path(path)
        self._limit = limit
        self._provider = provider
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        today = _today()
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        if not isinstance(data, dict):
            return {"date": today, "requests": 0}
        if data.get("date") != today:
            return {"date": today, "requests": 0}
        try:
            used = int(data.get("requests", 0))
        except (TypeError, ValueError):
            used = 0
        return {"date": today, "requests": max(0, used)}

    def _write(self) -> None:
        """Write the counter atomically."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(
            dir=str(self._path.parent), prefix=self._path.name + ".", suffix=".tmp"
        )
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(self._data, handle, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self._path)
        except OSError:
            with contextlib.suppress(OSError):
                temporary.unlink()

    @property
    def used(self) -> int:
        """The requests of today."""
        return int(self._data.get("requests", 0))

    @property
    def limit(self) -> int:
        """The daily limit of the provider."""
        return self._limit

    @property
    def remaining(self) -> int:
        """The requests that are still allowed today."""
        return max(0, self._limit - self.used)

    def reserve(self, count: int = 1) -> None:
        """Book ``count`` requests, or refuse.

        Raises:
            OpenAICompatibleError: When the daily limit would be exceeded.
        """
        if self.used + count > self._limit:
            raise OpenAICompatibleError(
                f"the daily limit of {self._limit} requests of {self._provider} is reached "
                f"({self.used} used); the run must wait for the next day"
            )
        self._data["requests"] = self.used + count
        self._write()


# ----------------------------------------------------------------------
# the key
# ----------------------------------------------------------------------
def resolve_api_key(api_key_env: str | None) -> str:
    """Find the API key in the environment.

    Args:
        api_key_env: The name of the environment variable to read.

    Returns:
        The key, or an empty string when the provider needs none.

    Raises:
        ConfigurationError: If no key was found.  The message names the
            variable and never contains a value.
    """
    if not api_key_env:
        return ""
    value = os.environ.get(api_key_env)
    if not value:
        lowered = {key.lower(): item for key, item in os.environ.items()}
        value = lowered.get(api_key_env.lower())
    if not value:
        raise ConfigurationError(f"the environment variable {api_key_env!r} is not set or empty")
    return value


def resolve_provider_key(spec: ProviderSpec) -> str:
    """Find the key of a provider in the environment.

    The names of the variables are tried as written and then case
    insensitively, which is what a provider with several possible variable
    names needs (OpenRouter accepts ``minimax``, ``MINIMAX``,
    ``MINIMAX_API_KEY`` and ``OPENROUTER_API_KEY``).

    Args:
        spec: The provider.

    Returns:
        The key, or an empty string when the provider needs none.

    Raises:
        ConfigurationError: If no key was found.  The message names the
            variables and never contains a value.
    """
    names = spec.key_variables()
    if not names:
        return ""
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    lowered = {key.lower(): value for key, value in os.environ.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value:
            return value
    raise ConfigurationError(
        f"no API key found for {spec.name}: set one of "
        + ", ".join(names)
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


# ----------------------------------------------------------------------
# the call
# ----------------------------------------------------------------------
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
        OpenAICompatibleTransientError: On a rate limit, a server error or
            a network failure.  The message never contains the key.
        OpenAICompatibleError: On a rejected request or a broken answer.
    """
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={**headers, "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        body = b""
        with contextlib.suppress(Exception):  # the body is best effort
            body = exc.read(4096)
        detail = _redact(body.decode("utf-8", errors="replace"), secret)[:500]
        message = f"the provider returned HTTP {exc.code}"
        if detail:
            message = f"{message}: {detail}"
        if exc.code in NON_RETRYABLE_STATUS:
            if exc.code == 402:
                raise OpenAICompatibleError(
                    f"{message} (the request needs a paid plan; this tool never enables billing)"
                ) from exc
            raise OpenAICompatibleError(
                f"{message} (the API key was rejected; check the key and its access to the model)"
            ) from exc
        if exc.code in RETRYABLE_STATUS:
            raise OpenAICompatibleTransientError(
                message, retry_after=_retry_after_seconds(exc.headers)
            ) from exc
        raise OpenAICompatibleError(message) from exc
    except urllib.error.URLError as exc:
        reason = _redact(str(getattr(exc, "reason", exc)), secret)
        raise OpenAICompatibleTransientError(f"could not reach the provider: {reason}") from exc
    except (TimeoutError, OSError) as exc:
        reason = _redact(str(exc), secret)
        raise OpenAICompatibleTransientError(f"the request failed: {reason}") from exc

    if len(raw) > max_bytes:
        raise OpenAICompatibleError(f"the response was larger than {max_bytes} bytes")
    try:
        decoded = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise OpenAICompatibleError("the response was not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise OpenAICompatibleError("the response was not a JSON object")
    return decoded


def _get_json(
    url: str,
    headers: dict[str, str],
    timeout: float,
    max_bytes: int,
    secret: str,
) -> dict[str, Any]:
    """Send one GET request and return the decoded JSON body.

    The catalogue of the models is a GET, not a POST: a POST on it is
    answered with 404 or 405 by most of the providers.

    Raises:
        OpenAICompatibleError: On a rejected request or a broken answer.
    """
    request = urllib.request.Request(
        url, headers={**headers, "User-Agent": USER_AGENT}, method="GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        body = b""
        with contextlib.suppress(Exception):  # the body is best effort
            body = exc.read(4096)
        detail = _redact(body.decode("utf-8", errors="replace"), secret)[:500]
        message = f"the provider returned HTTP {exc.code}"
        if detail:
            message = f"{message}: {detail}"
        if exc.code in NON_RETRYABLE_STATUS:
            raise OpenAICompatibleError(
                f"{message} (the API key was rejected; check the key and its access "
                f"to the catalogue)"
            ) from exc
        if exc.code in RETRYABLE_STATUS:
            raise OpenAICompatibleTransientError(
                message, retry_after=_retry_after_seconds(exc.headers)
            ) from exc
        raise OpenAICompatibleError(message) from exc
    except urllib.error.URLError as exc:
        reason = _redact(str(getattr(exc, "reason", exc)), secret)
        raise OpenAICompatibleTransientError(f"could not reach the provider: {reason}") from exc
    except (TimeoutError, OSError) as exc:
        reason = _redact(str(exc), secret)
        raise OpenAICompatibleTransientError(f"the request failed: {reason}") from exc

    if len(raw) > max_bytes:
        raise OpenAICompatibleError(f"the response was larger than {max_bytes} bytes")
    try:
        decoded = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise OpenAICompatibleError("the response was not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise OpenAICompatibleError("the response was not a JSON object")
    return decoded


def _to_worker_output(data: dict[str, Any], secret: str) -> WorkerOutput:
    """Turn the decoded answer into a :class:`WorkerOutput`."""
    reported = data.get("error")
    if isinstance(reported, dict) and reported.get("message"):
        detail = _redact(str(reported["message"]), secret)
        raise OpenAICompatibleError(f"the provider reported an error: {detail}")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise OpenAICompatibleError("the response contained no choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise OpenAICompatibleError("the response contained a malformed choice")
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


async def openai_compatible_complete(
    prompt: str,
    *,
    spec: ProviderSpec,
    model: str,
    api_key: str | None = None,
    api_key_resolver: Callable[[], str] | None = None,
    timeout: float = 60.0,
    max_retries: int = 4,
    backoff_base: float = 1.0,
    backoff_max: float = 20.0,
    extra_headers: Mapping[str, str] | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    seed: int | None = None,
    response_format: Mapping[str, Any] | None = None,
    max_response_bytes: int = MAX_RESPONSE_BYTES,
    limiter: TokenBucketLimiter | None = None,
    counter: DailyCounter | None = None,
) -> WorkerOutput:
    """Send one prompt to a provider and return the answer.

    Args:
        prompt: The user prompt.
        spec: The provider.
        model: The model id.
        api_key: The key.  It is read from the environment when it is
            ``None`` and the provider needs one.
        api_key_resolver: A callable that returns the key.  It is used
            instead of the environment variable of the spec, which is what
            a provider with several possible variable names needs.
        timeout: The HTTP timeout in seconds.
        max_retries: How many extra attempts a rate limit or a server error
            gets.
        backoff_base: The base of the exponential backoff.
        backoff_max: The cap of a single backoff delay.
        extra_headers: Headers that are added to the request.
        system_prompt: An optional system message.
        temperature: The sampling temperature.
        max_tokens: The cap of the answer, when the provider takes one.
        seed: The seed, when the provider takes one.
        response_format: The ``response_format`` of the request.
        max_response_bytes: The cap of the response body that is read.
        limiter: The rate limiter of the provider.
        counter: The daily counter of the provider.

    Returns:
        The answer and the usage reported by the server.

    Raises:
        OpenAICompatibleError: On a rejected request or a broken answer.
        OpenAICompatibleTransientError: When the failure may be temporary.
        ConfigurationError: When no API key was found.
    """
    if api_key is not None:
        secret = api_key
    elif api_key_resolver is not None:
        secret = api_key_resolver()
    else:
        secret = resolve_api_key(spec.api_key_env)
    if (spec.api_key_env or api_key_resolver is not None) and not secret:
        raise ConfigurationError(
            f"the environment variable {spec.api_key_env!r} is not set or empty"
        )
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    if extra_headers:
        headers.update(extra_headers)
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if seed is not None and spec.seed_parameter:
        # The name of the seed is not the same everywhere: Mistral calls it
        # "random_seed" and Gemini has no seed for the chat completions.
        payload[spec.seed_parameter] = seed
    if response_format is not None:
        payload["response_format"] = dict(response_format)

    if limiter is not None:
        await limiter.acquire()
    if counter is not None:
        counter.reserve()

    attempt = 0
    while True:
        try:
            data = await asyncio.to_thread(
                _post_json,
                spec.url(spec.chat_path),
                payload,
                headers,
                timeout,
                max_response_bytes,
                secret,
            )
            break
        except OpenAICompatibleTransientError as exc:
            if attempt >= max_retries:
                raise
            attempt += 1
            delay = exc.retry_after
            if delay is None:
                cap = min(backoff_max, backoff_base * (2 ** (attempt - 1)))
                delay = random.uniform(0.0, cap)
            await asyncio.sleep(min(delay, backoff_max))
    return _to_worker_output(data, secret)


def openai_compatible_worker(
    *,
    spec: ProviderSpec,
    model: str,
    api_key_env: str | None = None,
    api_key_resolver: Callable[[], str] | None = None,
    timeout: float = 60.0,
    max_retries: int = 4,
    backoff_base: float = 1.0,
    backoff_max: float = 20.0,
    extra_headers: Mapping[str, str] | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    seed: int | None = None,
    response_format: Mapping[str, Any] | None = None,
    max_response_bytes: int = MAX_RESPONSE_BYTES,
    limiter: TokenBucketLimiter | None = None,
    counter: DailyCounter | None = None,
) -> Callable[[StepContext], Awaitable[WorkerOutput]]:
    """Create a worker that calls a provider.

    Args:
        spec: The provider.
        model: The model id.
        api_key_env: The environment variable that holds the key.  It
            defaults to the one of the spec.
        api_key_resolver: A callable that returns the key.  It is used
            instead of the environment variable, which is what a provider
            with several possible variable names needs.
        timeout: The HTTP timeout in seconds.
        max_retries: How many extra attempts a rate limit or a server error
            gets.
        backoff_base: The base of the exponential backoff.
        backoff_max: The cap of a single backoff delay.
        extra_headers: Headers that are added to the request.
        system_prompt: An optional system message.
        temperature: The sampling temperature.
        max_tokens: The cap of the answer, when the provider takes one.
        seed: The seed, when the provider takes one.
        response_format: The ``response_format`` of the request.
        max_response_bytes: The cap of the response body that is read.
        limiter: The rate limiter of the provider.
        counter: The daily counter of the provider.

    Returns:
        A worker that can be used with ``@orch.guard_step("name")``.

    .. warning::
       Untested against live APIs unless ``AGENTETHER_LIVE_TESTS=1`` is set.
    """
    key_env = spec.api_key_env if api_key_env is None else api_key_env

    async def worker(ctx: StepContext) -> WorkerOutput:
        return await openai_compatible_complete(
            ctx.build_prompt(ctx.step_name),
            spec=spec,
            model=model,
            api_key=None if (key_env or api_key_resolver) else "",
            api_key_resolver=api_key_resolver,
            timeout=timeout,
            max_retries=max_retries,
            backoff_base=backoff_base,
            backoff_max=backoff_max,
            extra_headers=extra_headers,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
            response_format=response_format,
            max_response_bytes=max_response_bytes,
            limiter=limiter,
            counter=counter,
        )

    return worker


# ----------------------------------------------------------------------
# the model list
# ----------------------------------------------------------------------
def list_free_models(
    spec: ProviderSpec,
    *,
    api_key: str | None = None,
    timeout: float = 30.0,
    max_response_bytes: int = MAX_RESPONSE_BYTES,
) -> list[str]:
    """The ids of the free models of a provider, discovered live.

    A model is free when the provider says that both the prompt and the
    completion cost nothing.  Only OpenRouter publishes the price of a
    model in its catalogue; the other providers do not, so their free
    models are the ones whose name carries the free marker of the
    provider.  The ids are never hard-coded in this module: they are read
    from the catalogue of the provider, so a model that disappears does not
    break a run and a new free model is found without a code change.

    Args:
        spec: The provider.
        api_key: The key.  It is read from the environment when it is
            ``None``.
        timeout: The HTTP timeout in seconds.
        max_response_bytes: The cap of the response body that is read.

    Returns:
        The ids of the free models, sorted.

    Raises:
        OpenAICompatibleError: When the catalogue cannot be read.
        ConfigurationError: When no API key was found.
    """
    if spec.models_path is None:
        return []
    secret = resolve_api_key(spec.api_key_env) if api_key is None else api_key
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    data = _get_json(
        spec.url(spec.models_path),
        headers,
        timeout,
        max_response_bytes,
        secret,
    )
    items = data.get("data")
    if not isinstance(items, list):
        raise OpenAICompatibleError("the model list was not a list")
    found: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier:
            continue
        if spec.free_models:
            # The documentation of the provider lists the models of the
            # free tier.  The catalogue is only used to know that they
            # still exist: the price of the catalogue is the price of the
            # paid tier (Groq publishes one) and says nothing about the
            # free tier.
            # The catalogue of Google prefixes the ids with "models/",
            # while the request wants the bare id.
            request_id = identifier.removeprefix("models/")
            if request_id in spec.free_models:
                found.append(request_id)
            continue
        pricing = item.get("pricing")
        if isinstance(pricing, dict):
            prompt = str(pricing.get("prompt", "1"))
            completion = str(pricing.get("completion", "1"))
            if prompt in ("0", "0.0") and completion in ("0", "0.0"):
                found.append(identifier)
            continue
        if spec.free_marker and identifier.endswith(spec.free_marker):
            found.append(identifier)
    return sorted(found)


# ----------------------------------------------------------------------
# the presets
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class _ProviderRegistry:
    """The providers this module knows about."""

    items: dict[str, ProviderSpec] = field(default_factory=dict)

    def get(self, name: str) -> ProviderSpec:
        """The spec of a provider, by name."""
        key = name.strip().lower()
        if key not in self.items:
            known = ", ".join(sorted(self.items))
            raise ConfigurationError(f"unknown provider {name!r}; known providers: {known}")
        return self.items[key]

    def names(self) -> list[str]:
        """The names of the known providers."""
        return sorted(self.items)


#: The providers of the free tier.  The facts come from the official
#: documentation; ``docs/providers.md`` has the links and the access date.
#: A fact that could not be verified is marked "unverified" there.
#:
#: The model ids are **not** in this table: they are discovered live with
#: :func:`list_free_models`, so a model that disappears does not break a
#: run and a new free model is found without a code change.
PROVIDERS: dict[str, ProviderSpec] = {
    "openrouter": ProviderSpec(
        name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env=None,
        requests_per_minute=20,
        requests_per_day=50,
        seed_parameter="seed",
        free_marker=":free",
        key_names=("minimax", "MINIMAX", "MINIMAX_API_KEY", "OPENROUTER_API_KEY"),
        docs_url="https://openrouter.ai/docs/api-reference/limits",
        verified_on="2026-10-20",
        notes=(
            "The key may be in any of the names of "
            "agentether.adapters.openrouter.KEY_ENVIRONMENT_VARIABLES, so the "
            "preset has no single environment variable.  The catalogue is the "
            "only one that documents the price of a model, so the free "
            "models are found there and not by their name."
        ),
    ),
    "groq": ProviderSpec(
        name="Groq",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        requests_per_minute=30,
        requests_per_day=1000,
        seed_parameter="seed",
        free_models=("openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"),
        docs_url="https://console.groq.com/docs/rate-limits",
        verified_on="2026-10-20",
        notes=(
            "The free plan limits are given per model: 30 requests per minute "
            "and 1000 requests per day for the instruction models, 200000 "
            "tokens per day.  The catalogue does not document a price, so the "
            "free models are the ones the free plan lists."
        ),
    ),
    "cerebras": ProviderSpec(
        name="Cerebras",
        base_url="https://api.cerebras.ai/v1",
        api_key_env="CEREBRAS_API_KEY",
        requests_per_minute=5,
        requests_per_day=1000,
        seed_parameter="seed",
        free_models=("gpt-oss-120b", "qwen-3.8-27b"),
        docs_url="https://inference-docs.cerebras.ai/support/rate-limits",
        verified_on="2026-10-20",
        notes=(
            "UNVERIFIED: the number of requests per day.  The documentation "
            "gives 5 requests per minute and 1000000 tokens per day for the "
            "free models, and no daily request count; 1000 is a safety net."
        ),
    ),
    "mistral": ProviderSpec(
        name="Mistral",
        base_url="https://api.mistral.ai/v1",
        api_key_env="MISTRAL_API_KEY",
        requests_per_minute=2,
        requests_per_day=100,
        seed_parameter="random_seed",
        docs_url="https://docs.mistral.ai/admin/billing-usage/usage-limits",
        verified_on="2026-10-20",
        notes=(
            "UNVERIFIED: the free tier limits.  The documentation shows them "
            "in the console and does not publish the numbers; the values here "
            "are a safety net taken from the brief of the maintainer.  The "
            "provider calls the seed 'random_seed'."
        ),
    ),
    "google": ProviderSpec(
        name="Google AI Studio",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        api_key_env="GEMINI_API_KEY",
        requests_per_minute=15,
        requests_per_day=1500,
        seed_parameter=None,
        free_models=(
            "gemini-3.8-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3-flash-preview",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
        ),
        docs_url="https://ai.google.dev/gemini-api/docs/rate-limits",
        verified_on="2026-10-20",
        notes=(
            "UNVERIFIED: the free tier limits.  The documentation says that "
            "they depend on the tier and are shown in AI Studio.  The limits "
            "apply per project, not per key, and the daily count is reset at "
            "midnight Pacific time.  The provider has no seed for the chat "
            "completions."
        ),
    ),
    "ollama": ProviderSpec(
        name="Ollama",
        base_url="http://localhost:11434/v1",
        api_key_env=None,
        requests_per_minute=600,
        requests_per_day=100000,
        seed_parameter="seed",
        docs_url="https://docs.ollama.com/api/openai-compatibility",
        verified_on="2026-10-20",
        notes=(
            "A local server: there is no quota, so the limits are only a "
            "safety net.  UNVERIFIED: the names of the rate limit headers."
        ),
    ),
}


def provider_for(name: str) -> ProviderSpec:
    """The spec of a provider, by name."""
    return _ProviderRegistry(PROVIDERS).get(name)


def providers() -> list[str]:
    """The names of the known providers."""
    return _ProviderRegistry(PROVIDERS).names()
