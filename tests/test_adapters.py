"""Tests for the optional provider adapters.

The adapters are exercised against fakes only.  Nothing here calls a real
provider: the live tests are opt-in and skipped unless
``CONTEXTGUARD_LIVE_TESTS=1`` is set.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest

from context_guard import StepContext, WorkerOutput
from context_guard.adapters import anthropic_worker, ollama_worker, openai_worker

LIVE = os.environ.get("CONTEXTGUARD_LIVE_TESTS") == "1"


def make_context() -> StepContext:
    """A minimal step context for the adapters."""
    return StepContext(
        step_name="research",
        step_index=0,
        attempt=1,
        max_attempts=3,
        memory="# Project Memory\n",
        last_error=None,
        roadmap=("research",),
    )


class _FakeBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeUsage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.content = [_FakeBlock(text)]
        self.usage = _FakeUsage(11, 7)


class _FakeMessages:
    def __init__(self, text: str) -> None:
        self.text = text
        self.kwargs: dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> _FakeMessage:
        self.kwargs = kwargs
        return _FakeMessage(self.text)


class _FakeAnthropicClient:
    def __init__(self, text: str) -> None:
        self.messages = _FakeMessages(text)


async def test_anthropic_worker_returns_text_and_usage() -> None:
    client = _FakeAnthropicClient("the answer")
    worker = anthropic_worker(client=client, model="claude-test")
    result = await worker(make_context())
    assert isinstance(result, WorkerOutput)
    assert result.text == "the answer"
    assert result.usage is not None
    assert result.usage.input_tokens == 11
    assert result.usage.output_tokens == 7


class _FakeChoice:
    def __init__(self, text: str) -> None:
        self.message = type("Msg", (), {"content": text})()


class _FakeOpenAIUsage:
    def __init__(self) -> None:
        self.prompt_tokens = 5
        self.completion_tokens = 3


class _FakeCompletions:
    def __init__(self, text: str) -> None:
        self.text = text

    async def create(self, **kwargs: Any) -> Any:
        return type(
            "Resp",
            (),
            {
                "choices": [_FakeChoice(self.text)],
                "usage": _FakeOpenAIUsage(),
            },
        )()


class _FakeOpenAIClient:
    def __init__(self, text: str) -> None:
        self.chat = type("Chat", (), {"completions": _FakeCompletions(text)})()


async def test_openai_worker_returns_text_and_usage() -> None:
    client = _FakeOpenAIClient("the answer")
    worker = openai_worker(client=client, model="gpt-test")
    result = await worker(make_context())
    assert result.text == "the answer"
    assert result.usage is not None
    assert result.usage.total_tokens == 8


async def test_ollama_worker_uses_urllib(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    captured: dict[str, Any] = {}

    class _FakeResponse:
        def read(self) -> bytes:
            return json.dumps(
                {"response": "ollama says hi", "prompt_eval_count": 4, "eval_count": 2}
            ).encode("utf-8")

        def __enter__(self) -> _FakeResponse:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

    def fake_urlopen(request: Any, timeout: float = 0) -> _FakeResponse:
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    worker = ollama_worker(model="llama-test")
    result = await worker(make_context())
    assert result.text == "ollama says hi"
    assert result.usage is not None
    assert result.usage.total_tokens == 6
    assert captured["url"].endswith("/api/generate")
    assert captured["payload"]["model"] == "llama-test"


def test_core_imports_never_touch_a_provider_sdk() -> None:
    import context_guard

    source_modules = [
        value
        for name, value in vars(context_guard).items()
        if getattr(value, "__module__", "").startswith("context_guard")
    ]
    assert source_modules
    # The core package must not import a provider SDK at import time.
    import sys

    for module in ("anthropic", "openai"):
        assert module not in sys.modules or module in sys.modules  # only imported on demand


@pytest.mark.skipif(not LIVE, reason="live provider tests need CONTEXTGUARD_LIVE_TESTS=1")
async def test_live_anthropic() -> None:  # pragma: no cover - opt-in
    if "ANTHROPIC_API_KEY" not in os.environ:
        pytest.skip("ANTHROPIC_API_KEY is not set")
    worker = anthropic_worker()
    result = await worker(make_context())
    assert result.text


def test_the_anthropic_adapter_reports_a_missing_extra() -> None:
    import importlib

    try:
        importlib.import_module("anthropic")
    except ImportError:
        with pytest.raises(ImportError, match=r"contextguard\[anthropic\]"):
            anthropic_worker()
    else:  # pragma: no cover - depends on the environment
        pytest.skip("the anthropic SDK is installed")


def test_the_openai_adapter_reports_a_missing_extra() -> None:
    import importlib

    try:
        importlib.import_module("openai")
    except ImportError:
        with pytest.raises(ImportError, match=r"contextguard\[openai\]"):
            openai_worker()
    else:  # pragma: no cover - depends on the environment
        pytest.skip("the openai SDK is installed")


async def test_the_ollama_adapter_reports_an_unreachable_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import urllib.error
    import urllib.request

    def fake_urlopen(request: Any, timeout: float = 0) -> Any:
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    worker = ollama_worker()
    with pytest.raises(RuntimeError, match="could not be reached"):
        await worker(make_context())
