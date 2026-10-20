"""Data structures exchanged between the supervisor and the agent.

The supervisor owns the control path (roadmap, state, limits, validation); the
agent only produces a *data path* payload -- a text answer that must end with a
telemetry JSON object.  These dataclasses describe both sides of that
boundary.

.. versionchanged:: 0.2.0
    Added :class:`Usage`, :class:`WorkerOutput`, the verification types and
    the human-in-the-loop memory fields.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal, Protocol, runtime_checkable

from .exceptions import TelemetryParseError

__all__ = [
    "ALLOWED_STATUSES",
    "StepContext",
    "StepResult",
    "Telemetry",
    "TelemetryStatus",
    "Usage",
    "Verifier",
    "VerifyContext",
    "VerifyResult",
    "WorkerOutput",
]

#: The only status values the telemetry contract allows.
ALLOWED_STATUSES: Final[tuple[TelemetryStatus, ...]] = (
    "in_progress",
    "completed",
    "blocked",
    "failed",
)

TelemetryStatus = Literal["in_progress", "completed", "blocked", "failed"]

#: The exact JSON shape the agent must emit at the end of its answer.  It is
#: embedded verbatim in the prompt so the contract has a single source of truth.
TELEMETRY_CONTRACT: Final[str] = """{
  "step": "<the name of the roadmap step you were asked to perform>",
  "status": "in_progress | completed | blocked | failed",
  "summary": "<one short paragraph: what you did and what you found>",
  "progress": <integer 0-100, or null if not meaningful>,
  "next_step": "<the name of the next roadmap step, or null if this was the last one>",
  "artifacts": ["<path, URL or identifier of anything you produced>"]
}"""


@dataclass(frozen=True)
class Usage:
    """Resource usage reported by a worker.

    Attributes:
        input_tokens: Prompt tokens, when the provider reports them.
        output_tokens: Completion tokens, when the provider reports them.
        cost: Monetary cost, when the provider reports it.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cost: float | None = None

    @property
    def total_tokens(self) -> int:
        """Sum of input and output tokens."""
        return int(self.input_tokens) + int(self.output_tokens)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation of this usage."""
        return {
            "input_tokens": int(self.input_tokens),
            "output_tokens": int(self.output_tokens),
            "cost": self.cost,
        }


@dataclass(frozen=True)
class WorkerOutput:
    """The result of a worker call: the answer text plus optional usage.

    A worker may simply return the answer as a string; returning a
    :class:`WorkerOutput` additionally reports how much the call cost, which
    is what makes token and cost budgets possible.
    """

    text: str
    usage: Usage | None = None


@dataclass(frozen=True)
class Telemetry:
    """The structured status report the agent must emit.

    Attributes:
        step: Name of the roadmap step this report belongs to.
        status: One of :data:`ALLOWED_STATUSES`.
        summary: Short human readable description of what happened.
        progress: Completion percentage between 0 and 100, or ``None``.
        next_step: The roadmap step the agent believes comes next, or ``None``.
        artifacts: Files / URLs / identifiers produced by the step.
    """

    step: str
    status: TelemetryStatus
    summary: str
    progress: float | None = None
    next_step: str | None = None
    artifacts: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Frozen dataclasses cannot assign in __post_init__, only validate.
        if self.status not in ALLOWED_STATUSES:
            raise ValueError(
                f"invalid telemetry status {self.status!r}; "
                f"expected one of {', '.join(ALLOWED_STATUSES)}"
            )
        progress = self.progress
        if progress is not None and not 0.0 <= progress <= 100.0:
            raise ValueError(f"progress must be between 0 and 100, got {progress!r}")

    @classmethod
    def from_dict(cls, data: Any) -> Telemetry:
        """Build a :class:`Telemetry` from a decoded JSON object.

        Validates presence and types of the required fields (``step``,
        ``status``, ``summary``) and the optional fields.  A status outside
        :data:`ALLOWED_STATUSES` is rejected here as well, so a
        ``Telemetry`` instance can never carry a value the orchestrator's
        drift checks would reject.

        Raises:
            TelemetryParseError: If the payload does not satisfy the contract.
        """
        if not isinstance(data, Mapping):
            raise TelemetryParseError(
                "<unknown>",
                f"telemetry payload must be a JSON object, got {type(data).__name__}",
                repr(data),
            )

        step_value = data.get("step")
        step = step_value if isinstance(step_value, str) and step_value else "<unknown>"

        if "step" not in data:
            raise TelemetryParseError(step, "missing required field 'step'", repr(data))
        if not isinstance(step_value, str) or not step_value:
            raise TelemetryParseError(step, "field 'step' must be a non-empty string", repr(data))

        if "status" not in data:
            raise TelemetryParseError(step, "missing required field 'status'", repr(data))
        status_value = data.get("status")
        if not isinstance(status_value, str):
            raise TelemetryParseError(
                step,
                f"field 'status' must be a string, got {type(status_value).__name__}",
                repr(data),
            )
        if status_value not in ALLOWED_STATUSES:
            raise TelemetryParseError(
                step,
                f"field 'status' must be one of {', '.join(ALLOWED_STATUSES)}, "
                f"got {status_value!r}",
                repr(data),
            )

        if "summary" not in data:
            raise TelemetryParseError(step, "missing required field 'summary'", repr(data))
        summary_value = data.get("summary")
        if not isinstance(summary_value, str):
            raise TelemetryParseError(
                step,
                f"field 'summary' must be a string, got {type(summary_value).__name__}",
                repr(data),
            )

        progress: float | None = None
        progress_value = data.get("progress")
        if progress_value is not None:
            if isinstance(progress_value, bool) or not isinstance(progress_value, (int, float)):
                raise TelemetryParseError(
                    step,
                    "field 'progress' must be a number or null, "
                    f"got {type(progress_value).__name__}",
                    repr(data),
                )
            numeric_progress = float(progress_value)
            if not 0.0 <= numeric_progress <= 100.0:
                raise TelemetryParseError(
                    step,
                    f"field 'progress' must be between 0 and 100, got {numeric_progress!r}",
                    repr(data),
                )
            progress = numeric_progress

        next_step_value = data.get("next_step")
        if next_step_value is not None and not isinstance(next_step_value, str):
            raise TelemetryParseError(
                step,
                f"field 'next_step' must be a string or null, got {type(next_step_value).__name__}",
                repr(data),
            )
        next_step: str | None = next_step_value

        artifacts_value = data.get("artifacts", [])
        if artifacts_value is None:
            artifacts_value = []
        if not isinstance(artifacts_value, (list, tuple)):
            raise TelemetryParseError(
                step,
                "field 'artifacts' must be a list of strings, "
                f"got {type(artifacts_value).__name__}",
                repr(data),
            )
        artifacts: list[str] = []
        for index, artifact in enumerate(artifacts_value):
            if not isinstance(artifact, str):
                raise TelemetryParseError(
                    step,
                    f"field 'artifacts[{index}]' must be a string, got {type(artifact).__name__}",
                    repr(data),
                )
            artifacts.append(artifact)

        return cls(
            step=step_value,
            status=status_value,  # narrowed by the checks above
            summary=summary_value,
            progress=progress,
            next_step=next_step,
            artifacts=artifacts,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation of this telemetry."""
        return {
            "step": self.step,
            "status": self.status,
            "summary": self.summary,
            "progress": self.progress,
            "next_step": self.next_step,
            "artifacts": list(self.artifacts),
        }


@dataclass(frozen=True)
class VerifyContext:
    """Everything a verifier is allowed to look at.

    Attributes:
        step: Name of the step that is being verified.
        telemetry: The telemetry the agent reported.
        raw_output: The agent's raw answer text.
        memory_dir: Directory holding the project memory.
        workdir: Directory the agent is supposed to work in.  All paths taken
            from telemetry must resolve inside this directory.
    """

    step: str
    telemetry: Telemetry
    raw_output: str
    memory_dir: Path
    workdir: Path


@dataclass(frozen=True)
class VerifyResult:
    """The outcome of one verification.

    Attributes:
        ok: ``True`` when the claim passed verification.
        reason: Why it failed (empty when ``ok`` is true).
        evidence: Structured evidence, stored in the attempt log.
    """

    ok: bool
    reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(cls, **evidence: Any) -> VerifyResult:
        """Create a passing result, optionally carrying evidence."""
        return cls(ok=True, reason="", evidence=dict(evidence))

    @classmethod
    def failure(cls, reason: str, **evidence: Any) -> VerifyResult:
        """Create a failing result, optionally carrying evidence."""
        return cls(ok=False, reason=reason, evidence=dict(evidence))


@runtime_checkable
class Verifier(Protocol):
    """Independent check of what the agent claimed.

    A verifier is an async callable that receives a :class:`VerifyContext` and
    returns a :class:`VerifyResult`.  Exceptions raised inside a verifier are
    treated as a *failed verification*, never as a crash.
    """

    async def __call__(self, ctx: VerifyContext) -> VerifyResult: ...


@dataclass
class StepContext:
    """Everything the agent needs to know before it does any work.

    The context is rebuilt from disk for *every* attempt, so the agent always
    sees the current state of the project rather than a stale in-memory copy.
    That re-read is the core "external memory" guarantee of AgenTether.

    Attributes:
        step_name: The roadmap step being executed.
        step_index: Zero-based position of the step in the roadmap.
        attempt: One-based attempt number for this step.
        max_attempts: Total number of attempts allowed for this step.
        memory: Compacted contents of ``PROJECT_MEMORY.md`` (including the
            human owned section, which is always injected).
        last_error: Corrective hint from the previous failed attempt, if any.
        roadmap: The full ordered roadmap.
        workdir: Directory the agent is supposed to work in.
        human_memory: The human owned part of the memory, verbatim.
    """

    step_name: str
    step_index: int
    attempt: int
    max_attempts: int
    memory: str
    last_error: str | None
    roadmap: tuple[str, ...]
    workdir: Path = Path(".")
    human_memory: str = ""

    def build_prompt(self, task: str) -> str:
        """Assemble the prompt for this step.

        The prompt contains four parts: the task, the roadmap position, the
        compacted project memory and the telemetry contract the answer must
        end with.  When the previous attempt failed, a corrective hint is
        appended so the agent can fix its mistake instead of repeating it.
        """
        total = len(self.roadmap)
        position = self.step_index + 1
        roadmap_lines = []
        for index, name in enumerate(self.roadmap):
            if index < self.step_index:
                marker = "[x]"
            elif index == self.step_index:
                marker = "[>]"
            else:
                marker = "[ ]"
            roadmap_lines.append(f"  {marker} {index + 1}. {name}")
        roadmap_block = "\n".join(roadmap_lines)

        parts = [
            "# Task",
            task.strip(),
            "",
            "# Roadmap position",
            f'You are on step {position} of {total}: "{self.step_name}"',
            "Roadmap:",
            roadmap_block,
            "",
            "# Project memory",
            self.memory.strip() or "(no memory yet)",
            "",
            "# Telemetry contract",
            "Your answer MUST end with a single JSON object matching this schema:",
            TELEMETRY_CONTRACT,
            "Rules:",
            "- The JSON object must be the last thing in your answer.",
            "- Do not wrap it in extra prose, markdown quotes or code fences.",
            '- "step" must be exactly the roadmap step you were asked to perform.',
            '- Use status "completed" only when the step is really done.',
        ]
        if self.last_error:
            parts.extend(
                [
                    "",
                    "# Corrective hint",
                    "The previous attempt failed. Fix this before answering:",
                    self.last_error,
                ]
            )
        return "\n".join(parts)


@dataclass
class StepResult:
    """The validated outcome of one roadmap step.

    Attributes:
        step: Name of the step.
        raw_output: The agent's raw text answer.
        telemetry: The parsed and validated telemetry.
        attempts: How many attempts were consumed (0 for a cached result).
        duration_seconds: Wall clock duration of the execution.
        from_cache: True when the result was restored from the project memory
            instead of being produced by the agent.
        usage: Resource usage reported by the worker, when available.
    """

    step: str
    raw_output: str
    telemetry: Telemetry
    attempts: int
    duration_seconds: float
    from_cache: bool
    usage: Usage | None = None
