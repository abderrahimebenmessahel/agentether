"""Semantic loop and stall detection.

A retry counter only catches the *obvious* loop: the agent failing the same
way over and over.  The dangerous case looks different every time -- different
ids, different timestamps, different wording -- while doing the same thing.
This module compares the *meaning* of the answers instead of their bytes.

Everything here is standard library only: normalisation, shingling and the
Jaccard similarity are implemented directly.

.. versionadded:: 0.2.0
"""

from __future__ import annotations

import hashlib
import re
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

from .models import Telemetry
from .policy import LoopPolicy, StallPolicy

__all__ = [
    "LoopDetector",
    "LoopVerdict",
    "StallDetector",
    "StallVerdict",
    "fingerprint",
    "jaccard",
    "normalize",
]

#: A hexadecimal blob of at least this length is treated as an id and masked.
_HEX_RE: Final = re.compile(r"\b[0-9a-f]{8,}\b")
#: Numbers (including decimals) are masked so that "42" and "43" look alike.
_NUMBER_RE: Final = re.compile(r"\d+(?:[.,]\d+)*")
#: ISO-8601 style timestamps are masked.
_TIMESTAMP_RE: Final = re.compile(r"\d{4}-\d{2}-\d{2}[t ]\d{2}:\d{2}:\d{2}(?:\.\d+)?z?", re.I)
#: Any whitespace run.
_WHITESPACE_RE: Final = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Normalise an answer so that volatile details stop mattering.

    Lowercases, masks numbers, hex ids and timestamps, and collapses
    whitespace.  Two answers that differ only in ids and formatting normalise
    to the same text.
    """
    lowered = text.lower()
    lowered = _TIMESTAMP_RE.sub(" <ts> ", lowered)
    lowered = _HEX_RE.sub(" <id> ", lowered)
    lowered = _NUMBER_RE.sub(" <num> ", lowered)
    return _WHITESPACE_RE.sub(" ", lowered).strip()


def fingerprint(text: str, shingle_size: int = 5) -> frozenset[str]:
    """Hash ``text`` into a set of shingle hashes.

    The text is normalised, split into words and every window of
    ``shingle_size`` words is hashed.  The resulting set is a cheap, stable
    fingerprint of the *content* of the answer.
    """
    words = normalize(text).split()
    if not words:
        return frozenset()
    if len(words) <= shingle_size:
        joined = " ".join(words)
        return frozenset({hashlib.sha256(joined.encode("utf-8")).hexdigest()})
    shingles = set()
    for index in range(len(words) - shingle_size + 1):
        window = " ".join(words[index : index + shingle_size])
        shingles.add(hashlib.sha256(window.encode("utf-8")).hexdigest())
    return frozenset(shingles)


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    """Return the Jaccard similarity of two fingerprint sets (0.0 - 1.0)."""
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    union = len(left | right)
    return intersection / union if union else 0.0


@dataclass(frozen=True)
class LoopVerdict:
    """Outcome of one loop check.

    Attributes:
        loop: True when the step looks like it is looping.
        similarity: Highest similarity found against a previous answer.
        window: How many answers were compared.
        hint: Corrective hint to show the agent.
    """

    loop: bool
    similarity: float = 0.0
    window: int = 0
    hint: str = ""


@dataclass
class LoopDetector:
    """Keeps a ring buffer of output fingerprints per step.

    Attributes:
        policy: The loop policy in use.
    """

    policy: LoopPolicy = field(default_factory=LoopPolicy)
    _history: dict[str, deque[frozenset[str]]] = field(default_factory=dict, init=False)

    def reset(self, step: str) -> None:
        """Forget the history of one step."""
        self._history.pop(step, None)

    def record(self, step: str, text: str) -> LoopVerdict:
        """Add an answer to the history and check it for looping.

        The step loops when the new answer is similar to each of the previous
        ``repeat_window - 1`` answers.
        """
        if not self.policy.enabled:
            return LoopVerdict(loop=False)

        history = self._history.setdefault(step, deque(maxlen=self.policy.repeat_window))
        current = fingerprint(text, self.policy.shingle_size)
        previous = list(history)
        history.append(current)

        window = self.policy.repeat_window
        if len(previous) + 1 < window:
            return LoopVerdict(loop=False, window=len(previous) + 1)

        similarities = [jaccard(current, other) for other in previous]
        best = max(similarities) if similarities else 0.0
        worst = min(similarities) if similarities else 0.0
        if worst >= self.policy.similarity_threshold:
            hint = (
                f"your last {window} answers were near-identical "
                f"(similarity {best:.2f}); change strategy instead of rephrasing"
            )
            return LoopVerdict(loop=True, similarity=best, window=window, hint=hint)
        return LoopVerdict(loop=False, similarity=best, window=len(previous) + 1)


@dataclass(frozen=True)
class StallVerdict:
    """Outcome of one stall check.

    Attributes:
        stalled: True when the step makes no progress any more.
        window: How many attempts were considered.
        hint: Corrective hint to show the agent.
    """

    stalled: bool
    window: int = 0
    hint: str = ""


@dataclass
class _StallSample:
    progress: float | None
    artifacts: int
    status: str


@dataclass
class StallDetector:
    """Detects steps that keep saying ``in_progress`` without moving.

    Attributes:
        policy: The stall policy in use.
    """

    policy: StallPolicy = field(default_factory=StallPolicy)
    _history: dict[str, deque[_StallSample]] = field(default_factory=dict, init=False)

    def reset(self, step: str) -> None:
        """Forget the history of one step."""
        self._history.pop(step, None)

    def record(self, step: str, telemetry: Telemetry) -> StallVerdict:
        """Add a telemetry report and check whether the step is stalled."""
        if not self.policy.enabled:
            return StallVerdict(stalled=False)

        history = self._history.setdefault(step, deque(maxlen=self.policy.stall_window))
        history.append(
            _StallSample(
                progress=telemetry.progress,
                artifacts=len(telemetry.artifacts),
                status=telemetry.status,
            )
        )
        samples = list(history)
        if len(samples) < self.policy.stall_window:
            return StallVerdict(stalled=False, window=len(samples))
        if any(sample.status != "in_progress" for sample in samples):
            return StallVerdict(stalled=False, window=len(samples))

        # A stall means: no sign of progress at all.  Progress is either a
        # strictly increasing ``progress`` value or new artifacts; when both
        # are required, *both* must be missing.
        checks: list[bool] = []
        if self.policy.require_progress:
            progresses = [sample.progress for sample in samples]
            checks.append(not _strictly_increases(progresses))
        if self.policy.require_artifacts:
            counts = [sample.artifacts for sample in samples]
            checks.append(not _strictly_increases(counts))
        if not all(checks):
            return StallVerdict(stalled=False, window=len(samples))
        hint = (
            f"the last {self.policy.stall_window} attempts reported 'in_progress' "
            "without any measurable progress; finish the work or report 'blocked'"
        )
        return StallVerdict(stalled=True, window=len(samples), hint=hint)


def _strictly_increases(values: Sequence[float | int | None]) -> bool:
    """Return whether ``values`` grows strictly from one entry to the next.

    ``None`` counts as "no progress reported" and therefore breaks the chain.
    """
    previous: float | int | None = None
    for value in values:
        if value is None or previous is None:
            previous = value
            continue
        if value <= previous:
            return False
        previous = value
    return previous is not None
