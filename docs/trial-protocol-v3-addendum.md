# The addendum of the protocol of the evidence trial, version 3

> **Status: pre-registered.**  This document was written and committed
> **before** any result file that was collected with the extended task set
> existed.  The commit that adds this file comes before every such result
> file.  The protocol it amends is
> [`docs/trial-protocol-v3.md`](trial-protocol-v3.md), which stays the
> protocol of the run: the twenty hand-written tasks and the results that
> were collected on them are **not** touched by this addendum.
>
> The addendum was decided **before** the new data, and **without regard to
> the results**: no data of the extended set existed when it was written,
> and the rule it fixes is the same for every model, every arm and every
> day.

## 1. Why the number of tasks is extended

**The planned grid of the protocol v3 is 60 tasks per cell** (2 models, 2
conditions, 4 arms, 60 tasks).  **The task set had 20 tasks**
(`benchmarks/tasks_v3.py`).  The grid was therefore **not reachable**: with
`--tasks 20` the runner can never produce more than twenty cells per arm,
and the minimum detectable effect of a paired comparison at N = 20 is
**0.313**, which is larger than any effect the trial could hope to see
besides the complete removal of a whole class of false completions.

The extension is **additive**: the twenty hand-written tasks keep their
names, their order and their index, and the fault schedule is a function of
the *index* of the task, so the schedule of those twenty tasks is
**unchanged**.  The data that were already collected on them stay valid and
stay what they are.

## 2. The generator

**The seed is `20261022`** (`benchmarks/tasks_v3_gen.py:TASK_GENERATOR_SEED`).
It was chosen before the tasks were built, and it is the only source of
randomness of the extension.  The same seed builds the same sixty tasks on
every machine and every version of Python.

**What the generator does.**  It draws a subject, a number and a function
name from fixed pools, and it picks a template.  A generated task has the
**same shape** as a hand-written one:

| | hand-written (tasks 1 to 20) | generated (tasks 21 to 60) |
| --- | --- | --- |
| steps | 3 or 4 | 3 or 4 (the same mix: half of them) |
| files | real files, written by the model | the same |
| cross-file consistency | the number and the function name appear in the data file, in the script, in the readme and in the report | the same |
| hidden ground truth | 13 or 16 checks of the same kinds | the same |
| expectations of the guarded arm | built from the visible specification alone | the same |

The templates differ by the **names** of the files and of the headings
(`notes.md` / `summary.md`, `build.py` / `script.py` / `main.py`,
`README.md` / `GUIDE.md`) and by the wording of the headings.  They are
**equivalent**: the same number of steps, the same number of files and the
same kind of check, so a task of one template is not easier than a task of
another one.

**The subjects of the generated tasks are new**: none of them is a subject
of the trial v2 or of the trial v3, so a task of the grid is never a task
of another run under another name.

**The tests** (`tests/test_task_generator.py`) pin the properties of the
generator: it is deterministic, it produces distinct tasks, the twenty
hand-written tasks are untouched, the ground truth **passes on a correct
solution and fails on a broken one**, and the expectations of the guarded
arm fail on the same broken solution.

## 3. What does not change

* **The arms**: `naive`, `simple-retry`, `agentether-claims-only`,
  `agentether`.  The same prompt, the same attempt cap (3), the same
  settings of the two guarded arms (`strict_order=False`, the breaker
  closed again before every step).
* **The faults**: the seven of the protocol v3 (`drop_file_block`,
  `truncate_file`, `corrupt_telemetry`, `wrong_step`, `replay_previous`,
  `lie`, `hide_file`), the same rate (20 % of the attempts) and the same
  seed of the schedule (**20261021**).  The schedule of the tasks 21 to 60
  is simply the continuation of the same function.
* **The statistics**: the Wilson intervals, the paired differences, the
  exact two-sided McNemar test, the MDE of `1.4 / sqrt(N)` and the
  **sign convention** (arm A minus arm B; a **negative** difference of the
  false completion rate is an improvement).
* **The hypotheses** H1 to H4 and their thresholds.  The rule of the
  verdict is unchanged: a difference smaller than the MDE of the sample is
  **INCONCLUSIVE**, and it is only **SUPPORTED** when the McNemar test
  rejects the null hypothesis.
* **The quota rule**: a run stops **before half** of the documented daily
  quota of its provider, and the counter is kept on disk.

## 4. The stopping rule

* The tasks are run in a **fixed order** (task 1, task 2, ... task 60),
  and **every arm of a task is run before the next task**: a run that
  stops at the cap of the day leaves the tasks that are done complete, so
  the arms of a task are always comparable.
* A run **stops at the daily cap** of its provider, and it is **continued
  on the next day** with the same command.  The stopping is decided by the
  **quota and not by the results**: no task is added, removed or repeated
  because of what it showed, and no run is stopped early because the
  result looked good or bad.
* **No peeking**: the analysis of a partial run is reported as a partial
  run, and the final analysis of a cell is made at **N = 60** or at the
  **quota limit**, whichever comes first.  The verdict of a cell that
  stopped early carries the MDE of the N it reached, so a reader can see
  that the sample was too small to decide.
* The provider that answers `HTTP 429` is **left alone for the day**.
* `HTTP 402` stops the run at once: no request of this project ever needs
  a paid plan.

## 5. The presentation of an unequal N

A run that stops in the middle of a task can leave the arms of a model and
of a condition with a different number of tasks (the run of the first
session of the trial v3 left two arms of the Google model with seven tasks
and two with six).  A rate computed on different sets of tasks is not
comparable, and it is the kind of error that makes a table look better
than it is.

**The rule.**  Every headline rate of a model and of a condition is
computed on the **common set of tasks**: the tasks that **every** arm of
that model and of that condition completed.  The paired analysis is made on
**the same set**.  The number of tasks that was dropped for this reason is
**shown** in the table, so a reader can see what the common set cost.

**The test** (`tests/test_evidence_consistency.py`) fails when a table of
the evidence document mixes two different numbers of tasks in the same
comparison, and the document is **generated** from the raw cells: it is
never edited by hand.

## 6. The mechanism and the natural frequency are reported separately

The primary endpoint of the trial v3 is the false completion rate **under
the injected faults**.  The faults are designed, and one of them
(`hide_file`) is designed to be caught **only** by the declarative
expectations.  The evidence for the real-world value of `expects` must
therefore not rest on that fault alone.

**The rule.**  Two numbers are reported **separately**, per model:

1. the **mechanism** result: the false completion rate under the injected
   faults, with the Wilson interval;
2. the **natural** frequency of the false completions of the kind
   "**a required file was never produced and the claim did not mention
   it**", measured in the **natural** condition (no fault is injected),
   with its Wilson interval.

The second number is the one that says how often the real-world failure
happens on its own.  A mechanism that catches a frequent failure is worth
more than a mechanism that catches a rare one, and the two numbers must
both be read.

## 7. The third model

A **local** model (Ollama) joins the trial as a **third model**.  It has
**no quota**: the local compute is free, so the rule of the half of the
daily quota does not apply to it, and the caps of the day are only a
safety net.

The model must **pass the capability probe** of the protocol v2 (it
follows the protocol, its telemetry parses, it honours a low temperature)
before it takes part.  A small local model is **expected** to fail more
often than a free cloud model: that is not a defect of the model but the
property that makes the measurement interesting, because the guard can only
show its effect where there is something to catch.  The local model is
**never** mixed with the cloud models: it has its own rows, its own
verdicts and its own MDE.

## 8. The minimum detectable effect per achieved N

The MDE of a paired comparison, with alpha = 0.05 (two sided), power =
80 % and the conservative assumption that half of the pairs are discordant,
is `1.4 / sqrt(N)`:

| N per cell | MDE of the paired difference |
| --- | --- |
| 60 | 0.181 |
| 50 | 0.198 |
| 40 | 0.221 |
| 30 | 0.256 |
| 24 | 0.286 |
| 20 | 0.313 |
| 16 | 0.350 |
| 12 | 0.404 |
| 8 | 0.495 |
| 6 | 0.571 |
| 4 | 0.700 |
| 3 | 0.808 |
| 2 | 0.990 |

**The verdict of a cell carries the MDE of the N it reached.**  A
difference smaller than that MDE is **INCONCLUSIVE**, which is not a polite
word for "not supported": it means the sample was too small to say
anything either way.

## 9. What does not change in the data that were already collected

* The twenty hand-written tasks keep their **names**, their **order** and
  their **index**.
* The **fault schedule** of those tasks is unchanged: it is a function of
  the seed, of the index of the task, of the index of the step and of the
  number of the attempt, and none of them moved.
* The **results** of the first session of the trial v3 are kept as they
  are, and they are re-analysed with the **common-set rule** of the
  section 5, which is a presentation rule and not a change of the data.
* The data of the trial v2 stay a **supplementary** run and are not mixed
  with the data of the trial v3.

## 10. What will not be done

* No money will be spent, no credit will be bought, no payment method will
  be added and no key will be rotated.
* The repository will not be made public, nothing will be published to
  PyPI and no tag will be pushed without the maintainer.
* A null result will be published as a null result.
* The number of tasks of a cell will never be chosen because of the
  results.
