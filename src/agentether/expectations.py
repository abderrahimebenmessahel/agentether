"""Declarative expectations: what a step **must** produce.

The verifiers of :mod:`agentether.verifier` check the **claim** of the
agent: the files it listed must exist.  They cannot know what the step was
supposed to produce, so a step whose agent claims to be done without having
written half of its files passes every check.

An **expectation** is the contract of the step: the files it must produce
and what those files must look like.  The library checks it after every
attempt, whatever the agent claimed, and the step cannot complete while an
expectation is unmet.

    @orch.guard_step(
        "write-docs",
        expects=[
            "README.md",
            Expectation("data.json", json_keys=("a", "b")),
            Expectation("build.py", python_valid=True, contains=("def build",)),
        ],
    )
    async def write_docs(ctx: StepContext) -> str:
        ...

**What an expectation cannot do.**  It checks the **shape** of a file, not
its meaning: a JSON that parses may hold the wrong number, a Markdown that
has its headings may say the wrong thing, and a Python file that compiles
may do the wrong thing.  A semantic check needs a judge (see
:func:`agentether.verifier.llm_judge`) or a check of your own; an
expectation is a floor, not a proof.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import ConfigurationError
from .models import Verifier, VerifyContext, VerifyResult
from .verifier import (
    PathNotAllowedError,
    file_contains,
    file_exists,
    json_file_valid,
    markdown_has_headings,
    python_syntax_valid,
    resolve_within,
)

__all__ = ["Expectation", "expectations_verifier", "resolve_expectations"]


@dataclass(frozen=True)
class Expectation:
    """What one file of a step must be.

    Attributes:
        path: The path of the file, relative to the work directory.  An
            absolute path, a ``..`` component and a path that leaves the
            work directory through a symbolic link are refused.
        contains: The regular expressions the file must contain (the
            patterns of :func:`agentether.verifier.file_contains`).
        json_keys: The keys the file must have when it is a JSON object.
        json_valid: Whether the file must be valid JSON.
        python_valid: Whether the file must be valid Python (it is only
            compiled, never executed).
        markdown_headings: The headings the file must have when it is a
            Markdown file.
        non_empty: Whether the file must have a size greater than zero.

    A plain string in the ``expects`` list is a shorthand for
    ``Expectation(path)``: the file must exist and must not be empty.
    """

    path: str
    contains: tuple[str, ...] = ()
    json_keys: tuple[str, ...] = ()
    json_valid: bool = False
    python_valid: bool = False
    markdown_headings: tuple[str, ...] = ()
    non_empty: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.path, str) or not self.path.strip():
            raise ConfigurationError("the path of an expectation must be a non-empty string")
        for name in ("contains", "json_keys", "markdown_headings"):
            value = getattr(self, name)
            if not isinstance(value, tuple):
                object.__setattr__(self, name, tuple(value))

    def content_verifiers(self) -> list[tuple[str, Verifier]]:
        """The checks of the **content** of the file, with their label.

        The checks are the verifiers of :mod:`agentether.verifier`; the
        expectation only says which ones apply to this file.
        """
        checks: list[tuple[str, Verifier]] = []
        for pattern in self.contains:
            checks.append((f"does not contain {pattern!r}", file_contains(self.path, pattern)))
        if self.json_valid or self.json_keys:
            checks.append(
                ("is not a valid JSON object", json_file_valid(self.path, self.json_keys))
            )
        if self.python_valid:
            checks.append(("is not valid Python", python_syntax_valid(self.path)))
        if self.markdown_headings:
            checks.append(
                (
                    "is missing the headings " + ", ".join(self.markdown_headings),
                    markdown_has_headings(self.path, self.markdown_headings),
                )
            )
        return checks

    def exists_verifier(self) -> Verifier:
        """The check that the file exists (and is not empty)."""
        return file_exists(self.path, non_empty=self.non_empty)


def resolve_expectations(workdir: Path, expects: Sequence[str | Expectation]) -> list[Expectation]:
    """Check the declared expectations and return them.

    The paths are checked **now**, when the step is declared, and not only
    when the step runs: a path that leaves the work directory is a
    programming error and must be found at once.

    Args:
        workdir: The directory the agent works in.
        expects: The declared expectations: a path or an
            :class:`Expectation`.

    Returns:
        The expectations, in the order they were declared.

    Raises:
        ConfigurationError: If an item is neither a string nor an
            :class:`Expectation`, or if a path is not allowed.
    """
    resolved: list[Expectation] = []
    for item in expects:
        if isinstance(item, str):
            expectation = Expectation(item)
        elif isinstance(item, Expectation):
            expectation = item
        else:
            raise ConfigurationError(
                f"an expectation must be a path or an Expectation, got {type(item).__name__}"
            )
        try:
            resolve_within(workdir, expectation.path)
        except PathNotAllowedError as exc:
            raise ConfigurationError(
                f"the expected path {expectation.path!r} is not allowed: {exc}"
            ) from exc
        resolved.append(expectation)
    return resolved


def expectations_verifier(expectations: Sequence[Expectation]) -> Verifier:
    """One verifier that checks every declared expectation.

    The reason of the failure names the **missing** files and the files
    whose content does not satisfy the declaration, so that the corrective
    hint of the next attempt tells the agent what to do.

    Args:
        expectations: The expectations of the step.

    Returns:
        A verifier.
    """

    items = list(expectations)

    async def verify(ctx: VerifyContext) -> VerifyResult:
        missing: list[str] = []
        unmet: list[str] = []
        for expectation in items:
            exists = await expectation.exists_verifier()(ctx)
            if not exists.ok:
                missing.append(expectation.path)
                continue
            for label, verifier in expectation.content_verifiers():
                result = await verifier(ctx)
                if not result.ok:
                    unmet.append(f"{expectation.path} ({label})")
        if not missing and not unmet:
            return VerifyResult.success(checked=[item.path for item in items])
        parts: list[str] = []
        if missing:
            parts.append("the step must produce these files: " + ", ".join(missing))
        if unmet:
            parts.append(
                "the content of these files does not satisfy the declaration: " + ", ".join(unmet)
            )
        reason = "; ".join(parts)
        evidence: dict[str, Any] = {
            "missing": missing,
            "unmet": unmet,
            "expected": [item.path for item in items],
        }
        return VerifyResult(ok=False, reason=reason, evidence=evidence)

    return verify
