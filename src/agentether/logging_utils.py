"""Logging helpers.

AgenTether is a library: it must never install handlers on import, because
that would hijack the logging configuration of the application embedding it.
Importing this module only attaches a :class:`logging.NullHandler` so that
``logging.getLogger("agentether")`` never complains about missing handlers.
"""

from __future__ import annotations

import logging
import os
import sys

__all__ = ["LOGGER_NAME", "ColorFormatter", "configure_logging", "logger"]

#: The name of the library logger.
LOGGER_NAME = "agentether"

logger = logging.getLogger(LOGGER_NAME)
# A library must not configure logging, but it should not warn either.
logger.addHandler(logging.NullHandler())


class ColorFormatter(logging.Formatter):
    """A formatter that paints log records according to their level.

    Colours are disabled automatically when stderr is not a TTY or when the
    ``NO_COLOR`` environment variable is set, so piped or redirected output
    stays clean.
    """

    RESET = "\033[0m"
    COLORS: dict[int, str] = {
        logging.DEBUG: "\033[90m",  # bright black / grey
        logging.INFO: "\033[32m",  # green
        logging.WARNING: "\033[33m",  # yellow
        logging.ERROR: "\033[31m",  # red
        logging.CRITICAL: "\033[1;31m",  # bold red
    }

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        color: bool | None = None,
    ) -> None:
        super().__init__(fmt or "%(message)s", datefmt)
        self.color = self._should_use_color(color)

    @staticmethod
    def _should_use_color(color: bool | None) -> bool:
        if color is not None:
            return color
        if os.environ.get("NO_COLOR"):
            return False
        try:
            return bool(sys.stderr.isatty())
        except (AttributeError, ValueError):  # pragma: no cover - closed stream
            return False

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        if not self.color:
            return message
        color = self.COLORS.get(record.levelno, "")
        if not color:
            return message
        return f"{color}{message}{self.RESET}"


def configure_logging(level: int = logging.INFO, color: bool | None = None) -> logging.Logger:
    """Attach a coloured stderr handler to the library logger.

    This is an explicit opt-in convenience for scripts and examples.  Calling
    it twice does not duplicate handlers.

    Args:
        level: Logging level for the library logger.
        color: Force colours on or off.  ``None`` auto-detects.

    Returns:
        The configured library logger.
    """
    if not any(getattr(handler, "_agentether_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(ColorFormatter(color=color))
        handler._agentether_handler = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
