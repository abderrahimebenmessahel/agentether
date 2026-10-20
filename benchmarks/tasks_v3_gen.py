"""The procedural extension of the task set of the trial v3.

The protocol of the trial v3 planned **60 tasks per cell** and the task set
had **20**.  The set was extended by a **seeded procedural generator**: the
tasks it builds have the same shape as the twenty hand-written ones (3 or 4
steps, real files, a cross-file consistency requirement, a hidden ground
truth) and they differ from them by their subject, their number, their
function name and the names of their files.

**The twenty hand-written tasks are not touched.**  They are the tasks of the
first session of the trial v3 and their results stay valid: the first
twenty tasks of the combined set are the twenty hand-written ones, in the
same order, and the fault schedule is a function of the *index* of the task,
so the schedule of those twenty tasks is unchanged as well.

**The seed is declared in the protocol** (``docs/trial-protocol-v3-addendum.md``)
and it is the only source of randomness: the same seed always builds the
same tasks, on every machine and every version of Python.

The generator is **deterministic by construction**:

* the subjects, the numbers and the verbs are drawn from **fixed pools**
  that are shuffled with the seed and cut at the requested length, so the
  first *n* subjects do not depend on the *n* that is asked for;
* the template of a task and its headings are drawn from the seed of the
  task itself, so a task does not depend on the tasks before it.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from tasks import Check, FileSpec, StepSpec, TaskSpec
from tasks_v3 import TASKS_V3

__all__ = [
    "GENERATED_TASK_COUNT",
    "NUMBER_POOL",
    "SUBJECT_POOL",
    "TASKS_V3_FULL",
    "TASK_GENERATOR_SEED",
    "TEMPLATES",
    "Template",
    "build_generated_task",
    "build_generated_tasks",
    "build_task_set_v3",
]

#: The seed of the generator of the tasks 21 to 60.  It is **declared in
#: the protocol** (``docs/trial-protocol-v3-addendum.md``) and it was
#: chosen before the tasks were built, not after a result was seen.
TASK_GENERATOR_SEED = 20261022

#: The number of generated tasks.  The hand-written set has twenty tasks
#: and the grid of the protocol needs sixty: twenty plus forty.
GENERATED_TASK_COUNT = 40

#: The subjects of the generated tasks.  None of them is a subject of the
#: trial v2 or of the trial v3, so a task of the grid is never a task of
#: another run with another name.  The pool is longer than the number of
#: tasks so that the pool can be cut at any length without changing the
#: tasks that come first.
SUBJECT_POOL: tuple[str, ...] = (
    "airfield",
    "anchorage",
    "arboretum",
    "armature",
    "atelier",
    "auction",
    "aviary",
    "bandstand",
    "barracks",
    "boatyard",
    "bookshop",
    "bottling",
    "brickyard",
    "buttery",
    "canteen",
    "cardroom",
    "carpentry",
    "cartage",
    "chandlery",
    "chapel",
    "charcoal",
    "cheesery",
    "chimney",
    "cobbler",
    "copperworks",
    "cornfield",
    "cottage",
    "creamery",
    "customs",
    "dairyman",
    "dyehouse",
    "elevator",
    "emporium",
    "enginehouse",
    "estate",
    "factory",
    "farmstead",
    "foundry",
    "glasshouse",
    "glassworks",
    "gristmill",
    "hall",
    "hangar",
    "hearth",
    "hopfield",
    "inn",
    "ironworks",
    "joinery",
    "kiln",
    "laundry",
    "lighthouse",
    "linen",
    "lumberyard",
    "machine",
    "maltings",
    "masons",
    "millrace",
    "mineral",
    "mint",
    "moor",
    "netloft",
    "observatory",
    "oilfield",
    "outworks",
    "packhouse",
    "papermill",
    "parlour",
    "pasture",
    "peat",
    "pharmacy",
    "plantation",
    "pottery",
    "press",
    "quern",
    "rectory",
    "ropewalk",
    "sawpit",
    "shipyard",
    "silkworks",
    "smithy",
    "stables",
    "station",
    "store",
    "studio",
    "sugarhouse",
    "taphouse",
    "teahouse",
    "timber",
    "tinsmith",
    "tollgate",
    "turret",
    "vintners",
    "wainwright",
    "watermill",
    "weaver",
    "wheelhouse",
    "windmill",
    "woodyard",
    "workshop",
)

#: The numbers of the generated tasks.  They are two or three digits long,
#: like the numbers of the hand-written tasks.
NUMBER_POOL: tuple[int, ...] = tuple(range(60, 200))

#: The verbs of the function names of the generated tasks.
VERB_POOL: tuple[str, ...] = (
    "assemble",
    "build",
    "compose",
    "compile",
    "craft",
    "design",
    "draft",
    "make",
    "plan",
    "prepare",
    "render",
)

#: The sets of the headings of the notes file.  Every set has three
#: headings, like the set of the hand-written tasks.
HEADING_SETS: tuple[tuple[str, ...], ...] = (
    ("## Context", "## Findings", "## Next steps"),
    ("## Context", "## Observations", "## Next steps"),
    ("## Context", "## Findings", "## Actions"),
)

#: The headings of the report file.
REPORT_HEADINGS: tuple[str, ...] = ("## Summary", "## Overview")


@dataclass(frozen=True)
class Template:
    """The shape of a generated task.

    A template says which files the steps of a task ask for.  The templates
    are **equivalent**: they have the same number of steps, the same number
    of files and the same kind of ground truth check, so a task of one
    template is not easier than a task of another one.

    Attributes:
        name: The name of the template.
        notes_step: The name of the step of the notes.
        notes_path: The path of the notes.
        data_path: The path of the data file.
        script_step: The name of the step of the script.
        script_path: The path of the script.
        readme_path: The path of the readme.
        report_path: The path of the report.
    """

    name: str
    notes_step: str
    notes_path: str
    data_path: str
    script_step: str
    script_path: str
    readme_path: str
    report_path: str


#: The templates of the generated tasks.
TEMPLATES: tuple[Template, ...] = (
    Template(
        name="ledger",
        notes_step="notes",
        notes_path="notes.md",
        data_path="data.json",
        script_step="script",
        script_path="build.py",
        readme_path="README.md",
        report_path="report.md",
    ),
    Template(
        name="dossier",
        notes_step="summary",
        notes_path="summary.md",
        data_path="data.json",
        script_step="script",
        script_path="script.py",
        readme_path="README.md",
        report_path="report.md",
    ),
    Template(
        name="record",
        notes_step="notes",
        notes_path="notes.md",
        data_path="data.json",
        script_step="code",
        script_path="main.py",
        readme_path="GUIDE.md",
        report_path="report.md",
    ),
)


def _shuffled(pool: tuple[Any, ...], seed: int) -> list[Any]:
    """A deterministic shuffle of a pool.

    The whole pool is shuffled and not a prefix of it, so the first *n*
    items of the result do not depend on *n*: a task keeps its subject when
    the grid grows.
    """
    items = list(pool)
    random.Random(seed).shuffle(items)
    return items


def _plan(seed: int, count: int) -> list[tuple[str, int, str]]:
    """The parameters of the generated tasks.

    The subjects, the numbers and the verbs are drawn from the pools with
    three **independent** shuffles, so the subjects of two tasks differ
    and the functions of two tasks differ.
    """
    subjects = _shuffled(SUBJECT_POOL, seed)
    numbers = _shuffled(NUMBER_POOL, seed + 1)
    verbs = _shuffled(VERB_POOL, seed + 2)
    return [
        (
            str(subjects[index]),
            int(numbers[index]),
            f"{verbs[index % len(verbs)]}_{subjects[index]}",
        )
        for index in range(count)
    ]


def build_generated_task(
    index: int,
    subject: str,
    number: int,
    function: str,
    template: Template,
    headings: tuple[str, ...],
    report_heading: str,
    with_report: bool,
) -> TaskSpec:
    """Build one generated task.

    The task has the shape of the tasks of the trial v3: three steps (four
    when it has a report), real files, and a consistency requirement that
    spans the files (the number and the function name appear in the data
    file, in the script, in the readme and in the report).

    The **visible** specification of a step says what the step must
    produce, and the **hidden** ground truth checks it.  The arms never see
    the ground truth, and the expectations of the guarded arm are built
    from the visible specification alone (see :func:`tasks.expectations_of`).

    Args:
        index: The index of the task in the set (21 to 60).
        subject: The subject of the task.
        number: The number of the task.
        function: The name of the function of the task.
        template: The template of the task.
        headings: The headings of the notes file.
        report_heading: The heading of the report file.
        with_report: Whether the task has a fourth step.

    Returns:
        The task.
    """
    notes = FileSpec(path=template.notes_path, headings=headings)
    data = FileSpec(
        path=template.data_path,
        json_keys=("a", "b", "c"),
        json_values=(("a", str(number)), ("b", subject)),
    )
    script = FileSpec(
        path=template.script_path,
        python_valid=True,
        contains=(f"def {function}", str(number)),
    )
    readme = FileSpec(path=template.readme_path, contains=(function, str(number)))

    steps = [
        StepSpec(
            name=template.notes_step,
            instruction=(
                f"Write the file {template.notes_path} about {subject}. It must have "
                f"exactly the three headings '{headings[0]}', '{headings[1]}' and "
                f"'{headings[2]}'."
            ),
            files=(notes,),
        ),
        StepSpec(
            name="data",
            instruction=(
                f"Write the file {template.data_path} about {subject}. It must be a JSON "
                "object with exactly the three keys 'a', 'b' and 'c'. The value of 'a' "
                f"must be the number {number}, the value of 'b' must be the string "
                f"'{subject}' and the value of 'c' must be the list "
                f"['{function}', '{number}']."
            ),
            files=(data,),
        ),
        StepSpec(
            name=template.script_step,
            instruction=(
                f"Write the file {template.script_path} and the file "
                f"{template.readme_path} about {subject}. {template.script_path} must be "
                f"a valid Python script that defines a function named {function} and "
                f"prints a line containing the number {number}. {template.readme_path} "
                f"must mention the function name {function} and the number {number}."
            ),
            files=(script, readme),
        ),
    ]
    checks = [
        Check("file_exists", template.notes_path),
        Check("headings", template.notes_path, value=headings[0]),
        Check("headings", template.notes_path, value=headings[1]),
        Check("headings", template.notes_path, value=headings[2]),
        Check("file_exists", template.data_path),
        Check("json_keys", template.data_path, value="a,b,c"),
        Check("json_value", template.data_path, value=f"a={number}"),
        Check("json_value", template.data_path, value=f"b={subject}"),
        Check("file_exists", template.script_path),
        Check("python_valid", template.script_path),
        Check("file_exists", template.readme_path),
        Check("contains", template.readme_path, value=function),
        Check("contains", template.readme_path, value=str(number)),
    ]
    if with_report:
        steps.append(
            StepSpec(
                name="report",
                instruction=(
                    f"Write the file {template.report_path} about {subject}. It must "
                    f"contain a section '{report_heading}' and the number {number} must "
                    "appear in it exactly as it is written in "
                    f"{template.data_path}."
                ),
                files=(
                    FileSpec(
                        path=template.report_path,
                        headings=(report_heading,),
                        contains=(str(number),),
                    ),
                ),
            )
        )
        checks.extend(
            [
                Check("file_exists", template.report_path),
                Check("headings", template.report_path, value=report_heading),
                Check("contains", template.report_path, value=str(number)),
            ]
        )
    return TaskSpec(
        name=f"task{index:02d}-{subject}",
        steps=tuple(steps),
        checks=tuple(checks),
    )


def build_generated_tasks(
    seed: int = TASK_GENERATOR_SEED,
    count: int = GENERATED_TASK_COUNT,
    start_index: int = len(TASKS_V3) + 1,
) -> list[TaskSpec]:
    """Build the generated tasks of the trial v3.

    The tasks are numbered from ``start_index`` (21) so that the name of a
    task of the grid is unique: the twenty hand-written tasks are named
    ``task01-`` to ``task20-``.

    Args:
        seed: The seed of the generator.
        count: The number of tasks to build.
        start_index: The index of the first generated task.

    Returns:
        The tasks, in the order of their index.
    """
    plan = _plan(seed, count)
    tasks: list[TaskSpec] = []
    for offset, (subject, number, function) in enumerate(plan):
        index = start_index + offset
        rng = random.Random(f"{seed}:{index}")
        template = TEMPLATES[rng.randrange(len(TEMPLATES))]
        headings = HEADING_SETS[rng.randrange(len(HEADING_SETS))]
        report_heading = REPORT_HEADINGS[rng.randrange(len(REPORT_HEADINGS))]
        # The alternation of the hand-written tasks: an even index has the
        # report step, an odd index does not.
        tasks.append(
            build_generated_task(
                index=index,
                subject=subject,
                number=number,
                function=function,
                template=template,
                headings=headings,
                report_heading=report_heading,
                with_report=index % 2 == 0,
            )
        )
    return tasks


def build_task_set_v3() -> list[TaskSpec]:
    """The whole task set of the trial v3: the hand-written tasks and the generated ones."""
    return [*TASKS_V3, *build_generated_tasks()]


#: The sixty tasks of the trial v3.
TASKS_V3_FULL: list[TaskSpec] = build_task_set_v3()
