"""The task set of the evidence trial.

Twenty distinct multi-step tasks.  A model cannot touch a filesystem, so
every step asks for the content of one or more files, and the harness writes
them into a sandbox (path confined, size capped).

The ground truth of a task is a list of checks that the arms never see: the
files must exist, be valid, and be *consistent with each other*.  The
cross-file consistency is what makes the tasks harder than "write a file with
three headings": a script and a README that must mention the real function
name, a report that must repeat the number of the data file.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["TASKS", "Check", "StepSpec", "TaskSpec", "build_tasks"]


@dataclass(frozen=True)
class Check:
    """One ground truth check.

    Attributes:
        kind: What is checked.
        path: The file the check is about.
        value: The parameter of the check (a key, a heading, a number).
        second: A second path, for the cross-file checks.
    """

    kind: str
    path: str
    value: str = ""
    second: str = ""


@dataclass(frozen=True)
class FileSpec:
    """A file a step must produce."""

    path: str
    contains: tuple[str, ...] = ()
    json_keys: tuple[str, ...] = ()
    json_values: tuple[tuple[str, str], ...] = ()
    headings: tuple[str, ...] = ()
    python_valid: bool = False


@dataclass(frozen=True)
class StepSpec:
    """One step of a task."""

    name: str
    instruction: str
    files: tuple[FileSpec, ...] = ()


@dataclass(frozen=True)
class TaskSpec:
    """One task of the trial."""

    name: str
    steps: tuple[StepSpec, ...]
    checks: tuple[Check, ...] = field(default=())

    @property
    def expected_files(self) -> tuple[str, ...]:
        """Every file the task must produce."""
        seen: list[str] = []
        for step in self.steps:
            for spec in step.files:
                if spec.path not in seen:
                    seen.append(spec.path)
        return tuple(seen)


def _task(
    index: int,
    subject: str,
    number: int,
    function: str,
    with_report: bool,
) -> TaskSpec:
    """Build one task of the trial.

    The steps are always the same shape, but the content differs: a different
    subject, a different number, a different function name.  That keeps the
    twenty tasks comparable while still being twenty distinct tasks.
    """
    notes = FileSpec(
        path="notes.md",
        headings=("## Context", "## Findings", "## Next steps"),
    )
    data = FileSpec(
        path="data.json",
        json_keys=("a", "b", "c"),
        json_values=(("a", str(number)), ("b", subject)),
    )
    script = FileSpec(path="build.py", python_valid=True, contains=(f"def {function}",))
    readme = FileSpec(path="README.md", contains=(function,))

    steps = [
        StepSpec(
            name="notes",
            instruction=(
                f"Write the file notes.md about {subject}. It must have exactly the "
                "three headings '## Context', '## Findings' and '## Next steps'."
            ),
            files=(notes,),
        ),
        StepSpec(
            name="data",
            instruction=(
                f"Write the file data.json about {subject}. It must be a JSON object "
                f"with exactly the three keys 'a', 'b' and 'c'. The value of 'a' must "
                f"be the number {number}, the value of 'b' must be the string "
                f"'{subject}' and the value of 'c' must be the list "
                f"['{function}', '{number}']."
            ),
            files=(data,),
        ),
        StepSpec(
            name="script",
            instruction=(
                f"Write the file build.py and the file README.md about {subject}. "
                f"build.py must be a valid Python script that defines a function "
                f"named {function} and prints a line containing the number {number}. "
                f"README.md must mention the function name {function} and the number "
                f"{number}."
            ),
            files=(script, readme),
        ),
    ]
    checks = [
        Check("file_exists", "notes.md"),
        Check("headings", "notes.md", value="## Context"),
        Check("headings", "notes.md", value="## Findings"),
        Check("headings", "notes.md", value="## Next steps"),
        Check("file_exists", "data.json"),
        Check("json_keys", "data.json", value="a,b,c"),
        Check("json_value", "data.json", value=f"a={number}"),
        Check("json_value", "data.json", value=f"b={subject}"),
        Check("file_exists", "build.py"),
        Check("python_valid", "build.py"),
        Check("file_exists", "README.md"),
        Check("contains", "README.md", value=function),
        Check("contains", "README.md", value=str(number)),
    ]
    if with_report:
        steps.append(
            StepSpec(
                name="report",
                instruction=(
                    f"Write the file report.md about {subject}. It must contain a "
                    f"section '## Summary' and the number {number} must appear in it "
                    "exactly as it is written in data.json."
                ),
                files=(FileSpec(path="report.md", headings=("## Summary",)),),
            )
        )
        checks.extend(
            [
                Check("file_exists", "report.md"),
                Check("headings", "report.md", value="## Summary"),
                Check("contains", "report.md", value=str(number)),
            ]
        )
    return TaskSpec(name=f"task{index:02d}-{subject}", steps=tuple(steps), checks=tuple(checks))


def build_tasks() -> list[TaskSpec]:
    """The twenty tasks of the trial."""
    subjects = [
        ("harbour", 11, "build_harbour"),
        ("orchard", 12, "build_orchard"),
        ("lantern", 13, "build_lantern"),
        ("meridian", 14, "build_meridian"),
        ("quarry", 15, "build_quarry"),
        ("beacon", 16, "build_beacon"),
        ("trellis", 17, "build_trellis"),
        ("compass", 18, "build_compass"),
        ("ferry", 19, "build_ferry"),
        ("almanac", 20, "build_almanac"),
        ("vellum", 21, "build_vellum"),
        ("cinder", 22, "build_cinder"),
        ("mariner", 23, "build_mariner"),
        ("granary", 24, "build_granary"),
        ("cairn", 25, "build_cairn"),
        ("sable", 26, "build_sable"),
        ("wicket", 27, "build_wicket"),
        ("pylon", 28, "build_pylon"),
        ("cistern", 29, "build_cistern"),
        ("bramble", 30, "build_bramble"),
    ]
    return [
        _task(index, subject, number, function, with_report=index % 2 == 0)
        for index, (subject, number, function) in enumerate(subjects, start=1)
    ]


#: The task set of the trial.
TASKS: list[TaskSpec] = build_tasks()
