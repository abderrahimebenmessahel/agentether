"""Event hooks and the append-only event log.

Two things live here:

* :class:`EventBus` -- in-process callbacks (``orch.on(event, callback)``).
  Callbacks may be synchronous or asynchronous and their exceptions are
  logged, never propagated: an observer must not be able to break a run.
* :class:`EventLog` -- the append-only ``events.jsonl`` file in the memory
  directory.  One JSON object per line, with a monotonic sequence number and
  an ISO-8601 UTC timestamp.  The file is rotated when it grows past a
  configurable size, keeping one previous file.

.. versionadded:: 0.2.0
"""

from __future__ import annotations

import inspect
import json
import logging
import os
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Literal

__all__ = ["EVENT_NAMES", "EventBus", "EventLog", "EventName"]

logger = logging.getLogger("agentether")

#: Every event the orchestrator emits.
EVENT_NAMES: tuple[str, ...] = (
    "attempt_started",
    "attempt_failed",
    "step_completed",
    "breaker_opened",
    "loop_detected",
    "budget_exceeded",
    "verification_failed",
)

EventName = Literal[
    "attempt_started",
    "attempt_failed",
    "step_completed",
    "breaker_opened",
    "loop_detected",
    "budget_exceeded",
    "verification_failed",
]


class EventBus:
    """Fan-out of supervisor events to user callbacks.

    Attributes:
        enabled: When false, ``emit`` is a no-op.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._callbacks: dict[str, list[Callable[[dict[str, Any]], Any]]] = {}

    def on(self, event: str, callback: Callable[[dict[str, Any]], Any]) -> None:
        """Register ``callback`` for ``event``.

        The callback receives a single dict with the event payload.  It may be
        synchronous or asynchronous.

        Raises:
            ValueError: If ``event`` is not a known event name.
        """
        if event not in EVENT_NAMES:
            raise ValueError(f"unknown event {event!r}; known events: {', '.join(EVENT_NAMES)}")
        self._callbacks.setdefault(event, []).append(callback)

    def listeners(self, event: str) -> int:
        """Return how many callbacks are registered for ``event``."""
        return len(self._callbacks.get(event, ()))

    async def emit(self, event: str, payload: Mapping[str, Any] | None = None) -> None:
        """Emit an event to every registered callback.

        The callback receives a copy of ``payload`` (the full event record).

        Exceptions raised by a callback are logged and swallowed.
        """
        if not self.enabled:
            return
        body = dict(payload or {})
        for callback in self._callbacks.get(event, ()):
            try:
                outcome = callback(dict(body))
                if inspect.isawaitable(outcome):
                    await outcome
            except Exception as exc:
                logger.warning(
                    "Supervisor: event callback for '%s' raised %s: %s",
                    event,
                    type(exc).__name__,
                    exc,
                )


class EventLog:
    """Append-only JSON-lines event log with size based rotation.

    Attributes:
        directory: Where ``events.jsonl`` is written.
        max_bytes: Rotate when the file would grow past this size.
        enabled: When false, nothing is written.
    """

    def __init__(
        self,
        directory: str | os.PathLike[str],
        max_bytes: int = 5 * 1024 * 1024,
        enabled: bool = True,
    ) -> None:
        self.directory = Path(directory)
        self.max_bytes = int(max_bytes)
        self.enabled = enabled
        self._sequence = self._last_sequence()

    @property
    def path(self) -> Path:
        """Path of the current event file."""
        return self.directory / "events.jsonl"

    @property
    def rotated_path(self) -> Path:
        """Path of the previous event file."""
        return self.directory / "events.jsonl.1"

    def _last_sequence(self) -> int:
        """Continue the sequence numbering of an existing log."""
        highest = 0
        for candidate in (self.path, self.rotated_path):
            try:
                if not candidate.exists():
                    continue
                with candidate.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        seq = record.get("seq")
                        if isinstance(seq, int) and seq > highest:
                            highest = seq
            except OSError:  # pragma: no cover - unreadable log
                continue
        return highest

    def append(self, event: str, **payload: Any) -> dict[str, Any]:
        """Append one event and return the record that was written."""
        self._sequence += 1
        record: dict[str, Any] = {
            "seq": self._sequence,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z",
            "event": event,
        }
        record.update(payload)
        if not self.enabled:
            return record
        line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
        self._rotate_if_needed(len(line.encode("utf-8")))
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError as exc:  # pragma: no cover - unwritable directory
            logger.warning("Supervisor: could not write the event log: %s", exc)
        return record

    def _rotate_if_needed(self, incoming: int) -> None:
        """Rotate the log when the new line would push it past the limit."""
        if self.max_bytes <= 0:
            return
        try:
            current = self.path.stat().st_size if self.path.exists() else 0
        except OSError:  # pragma: no cover - unreadable file
            return
        if current + incoming <= self.max_bytes:
            return
        try:
            if self.rotated_path.exists():
                self.rotated_path.unlink()
            if self.path.exists():
                os.replace(self.path, self.rotated_path)
        except OSError as exc:  # pragma: no cover - racing with another writer
            logger.warning("Supervisor: could not rotate the event log: %s", exc)
