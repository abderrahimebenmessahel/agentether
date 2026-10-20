"""Tests for the logging helpers."""

from __future__ import annotations

import logging
import os

import pytest

from context_guard import ColorFormatter, configure_logging
from context_guard.logging_utils import LOGGER_NAME, logger


def make_record(message: str, level: int = logging.INFO) -> logging.LogRecord:
    """Build a log record for the formatter."""
    return logging.LogRecord(LOGGER_NAME, level, __file__, 1, message, None, None)


def test_the_library_logger_only_has_a_null_handler_on_import() -> None:
    # The library must not configure logging on import.
    assert any(isinstance(handler, logging.NullHandler) for handler in logger.handlers)


def test_the_formatter_uses_the_message_only() -> None:
    formatter = ColorFormatter(color=False)
    assert formatter.format(make_record("Supervisor: hello")) == "Supervisor: hello"


def test_the_formatter_paints_by_level() -> None:
    formatter = ColorFormatter(color=True)
    painted = formatter.format(make_record("hello", logging.WARNING))
    assert painted.startswith("\033[33m")
    assert painted.endswith("\033[0m")


def test_the_formatter_disables_the_colour_without_a_tty() -> None:
    formatter = ColorFormatter()
    assert formatter.color is False  # pytest captures stderr, so it is not a tty


def test_no_color_environment_variable_disables_the_colour(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    formatter = ColorFormatter()
    assert formatter.color is False


def test_an_explicit_colour_choice_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    assert ColorFormatter(color=True).color is True


def test_configure_logging_adds_one_handler() -> None:
    before = len(logger.handlers)
    try:
        configure_logging(level=logging.DEBUG)
        configure_logging(level=logging.DEBUG)
        assert len(logger.handlers) == before + 1
        assert logger.level == logging.DEBUG
    finally:
        for handler in list(logger.handlers):
            if getattr(handler, "_context_guard_handler", False):
                logger.removeHandler(handler)
        logger.setLevel(logging.NOTSET)


def test_the_critical_colour_is_bold_red() -> None:
    formatter = ColorFormatter(color=True)
    painted = formatter.format(make_record("boom", logging.CRITICAL))
    assert painted.startswith("\033[1;31m")


def test_the_debug_colour_is_grey() -> None:
    formatter = ColorFormatter(color=True)
    painted = formatter.format(make_record("details", logging.DEBUG))
    assert painted.startswith("\033[90m")


def test_an_unknown_level_is_not_painted() -> None:
    formatter = ColorFormatter(color=True)
    record = make_record("custom", 25)
    assert formatter.format(record) == "custom"


def test_the_environment_variable_is_read_at_call_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert ColorFormatter(color=None).color is False
    monkeypatch.setenv("NO_COLOR", "1")
    assert ColorFormatter(color=None).color is False
    assert os.environ.get("NO_COLOR") == "1"
