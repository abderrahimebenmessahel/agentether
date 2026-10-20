# Trial protocol (pre-registration)

> **This document is the pre-registration of the trial.**  It was written
> and committed **before** any result file was produced.  The commit of this
> file therefore precedes every result file in `benchmarks/results/`.  If a
> prompt or a parameter had to be changed after the first run, the change is
> recorded below under "Changes after the first run" and applied to *all*
> arms; the earlier results are kept and labelled.

Date of the pre-registration: 2026-10-20.
Author of the trial: the AI assistant, for the maintainer
(Abderrahime BENMESSAHEL).  This is **not** an independent review.

## What is being measured

AgenTether claims three things.  This trial tries to give each of them a
number, and to be honest about what the number does not show.

* **H1**: under injected faults, the *guarded* arm completes more tasks
  correctly than the *naive* arm and than the *simple-retry* arm.
* **H2**: the guarded arm catches a larger share of the false completions
  (a step that claims "completed" without doing the work) than the other
  arms.
* **H3**: the guarded arm costs more: more requests, more tokens and more
  wall clock time.

H1 and H2 are the claims; H3 is the cost.  A result that supports H1 and H2
but not H3 would be a bad trade; a result that supports H3 but not H1/H2
would mean the library is not worth its overhead.

## The arms

All three arms get **the same tasks**, **the same injected fault schedule**
(seeded, identical per task and attempt) and **the same attempt cap**.

| Arm | What it does |
| --- | --- |
| **A: naive** | One call per step.  The telemetry is parsed; if it says "completed", the step is done.  No retry, no check. |
| **B: simple-retry** | The baseline most people would write: retry up to the same attempt cap on a parse failure, an exception or a timeout, with a backoff.  **No** verification, **no** loop detection, **no** drift check. |
| **C: agentether** | The full library: the telemetry contract, the drift checks, the verifiers (`artifacts_exist` plus the content checks of the task), the semantic loop detector, the budget and the circuit breaker. |

The attempt cap is the same for B and C (3 attempts per step).  Arm A never
retries, by definition.

## The task set

Twenty distinct multi-step tasks, three to five steps each, in
`benchmarks/tasks.py`.  Every step asks the model to produce one or more
files, and the harness writes the files the model returns into a sandbox
(path confined, size capped) -- a model cannot touch a filesystem directly.

The tasks are deliberately **harder** than the first trial: several of them
require *cross-file consistency* (a script and a README that must mention the
real function names of the script; a data file whose keys match the keys the
next step has to use; a table that must contain the numbers of the previous
file).  A model that produces a plausible but inconsistent answer is exactly
the failure mode this library is about.

The ground truth of a task is checked by the harness, which the arms never
see: the files must exist, be valid (JSON parses, Python compiles, Markdown
has the required headings) and be consistent with each other.

## The two conditions

| Condition | Faults |
| --- | --- |
| **natural** | None.  Only the model's own mistakes. |
| **injected** | After the model answered, the harness applies **one** fault to the answer with probability 0.20 per attempt.  The fault is drawn from a seeded schedule that is **identical for every arm**. |

The injected faults (each clearly labelled "injected" in the raw results):

1. `drop_file_block` -- the `FILE:` block is removed, so the claim is not backed by a file.
2. `truncate_file` -- the file content is cut in half.
3. `corrupt_telemetry` -- the telemetry JSON is corrupted (invalid JSON).
4. `wrong_step` -- the telemetry reports another step name.
5. `replay_previous` -- the previous answer is replayed (a loop).
6. `lie` -- the telemetry says "completed" while the file block is removed.

The fault schedule is generated from the task index and the attempt number
with a fixed seed, so it is reproducible and identical across arms.

## The models

Free models of **three different families**, queried from the OpenRouter
model list on 2026-10-20:

| Model id | Family |
| --- | --- |
| `minimax/minimax-m3.1-flash:free` | MiniMax |
| `google/gemma-4-31b-it:free` | Google |
| `nvidia/nemotron-3-super-120b-a12b:free` | NVIDIA |

If a model disappears mid-run, it is recorded and the run continues with the
others.  No model is assumed to exist.

## Sample size and what the numbers mean

The free tier limits the run, not the design.  The cap is **400 requests per
model per day** and a global limiter of 15 requests per minute (the observed
limit of the tier was higher, but the run does not use more than the cap).

* Task set: 20 tasks.
* Tasks per cell: **10** (the first 10 of the task set, the same 10 for
  every cell).  The remaining 10 are available for a follow-up run.
* Cells: 3 models x 3 arms x 2 conditions = 18 cells.
* N per cell: 10 tasks.  **A cell with 10 tasks is small**: the Wilson 95%
  interval of a proportion near 0.5 is about +/- 30 percentage points.  Any
  difference that is smaller than that is *not* a result, and it is reported
  as such.

## The statistics

* **Proportions** (completion rate, false completion rate) are reported with
  a **Wilson score 95% interval**, which behaves better than the normal
  approximation for small samples and for proportions near 0 or 1.
* **The comparison is paired**: every arm sees the same tasks and the same
  injected faults, so the comparison is per task.  The **paired difference**
  of the proportions is reported with its Wilson interval on the paired
  counts, and the **effect size** (the difference of the proportions) is
  reported next to it.  No p-value is used as the headline; a p-value on 10
  paired tasks is not informative.
* **Natural and injected are never mixed.**  They are two separate tables.
* No metric is selected after the fact: the table below is the table that is
  reported, whatever it says.

## The metrics

| Metric | Definition |
| --- | --- |
| `correct_completion_rate` | The task is finished **and** every ground truth check passes. |
| `false_completion_rate` | The task is reported as finished **but** a ground truth check fails. |
| `reported_completion_rate` | The task is reported as finished, whatever the truth is. |
| `requests` | The HTTP requests per cell. |
| `tokens` | The input and output tokens per cell. |
| `wall_seconds` | The wall clock time per cell. |
| `verifier_rejections` | The number of times a verifier rejected a completion claim. |
| `loop_detections` | The number of detected loops. |
| `retries` | The attempts beyond the first one. |

## The stopping rules

* The run stops when the cap of 400 requests per model is reached.
* The run stops when a model returns 429 for 5 consecutive attempts (a
  persistent rate limit).
* The runner persists its progress after **every** call, so it can be resumed
  with the same command later.  The resume command is printed at the end.
* Partial results are always saved and reported with the N that was actually
  achieved.

## The frozen prompt rule

The prompts are frozen at the first run.  If a prompt has to be changed
(because, for example, the model consistently misreads the protocol), the
change is:

1. applied to **all** arms,
2. recorded in this document under "Changes after the first run",
3. the results of the earlier run are kept and labelled with the version of
   the prompt they used.

No prompt is tuned to make the guarded arm look better than it is.

## The known limits of this trial (before running it)

* The tasks are synthetic and small.  A real project is not this.
* The model is asked to produce files through a text protocol, not through
  tools.  A real agent with tools behaves differently.
* The injected faults are the ones I thought of.  A real agent fails in ways
  that are not in this list.
* Three free models are not a sample of "agents".
* The guarded arm is a library that I wrote, so the comparison is not
  independent.  The *ground truth checks* are the part that is meant to be
  independent of the library.
* Even a clean win here says nothing about a project of a different shape.

## Changes after the first run

(none yet -- this section is filled in if a change becomes necessary)
