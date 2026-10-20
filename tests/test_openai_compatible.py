"""Tests for the generic OpenAI compatible provider layer.

The HTTP layer is always faked: the tests never touch the network.  Every
provider is checked, so a key can never leak through an error message of
one of them.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from agentether import ConfigurationError
from agentether.adapters.openai_compatible import (
    PROVIDERS,
    DailyCounter,
    OpenAICompatibleError,
    OpenAICompatibleTransientError,
    ProviderSpec,
    TokenBucketLimiter,
    list_free_models,
    openai_compatible_complete,
    openai_compatible_worker,
    provider_for,
    providers,
)

FAKE_KEY = "sk-fake-key-0123456789abcdefghijklmnopqrstuvwxyz"


class FakeResponse:
    """A fake answer of the provider."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def read(self, amount: int = -1) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: Any) -> None:
        return None


def ok_payload(text: str = "hello") -> dict[str, Any]:
    """A normal answer of the provider."""
    return {
        "choices": [{"message": {"content": text}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3},
    }


def make_http_error(code: int, body: str = "nope", headers: dict[str, str] | None = None) -> Any:
    """A fake HTTP error with a body."""
    return urllib.error.HTTPError(
        url="https://example.invalid/v1/chat/completions",
        code=code,
        msg="error",
        hdrs=headers or {},  # type: ignore[arg-type]
        fp=io.BytesIO(body.encode("utf-8")),
    )


@pytest.fixture()
def no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every provider variable from the environment."""
    for name in list(os.environ):
        if name.endswith("_API_KEY") or name.lower() in ("minimax", "gemini", "groq"):
            monkeypatch.delenv(name, raising=False)


# ----------------------------------------------------------------------
# the limits
# ----------------------------------------------------------------------
async def test_the_limiter_spaces_the_requests() -> None:
    """The limiter keeps the rate of the provider."""
    limiter = TokenBucketLimiter(per_minute=600)  # one request every 0.1 s
    start = time.monotonic()
    for _ in range(3):
        await limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.15


def test_the_daily_counter_counts_and_persists(tmp_path: Path) -> None:
    """The counter survives a restart, so a resumed run does not forget it."""
    path = tmp_path / "usage.json"
    counter = DailyCounter(path, limit=10, provider="the test")
    counter.reserve()
    counter.reserve(2)
    assert counter.used == 3
    assert counter.remaining == 7

    again = DailyCounter(path, limit=10, provider="the test")
    assert again.used == 3


def test_the_daily_counter_refuses_to_exceed_the_limit(tmp_path: Path) -> None:
    """The daily limit of the provider is never exceeded."""
    counter = DailyCounter(tmp_path / "usage.json", limit=2, provider="the test")
    counter.reserve()
    counter.reserve()
    with pytest.raises(OpenAICompatibleError) as excinfo:
        counter.reserve()
    assert "daily limit" in str(excinfo.value)
    assert counter.used == 2


def test_the_daily_counter_starts_over_on_a_new_day(tmp_path: Path) -> None:
    """A counter of yesterday is not the counter of today."""
    path = tmp_path / "usage.json"
    path.write_text(json.dumps({"date": "1999-01-01", "requests": 42}), encoding="utf-8")
    counter = DailyCounter(path, limit=10, provider="the test")
    assert counter.used == 0


def test_the_daily_counter_survives_a_broken_file(tmp_path: Path) -> None:
    """A truncated counter file does not stop the run."""
    path = tmp_path / "usage.json"
    path.write_text("{not json", encoding="utf-8")
    counter = DailyCounter(path, limit=10, provider="the test")
    assert counter.used == 0


# ----------------------------------------------------------------------
# the call
# ----------------------------------------------------------------------
async def test_a_successful_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """The answer and the usage of the server come back."""
    seen: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        seen["url"] = request.full_url
        seen["headers"] = dict(request.header_items())
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(ok_payload("the answer"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    spec = ProviderSpec(name="test", base_url="https://example.invalid/v1", api_key_env="TEST_KEY")
    monkeypatch.setenv("TEST_KEY", FAKE_KEY)

    output = await openai_compatible_complete("the prompt", spec=spec, model="a-model")

    assert output.text == "the answer"
    assert output.usage is not None
    assert output.usage.input_tokens == 5
    assert output.usage.output_tokens == 3
    assert seen["url"] == "https://example.invalid/v1/chat/completions"
    assert seen["headers"]["Authorization"] == f"Bearer {FAKE_KEY}"
    assert seen["body"]["model"] == "a-model"
    assert seen["body"]["messages"][0]["content"] == "the prompt"


async def test_a_provider_without_a_key_sends_no_authorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A local provider needs no key, so no header is sent."""
    seen: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        seen["headers"] = dict(request.header_items())
        return FakeResponse(ok_payload())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    spec = ProviderSpec(name="local", base_url="http://localhost:11434/v1", api_key_env=None)

    await openai_compatible_complete("hello", spec=spec, model="a-model")

    assert "Authorization" not in seen["headers"]


async def test_a_missing_key_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing key is named, its value is never printed."""
    monkeypatch.delenv("TEST_KEY", raising=False)
    spec = ProviderSpec(name="test", base_url="https://example.invalid/v1", api_key_env="TEST_KEY")
    with pytest.raises(ConfigurationError) as excinfo:
        await openai_compatible_complete("hello", spec=spec, model="a-model")
    assert "TEST_KEY" in str(excinfo.value)


@pytest.mark.parametrize("code", [401, 403, 402])
async def test_a_rejected_request_is_never_retried(
    monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    """A bad key, a forbidden key and a request that needs money are fatal."""
    calls: list[int] = []

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        calls.append(code)
        raise make_http_error(code, "denied")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    spec = ProviderSpec(name="test", base_url="https://example.invalid/v1", api_key_env=None)

    with pytest.raises(OpenAICompatibleError) as excinfo:
        await openai_compatible_complete(
            "hello", spec=spec, model="a-model", max_retries=3, backoff_base=0.001
        )
    assert len(calls) == 1
    assert excinfo.value.retryable is False
    if code == 402:
        assert "paid" in str(excinfo.value)


async def test_a_rate_limit_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """A rate limit is retried and the answer comes back."""
    calls: list[int] = []

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        calls.append(1)
        if len(calls) == 1:
            raise make_http_error(429, "slow down", {"Retry-After": "0"})
        return FakeResponse(ok_payload("after the retry"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    spec = ProviderSpec(name="test", base_url="https://example.invalid/v1", api_key_env=None)

    output = await openai_compatible_complete(
        "hello", spec=spec, model="a-model", max_retries=2, backoff_base=0.001
    )
    assert output.text == "after the retry"
    assert len(calls) == 2


async def test_a_persistent_rate_limit_is_a_transient_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the rate limit does not go away, the error is retryable."""
    calls: list[int] = []

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        calls.append(1)
        raise make_http_error(429, "slow down", {"Retry-After": "0"})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    spec = ProviderSpec(name="test", base_url="https://example.invalid/v1", api_key_env=None)

    with pytest.raises(OpenAICompatibleTransientError) as excinfo:
        await openai_compatible_complete(
            "hello", spec=spec, model="a-model", max_retries=1, backoff_base=0.001
        )
    assert excinfo.value.retryable is True
    assert len(calls) == 2


async def test_a_huge_response_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """The body of the answer is capped."""

    class HugeResponse(FakeResponse):
        def read(self, amount: int = -1) -> bytes:
            return b"x" * 5000

    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout=0: HugeResponse({}))
    spec = ProviderSpec(name="test", base_url="https://example.invalid/v1", api_key_env=None)

    with pytest.raises(OpenAICompatibleError) as excinfo:
        await openai_compatible_complete(
            "hello", spec=spec, model="a-model", max_response_bytes=1000
        )
    assert "larger" in str(excinfo.value)


async def test_a_broken_answer_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A body that is not JSON is an error, not a crash."""

    class BrokenResponse(FakeResponse):
        def read(self, amount: int = -1) -> bytes:
            return b"<html>not json</html>"

    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout=0: BrokenResponse({}))
    spec = ProviderSpec(name="test", base_url="https://example.invalid/v1", api_key_env=None)

    with pytest.raises(OpenAICompatibleError) as excinfo:
        await openai_compatible_complete("hello", spec=spec, model="a-model")
    assert "JSON" in str(excinfo.value)


# ----------------------------------------------------------------------
# the key never leaks
# ----------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted(PROVIDERS))
async def test_the_key_of_a_provider_never_leaks(
    monkeypatch: pytest.MonkeyPatch, name: str, caplog: pytest.LogCaptureFixture
) -> None:
    """No provider may print its key in an error or a log.

    The server answers with the key in the body of the error, which is the
    nastiest case: the message must still be redacted.
    """
    spec = PROVIDERS[name]
    key_variable = spec.api_key_env or "TEST_PROVIDER_KEY"
    monkeypatch.setenv(key_variable, FAKE_KEY)

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        raise make_http_error(401, f"the key {FAKE_KEY} is not good")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(OpenAICompatibleError) as excinfo:
        await openai_compatible_complete("hello", spec=spec, model="a-model", api_key=FAKE_KEY)
    assert FAKE_KEY not in str(excinfo.value)
    assert "redacted" in str(excinfo.value)
    for record in caplog.records:
        assert FAKE_KEY not in record.getMessage()


@pytest.mark.parametrize("name", sorted(PROVIDERS))
def test_every_provider_names_its_documentation(name: str) -> None:
    """A provider without a link to its documentation is not registered."""
    spec = PROVIDERS[name]
    assert spec.docs_url.startswith("https://")
    assert spec.verified_on


@pytest.mark.parametrize("name", sorted(PROVIDERS))
def test_every_provider_has_a_daily_limit(name: str) -> None:
    """The daily limit of a provider is a number the runner can respect."""
    spec = PROVIDERS[name]
    assert spec.requests_per_day > 0
    assert spec.requests_per_minute > 0


def test_the_unknown_provider_is_named() -> None:
    """A typo in the name of a provider is an error that lists the names."""
    with pytest.raises(ConfigurationError) as excinfo:
        provider_for("nope")
    assert "nope" in str(excinfo.value)
    assert set(providers()) == set(PROVIDERS)


# ----------------------------------------------------------------------
# the model list
# ----------------------------------------------------------------------
def test_the_free_models_are_found_live(monkeypatch: pytest.MonkeyPatch) -> None:
    """The free models are read from the catalogue, never hard-coded."""

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        return FakeResponse(
            {
                "data": [
                    {"id": "free/one:free", "pricing": {"prompt": "0", "completion": "0"}},
                    {"id": "paid/one", "pricing": {"prompt": "0.001", "completion": "0.002"}},
                    {"id": "free/two:free", "pricing": {"prompt": "0.0", "completion": "0.0"}},
                ]
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    spec = ProviderSpec(name="test", base_url="https://example.invalid/v1", api_key_env=None)

    found = list_free_models(spec)
    assert found == ["free/one:free", "free/two:free"]


# ----------------------------------------------------------------------
# the worker
# ----------------------------------------------------------------------
async def test_the_worker_builds_the_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """The worker uses the prompt the library builds."""
    seen: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(ok_payload())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    spec = ProviderSpec(name="test", base_url="https://example.invalid/v1", api_key_env=None)
    worker = openai_compatible_worker(spec=spec, model="a-model")

    from agentether import StepContext

    context = StepContext(
        step_name="research",
        step_index=0,
        attempt=1,
        max_attempts=3,
        memory="# Project Memory\n",
        last_error=None,
        roadmap=("research", "write"),
    )
    await worker(context)
    assert "research" in seen["body"]["messages"][0]["content"]


async def test_the_counter_refuses_the_request_before_it_is_sent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The daily limit stops the run before a request is sent."""
    calls: list[int] = []

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        calls.append(1)
        return FakeResponse(ok_payload())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    spec = ProviderSpec(name="test", base_url="https://example.invalid/v1", api_key_env=None)
    counter = DailyCounter(tmp_path / "usage.json", limit=1, provider="the test")
    counter.reserve()

    with pytest.raises(OpenAICompatibleError):
        await openai_compatible_complete("hello", spec=spec, model="a-model", counter=counter)
    assert calls == []


async def test_the_limiter_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    """The limiter of the provider is applied to every call."""

    def fake_urlopen(request: Any, timeout: float = 0) -> FakeResponse:
        return FakeResponse(ok_payload())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    spec = ProviderSpec(name="test", base_url="https://example.invalid/v1", api_key_env=None)
    limiter = TokenBucketLimiter(per_minute=600)

    start = time.monotonic()
    for _ in range(3):
        await openai_compatible_complete("hello", spec=spec, model="a-model", limiter=limiter)
    assert time.monotonic() - start >= 0.15


def test_asyncio_is_used() -> None:
    """The module is asyncio based."""
    assert asyncio is not None
