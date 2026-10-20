"""Tests for the configuration objects."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable

import pytest

from context_guard import (
    AgentExecutionError,
    AgentTimeoutError,
    BreakerPolicy,
    BudgetPolicy,
    ConfigurationError,
    ContextDriftError,
    GuardPolicy,
    LoopPolicy,
    RetryPolicy,
    StallPolicy,
    TelemetryParseError,
    VerificationFailedError,
)
from context_guard.policy import DEFAULT_NO_RETRY_ON, DEFAULT_RETRY_ON


def test_the_defaults_are_documented() -> None:
    policy = GuardPolicy()
    assert policy.strict_order is True
    assert policy.strict_next_step is False
    assert policy.resume is True
    assert policy.verification_enabled is True
    assert policy.verify_timeout_seconds == 30.0
    assert policy.store_raw_outputs is False
    assert policy.events_enabled is True
    assert policy.events_max_bytes == 5 * 1024 * 1024
    assert policy.loop.similarity_threshold == 0.9
    assert policy.loop.repeat_window == 3
    assert policy.stall.stall_window == 3
    assert policy.breaker.cooldown_seconds is None
    assert policy.retry.max_attempts == 3
    assert policy.retry.backoff_base == 1.0
    assert policy.retry.backoff_max == 30.0


def test_the_default_retry_set() -> None:
    assert AgentTimeoutError in DEFAULT_RETRY_ON
    assert TelemetryParseError in DEFAULT_RETRY_ON
    assert ContextDriftError in DEFAULT_RETRY_ON
    assert AgentExecutionError in DEFAULT_RETRY_ON
    assert VerificationFailedError in DEFAULT_RETRY_ON
    assert ConfigurationError in DEFAULT_NO_RETRY_ON


def _set_attribute(obj: object, name: str, value: object) -> None:
    """Set an attribute without the type checker knowing the attribute."""
    setattr(obj, name, value)


def test_the_policy_is_frozen() -> None:
    policy = GuardPolicy()
    with pytest.raises(dataclasses.FrozenInstanceError):
        _set_attribute(policy, "verification_enabled", False)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: LoopPolicy(similarity_threshold=0.0),
        lambda: LoopPolicy(similarity_threshold=1.5),
        lambda: LoopPolicy(repeat_window=1),
        lambda: LoopPolicy(max_retries_after_detection=-1),
        lambda: StallPolicy(stall_window=1),
        lambda: BudgetPolicy(max_total_seconds=0),
        lambda: BudgetPolicy(max_total_tokens=-1),
        lambda: RetryPolicy(max_attempts=0),
        lambda: RetryPolicy(backoff_base=-1),
        lambda: RetryPolicy(backoff_max=0),
        lambda: BreakerPolicy(cooldown_seconds=-1),
    ],
)
def test_invalid_policies_are_rejected(factory: Callable[[], object]) -> None:
    with pytest.raises(ConfigurationError):
        factory()


def test_the_retry_classification() -> None:
    policy = RetryPolicy()
    assert policy.is_retryable(AgentTimeoutError("step", 1.0)) is True
    assert policy.is_retryable(ConfigurationError("bad")) is False

    policy = RetryPolicy(retry_on=(ValueError,), no_retry_on=(KeyError,))
    assert policy.is_retryable(ValueError("boom")) is True
    assert policy.is_retryable(KeyError("boom")) is False
    assert policy.is_retryable(TypeError("boom")) is False
