"""The claims ledger and the tamper evident log chain.

Two ideas live here:

* **The claims ledger** (``claims.jsonl``) records, for every attempt, what
  the agent *claimed* (the status and the artifacts it reported) and what the
  *verification* said about that claim.  It is the raw material of the
  "false claim rate" that :mod:`agentether.cli` reports.
* **The hash chain**: every line of ``claims.jsonl`` and ``events.jsonl``
  carries the SHA-256 of the previous line.  A line that was edited, removed
  or inserted breaks the chain, and :func:`verify_chain` reports the first
  broken link.

.. warning::
   The chain detects *accidental* or *naive* tampering.  It does **not**
   protect against an attacker who rewrites the whole file: the last line's
   hash is recomputed, so a full rewrite produces a consistent chain again.
   It is a tripwire, not a signature.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "CLAIMS_FILENAME",
    "ChainBreak",
    "ClaimStats",
    "ClaimsLedger",
    "chain_hash",
    "read_claims",
    "verify_chain",
]

#: The name of the claims ledger inside the memory directory.
CLAIMS_FILENAME = "claims.jsonl"

#: The hash of the "line before the first one".
GENESIS_HASH = "0" * 64


def chain_hash(line: str) -> str:
    """Return the SHA-256 of a log line (without its trailing newline)."""
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def head_path(path: Path) -> Path:
    """The file that holds the hash of the last line of a log."""
    return path.with_name(path.name + ".head")


def write_head(path: Path, digest: str) -> None:
    """Write the hash of the last line of a log.

    The head is what makes a change to the *last* line detectable: the chain
    alone cannot tell that the final line was edited.
    """
    target = head_path(path)
    temporary = target.with_name(target.name + ".tmp")
    try:
        temporary.write_text(digest + "\n", encoding="utf-8")
        os.replace(temporary, target)
    except OSError:  # pragma: no cover - unwritable directory
        with contextlib.suppress(OSError):
            temporary.unlink()


def read_head(path: Path) -> str:
    """Read the hash of the last line of a log (empty when there is none)."""
    try:
        return head_path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


@dataclass
class ChainBreak:
    """A broken link in a hash chain.

    Attributes:
        line: The number of the first line that does not fit.
        expected: The hash the line claims to follow.
        found: The hash of the previous line.
        reason: What went wrong.
    """

    line: int
    expected: str
    found: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable copy of the break."""
        return {
            "line": self.line,
            "expected": self.expected,
            "found": self.found,
            "reason": self.reason,
        }


def verify_chain(path: Path) -> tuple[int, list[ChainBreak]]:
    """Verify the hash chain of a log file.

    Args:
        path: The log file.

    Returns:
        ``(lines_checked, breaks)``.  An empty list of breaks means the chain
        is intact.
    """
    if not path.exists():
        return 0, []
    breaks: list[ChainBreak] = []
    previous_hash = GENESIS_HASH
    number = 0
    with path.open("r", encoding="utf-8") as handle:
        for number, raw in enumerate(handle, start=1):
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                breaks.append(ChainBreak(number, previous_hash, "", "the line is not valid JSON"))
                previous_hash = chain_hash(line)
                continue
            claimed = record.get("prev")
            if claimed != previous_hash:
                breaks.append(
                    ChainBreak(
                        number,
                        str(claimed),
                        previous_hash,
                        "the line does not follow the previous one",
                    )
                )
            previous_hash = chain_hash(line)
    head = read_head(path)
    if head and previous_hash != head:
        breaks.append(
            ChainBreak(
                number,
                head,
                previous_hash,
                "the last line does not match the recorded head hash",
            )
        )
    return number, breaks


@dataclass(frozen=True)
class ClaimStats:
    """The statistics of a claims ledger.

    Attributes:
        total_claims: Every claim that was recorded.
        completed_claims: The claims that said "completed".
        verified_true: The completed claims whose verification passed.
        verified_false: The completed claims whose verification failed.
        unverified: The claims that were never verified (no verifier was
            attached, or the step did not finish).
        by_step: The same numbers per step.
        by_model: The same numbers per model, when the worker identified one.
    """

    total_claims: int = 0
    completed_claims: int = 0
    verified_true: int = 0
    verified_false: int = 0
    unverified: int = 0
    by_step: dict[str, dict[str, int]] = field(default_factory=dict)
    by_model: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def false_claim_rate(self) -> float:
        """The share of the "completed" claims that did not survive a check."""
        if not self.completed_claims:
            return 0.0
        return self.verified_false / self.completed_claims

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable copy of the statistics."""
        return {
            "total_claims": self.total_claims,
            "completed_claims": self.completed_claims,
            "verified_true": self.verified_true,
            "verified_false": self.verified_false,
            "unverified": self.unverified,
            "false_claim_rate": self.false_claim_rate,
            "by_step": self.by_step,
            "by_model": self.by_model,
        }


def _empty_bucket() -> dict[str, int]:
    return {
        "claims": 0,
        "completed": 0,
        "verified_true": 0,
        "verified_false": 0,
        "unverified": 0,
    }


def compute_stats(records: Iterable[Mapping[str, Any]]) -> ClaimStats:
    """Compute the statistics of a claims ledger.

    A *false claim* is a claim that said "completed" and whose verification
    failed.  The rate is the share of the completed claims that were false.
    """
    total = 0
    completed = 0
    verified_true = 0
    verified_false = 0
    unverified = 0
    by_step: dict[str, dict[str, int]] = {}
    by_model: dict[str, dict[str, int]] = {}

    for record in records:
        total += 1
        step = str(record.get("step", "?"))
        model = record.get("model")
        buckets = [by_step.setdefault(step, _empty_bucket())]
        if isinstance(model, str) and model:
            buckets.append(by_model.setdefault(model, _empty_bucket()))
        verification = record.get("verification")
        is_completed = record.get("claimed_status") == "completed"
        for bucket in buckets:
            bucket["claims"] += 1
        if is_completed:
            completed += 1
            for bucket in buckets:
                bucket["completed"] += 1
        if isinstance(verification, Mapping):
            ok = bool(verification.get("ok"))
            if is_completed:
                if ok:
                    verified_true += 1
                    for bucket in buckets:
                        bucket["verified_true"] += 1
                else:
                    verified_false += 1
                    for bucket in buckets:
                        bucket["verified_false"] += 1
            elif not ok:
                unverified += 1
                for bucket in buckets:
                    bucket["unverified"] += 1
        else:
            unverified += 1
            for bucket in buckets:
                bucket["unverified"] += 1

    return ClaimStats(
        total_claims=total,
        completed_claims=completed,
        verified_true=verified_true,
        verified_false=verified_false,
        unverified=unverified,
        by_step=by_step,
        by_model=by_model,
    )


def read_claims(memory_dir: str | os.PathLike[str]) -> list[dict[str, Any]]:
    """Read the claims ledger of a project.

    A line that is not valid JSON is skipped: the ledger is an observation
    file, not the source of truth.
    """
    path = Path(memory_dir) / CLAIMS_FILENAME
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                records.append(record)
    return records


class ClaimsLedger:
    """The append-only ledger of the claims of an agent.

    Every line carries the SHA-256 of the previous line, so a changed or
    removed line breaks the chain.

    Attributes:
        path: The file the claims are written to.
    """

    def __init__(self, memory_dir: str | os.PathLike[str]) -> None:
        self.path = Path(memory_dir) / CLAIMS_FILENAME
        self._last_hash = GENESIS_HASH
        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8", errors="replace") as handle:
                    for raw in handle:
                        line = raw.rstrip("\n")
                        if line.strip():
                            self._last_hash = chain_hash(line)
            except OSError:  # pragma: no cover - unreadable ledger
                pass
        else:
            write_head(self.path, GENESIS_HASH)

    def append(
        self,
        *,
        step: str,
        attempt: int,
        claimed_status: str,
        claimed_summary: str = "",
        claimed_artifacts: list[str] | None = None,
        model: str | None = None,
        verification: Mapping[str, Any] | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append one claim and return the record that was written."""
        record: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "step": step,
            "attempt": attempt,
            "claimed_status": claimed_status,
            "claimed_summary": claimed_summary,
            "claimed_artifacts": list(claimed_artifacts or []),
            "model": model,
            "verification": dict(verification) if verification is not None else None,
            "prev": self._last_hash,
        }
        if extra:
            record.update(dict(extra))
        line = json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")
        except OSError:  # pragma: no cover - unwritable directory
            return record
        self._last_hash = chain_hash(line)
        write_head(self.path, self._last_hash)
        return record
