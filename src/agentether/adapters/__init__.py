"""Optional provider adapters.

These helpers turn a provider call into a worker function that returns a
:class:`~agentether.models.WorkerOutput` with usage information, so that
token and cost budgets work with real providers.

**The core package never imports a provider SDK.**  Every adapter imports its
dependency lazily, when the adapter is created, and raises a clear
``ImportError`` when the optional extra is missing::

    pip install "agentether[anthropic]"
    pip install "agentether[openai]"

.. warning::
   These adapters are thin and **untested against live APIs** unless you set
   ``AGENTETHER_LIVE_TESTS=1`` and run the opt-in live tests.  They have
   only been exercised against fakes.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "anthropic_worker",
    "ollama_worker",
    "openai_compatible_worker",
    "openai_worker",
    "openrouter_worker",
    "provider_for",
    "providers",
]


def _require(module: str, extra: str) -> Any:
    """Import an optional dependency with a helpful error message."""
    import importlib

    try:
        return importlib.import_module(module)
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise ImportError(
            f"the {module!r} package is required for this adapter; "
            f"install it with: pip install 'agentether[{extra}]'"
        ) from exc


def anthropic_worker(**kwargs: Any) -> Any:
    """Create a worker that calls the Anthropic Messages API.

    Keyword arguments are passed to ``anthropic.Anthropic`` and the request
    (``model``, ``max_tokens``, ``system``, ...).

    .. warning::
       Untested against live APIs unless ``AGENTETHER_LIVE_TESTS=1`` is set.
       The API key is read from the environment by the SDK; never pass it in
       the source code and never log it.
    """
    from .anthropic import anthropic_worker as _worker

    return _worker(**kwargs)


def openrouter_worker(**kwargs: Any) -> Any:
    """Create a worker that calls the OpenRouter API.

    The key is read from the environment only: ``api_key_env`` or, when that
    is ``None``, the first of ``minimax``, ``MINIMAX``, ``MINIMAX_API_KEY``
    and ``OPENROUTER_API_KEY`` that is set.  The key is never logged and never
    appears in an error message.

    .. warning::
       Untested against live APIs unless ``AGENTETHER_LIVE_TESTS=1`` is set.
    """
    from .openrouter import openrouter_worker as _worker

    return _worker(**kwargs)


def openai_worker(**kwargs: Any) -> Any:
    """Create a worker that calls the OpenAI Chat Completions API.

    Keyword arguments are passed to ``openai.OpenAI`` and the request
    (``model``, ``max_tokens``, ...).

    .. warning::
       Untested against live APIs unless ``AGENTETHER_LIVE_TESTS=1`` is set.
       The API key is read from the environment by the SDK.
    """
    from .openai import openai_worker as _worker

    return _worker(**kwargs)


def ollama_worker(**kwargs: Any) -> Any:
    """Create a worker that calls a local Ollama server.

    Only the standard library is used (``urllib``).  The default endpoint is
    ``http://127.0.0.1:11434``.

    .. warning::
       Untested against live APIs unless ``AGENTETHER_LIVE_TESTS=1`` is set.
    """
    from .ollama import ollama_worker as _worker

    return _worker(**kwargs)


def openai_compatible_worker(**kwargs: Any) -> Any:
    """Create a worker for any provider that speaks the OpenAI dialect.

    The providers of the free tier are registered in
    :data:`agentether.adapters.openai_compatible.PROVIDERS`: OpenRouter,
    Groq, Cerebras, Mistral, Google AI Studio and a local Ollama.  Only
    the standard library is used and the key is read from the environment.

    .. warning::
       Untested against live APIs unless ``AGENTETHER_LIVE_TESTS=1`` is set.
    """
    from .openai_compatible import openai_compatible_worker as _worker

    return _worker(**kwargs)


def provider_for(name: str) -> Any:
    """The preset of a provider, by name.

    Args:
        name: The name of the provider, for example ``"groq"``.

    Returns:
        The :class:`~agentether.adapters.openai_compatible.ProviderSpec`.

    Raises:
        ConfigurationError: When the name is not known.  The message lists
            the known names.
    """
    from .openai_compatible import provider_for as _provider_for

    return _provider_for(name)


def providers() -> list[str]:
    """The names of the known providers."""
    from .openai_compatible import providers as _providers

    return _providers()
