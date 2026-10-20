"""Tests for the OpenRouter adapter.

The HTTP layer is always faked: the tests never touch the network.  The API
key is a fake string, and one of the tests asserts that it never appears in
an exception message or in a log record.
"""

from __future__ import annotations

import io
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

import pytest

from agentether import ConfigurationError, StepContext, WorkerOutput
from agentether.adapters import openrouter_worker
from agentether.adapters.openrouter import (
    OpenRouterError,
    OpenRouterTransientError,
    resolve_api_key,
)

FAKE_KEY = "sk-or-v1-FAKE-KEY-0123456789abcdefghijklmnopqrstuvwxyz"

#: The names the adapter may look at.  The tests remove every one of them
#: from the environment, so a real key on the machine is never read.
CANDIDATE_NAMES = ("minimax", "minimax_api_key", "openrouter_api_key")


@pytest.fixture()
def fake_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Install a fake key and remove every real one from the environment."""
    for name in list(os.environ):
        if name.lower() in CANDIDATE_NAMES:
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MINIMAX_API_KEY", FAKE_KEY)
    return FAKE_KEY


@pytest.fixture()
def no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every candidate variable from the environment."""
    for name in list(os.environ):
        if name.lower() in CANDIDATE_NAMES:
            monkeypatch.delenv(name, raising=False)


def make_context() -> StepContext:
    """A minimal step context for the adapter."""
    return StepContext(
        step_name="research",
        step_index=0,
        attempt=1,
        max_attempts=3,
        memory="# Project Memory\n",
        last_error=None,
        roadmap=("research",),
    )


class FakeResponse:
    """A minimal stand-in for an ``http.client.HTTPResponse``."""

    def __init__(self, payload: dict[str, Any], status: int = 200) -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self.status = status
        self.headers: dict[str, str] = {}

    def read(self, amount: int = -1) -> bytes:
        if amount is None or amount < 0:
            return self._body
        return self._body[:amount]

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: Any) -> None:
        return None


def ok_payload(text: str = "hello", usage: dict[str, Any] | None = None) -> dict[str, Any]:
    """A successful chat completion body."""
    body: dict[str, Any] = {"choices": [{"message": {"role": "assistant", "content": text}}]}
    if usage is not None:
        body["usage"] = usage
    return body


def make_http_error(
    code: int, body: str = "{}", headers: dict[str, str] | None = None
) -> urllib.error.HTTPError:
    """Build an ``HTTPError`` with a readable body and headers."""
    return urllib.error.HTTPError(
        url="https://openrouter.ai/api/v1/chat/completions",
        code=code,
        msg="error",
        hdrs=headers or {},  # type: ignore[arg-type]
        fp=io.BytesIO(body.encode("utf-8")),
    )


def test_the_key_is_read_from_the_environment(fake_key: str) -> None:
    assert resolve_api_key() == FAKE_KEY
    assert resolve_api_key("MINIMAX_API_KEY") == FAKE_KEY


def test_the_key_is_found_case_insensitively(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.lower() in CANDIDATE_NAMES:
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MiNiMaX", FAKE_KEY)
    assert resolve_api_key() == FAKE_KEY


def test_a_missing_key_names_the_variables_and_never_a_value(
    no_key: None,
) -> None:
    with pytest.raises(ConfigurationError) as excinfo:
        resolve_api_key()
    message = str(excinfo.value)
    assert "MINIMAX" in message
    assert "OPENROUTER_API_KEY" in message
    assert FAKE_KEY not in message


def test_a_named_variable_that_is_empty_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENTETHER_TEST_KEY", raising=False)
    with pytest.raises(ConfigurationError):
        resolve_api_key("AGENTETHER_TEST_KEY")


async def test_a_successful_call(monkeypatch: pytest.MonkeyPatch, fake_key: str) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        captured["url"] = request.full_url
        # urllib capitalises the header names, so compare them lower cased.
        captured["headers"] = {k.lower(): v for k, v in request.headers.items()}
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse(ok_payload("the answer", {"prompt_tokens": 11, "completion_tokens": 7}))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    worker = openrouter_worker(model="test/model", backoff_base=0.01)
    result = await worker(make_context())

    assert isinstance(result, WorkerOutput)
    assert result.text == "the answer"
    assert result.usage is not None
    assert result.usage.input_tokens == 11
    assert result.usage.output_tokens == 7
    assert result.usage.cost is None
    assert captured["body"]["model"] == "test/model"
    assert captured["headers"]["authorization"] == f"Bearer {FAKE_KEY}"
    # The optional headers are off by default.
    assert "http-referer" not in captured["headers"]
    assert "x-title" not in captured["headers"]


async def test_the_optional_headers_are_sent(
    monkeypatch: pytest.MonkeyPatch, fake_key: str
) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        captured["headers"] = {k.lower(): v for k, v in request.headers.items()}
        return FakeResponse(ok_payload())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    worker = openrouter_worker(referer="https://example.invalid", title="AgenTether")
    await worker(make_context())
    assert captured["headers"]["http-referer"] == "https://example.invalid"
    assert captured["headers"]["x-title"] == "AgenTether"


async def test_missing_usage_is_tolerated(monkeypatch: pytest.MonkeyPatch, fake_key: str) -> None:
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda request, timeout=0: FakeResponse(ok_payload("x"))
    )
    worker = openrouter_worker()
    result = await worker(make_context())
    assert result.usage is not None
    assert result.usage.total_tokens == 0


async def test_a_rate_limit_is_retried_and_then_succeeds(
    monkeypatch: pytest.MonkeyPatch, fake_key: str
) -> None:
    calls: list[int] = []

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        calls.append(1)
        if len(calls) == 1:
            raise make_http_error(429, "slow down", {"Retry-After": "0"})
        return FakeResponse(ok_payload("after the retry"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    worker = openrouter_worker(backoff_base=0.01, backoff_max=0.05)
    result = await worker(make_context())
    assert result.text == "after the retry"
    assert len(calls) == 2


async def test_a_persistent_rate_limit_raises_a_retryable_error(
    monkeypatch: pytest.MonkeyPatch, fake_key: str
) -> None:

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        raise make_http_error(429, "slow down", {"Retry-After": "0"})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    worker = openrouter_worker(max_retries=1, backoff_base=0.01, backoff_max=0.05)
    with pytest.raises(OpenRouterTransientError) as excinfo:
        await worker(make_context())
    assert excinfo.value.retryable is True
    assert FAKE_KEY not in str(excinfo.value)


async def test_a_rejected_key_is_never_retried(
    monkeypatch: pytest.MonkeyPatch, fake_key: str
) -> None:
    calls: list[int] = []

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        calls.append(1)
        raise make_http_error(401, "no dice")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    worker = openrouter_worker(max_retries=3, backoff_base=0.01)
    with pytest.raises(OpenRouterError) as excinfo:
        await worker(make_context())
    assert excinfo.value.retryable is False
    assert len(calls) == 1, "a rejected key must not be retried"
    assert FAKE_KEY not in str(excinfo.value)


async def test_a_forbidden_key_is_never_retried(
    monkeypatch: pytest.MonkeyPatch, fake_key: str
) -> None:
    calls: list[int] = []

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        calls.append(1)
        raise make_http_error(403, "forbidden")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    worker = openrouter_worker(max_retries=3, backoff_base=0.01)
    with pytest.raises(OpenRouterError):
        await worker(make_context())
    assert len(calls) == 1


async def test_a_malformed_answer_is_an_error(
    monkeypatch: pytest.MonkeyPatch, fake_key: str
) -> None:

    class BrokenResponse(FakeResponse):
        def read(self, amount: int = -1) -> bytes:
            return b"not json at all"

    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout=0: BrokenResponse({}))
    worker = openrouter_worker()
    with pytest.raises(OpenRouterError) as excinfo:
        await worker(make_context())
    assert "JSON" in str(excinfo.value)


async def test_an_answer_without_choices_is_an_error(
    monkeypatch: pytest.MonkeyPatch, fake_key: str
) -> None:
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda request, timeout=0: FakeResponse({"choices": []}),
    )
    worker = openrouter_worker()
    with pytest.raises(OpenRouterError):
        await worker(make_context())


async def test_the_key_never_appears_in_an_exception_or_a_log(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, fake_key: str
) -> None:

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        # The server echoes the key back -- it must still not leak.
        raise make_http_error(400, f"the key {FAKE_KEY} is not acceptable")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    worker = openrouter_worker()
    with (
        caplog.at_level(logging.DEBUG, logger="agentether"),
        pytest.raises(OpenRouterError) as excinfo,
    ):
        await worker(make_context())
    assert FAKE_KEY not in str(excinfo.value)
    assert "redacted" in str(excinfo.value)
    for record in caplog.records:
        assert FAKE_KEY not in record.getMessage()


async def test_a_huge_response_is_refused(monkeypatch: pytest.MonkeyPatch, fake_key: str) -> None:

    class HugeResponse(FakeResponse):
        def read(self, amount: int = -1) -> bytes:
            return b"x" * 5000

    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout=0: HugeResponse({}))
    worker = openrouter_worker(max_response_bytes=1000)
    with pytest.raises(OpenRouterError) as excinfo:
        await worker(make_context())
    assert "larger" in str(excinfo.value)


@pytest.mark.skipif(
    os.environ.get("AGENTETHER_LIVE_TESTS") != "1",
    reason="live provider tests need AGENTETHER_LIVE_TESTS=1",
)
async def test_live_openrouter() -> None:  # pragma: no cover - opt-in
    worker = openrouter_worker()
    result = await worker(make_context())
    assert result.text
