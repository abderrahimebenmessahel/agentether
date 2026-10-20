"""The task set of the trial v3.

The tasks of the trial v3 are **new**: new subjects, new numbers and new
function names.  They have the same shape as the tasks of the trial v2
(3 or 4 steps, real files, a cross file consistency requirement) and the
same kind of hidden ground truth, but they are not the tasks of the v2 and
the fault schedule of the v3 uses another seed.

**The visible specification and the ground truth.**  The visible
specification of a step (the ``FileSpec`` of the step) says what the step
must produce, and the ground truth of the task (the ``Check`` of the task)
checks it.  In the v3 the two say the **same** thing: the visible
specification of a step states the files, the content, the keys, the
values, the headings and the syntax that the ground truth checks.  The
expectations of the ``agentether`` arm are built from the visible
specification alone (see :func:`tasks.expectations_of`), and they are
therefore as strong as the ground truth: an arm with expectations can only
fail a task that the ground truth also fails.

The ground truth is never shown to any arm.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

from tasks import Check, FileSpec, StepSpec, TaskSpec

__all__ = ["TASKS_V3", "build_task_v3", "build_tasks_v3"]

#: The subjects of the trial v3: new ones, with a new number and a new
#: function name each.
SUBJECTS_V3: tuple[tuple[str, int, str], ...] = (
    ("bakery", 32, "build_bakery"),
    ("clinic", 33, "build_clinic"),
    ("depot", 34, "build_depot"),
    ("forge", 35, "build_forge"),
    ("garden", 36, "build_garden"),
    ("mill", 37, "build_mill"),
    ("nursery", 38, "build_nursery"),
    ("paddock", 39, "build_paddock"),
    ("refinery", 40, "build_refinery"),
    ("sawmill", 41, "build_sawmill"),
    ("tannery", 42, "build_tannery"),
    ("vineyard", 43, "build_vineyard"),
    ("warehouse", 44, "build_warehouse"),
    ("wharf", 45, "build_wharf"),
    ("yardarm", 46, "build_yardarm"),
    ("ziggurat", 47, "build_ziggurat"),
    ("apiary", 48, "build_apiary"),
    ("brewery", 49, "build_brewery"),
    ("cannery", 50, "build_cannery"),
    ("distillery", 51, "build_distillery"),
)


def build_task_v3(
    index: int,
    subject: str,
    number: int,
    function: str,
    with_report: bool,
) -> TaskSpec:
    """Build one task of the trial v3.

    The steps have the same shape as the steps of the trial v2, and the
    visible specification of a step says exactly what the ground truth
    checks.
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
    script = FileSpec(
        path="build.py",
        python_valid=True,
        contains=(f"def {function}", str(number)),
    )
    readme = FileSpec(path="README.md", contains=(function, str(number)))

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
                "with exactly the three keys 'a', 'b' and 'c'. The value of 'a' must "
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
                files=(
                    FileSpec(
                        path="report.md",
                        headings=("## Summary",),
                        contains=(str(number),),
                    ),
                ),
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


def build_tasks_v3() -> list[TaskSpec]:
    """The twenty tasks of the trial v3."""
    return [
        build_task_v3(index, subject, number, function, with_report=index % 2 == 0)
        for index, (subject, number, function) in enumerate(SUBJECTS_V3, start=1)
    ]


#: The task set of the trial v3.
TASKS_V3: list[TaskSpec] = build_tasks_v3()
