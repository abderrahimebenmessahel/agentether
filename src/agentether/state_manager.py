"""Durable project memory.

The control path of AgenTether lives on disk, not in the agent's context
window.  ``PROJECT_MEMORY.md`` is a human readable Markdown file that also
carries a machine readable JSON block, so a human can read the plan while the
supervisor can read the state.

The file has two owners:

* the **library** owns the title, the roadmap checklist, the completed step
  summaries, the "needs human input" notes, the verification summary and the
  machine readable state block;
* the **human** owns everything between
  ``<!-- agentether:human:start -->`` and ``<!-- agentether:human:end -->``.
  That text is preserved byte for byte across every write and every
  migration, and it is injected into the agent's context with the highest
  priority.

Concurrency scope: **single process only.**  Writers are serialised with an
:class:`asyncio.Lock` inside one process.  There is deliberately no
cross-process locking (no ``fcntl``, no ``msvcrt``, no lock files): two
orchestrators must not share a memory directory.  Give each orchestrator its
own directory instead.

.. versionchanged:: 0.2.0
    Schema version 2: human owned section, attempt log, token aware
    compaction and an automatic migration from schema version 1.
"""

from __future__ import annotations

import asyncio
import contextlib
import copy
import errno
import hashlib
import json
import os
import re
import tempfile
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .exceptions import StateCorruptionError
from .logging_utils import logger
from .models import Telemetry
from .policy import approximate_token_count

__all__ = [
    "HUMAN_END_MARKER",
    "HUMAN_START_MARKER",
    "MEMORY_FILENAME",
    "SCHEMA_VERSION",
    "STATE_MARKER",
    "StateManager",
    "slugify",
]

#: Name of the main memory file inside the memory directory.
MEMORY_FILENAME = "PROJECT_MEMORY.md"

#: Version of the on-disk state schema.
SCHEMA_VERSION = 2

#: Marker that introduces the machine readable block in the memory file.
STATE_MARKER = "<!-- agentether:state -->"

#: Markers that delimit the human owned section.
HUMAN_START_MARKER = "<!-- agentether:human:start -->"
HUMAN_END_MARKER = "<!-- agentether:human:end -->"

#: The markers of the previous name.  They are still *read*, so a memory
#: file written by ContextGuard 0.2 keeps working; they are never written
#: again.
LEGACY_STATE_MARKER = "<!-- contextguard:state -->"
LEGACY_HUMAN_START_MARKER = "<!-- contextguard:human:start -->"
LEGACY_HUMAN_END_MARKER = "<!-- contextguard:human:end -->"

#: Sub directory that holds the raw output of each step.
STEPS_DIRNAME = "steps"

#: Temporary files older than this are considered leftovers of a crashed run.
STALE_TMP_SECONDS = 3600

#: How many attempt records are kept in the state file (the full log stays
#: in ``steps/*.attempts.jsonl``).
MAX_ATTEMPTS_IN_STATE = 20

#: The machine block is located by the *last* marker that stands on its own
#: line, so a marker smuggled into a JSON string cannot be mistaken for it.
#: A carriage return is allowed at the end of the line: a human may edit the
#: file with an editor that writes CRLF line endings.
_STATE_MARKER_RE = re.compile(r"(?m)^" + re.escape(STATE_MARKER) + r"[ \t\r]*$")
_LEGACY_STATE_MARKER_RE = re.compile(r"(?m)^" + re.escape(LEGACY_STATE_MARKER) + r"[ \t\r]*$")
_FENCE_OPEN = "```json"


def escape_embedded(text: str) -> str:
    """Neutralise markup markers in text that is written into the memory file.

    The agent controls the summary, the step names, the artifact paths and
    the failure reasons.  None of them may ever contain a literal
    ``<!--``, because that is what the library uses to find its own markers.

    The ampersand is escaped first, so the escaping is injective: a summary
    that already contains the text ``&lt;!--`` survives the round trip byte
    for byte.  The text is escaped on write and unescaped on read, so the
    state that is read back is the state that was written.
    """
    return text.replace("&", "&amp;").replace("<!--", "&lt;!--")


def unescape_embedded(text: str) -> str:
    """Undo :func:`escape_embedded`.

    The order is the reverse of the escaping, and it is what makes the round
    trip lossless.
    """
    return text.replace("&lt;!--", "<!--").replace("&amp;", "&")


def _escape_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of ``state`` with every untrusted string escaped."""
    copy_state = copy.deepcopy(dict(state))
    _transform_untrusted(copy_state, escape_embedded)
    return copy_state


def _transform_untrusted(state: dict[str, Any], transform: Callable[[str], str]) -> None:
    """Apply ``transform`` to every untrusted string in the state, in place.

    Untrusted means: written by the model (the telemetry of a step, the
    artifact paths, the reason a step is blocked) or derived from it.
    """
    telemetry = state.get("telemetry")
    if isinstance(telemetry, dict):
        for record in telemetry.values():
            if not isinstance(record, dict):
                continue
            for key in ("step", "summary"):
                value = record.get(key)
                if isinstance(value, str):
                    record[key] = transform(value)
            artifacts = record.get("artifacts")
            if isinstance(artifacts, list):
                record["artifacts"] = [
                    transform(item) if isinstance(item, str) else item for item in artifacts
                ]
    needs_human = state.get("needs_human")
    if isinstance(needs_human, dict):
        for name, reason in needs_human.items():
            if isinstance(reason, str):
                needs_human[name] = transform(reason)
    verifications = state.get("verifications")
    if isinstance(verifications, dict):
        for record in verifications.values():
            if isinstance(record, dict) and isinstance(record.get("reason"), str):
                record["reason"] = transform(record["reason"])
    failure = state.get("last_failure")
    if isinstance(failure, dict) and isinstance(failure.get("reason"), str):
        failure["reason"] = transform(failure["reason"])


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def slugify(name: str, max_length: int = 48) -> str:
    """Turn a step name into a safe file name component.

    Only ``[a-z0-9-]`` survives, so path separators, ``..`` and other
    traversal attempts are neutralised::

        >>> slugify("../../etc/passwd")
        'etc-passwd'
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    slug = slug[:max_length].strip("-")
    return slug or "step"


def sha256_text(text: str) -> str:
    """Return the hex SHA-256 digest of ``text``."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class StateManager:
    """Reads and writes the durable project memory.

    Args:
        memory_dir: Directory that holds ``PROJECT_MEMORY.md`` and ``steps/``.
            It is created if it does not exist.
        max_memory_chars: Maximum size of the memory string that is injected
            into a prompt.  **This counts characters, not tokens** -- it is an
            approximation.  Kept for backwards compatibility.
        max_memory_tokens: Maximum size of the injected memory measured in
            tokens.  When set it **takes precedence** over
            ``max_memory_chars``.
        token_counter: Callable that counts the tokens of a text.  Defaults to
            a character heuristic (roughly four characters per token).

    All file I/O is executed in a worker thread so the event loop is never
    blocked.
    """

    def __init__(
        self,
        memory_dir: str | os.PathLike[str],
        max_memory_chars: int = 12_000,
        max_memory_tokens: int | None = None,
        token_counter: Callable[[str], int] = approximate_token_count,
    ) -> None:
        self._dir = Path(memory_dir)
        self._max_memory_chars = int(max_memory_chars)
        self._max_memory_tokens = int(max_memory_tokens) if max_memory_tokens else None
        self._token_counter = token_counter
        if self._max_memory_chars < 0:
            raise ValueError("max_memory_chars must not be negative")
        self._roadmap: list[str] = []
        self._state: dict[str, Any] = self._fresh_state()
        self._human_text: str = ""
        self._lock: asyncio.Lock | None = None
        self._lock_loop: asyncio.AbstractEventLoop | None = None
        # Cheap one-time setup.  The heavy lifting happens in worker threads.
        self._dir.mkdir(parents=True, exist_ok=True)
        self._prune_stale_temp_files()

    # ------------------------------------------------------------------
    # paths
    # ------------------------------------------------------------------
    @property
    def memory_dir(self) -> Path:
        """The directory that holds the project memory."""
        return self._dir

    @property
    def memory_path(self) -> Path:
        """Path of the main memory file."""
        return self._dir / MEMORY_FILENAME

    @property
    def max_memory_chars(self) -> int:
        """Maximum number of characters of memory injected into a prompt."""
        return self._max_memory_chars

    @property
    def max_memory_tokens(self) -> int | None:
        """Maximum number of tokens of memory injected into a prompt."""
        return self._max_memory_tokens

    @property
    def human_text(self) -> str:
        """The human owned part of the memory, verbatim."""
        return self._human_text

    def set_roadmap(self, roadmap: tuple[str, ...] | list[str]) -> None:
        """Record the roadmap used to render the checklist (in memory only)."""
        self._roadmap = [str(name) for name in roadmap]

    # ------------------------------------------------------------------
    # locking
    # ------------------------------------------------------------------
    def _get_lock(self) -> asyncio.Lock:
        """Return the write lock, (re)creating it for the running loop.

        A lock is bound to the event loop that first awaits it.  Recreating it
        when the loop changes keeps the manager usable across loops (for
        example between two pytest-asyncio tests) without leaking state.
        """
        loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not loop:
            self._lock = asyncio.Lock()
            self._lock_loop = loop
        return self._lock

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    async def load(self) -> dict[str, Any]:
        """Read the current state from disk.

        Returns a fresh state when the memory file does not exist yet.  A
        schema version 1 file is migrated automatically (a ``.bak`` copy of
        the old file is written first).

        Raises:
            StateCorruptionError: If the file exists but its state block is
                missing or malformed.  The state is never silently reset.
        """
        async with self._get_lock():
            return await asyncio.to_thread(self._load_sync)

    async def record_step(
        self,
        step_name: str,
        telemetry: Telemetry,
        raw_output: str,
    ) -> None:
        """Persist the outcome of a step and its raw output.

        The step is added to ``completed_steps`` only when the telemetry
        reports ``status == "completed"``; otherwise the failure reason is
        stored in ``last_failure`` and the step is listed under
        ``needs_human``.
        """
        async with self._get_lock():
            await asyncio.to_thread(self._record_step_sync, step_name, telemetry, raw_output)

    async def append_attempt(
        self,
        step_name: str,
        attempt: int,
        outcome: str,
        error: str | None = None,
        output: str = "",
        store_raw: bool = False,
        usage: Mapping[str, Any] | None = None,
        budget: Mapping[str, Any] | None = None,
    ) -> None:
        """Append one attempt record to the per-step attempt log.

        The record contains the timestamp, the attempt number, the outcome
        kind, the error message, the length of the output and its SHA-256
        digest.  The full output is only stored when ``store_raw`` is true.
        """
        async with self._get_lock():
            await asyncio.to_thread(
                self._append_attempt_sync,
                step_name,
                attempt,
                outcome,
                error,
                output,
                store_raw,
                dict(usage) if usage else None,
                dict(budget) if budget else None,
            )

    async def set_breaker(
        self,
        open: bool,
        reason: str,
        *,
        step: str | None = None,
        attempts: int = 0,
        last_error: str | None = None,
        opened_at: float | None = None,
    ) -> None:
        """Persist the circuit breaker state.

        The breaker is part of the persisted state on purpose: it has to
        survive a process restart, otherwise a restarting agent would happily
        loop forever.
        """
        async with self._get_lock():
            await asyncio.to_thread(
                self._set_breaker_sync, open, reason, step, attempts, last_error, opened_at
            )

    async def record_budget_exceeded(
        self,
        step_name: str,
        kind: str,
        limit: float,
        used: float,
    ) -> None:
        """Persist the reason a budget was exhausted.

        The project stays resumable: the completed steps are kept, only the
        reason is recorded.
        """
        async with self._get_lock():
            await asyncio.to_thread(self._record_budget_exceeded_sync, step_name, kind, limit, used)

    async def set_verification(
        self,
        step_name: str,
        ok: bool,
        reason: str = "",
        evidence: Mapping[str, Any] | None = None,
    ) -> None:
        """Persist the outcome of the last verification of a step."""
        async with self._get_lock():
            await asyncio.to_thread(
                self._set_verification_sync, step_name, ok, reason, dict(evidence or {})
            )

    async def reset(self) -> None:
        """Clear the state back to a fresh project.

        The roadmap and the human owned section are kept, completed steps,
        telemetry, the breaker and the recorded raw outputs are removed.
        """
        async with self._get_lock():
            await asyncio.to_thread(self._reset_sync)

    def render_context(self, state: Mapping[str, Any]) -> str:
        """Render the memory that is injected into a prompt.

        The result is compacted to ``max_memory_tokens`` when that is set,
        otherwise to ``max_memory_chars``.  The header, the roadmap checklist
        and the human owned section are always kept, the most recent steps
        are kept in full and older steps collapse to a single line each.  A
        step section is never cut in the middle.
        """
        header = self._render_header(state)
        human = self._human_text.strip()
        human_block = ""
        if human:
            human_block = f"## Notes from the human\n\n{human}\n\n"

        entries = self._step_entries(state)
        full_sections = [self._render_full_step(name, summary) for name, summary in entries]
        budget = self._budget()

        def measure(text: str) -> int:
            return self._measure(text)

        if measure(header + human_block) > budget:
            # The human section alone does not fit: truncate it visibly and
            # say so, rather than silently dropping human instructions.
            human_block = self._truncate_human(human_block, budget, measure)
            logger.warning("Supervisor: the human section was truncated to fit the memory budget")

        if measure(header + human_block + "".join(full_sections)) <= budget:
            return header + human_block + "".join(full_sections)

        # Keep as many of the most recent steps in full as the budget allows.
        for keep in range(len(entries) - 1, -1, -1):
            collapsed = [
                self._render_collapsed_step(name, summary, 80)
                for name, summary in entries[: len(entries) - keep]
            ]
            tail = "".join(full_sections[len(entries) - keep :])
            candidate = header + human_block + "".join(collapsed) + tail
            if measure(candidate) <= budget:
                return candidate

        # Still too long: shorten the collapsed lines, then drop the oldest.
        for width in (40, 20, 0):
            collapsed = [
                self._render_collapsed_step(name, summary, width) for name, summary in entries
            ]
            candidate = header + human_block + "".join(collapsed)
            if measure(candidate) <= budget:
                return candidate

        collapsed = [self._render_collapsed_step(name, summary, 0) for name, summary in entries]
        while collapsed and measure(header + human_block + "".join(collapsed)) > budget:
            collapsed.pop(0)
        return header + human_block + "".join(collapsed)

    # ------------------------------------------------------------------
    # measurement
    # ------------------------------------------------------------------
    def _budget(self) -> int:
        """The active budget: tokens take precedence over characters."""
        if self._max_memory_tokens:
            return self._max_memory_tokens
        return self._max_memory_chars

    def _measure(self, text: str) -> int:
        """Measure a text with the active unit (tokens or characters)."""
        if self._max_memory_tokens:
            return int(self._token_counter(text))
        return len(text)

    def _truncate_human(self, human_block: str, budget: int, measure: Callable[[str], int]) -> str:
        """Cut the human section down so that it fits the budget."""
        marker = "\n<!-- truncated: the human section did not fit the memory budget -->\n"
        body = human_block
        while body and measure(body + marker) > budget:
            body = body[: max(0, len(body) - 200)]
        return body + marker

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _fresh_state(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "roadmap": [],
            "completed_steps": [],
            "telemetry": {},
            "step_files": {},
            "attempts": {},
            "verifications": {},
            "needs_human": {},
            "human_hash": sha256_text(""),
            "breaker": {
                "open": False,
                "reason": None,
                "step": None,
                "attempts": 0,
                "last_error": None,
                "opened_at": None,
            },
            "last_failure": None,
            "updated_at": _utc_now(),
        }

    def _load_sync(self) -> dict[str, Any]:
        path = self.memory_path
        if not path.exists():
            state = self._fresh_state()
            state["roadmap"] = list(self._roadmap)
            self._state = state
            self._human_text = ""
            return copy.deepcopy(state)
        try:
            # newline="" keeps the bytes of the file as they are: the universal
            # newline mode would translate a carriage return inside the human
            # and break the byte for byte guarantee.
            with path.open("r", encoding="utf-8", newline="") as handle:
                text = handle.read()
        except UnicodeDecodeError as exc:
            # A human edited the file with an editor that uses another
            # encoding.  That is a corrupt project, not a crash.
            raise StateCorruptionError(
                f"{path} is not valid UTF-8 ({exc.reason} at byte {exc.start}); "
                "it was probably edited with an editor that uses another encoding. "
                "Run 'contextguard doctor' to inspect the file."
            ) from exc
        except OSError as exc:  # pragma: no cover - unreadable file
            raise StateCorruptionError(f"could not read {path}: {exc}") from exc
        state_pos = self._find_state_marker(text)
        human = self._extract_human(text, state_pos)
        # The human section is known before anything is written, so that a
        # migration preserves it byte for byte.
        self._human_text = human
        state = self._parse_state_block(text, state_pos)
        version = state.get("schema_version")
        if version == 1:
            state = self._migrate_v1_to_v2(state, path)
        if self._roadmap:
            state["roadmap"] = list(self._roadmap)
        self._state = state
        self._human_text = human
        return copy.deepcopy(state)

    @staticmethod
    def _find_state_marker(text: str) -> int:
        """Return the position of the *last* state marker, or -1.

        The marker must stand on its own line, and the last one wins: the
        library writes the machine block last, so a marker that a model
        managed to smuggle into a summary can never be mistaken for it.

        The marker of the previous name is accepted as well, so a memory
        file written by ContextGuard 0.2 can still be read; it is rewritten
        with the current markers on the next save.
        """
        matches = list(_STATE_MARKER_RE.finditer(text))
        if matches:
            return matches[-1].start()
        legacy = list(_LEGACY_STATE_MARKER_RE.finditer(text))
        if legacy:
            return legacy[-1].start()
        return -1

    def _extract_human(self, text: str, state_pos: int) -> str:
        """Return the human owned text, byte for byte.

        The section is the region the library itself wrote: the last end
        marker before the state block and the nearest start marker before it.
        A model cannot inject a marker, because every untrusted string is
        escaped on write (see :func:`escape_embedded`).

        Exactly one newline is removed on each side: the writer always puts
        the text on its own line between the markers, so removing them keeps
        the section stable across repeated writes.
        """
        if state_pos < 0:
            return ""
        end_pos = text.rfind(HUMAN_END_MARKER, 0, state_pos)
        start_pos = text.rfind(HUMAN_START_MARKER, 0, end_pos)
        start_len = len(HUMAN_START_MARKER)
        if end_pos < 0 or start_pos < 0:
            # The file may still use the markers of the previous name.
            end_pos = text.rfind(LEGACY_HUMAN_END_MARKER, 0, state_pos)
            if end_pos < 0:
                return ""
            start_pos = text.rfind(LEGACY_HUMAN_START_MARKER, 0, end_pos)
            start_len = len(LEGACY_HUMAN_START_MARKER)
            if start_pos < 0:
                return ""
        content = text[start_pos + start_len : end_pos]
        if content.startswith(chr(10)):
            content = content[1:]
        if content.endswith(chr(10)):
            content = content[:-1]
        return content

    def _corruption_hint(self) -> str:
        """The actionable tail of a corruption message.

        A ``.bak`` file is only mentioned when it actually exists: promising
        a backup that is not there sends the reader looking for nothing.
        """
        backup = self.memory_path.with_suffix(self.memory_path.suffix + ".bak")
        if backup.exists():
            return f" A backup of an earlier version is at {backup.name}."
        return ""

    def _parse_state_block(self, text: str, state_pos: int) -> dict[str, Any]:
        marker_index = state_pos
        if marker_index == -1:
            raise StateCorruptionError(
                f"{self.memory_path} does not contain the AgenTether state marker "
                f"{STATE_MARKER!r}; refusing to silently reset the project memory. "
                "Run 'agentether doctor' to inspect the file."
                f"{self._corruption_hint()}"
            )
        # The block is the first fence after the marker up to the *last*
        # fence in the file: a summary that contains "```" cannot truncate it.
        open_pos = text.find(_FENCE_OPEN, marker_index)
        if open_pos < 0:
            raise StateCorruptionError(
                f"{self.memory_path} contains the state marker but no JSON block; "
                "the project memory is corrupted. Run 'agentether doctor' to "
                f"inspect the file.{self._corruption_hint()}"
            )
        newline = text.find(chr(10), open_pos)
        if newline < 0:
            raise StateCorruptionError(
                f"{self.memory_path} contains a truncated state block. "
                "Run 'agentether doctor' to inspect the file."
            )
        content_start = newline + 1
        close_pos = text.rfind("```", content_start)
        if close_pos < 0:
            raise StateCorruptionError(
                f"{self.memory_path} contains an unterminated state block. "
                "Run 'agentether doctor' to inspect the file."
            )
        try:
            data = json.loads(text[content_start:close_pos])
        except json.JSONDecodeError as exc:
            raise StateCorruptionError(
                f"{self.memory_path} contains a malformed state block: {exc}. "
                "Run 'agentether doctor' to inspect the file."
                f"{self._corruption_hint()}"
            ) from exc
        if not isinstance(data, dict):
            raise StateCorruptionError(
                f"{self.memory_path} contains a state block that is not a JSON object. "
                "Run 'agentether doctor' to inspect the file."
            )
        version = data.get("schema_version")
        if version not in (1, SCHEMA_VERSION):
            raise StateCorruptionError(
                f"{self.memory_path} uses unsupported schema_version {version!r}; "
                f"this build understands {version} and {SCHEMA_VERSION}. "
                "Run 'agentether doctor' to inspect the file."
                f"{self._corruption_hint()}"
            )
        state = self._fresh_state()
        state.update(data)
        for key, default in (
            ("completed_steps", []),
            ("telemetry", {}),
            ("step_files", {}),
            ("attempts", {}),
            ("verifications", {}),
            ("needs_human", {}),
        ):
            if not isinstance(state.get(key), type(default)):
                raise StateCorruptionError(
                    f"{self.memory_path} contains an invalid {key!r} section. "
                    "Run 'agentether doctor' to inspect the file."
                )
        breaker = state.get("breaker")
        if not isinstance(breaker, dict):
            raise StateCorruptionError(
                f"{self.memory_path} contains an invalid 'breaker' section. "
                "Run 'agentether doctor' to inspect the file."
            )
        budget = state.get("budget")
        if budget is not None and not isinstance(budget, dict):
            raise StateCorruptionError(
                f"{self.memory_path} contains an invalid 'budget' section. "
                "Run 'agentether doctor' to inspect the file."
            )
        # The untrusted strings are escaped on write; undo that so the state
        # that is read back is the state that was written.
        _transform_untrusted(state, unescape_embedded)
        return state

    def _migrate_v1_to_v2(self, state: dict[str, Any], path: Path) -> dict[str, Any]:
        """Migrate a schema version 1 state to version 2.

        The old file is copied to ``PROJECT_MEMORY.md.bak`` before anything is
        written, so no data is lost even if the migration is wrong.
        """
        backup = path.with_suffix(path.suffix + ".bak")
        try:
            path.replace(backup)
        except OSError as exc:  # pragma: no cover - unwritable directory
            raise StateCorruptionError(
                f"could not back up {path} before migrating it: {exc}"
            ) from exc
        migrated = self._fresh_state()
        migrated.update(state)
        migrated["schema_version"] = SCHEMA_VERSION
        migrated.setdefault("attempts", {})
        migrated.setdefault("verifications", {})
        migrated.setdefault("needs_human", {})
        migrated["human_hash"] = sha256_text(self._human_text.strip())
        breaker = dict(migrated.get("breaker") or {})
        breaker.setdefault("opened_at", None)
        migrated["breaker"] = breaker
        self._write_state(migrated)
        logger.info(
            "Supervisor: migrated %s from schema version 1 to 2 (backup: %s)",
            path.name,
            backup.name,
        )
        return migrated

    def _record_step_sync(
        self,
        step_name: str,
        telemetry: Telemetry,
        raw_output: str,
    ) -> None:
        state = self._load_sync()
        state["roadmap"] = list(self._roadmap) or list(state.get("roadmap", []))
        state.setdefault("telemetry", {})[step_name] = telemetry.to_dict()
        if telemetry.status == "completed":
            completed = list(state.get("completed_steps", []))
            if step_name not in completed:
                completed.append(step_name)
            state["completed_steps"] = completed
            state["last_failure"] = None
            state.setdefault("needs_human", {}).pop(step_name, None)
        else:
            state["last_failure"] = {
                "step": step_name,
                "status": telemetry.status,
                "reason": telemetry.summary,
            }
            if telemetry.status == "blocked":
                state.setdefault("needs_human", {})[step_name] = telemetry.summary
        relative = self._write_step_output(state, step_name, raw_output)
        state.setdefault("step_files", {})[step_name] = relative
        state["human_hash"] = sha256_text(self._human_text.strip())
        state["updated_at"] = _utc_now()
        self._write_state(state)

    def _append_attempt_sync(
        self,
        step_name: str,
        attempt: int,
        outcome: str,
        error: str | None,
        output: str,
        store_raw: bool,
        usage: dict[str, Any] | None,
        budget: dict[str, Any] | None,
    ) -> None:
        record: dict[str, Any] = {
            "ts": _utc_now(),
            "attempt": attempt,
            "outcome": outcome,
            "error": error,
            "output_length": len(output),
            "output_sha256": sha256_text(output),
        }
        if usage:
            record["usage"] = usage
        if store_raw:
            record["output"] = output
        state = self._load_sync()
        attempts = state.setdefault("attempts", {})
        history = list(attempts.get(step_name, []))
        history.append(record)
        attempts[step_name] = history[-MAX_ATTEMPTS_IN_STATE:]
        if budget is not None:
            state["budget"] = budget
        state["updated_at"] = _utc_now()
        self._write_state(state)
        self._append_attempt_line(state, step_name, record)

    def _append_attempt_line(
        self, state: Mapping[str, Any], step_name: str, record: dict[str, Any]
    ) -> None:
        """Append one JSON line to ``steps/NN_<slug>.attempts.jsonl``."""
        steps_dir = self._dir / STEPS_DIRNAME
        steps_dir.mkdir(parents=True, exist_ok=True)
        number = self._step_number(state, step_name)
        path = steps_dir / f"{number:02d}_{slugify(step_name)}.attempts.jsonl"
        line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
        try:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError as exc:  # pragma: no cover - unwritable directory
            logger.warning("Supervisor: could not write the attempt log: %s", exc)

    def _record_budget_exceeded_sync(
        self,
        step_name: str,
        kind: str,
        limit: float,
        used: float,
    ) -> None:
        state = self._load_sync()
        state["last_failure"] = {
            "step": step_name,
            "status": "budget_exceeded",
            "reason": f"budget '{kind}' exceeded: limit {limit}, used {used}",
        }
        state["updated_at"] = _utc_now()
        self._write_state(state)

    def _set_verification_sync(
        self,
        step_name: str,
        ok: bool,
        reason: str,
        evidence: dict[str, Any],
    ) -> None:
        state = self._load_sync()
        state.setdefault("verifications", {})[step_name] = {
            "ok": bool(ok),
            "reason": reason,
            "evidence": evidence,
            "ts": _utc_now(),
        }
        state["updated_at"] = _utc_now()
        self._write_state(state)

    def _set_breaker_sync(
        self,
        open: bool,
        reason: str,
        step: str | None,
        attempts: int,
        last_error: str | None,
        opened_at: float | None,
    ) -> None:
        state = self._load_sync()
        state["breaker"] = {
            "open": bool(open),
            "reason": reason or None,
            "step": step,
            "attempts": int(attempts),
            "last_error": last_error,
            "opened_at": opened_at,
        }
        state["updated_at"] = _utc_now()
        self._write_state(state)

    def _reset_sync(self) -> None:
        state = self._fresh_state()
        state["roadmap"] = list(self._roadmap)
        state["human_hash"] = sha256_text(self._human_text.strip())
        steps_dir = self._dir / STEPS_DIRNAME
        if steps_dir.is_dir():
            for entry in sorted(steps_dir.iterdir()):
                if entry.is_file() and entry.suffix == ".md":
                    with contextlib.suppress(OSError):
                        entry.unlink()
        self._write_state(state)
        self._state = state

    def _write_state(self, state: Mapping[str, Any]) -> None:
        self._atomic_write(self.memory_path, self._render_memory_file(state))

    def _write_step_output(
        self,
        state: Mapping[str, Any],
        step_name: str,
        raw_output: str,
    ) -> str:
        steps_dir = self._dir / STEPS_DIRNAME
        steps_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{self._step_number(state, step_name):02d}_{slugify(step_name)}.md"
        path = steps_dir / filename
        body = f"# Step: {step_name}\n\n{raw_output}\n"
        self._atomic_write(path, body)
        return f"{STEPS_DIRNAME}/{filename}"

    def _step_number(self, state: Mapping[str, Any], step_name: str) -> int:
        roadmap = list(state.get("roadmap", []))
        if step_name in roadmap:
            return roadmap.index(step_name) + 1
        completed = list(state.get("completed_steps", []))
        if step_name in completed:
            return completed.index(step_name) + 1
        return len(completed) + 1

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write ``content`` to ``path`` atomically.

        The temporary file is created in the *same* directory (so that
        ``os.replace`` stays atomic), flushed and ``fsync``-ed before the
        rename, and the directory itself is ``fsync``-ed afterwards.  On any
        error the temporary file is removed and the error re-raised, leaving
        the previous file untouched.
        """
        directory = path.parent
        directory.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(directory), suffix=".tmp")
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, path)
            self._fsync_directory(directory)
        except BaseException:
            with contextlib.suppress(OSError):
                tmp_path.unlink()
            raise

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        """Best effort directory ``fsync``.

        Only the platform-unsupported case is ignored (Windows cannot open a
        directory, some file systems return ``EINVAL``/``ENOTSUP``).  Every
        other error is logged as a warning, because a silently unsynced
        directory means a crash can lose the rename.
        """
        try:
            dir_fd = os.open(str(directory), os.O_RDONLY)
        except OSError as exc:
            if exc.errno in _UNSUPPORTED_DIR_FSYNC_ERRNOS:
                return
            logger.warning("Supervisor: could not open %s for directory fsync: %s", directory, exc)
            return
        try:
            os.fsync(dir_fd)
        except OSError as exc:
            if exc.errno not in _UNSUPPORTED_DIR_FSYNC_ERRNOS:
                logger.warning("Supervisor: directory fsync failed for %s: %s", directory, exc)
        finally:
            os.close(dir_fd)

    def _prune_stale_temp_files(self) -> None:
        """Remove leftover ``*.tmp`` files older than one hour.

        Fresh temporary files are left alone: a concurrent write may be in
        progress.  Nothing else is ever deleted.
        """
        cutoff = time.time() - STALE_TMP_SECONDS
        try:
            entries = list(self._dir.glob("*.tmp"))
        except OSError:  # pragma: no cover - unreadable directory
            return
        for entry in entries:
            try:
                if entry.is_file() and entry.stat().st_mtime < cutoff:
                    entry.unlink()
            except OSError:  # pragma: no cover - racing with another process
                continue

    # ------------------------------------------------------------------
    # rendering
    # ------------------------------------------------------------------
    def _render_header(self, state: Mapping[str, Any]) -> str:
        roadmap = list(state.get("roadmap", []))
        completed = set(state.get("completed_steps", []))
        lines = ["# Project Memory", "", "## Roadmap", ""]
        if roadmap:
            for name in roadmap:
                marker = "x" if name in completed else " "
                lines.append(f"- [{marker}] {name}")
        else:
            for name in sorted(completed):
                lines.append(f"- [x] {name}")
        lines.append("")
        return "\n".join(lines)

    def _step_entries(self, state: Mapping[str, Any]) -> list[tuple[str, str]]:
        telemetry = state.get("telemetry", {})
        entries: list[tuple[str, str]] = []
        for name in state.get("completed_steps", []):
            record = telemetry.get(name) or {}
            summary = str(record.get("summary", "")).strip()
            entries.append((str(name), summary))
        return entries

    @staticmethod
    def _render_full_step(name: str, summary: str) -> str:
        body = summary or "_no summary recorded_"
        return f"### {name}\n\n{body}\n\n"

    @staticmethod
    def _render_collapsed_step(name: str, summary: str, width: int) -> str:
        snippet = summary.replace("\n", " ").strip()
        if width and len(snippet) > width:
            snippet = snippet[: width - 1].rstrip() + "…" if width > 1 else ""
        return f"- {name}: {snippet}\n" if snippet else f"- {name}\n"

    def _render_memory_file(self, state: Mapping[str, Any]) -> str:
        # Every untrusted string is escaped before it is written, so that the
        # file can never contain a marker that the model forged.
        state = _escape_state(state)
        lines = [
            "# Project Memory",
            "",
            "<!-- Managed by AgenTether. Edit the code, not this file. -->",
            "<!-- The section between the human markers is never rewritten by AgenTether. -->",
            "",
            "## Roadmap",
            "",
        ]
        roadmap = list(state.get("roadmap", []))
        completed = set(state.get("completed_steps", []))
        if roadmap:
            for name in roadmap:
                marker = "x" if name in completed else " "
                lines.append(f"- [{marker}] {escape_embedded(str(name))}")
        else:
            for name in sorted(completed):
                lines.append(f"- [x] {escape_embedded(str(name))}")
        lines.extend(["", "## Completed Steps", ""])
        telemetry = state.get("telemetry", {})
        for name in state.get("completed_steps", []):
            record = telemetry.get(name) or {}
            summary = (
                escape_embedded(str(record.get("summary", "")).strip()) or "_no summary recorded_"
            )
            lines.extend([f"### {escape_embedded(str(name))}", "", summary, ""])

        needs_human = state.get("needs_human") or {}
        if needs_human:
            lines.extend(["## Needs human input", ""])
            for name, reason in needs_human.items():
                lines.append(f"- `{escape_embedded(str(name))}`: {escape_embedded(str(reason))}")
            lines.extend(
                [
                    "",
                    "Answer in the human section below, then run the step again.",
                    "",
                ]
            )

        verifications = state.get("verifications") or {}
        if verifications:
            lines.extend(["## Verification", ""])
            for name, record in verifications.items():
                status = "passed" if record.get("ok") else "failed"
                reason = record.get("reason") or ""
                suffix = f" - {escape_embedded(str(reason))}" if reason else ""
                lines.append(f"- `{escape_embedded(str(name))}`: {status}{suffix}")
            lines.append("")

        lines.extend([HUMAN_START_MARKER, self._human_text, HUMAN_END_MARKER, ""])
        lines.extend(
            [
                STATE_MARKER,
                "```json",
                json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False),
                "```",
                "",
            ]
        )
        return "\n".join(lines)


#: ``errno`` values that mean "this platform cannot fsync a directory".
_UNSUPPORTED_DIR_FSYNC_ERRNOS = frozenset(
    value
    for value in (
        getattr(errno, "EINVAL", None),
        getattr(errno, "ENOTSUP", None),
        getattr(errno, "EACCES", None),
        getattr(errno, "EPERM", None),
    )
    if value is not None
)
