"""Extraction of telemetry JSON from untrusted agent output.

Agent output is *data*, not code.  It is never ``eval``-ed, never used as a
file path and always size-bounded.  This module contains the only piece of
AgenTether that has to cope with arbitrary text, so it is deliberately
forgiving about prose and deliberately strict about structure.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .exceptions import TelemetryParseError
from .models import Telemetry

__all__ = ["MAX_INPUT_CHARS", "extract_json_telemetry", "parse_telemetry"]

#: Inputs longer than this are refused outright (cheap DoS protection).
MAX_INPUT_CHARS = 1_000_000

# ```json ... ``` (or a bare ``` ... ``` fence).
_FENCE_RE = re.compile(r"```[ \t]*[A-Za-z0-9_+.-]*[ \t]*(?:\r?\n)?(.*?)```", re.DOTALL)

# The machine readable block appended to PROJECT_MEMORY.md.
_STATE_BLOCK_RE = re.compile(r"```[ \t]*json[ \t]*\r?\n(.*?)```", re.DOTALL)

_REQUIRED_KEYS = ("step", "status")


def _decode_dicts(text: str) -> list[dict[str, Any]]:
    """Decode every JSON object embedded in ``text``.

    A naive ``\\{.*\\}`` regex is not used: it breaks on nested objects, on
    several blocks in one answer and on braces inside strings.  Instead every
    ``{`` position is offered to :meth:`json.JSONDecoder.raw_decode`, which
    parses exactly one well formed JSON value and tells us where it ended.

    A candidate that starts *inside* a previously decoded object is dropped:
    the outer object is the real one, the inner one is just a nested value.
    """
    decoder = json.JSONDecoder()
    candidates: list[dict[str, Any]] = []
    spans: list[tuple[int, int]] = []
    index = 0
    length = len(text)
    while index < length:
        if text[index] != "{":
            index += 1
            continue
        try:
            value, end = decoder.raw_decode(text, index)
        except ValueError:
            index += 1
            continue
        if isinstance(value, dict) and not any(start < index < stop for start, stop in spans):
            candidates.append(value)
            spans.append((index, end))
            index = max(end, index + 1)
        else:
            index += 1
    return candidates


def _fenced_dicts(text: str) -> list[dict[str, Any]]:
    """Return the dict payloads of all fenced code blocks, in order."""
    found: list[dict[str, Any]] = []
    for match in _FENCE_RE.finditer(text):
        body = match.group(1)
        try:
            value = json.loads(body)
        except ValueError:
            value = None
        if isinstance(value, dict):
            found.append(value)
            continue
        # The fence may hold prose around the JSON; fall back to a scan.
        for candidate in _decode_dicts(body):
            found.append(candidate)
    return found


def _has_contract_keys(candidate: dict[str, Any]) -> bool:
    return all(key in candidate for key in _REQUIRED_KEYS)


def extract_json_telemetry(llm_response: str) -> dict[str, Any]:
    """Extract the telemetry object from a raw agent answer.

    The algorithm is:

    1. Try every fenced code block (```` ```json ... ``` ````) first -- an
       explicit code block is the most reliable signal.
    2. Otherwise scan the whole text for JSON objects using
       :meth:`json.JSONDecoder.raw_decode`.
    3. Return the **last** candidate that carries the ``step`` and ``status``
       keys; if no candidate has them, return the last dictionary found.
    4. If nothing at all could be decoded, raise :class:`TelemetryParseError`.

    Trailing commas are *not* tolerated -- they are invalid JSON and the
    extraction fails cleanly instead of "fixing" the agent's output.

    Raises:
        TelemetryParseError: If the input is too large or contains no JSON.
    """
    if not isinstance(llm_response, str):
        raise TelemetryParseError(
            "<unknown>",
            f"expected a string response, got {type(llm_response).__name__}",
        )
    if len(llm_response) > MAX_INPUT_CHARS:
        raise TelemetryParseError(
            "<unknown>",
            f"response is too large to parse ({len(llm_response)} characters, "
            f"limit is {MAX_INPUT_CHARS})",
        )

    fenced: list[dict[str, Any]] = _fenced_dicts(llm_response)
    scanned: list[dict[str, Any]] = _decode_dicts(llm_response)
    candidates: list[dict[str, Any]]

    if fenced and any(_has_contract_keys(candidate) for candidate in fenced):
        candidates = fenced
    elif scanned and any(_has_contract_keys(candidate) for candidate in scanned):
        candidates = scanned
    elif fenced:
        candidates = fenced
    else:
        candidates = scanned

    if not candidates:
        raise TelemetryParseError(
            "<unknown>",
            "no JSON object found in the response",
            llm_response,
        )

    # Note: an explicit index loop is used instead of ``reversed()`` because
    # type checkers lose the element type for ``reversed(list[...])``.
    selected: dict[str, Any] | None = None
    for index in range(len(candidates) - 1, -1, -1):
        candidate = candidates[index]
        if _has_contract_keys(candidate):
            selected = candidate
            break
    if selected is None:
        selected = candidates[-1]
    return selected


def parse_telemetry(llm_response: str, step: str) -> Telemetry:
    """Extract *and* validate the telemetry of a given step.

    Raises:
        TelemetryParseError: If no JSON object can be extracted, or if the
            extracted object violates the telemetry contract.
    """
    try:
        data = extract_json_telemetry(llm_response)
    except TelemetryParseError as exc:
        raise TelemetryParseError(step, exc.reason, exc.raw_excerpt) from exc
    try:
        return Telemetry.from_dict(data)
    except TelemetryParseError as exc:
        raise TelemetryParseError(step, exc.reason, exc.raw_excerpt) from exc
