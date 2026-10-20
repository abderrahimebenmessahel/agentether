# The protocol of the evidence trial, version 3

> **Status: pre-registered.**  This document was written and committed
> **before** the first result file of the trial v3 existed.  The commit that
> adds this file comes before every result file of the trial v3.  The data
> of the trial v2 stay in the repository and stay a **supplementary** run:
> they are not replaced, they are not re-analysed as a confirmatory run.
>
> The deviations from the protocol v2 are stated in the section 1, and they
> were decided **before** any new data was collected, not after seeing a
> result.

## 1. The deviation from the protocol v2, stated openly

The protocol v2 selected the models with a **band**: the success rate of
the naive arm on a 20 task pilot had to be between **30 % and 85 %**.  The
band exists to keep the *correct completion* rate from having no room to
move.

**The band was not satisfiable by the models that had quota.**  The two
models that satisfied it were the two of Groq, and the daily quota of Groq
was spent by the capability probe and the pilots (130 000 of the 200 000
documented tokens per day).  The two models that *had* the budget (Cerebras
and Google) were excluded by the band for being too good: the naive arm
reached 0.950 and 0.944 on the pilot.  The rule was applied and reported as
it was written, and the trial v2 is a **supplementary** run of two models
the rule excludes.

**The deviation of the protocol v3.**  The primary endpoint of the trial v3
is the **false completion rate under the injected faults**.  A ceiling
effect on the naive success rate does not hide that effect: a model that
solves the tasks perfectly still produces false completions when the
harness removes or damages its file, and the question "does the library
catch it?" does not depend on how good the model is.  The selection rule of
the v3 is therefore:

> A model takes part in the trial v3 when it **passes the capability probe**
> of the protocol v2 (it follows the protocol, its telemetry parses, it
> honours a low temperature) **and it has quota** for the run.  **There is
> no band on the naive success rate.**

This is a deviation of the protocol, decided **before** the new data, and
not after a result.  The v2 data are kept and labelled.

## 2. What the trial is for

AgenTether claims that the *claims* of an agent step can be **checked**
instead of trusted.  The trial asks whether that makes a measurable
difference on real models, with real tasks, and what it costs.

The **belief** of an arm and the **ground truth** are two separate columns
of the result files; they are never mixed.  A false completion is a cell
whose arm believes the task is done while the ground truth says it is not.

The analysis of the false completions of the trial v2
([`docs/false-completions.md`](false-completions.md)) found that a verifier
that checks only the files the agent **claims** catches a false completion
whose artifact is **missing** and cannot catch one whose artifact is
**damaged but present**.  The trial v3 measures the fix.

## 3. The hypotheses

| | Hypothesis |
| --- | --- |
| **H1** (secondary) | Under the injected faults, the guarded arm completes more tasks correctly than the simple-retry baseline. |
| **H2** (PRIMARY) | Under the injected faults, the guarded arm **catches more false completions**: fewer of its beliefs are wrong. |
| **H3** (secondary) | The guarded arm costs more: more requests, more tokens and more wall clock time than the baseline. |
| **H4** (secondary, **new**) | The declarative expectations **add** something to the old configuration: the arm that declares what the step must produce has fewer false completions than the arm that only checks the claimed files. |

Each hypothesis is reported as **SUPPORTED**, **NOT SUPPORTED** or
**INCONCLUSIVE**.  "Inconclusive" is the honest verdict when the effect is
smaller than the minimum detectable effect of the sample; it is not a
polite word for "not supported".

## 4. The arms

The four arms see the **same tasks**, the **same prompt**, the **same
fault schedule** and the **same attempt cap** (3 attempts per step for the
three arms that retry).  They differ only in the way they supervise a
claim.

| Arm | What it does |
| --- | --- |
| **A: naive** | One call per step.  The claim of the model is trusted. |
| **B: simple-retry** | Retry a step whose answer does not satisfy the telemetry contract, or whose call failed, up to 3 attempts.  No verification of the files, no loop detection, no drift check. |
| **C: agentether-claims-only** | The full library with the verifier `artifacts_exist()`: the files the agent **claims** must exist.  This is the configuration of the trial v2, kept unchanged so that the contribution of the expectations is measured on its own. |
| **D: agentether** | The full library **with the declarative expectations** of the step: the files the step must produce must exist and must satisfy the declaration. |

**What the expectations of arm D are built from.**  They are built from the
**visible step specification** of the task (the `FileSpec` of the step: the
paths, the required content, the required keys and values, the required
headings and the syntax check).  The **hidden ground truth** of the task
(the `checks`) is never used and never seen by any arm.  The expectations
are a *developer* declaration, exactly as they are in a real project: the
developer knows what the step owes.

**The settings of arms C and D** are the documented deviations of the
protocol v2 and they are the same in every run:

1. `strict_order=False`: the roadmap order is not enforced, so a step that
   could not be done does not stop the task.
2. The breaker is closed again before every step: the steps of a task are
   independent.
3. The prompt of arms C and D is the one the library builds
   (`ctx.build_prompt`): the task, the roadmap position, the project memory
   and the corrective hint of the previous attempt.  Arms A and B repeat the
   same prompt on every attempt.  This is a **confound of the correct
   completion rate** (H1) and it is reported as such; it does not touch the
   false completion rate (H2, H4), which is the primary endpoint.

**The order of the arms inside a task** is the order above, and the order of
the models, of the conditions and of the tasks is fixed: every arm of a
task sees the same tasks and the same faults whatever the order.

## 5. The conditions

The two conditions are reported **separately** and never mixed.

| Condition | What it is |
| --- | --- |
| **injected** | A fault is injected into 20 % of the attempts, **after** the model answered and **before** the library verifies the step, and it is labelled as injected.  This is the **primary** condition. |
| **natural** | No fault is injected.  The failures are the ones the model makes by itself. |

**The order of the conditions.**  The injected condition is run **first**,
because it carries the primary endpoint, and the natural condition is run
with what is left of the budget of the day.  A run that cannot reach both
says so, with the arithmetic.

**The fault schedule** is a **function** of the task, the step and the
attempt number *inside that step*:
`random.Random(f"{seed}:{task}:{step}:{attempt}")`.  Every arm therefore
meets the same schedule; an arm that retries more simply walks further
along it.  The seed of the trial v3 is **20261021** (the seed of the trial
v2 was 20261020) and the task set is **new**.

**The seven faults** of the v3 are the six of the v2 plus one:

| Fault | What it does | Who catches it |
| --- | --- | --- |
| `drop_file_block` | Every file block of the answer is removed; the claim stays. | A: no.  B: no.  C: yes (the claimed file does not exist).  D: yes. |
| `truncate_file` | The first file of the answer is cut in half; the claim stays. | A: no.  B: no.  C: **no** (the file exists).  D: yes (the content does not satisfy the declaration). |
| `corrupt_telemetry` | The telemetry JSON is broken. | Nobody: the claim is not "completed", the step does not complete. |
| `wrong_step` | The telemetry names another step. | Nobody (the claim is not "completed").  C and D also raise a drift error. |
| `replay_previous` | The answer of the previous step replaces the answer of this one. | A: no.  B: **no** (the baseline does not check the name of the step).  C and D: yes (the drift check). |
| `lie` | The claim stays, the file block goes. | A: no.  B: no.  C: yes.  D: yes. |
| `hide_file` **(new)** | A file block is removed **and** the path is removed from the list of the artifacts of the claim. | A: no.  B: no.  C: **no** (the files it claims exist).  D: yes (the file the step owes is missing). |

`hide_file` is the fault of the mechanism that the trial v2 could not
measure: the model never produces a file and the claim mentions only the
files it did produce.  The analysis of the trial v2 found **no** case of it
(the six faults of the v2 could not produce it), so the v3 adds it.

## 6. The tasks

**New tasks.**  The trial v3 does not reuse the tasks of the trial v2: the
task set of the v3 is in `benchmarks/tasks_v3.py` and it has the same shape
(3 or 4 steps, real files, a cross file consistency requirement) with
**new subjects, new numbers and new function names**.

The ground truth of a task is a list of checks that the arms never see: the
files must exist, be valid and be *consistent with each other*.  The
visible specification of a step says which files it must produce and what
they must contain; the checks repeat that requirement in the form the
ground truth uses.

**The tasks are the same for every arm and every model**, and the same
fault schedule is applied to every arm.

## 7. The models and the parameters

| | Model | Provider | Free tier | Parameters |
| --- | --- | --- | --- | --- |
| 1 | `gpt-oss-120b` | Cerebras | the documented free tier | temperature 0, seed 20261021 |
| 2 | `gemini-3.5-flash-lite` | Google AI Studio | the documented free tier | temperature 0, **no seed** (the provider has none for the chat completions) |

A model that fails the capability probe of the protocol v2 is not used.
**Only the free tier is used**: no credit is bought, no payment method is
added, no key is rotated and no model whose freedom is not documented is
called.  The 50 % rule of the maintainer applies: a run stops before
**half** of the documented daily quota of its provider is used.

Every cell records the model id, the provider, the date, the temperature,
the seed and the parameters of the request.

## 8. The size of the sample, and the full grid

**The planned grid** is 60 tasks per cell, 4 arms, 2 conditions and 2
models: 2 x 2 x 4 x 60 = **960 cells**.

The measured cost of the trial v2 (the requests and the tokens of the raw
cells) is the estimate of the v3:

| Model | Requests per cell | Tokens per cell | Requests of the grid (960 cells, two models) | Tokens of the grid |
| --- | --- | --- | --- | --- |
| cerebras gpt-oss-120b | 2.6 - 3.9 | 2 600 - 3 700 | about 1 500 (four arms) | about 1.4 million |
| google gemini-3.5-flash-lite | 3.5 - 3.9 | 2 100 - 3 700 | about 1 900 (four arms) | about 1.3 million |

**The grid does not fit in the free tier of one day.**  The half of the
documented daily quotas is 500 requests and 500 000 tokens for Cerebras
(1 000 requests and 1 000 000 tokens per day) and 750 requests for Google
(1 500 requests per day; **the token limit of Google is not published** and
is marked UNVERIFIED in `docs/providers.md`).

| Model | The grid needs | The days it needs |
| --- | --- | --- |
| cerebras gpt-oss-120b | 1 500 requests, 1.4 million tokens | **3 days** |
| google gemini-3.5-flash-lite | 1 900 requests | **3 days** (the token limit is unknown) |

The run is therefore **spread over the days**: each day runs what fits
under the cap of the day, the progress file is resumable, and the exact
resume command is printed at the end of every session.

**The N that is actually run is decided by the quota of the day**, and the
achieved N and its MDE are reported with the results.  A run that cannot
reach N = 60 says so, with the arithmetic, instead of pretending.

## 9. The minimum detectable effect

The **MDE** of a paired comparison, with alpha = 0.05 (two sided), power
= 80 % and the conservative assumption that half of the pairs are
discordant, is `1.4 / sqrt(N)`:

| N per cell | MDE of the paired difference | MDE with a discordance of 0.3 |
| --- | --- | --- |
| 60 | 0.181 | 0.166 |
| 22 | 0.298 | 0.273 |
| 8 | 0.495 | 0.454 |
| 12 (the v2) | 0.404 | 0.371 |

A difference that is smaller than the MDE of the sample is **inconclusive**,
not "a small effect".

## 10. The statistics

* The proportion of every cell is reported with a **Wilson 95 % interval**.
* The arms are compared **paired**, on the identical tasks and the
  identical fault schedule: the report gives the number of the pairs where
  only one arm was right (the discordant pairs) and the difference of the
  two rates.
* The p value is the **exact two sided McNemar test** of the discordant
  pairs.
* **One sign convention for the whole document**: every paired difference
  is **arm A minus arm B**, and A is the first arm of the comparison.  A
  **positive** difference of the correct completion rate is an
  improvement; a **NEGATIVE** difference of the false completion rate is
  an improvement.  The convention is stated once, in the document itself.
* **No cherry-picking**: the tables are computed from the raw cells by
  `benchmarks/evidence.py`, and the document is regenerated from the raw
  file, never edited by hand.  A test compares every total of the document
  with the raw cells.
* The conditions are never mixed, and the models are never pooled.

## 11. The prompt is frozen

The prompt of a step is built by `benchmarks/harness.py:build_prompt` and
it is **the same for every arm and every model** of the trial v3.  It is
frozen now, with its hash:

```text
sha256(PROTOCOL) = 361b1a1d8d07b455de0097aee84f618c05d401cf458fdd3d1828c272d8ecff12
```

The prompt of the trial v3 asks for **four** backticks around the file
blocks.  The prompt of the trial v2 asked for three, and the parser of the
v2 closed a file on the next fence: a Markdown file that shows how to run
the script was cut in the middle, and three of the seventeen false
completions of the v2 were caused by that and not by the model.  The
parser of the v3 follows the rule of CommonMark, and the change of the
prompt is a **defect of the harness of the v2**, fixed before the data of
the v3.

After the freeze, a change of the prompt is a **bug fix**: it is
documented in `docs/WORKLOG.md`, it is applied to **every** arm and
**every** model, and the data collected before it are kept and labelled.

## 12. The stopping rules

* A run stops **before** half of the daily quota of its provider is used
  (the counter is written to disk with an atomic replace, so a resumed run
  continues on it and cannot start the day from zero).
* A run stops on `HTTP 402` (a request that needs a paid plan): the
  provider is reported at once and no further call is made.
* A run stops on a rate limit that does not go away; the progress file
  keeps the cells that are done, and the exact command to continue is
  printed.
* The raw cells are written after **every** cell (one JSON line per
  cell), so an interrupted run loses at most one cell.

## 13. What will not be done

* No money will be spent, no credit will be bought and no payment method
  will be added.
* The repository will not be made public, nothing will be published to
  PyPI and no tag will be pushed without the maintainer.
* A null result will be published as a null result.
* The data of the trial v2 will not be deleted, re-run or presented as a
  confirmatory run.
