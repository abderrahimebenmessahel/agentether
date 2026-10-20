# The protocol of the evidence trial, version 2

> **Status: pre-registered.**  This document was written and committed
> **before** the first confirmatory result file of the trial v2 existed.
> The commit that adds this file comes before every result file of the
> confirmatory run.  The run 1 results (`docs/evidence.md`, run 1) are
> **not** a comparison of the three arms; the six defects of the harness
> that made them invalid are listed there and fixed in
> `benchmarks/harness.py`.

## 1. What the trial is for

AgenTether claims that the *claims* of an agent step can be **checked**
instead of trusted.  The trial asks whether that makes a measurable
difference on real models, with real tasks, and what it costs.

The primary endpoint is the **false completion rate**: how often an arm
believes that a task is done when the ground truth says it is not.  The
belief of an arm and the ground truth are two **separate columns** of the
result files; they are never mixed.

## 2. The hypotheses

| | Hypothesis |
| --- | --- |
| **H1** (secondary) | Under the injected faults, the guarded arm completes more tasks correctly than the simple-retry baseline. |
| **H2** (PRIMARY) | Under the injected faults, the guarded arm **catches more false completions**: fewer of its beliefs are wrong. |
| **H3** (secondary) | The guarded arm costs more: more requests, more tokens and more wall clock time than the baseline. |

Each hypothesis is reported as **SUPPORTED**, **NOT SUPPORTED** or
**INCONCLUSIVE**.  "Inconclusive" is the honest verdict when the interval
of the effect contains zero differences of any interest; it is not a
polite word for "not supported".

## 3. The arms

The three arms see the **same tasks**, the **same prompt**, the **same
fault schedule** and the **same attempt cap** (3 attempts per step for
B and C).  They differ only in the way they supervise a claim.

| Arm | What it does | What it does **not** do |
| --- | --- | --- |
| **A: naive** | One call per step.  The claim of the model is trusted. | It never retries, never checks a file and never reads the contract. |
| **B: simple-retry** | Retry a step whose answer does not satisfy the telemetry contract, or whose call failed, up to 3 attempts. | It never checks a file, never detects a loop and never checks the drift. |
| **C: agentether** | The whole library: the telemetry contract, the drift checks, the verifiers, the loop detector, the budget and the breaker. | It does not use the hidden ground truth of the task. |

Three settings of arm C are **documented deviations**, and they are the
same in every run:

1. `strict_order=False`: the roadmap order is not enforced, so a step
   that could not be done does not stop the task.  Arms A and B walk
   through every step whatever happened, and the trial compares the
   supervision of the claims, not the enforcement of the roadmap.
2. The breaker is closed again before every step: the steps of a task are
   independent, and the other arms move on when a step is hopeless.
3. The verifier is `artifacts_exist()`: the files the model **claims**
   must exist.  It does not use the hidden ground truth, which would give
   arm C an unfair advantage.  A verifier that checks the *content* of a
   file would need the knowledge of the task, so it is not used.

**A confound that is reported, not hidden.**  Arm C sends the prompt that
the library builds (`ctx.build_prompt`): the task, the roadmap position,
the project memory, the telemetry contract and the corrective hint of the
previous attempt.  Arms A and B repeat the same prompt on every attempt.
This makes the **correct completion rate** (H1) a comparison of two
things at once (the verification *and* the context).  It does **not** touch
the false completion rate (H2), which is the primary endpoint: a claim is
a claim whatever the prompt was.

## 4. The conditions

The two conditions are reported **separately** and never mixed.

| Condition | What it is |
| --- | --- |
| **natural** | No fault is injected.  The failures are the ones the model makes by itself. |
| **injected** | A fault is injected into 20 % of the attempts, **after** the model answered, and it is labelled as injected. |

The fault schedule is a **function** of the task, the step and the attempt
number *inside* that step (`random.Random(f"{seed}:{task}:{step}:{attempt}")`).
Every arm therefore meets the same schedule; an arm that retries more
simply walks further along it.  The seed is `20261020`.

The six faults are: `drop_file_block`, `truncate_file`, `corrupt_telemetry`,
`wrong_step`, `replay_previous` and `lie` (the claim stays, the file goes).

## 5. The tasks

Twenty procedural multi-step tasks (3 or 4 steps) with real files, a
cross-file consistency requirement (a script and a README that must
mention the real function name and the real number) and a **hidden ground
truth**: the arms never see the checks.  The task set is in
`benchmarks/tasks.py` and it is not changed between the arms or between
the models.

## 6. The models and the selection rule

**The rule was committed before the probe ran** (this section and the
selection below are the rule; the probe results are in
`benchmarks/results/probe-*.json` and in `docs/WORKLOG.md`).

A candidate must pass the five capability checks:

1. it follows the `FILE: path` protocol of the harness;
2. its answer ends with a telemetry object that parses, with the exact
   step name and the artifacts of the step;
3. it honours a low temperature (the same prompt twice gives the same
   answer);
4. it handles the context of the prompt;
5. it stays available (the probe calls it 12 times in a row).

A candidate is then **selected** when the success rate of the **naive**
arm on a **20 task pilot** is between **30 % and 85 %** (a rate below
30 % means the task is too hard for the model, a rate above 85 % means
the task is too easy to tell the arms apart).  The pilot data are
**excluded** from the confirmatory analysis.

Three models of **three different families** and **three different
providers** are wanted.  The order of preference is:

1. `cerebras/gpt-oss-120b` (the OpenAI gpt-oss family)
2. `google/gemini-3.6-flash` (the Gemini family)
3. `groq/qwen/qwen3.8-27b` (the Qwen family)
4. `google/gemini-3.5-flash-lite` (a second Gemini model)
5. `groq/openai/gpt-oss-20b` (a second gpt-oss model)

A model that fails the pilot is replaced by the next candidate of a
**different family**.  If fewer than three models qualify, the trial runs
with the ones that qualify and says so.

**Only the free tier of the provider is used.**  No key is ever used with
a paid model, no credit is ever bought, no payment method is ever added
and no key is ever rotated to get around a quota.  The 50 % rule of the
maintainer applies: a run stops before **half** of the documented daily
quota of its provider is used.

## 7. The size of the sample, and what it can detect

**The planned grid** is 60 tasks per cell, 3 arms, 2 conditions and 3
models: 3 x 2 x 60 = **360 cells** and about 15 model calls per cell,
that is **5 400 model calls** and roughly 4 million tokens.

**That grid does not fit in the free tier of one day.**  The measured
daily budgets of the three providers are 1 000 000 tokens (Cerebras),
200 000 tokens (Groq, documented) and an unknown number (Google, the
documentation does not publish it).  Half of them is 500 000, 100 000
and an unknown number of tokens, that is about 400, 160 and (if the
budget is 1 000 000) 800 model calls.

The **minimum detectable effect** (MDE) of a paired comparison, with
alpha = 0.05 (two sided), power = 80 % and the conservative assumption
that half of the pairs are discordant, is `1.4 / sqrt(N)`:

| N per cell | MDE of the paired difference |
| --- | --- |
| 60 | 0.181 |
| 20 | 0.313 |
| 15 | 0.361 |
| 5 | 0.626 |

With a discordance rate of 0.3 (which the pilot of run 1 suggests) the
MDE is `2.8 * sqrt(0.21 / N)`: 0.166 for N = 60 and 0.331 for N = 15.

**The N that is actually run is decided by the quota of the day, and the
achieved N and its MDE are reported with the results.**  A run that
cannot reach N = 60 says so, with the arithmetic, instead of pretending.

## 8. The statistics

* The proportion of every cell is reported with a **Wilson 95 % interval**.
* The arms are compared **paired**, on the identical tasks and the
  identical fault schedule: the report gives the number of the pairs
  where only one arm was right (the discordant pairs) and the difference
  of the two rates.
* The effect size of a paired comparison is the difference of the two
  rates; the interval of a proportion is the Wilson interval.
* **No cherry-picking**: the tables are computed from the raw cells by
  `benchmarks/evidence.py`, and the document is regenerated from the raw
  file, never edited by hand.
* A difference that is smaller than the MDE is reported as
  **inconclusive**, not as a small effect.
* The conditions are never mixed, and the models are never pooled.

## 9. The prompt is frozen

The prompt of a step is built by `benchmarks/harness.py:build_prompt` and
it is **the same for every arm and every model**.  It was changed twice
during the preparation of the trial, and both changes were **defects of
the harness** that were fixed for **all** arms:

1. the prompt did not say that `progress` is a number from 0 to 100, so
   every completed step was rejected as drift (run 1);
2. the example of the prompt did not show the fences, so half of the
   models wrote the `FILE: path` line outside the block and the harness
   threw their work away.

After the freeze, a change of the prompt is a **bug fix**, it is
documented in `docs/WORKLOG.md`, and it is applied to **every** arm and
**every** model.  The data of run 1 are kept and labelled as run 1.

## 10. The stopping rules

* A run stops **before** half of the daily quota of its provider is used
  (the counter is written to disk, so a resumed run continues on it).
* A run stops on `HTTP 402` (a request that needs a paid plan): the
  provider is reported at once and no further call is made.
* A run stops on a rate limit that does not go away; the progress file
  keeps the cells that are done, and the exact command to continue is
  printed.
* The raw cells are written after **every** cell (one JSON line per
  cell), so an interrupted run loses at most one cell.

## 11. What will not be done

* No money will be spent, no credit will be bought and no payment method
  will be added.
* The repository will not be made public, nothing will be published to
  PyPI and no tag will be pushed without the maintainer.
* A null result will be published as a null result.
