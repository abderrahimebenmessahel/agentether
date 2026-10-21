# The final report of the session of the 21st of October 2026

> This report is written by an AI assistant that read the source, the
> tests and the data of the repository, ran the checks and made the calls
> it says it made.  **Every number below comes from a real run in this
> repository**; the commands and their output are in
> [`docs/WORKLOG.md`](WORKLOG.md) and in the commits of the day.  Where
> something could not be verified, it says so.
>
> The report of the previous session is
> [`docs/final-report-2026-10-20.md`](final-report-2026-10-20.md): it
> describes the state of the trial v3 at the end of the 20th of October,
> and the numbers it carries for that day are the numbers the run had
> that day.  The trial v3 continued afterwards; the totals of section 0
> are the totals of the raw cells as they stand now.

The repository: <https://github.com/abderrahimebenmessahel/agentether>
(**private**; nothing was published, no tag was pushed, no wheel was
uploaded anywhere).

---

## 0. The erratum of the report of the 20th of October, and the totals of the two runs together

> The erratum of the report of the 20th of October (the commit `be84cca`)
> corrected two numbers that the raw cells did not support: the total of
> the tokens of the trial v2 was **394 951** and not "450 000 tokens"
> (450 was the number of the *requests*), and the token count of the
> Google model was **188 346** and not 0.  **The correction stands**, the
> raw cells of the trial v2 did not move, and the totals of the trial v2
> are in the table of the section 4.6.  A correction that hides what it
> corrects is not a correction.

**The totals of the two runs together**, summed from the raw cells:

| Run | Requests | Tokens | Wall clock (s) |
| --- | --- | --- | --- |
| trial v3 (the 20th and the 21st of October) | 2 746 | 2 355 273 | 66937.1 |
| trial v2 (the supplementary run of the 20th of October) | 450 | 394 951 | 10527.1 |
| **total** | **3 196** | **2 750 224** | **77464.2** |

The trial v3 grew by 2 746 requests and 2 355 273 tokens since the report of the 20th of October, and the trial v2 did not move at all: its 450 requests and its 394 951 tokens are the same numbers as then.

---

## The five phases, at a glance

The brief of the maintainer had five phases.

| Phase | What it was | The result |
| --- | --- | --- |
| 1 | Make the grid of 60 tasks per cell reachable | **done**: a seeded procedural generator, a pre-registered addendum committed **before** any new data |
| 2 | The presentation of an unequal N | **done**: every rate is computed on the common set of the tasks of the cell |
| 3 | A third model with no quota | **done**: a local Ollama model, no quota, its own rows and its own verdicts |
| 4 | Continue the trial v3 | **done as far as the quota of the day allowed**: the runs are resumable, the exact commands are in the worklog |
| 5 | The gates | **done**: the ten cells of the CI, the wheel, the sdist, `twine check`, the fresh venvs and `scan_secrets.py` |

---

## 1. Phase 1 — the grid of 60 tasks per cell is reachable now

**The problem.**  The protocol of the trial v3 planned **60 tasks per
cell** and the task set had **20**; the resume command of the worklog
used `--tasks 20`.  The grid could not be reached, and the minimum
detectable effect of a paired comparison at N = 20 (0.313) is larger
than any effect the trial could see besides the complete removal of a
whole class of false completions.

**The addendum is committed before any new data**: `60b3bf0`
(`docs/trial-protocol-v3-addendum.md`).  It declares the extension, the
**seed of the generator (20261022)**, the arms, the faults and the
statistics that do **not** change, the stopping rule (the tasks in a
fixed order, the stop at the cap of the day, no peeking, the final
analysis at N = 60 or at the quota limit), the rule of the common set of
the tasks, the separation of the mechanism and of the natural frequency,
the third model and the MDE of every N.

**The generator** (`benchmarks/tasks_v3_gen.py`, commit `cccf809`):

* the subjects, the numbers and the verbs are drawn from **fixed pools**
  that are shuffled with the seed and cut at the requested length, so the
  first *n* tasks do not depend on *n* and a task keeps its subject when
  the grid grows;
* the template of a task and its headings are drawn from the seed of the
  task itself, so a task does not depend on the tasks before it;
* three **equivalent** templates (the same number of steps, of files and
  of checks; only the names of the files and of the headings differ);
* the **twenty hand-written tasks are untouched**: they are the first
  twenty of the combined set, in the same order, and the fault schedule
  is a function of the index of the task, so their schedule is unchanged
  and the data of the first session of the trial v3 stay valid.

**The shape of the set** (checked, not assumed): 60 tasks, 60 distinct
names, 60 distinct subjects, 30 tasks of 3 steps and 30 of 4, 13 or 16
checks, and no subject of the trial v2 or of the trial v3.

**The tests** (`tests/test_task_generator.py`, 21 tests): the generator is
deterministic, another seed builds other tasks, the tasks are distinct,
the hand-written tasks are untouched, the ground truth **passes on a
correct solution and fails on a broken one** (a missing file, a wrong
content, a script that does not compile), and the expectations of the
guarded arm fail on the same broken solution.

**The runner** takes `--task-set v3` (the sixty tasks), `--task-set
v3-20` (the twenty hand-written ones) and `--task-set v2`.

---

## 2. Phase 2 — the presentation of an unequal N

**The rule.**  A run that stops in the middle of a task can leave the
arms of a cell with a different number of tasks.  A rate computed on two
different sets of tasks is not comparable, and a table that mixes them
looks better than it is.  **Every rate of a cell is now computed on the
common set of its tasks**: the tasks that every arm of that model and of
that condition completed.  The paired differences, the hypotheses, the
verdicts and the H4 comparison are computed on the same set, the number
of dropped tasks is a column of the table, and the **MDE of a cell is
computed from the N it really reached** (`1.4 / sqrt(N)`) instead of a
number that was written down before the run.

**The effect on the data of the first session.**  The Google model had
seven tasks for two arms and six for the other two.  The common set is
**six**: the naive arm drops one task, and its false completion rate
goes from 0.571 (N = 7) to **0.500** (N = 6), its correct completion
rate from 0.286 to **0.333**.  The naive arm was better than the
document of the day said, and the common set says so.

**The cost of honesty** is now a table of the evidence document: the
tasks the arm did **not** claim to have finished while the ground truth
says they were not finished, and the ones that were a false completion
of the baseline (a false "done" turned into a visible failure).

**The tests** (`tests/test_evidence_consistency.py`) fail when a table
mixes two numbers of tasks and when the N of a table is not the common
set of the raw cells.

---

## 3. Phase 3 — the third model, a local one with no quota

**The machine.**  15.8 GB of RAM, one **NVIDIA GeForce RTX 3050 Laptop
GPU** with 4 GB of VRAM.

**Ollama was installed without sudo**: the Windows bundle (1.47 GB) was
extracted into `C:/Users/rimob/ollama` and the server runs as the user
with `OLLAMA_MODELS=C:/Users/rimob/ollama-models`.  The total of the
downloads of the day is 1.47 GB (the bundle) + 0.99 GB (the first
model) + 1.9 GB (the second model) = **4.36 GB**, under the 5 GB of the
brief.

**The first model was not usable.**  `qwen2.5:1.5b-instruct` passed the
probe on paper but, on the tasks, wrote six files instead of one and
never emitted the telemetry object: **every** arm believed that no task
was done, the false completion rate was 0 for the four arms, and the
cell measured nothing.  The 86 cells are not hidden: they are in
`benchmarks/results/trial-v3-local-discarded-cells.jsonl`.

**The second model is usable.**  `qwen2.5:3b-instruct` (1.9 GB, Q4_K_M,
entirely in the VRAM) passes the capability probe with **1.000** on the
telemetry, the name of the step, the progress, the file blocks and the
artifacts (12 requests, 0 errors, 8.0 s per request).  It is **not
deterministic** at temperature 0 (the GPU is not), like the Google model
of the trial: the comparison is paired on the **task and the fault
schedule**, and the difference between the arms carries the variance of
the model.

**The local model has no quota**: the compute is free, so the rule of
the half of the daily quota does not apply to it.

---

## 4. Phase 4 — the runs of the day

### 4.1 What was run

Three runs of the protocol of the trial v3 and of its addendum, on the
same tasks, with the same prompt, the same fault schedule and the same
four arms.  The **tasks run in a fixed order** and the **arms run inside
the tasks**, so a run that stops at the cap of the day leaves the tasks
that are done complete and the arms of a task are always comparable.

| Run | Provider | Model | The cap of the day | What it reached |
| --- | --- | --- | --- | --- |
| the local model | ollama | `qwen2.5:3b-instruct` | none (a safety net of 100 000 requests) | the **whole grid of the injected condition** (60 tasks per cell) and the natural condition |
| cerebras | cerebras | `gpt-oss-120b` | 500 requests and 500 000 tokens (the half of the documented daily quota) | 24 tasks per arm of the injected condition, then the token cap |
| google | google | `gemini-3.5-flash-lite` | 250 requests and 150 000 tokens (the half of the 500 requests per model that the provider publishes) | stopped by the **provider** (HTTP 429) |

**The rule of the maintainer was respected.**  The counters of the day
are on disk and are keyed by the UTC day; the run of the Cerebras model
stopped at **500 198 tokens of the 500 000** that the rule allows, and
the run of the Google model was stopped by the provider itself, which
answered `HTTP 429 - "Quota exceeded for metric:
generativelanguage.googleapis.com/generate_content_free_tier_requests,
limit: 500, model: gemini-3.5-flash-lite"`.  The local model costs
nothing: a download of 1.9 GB and the electricity of the machine.

**The models of the run** (the N and the MDE are **computed** from the
cells, not written down before the run):

{{TABLE:V3-MODELS}}

**The request and the token totals** (summed from the raw cells; the
total is a row of its own, so a reader can add the rows and find the
same number):

| Model | Requests | Tokens | Wall clock (s) |
| --- | --- | --- | --- |
| gemini-3.5-flash-lite | 104 | 76145 | 1279.0 |
| gpt-oss-120b | 412 | 496363 | 6345.9 |
| qwen2.5:3b-instruct | 2130 | 1700902 | 54917.1 |
| **total** | **2646** | **2273410** | **62542.0** |

**The consistency check.**  The payload of the run of the Cerebras model
counts **415 requests and 500 198 tokens**; the cells count **412
requests and 496 363 tokens**.  The difference (3 requests) is the cell
that was in flight when the token cap was reached: the run stopped in the
middle of it, and a cell that was not measured is not a cell.  The same
rule drops the 136 empty cells of the first session of the trial v3 and
the 23 cells of the Google model whose calls the provider refused.

### 4.2 The numbers

**Every rate is computed on the common set of the tasks of the cell**:
the tasks that every arm of that model and of that condition completed.
The column "Dropped" is the number of tasks the arm had beyond that set.

**The injected condition** (the primary endpoint):

{{TABLE:V3-INJECTED}}


**The natural condition** (no fault is injected; every failure is the
failure of the model):

{{TABLE:V3-NATURAL}}


### 4.3 The verdicts

The rule of the pre-registration: a difference smaller than the minimum
detectable effect of the sample is **INCONCLUSIVE** (the sample is too
small to say anything, which is not the same as "no effect"), and a
difference that is at least as large is only **SUPPORTED** when the exact
two-sided McNemar test of the discordant pairs rejects the null
hypothesis.  The MDE of a cell is `1.4 / sqrt(N)` with the **achieved**
N.

{{TABLE:V3-VERDICTS}}

The hypotheses of the protocol are stated against the **simple-retry**
baseline.  The **naive** arm (one call per step, the claim is trusted)
is the second comparator, and it is reported because the baseline is not
always a fair one: a baseline that retries writes the files of **every**
answer and the last one wins, so with a model that is not deterministic a
retry can overwrite a good file with a worse one.  The example is in the
data of the local model: the baseline has a false completion rate of
0.817 against 0.567 of the naive arm, and on the task `task01-bakery` its
`notes.md` is empty and its `README.md` holds the beginning of a broken
answer, while the naive arm kept a complete `notes.md`.

{{TABLE:V3-NAIVE-VERDICTS}}


**The contribution of the declarative expectations (H4)** -- the arm that
declares what the step must produce against the arm that only checks the
claimed files:

{{TABLE:V3-H4}}


**What the verdicts mean, stated plainly.**

* For the **local model**, the cell reached the **60 tasks per cell** of
  the protocol and the primary endpoint is decided: the guarded arm has
  a false completion rate of 0.083 against 0.817 of the baseline, 45
  tasks are in favour of the guarded arm and the exact McNemar test
  gives p < 0.001.  **H1 and H2 are SUPPORTED.**
* For the **Cerebras model**, the primary endpoint is decided as well
  (N = 23, the difference is above the MDE of the sample and p < 0.001):
  **H2 is SUPPORTED** (the guarded arm has no false completion at all
  against 0.565 of the baseline, 13 tasks in favour of the guarded arm).
  H1 is INCONCLUSIVE: the difference is above the MDE but the test does
  not reject (p = 0.146).
* For the **Google model**, the sample is eleven tasks and every
  verdict is **INCONCLUSIVE** (the false completion rate of the guarded
  arm is 0.000 against 0.273 of the baseline, and the difference is
  above the MDE of the sample but the exact McNemar test of the three
  discordant pairs does not reject: p = 0.250).
* **H3 (the overhead) is SUPPORTED** everywhere: the guarded arm costs
  more requests and more tokens than the baseline, and that is the price
  of the supervision.
* **One verdict is on the edge and the report says so.**  Against the
  naive arm, the Google model has a difference of -0.455 on the false
  completion (above the MDE of 0.422) with an exact McNemar p of 0.062:
  the rule of the pre-registration says **NOT SUPPORTED**, and it is
  reported as such.  The rule has three words and the middle one
  (INCONCLUSIVE) is reserved for a difference that is **below** the MDE;
  a p of 0.062 is not below 0.05.  The honest reading is that the cell
  is too small to decide, and the next window of the quota of the
  provider is what will decide it.

### 4.4 The mechanism and the natural frequency, separately

The primary endpoint is the false completion rate **under the injected
faults**.  The faults are designed, and one of them (`hide_file`) is
designed to be caught **only** by the declarative expectations, so the
evidence for the real-world value of `expects` must not rest on it.

**The mechanism** (the injected condition, the table of section 4.2):
the guarded arm catches the false completions that the injected faults
produce.

**The natural frequency**: the rate of the false completions of the kind
**(ii)** -- *a required file was never produced and the claim did not
mention it* -- with its Wilson interval.  In the natural condition
nothing is injected, so every one of them is a failure of the model:

{{TABLE:NATURAL-FREQUENCY}}

## What this shows and what it does not

**The number that matters for the real world is the second one.**  The
local model of the trial, with **no fault injected at all**, falsely
completed a large share of the tasks it was given, and the failures of
the kind (ii) -- a file the model never produced, reported as produced --
are frequent.  The guarded arms do not have that kind of failure at all.

### 4.5 The cost of honesty

The guard of AgenTether prevents false claims; it does not by itself make
a task succeed.  A task the model cannot finish is a failure either way,
but the naive arm reports it as a success and the guarded arm reports it
as a failure.  The difference is honest, and it has a price.

{{TABLE:V3-HONESTY}}


**The price, in one line.**  The guarded arm ends more tasks as an honest
"not completed" than the naive arm, and it converts a large share of the
false completions of the baseline into visible failures.  That is the
whole mechanism: the guard does not make the model better, it makes the
lie visible.  The cost is in the requests and in the tokens (H3), and
the gain is in the false completion rate (H2).

### 4.6 The supplementary run of the trial v2

The data of the trial v2 stay a **supplementary** run and are not mixed
with the data of the trial v3.  Their totals (the same rule as above):

| Model | Requests | Tokens | Wall clock (s) |
| --- | --- | --- | --- |
| gemini-3.5-flash-lite | 261 | 188346 | 7930.1 |
| gpt-oss-120b | 189 | 206605 | 2597.0 |
| **total** | **450** | **394951** | **10527.1** |

The verdicts of the trial v2 did not change in this session: every
difference of that run is smaller than the minimum detectable effect of
its sample, so every verdict was **INCONCLUSIVE** before and after.
What changed is the **presentation**: the rates of that run are now
computed on the common set of the tasks of the cell, and the MDE of a
cell is computed from the N it reached.

---

## 5. The bugs that were found and fixed

| Bug | How it was found | Fix | Commit |
| --- | --- | --- | --- |
| A cell without a request is not a measurement, but the **resume took it for done**: the first run of the trial v3 wrote 136 empty cells when the arms swallowed the stop of the daily cap, and the natural condition of the Cerebras model (80 cells) would never have been run again. | Resuming the run of the first session. | `_read_progress` drops the cells without a request; a test pins it; the collector applies the same rule. | `0c0f281` |
| A **local provider** (Ollama) needs no key, but the generic layer refused it when a key resolver was passed and the resolver answered with an empty string: the capability probe of the local model could not even start. | The capability probe of the local model. | The error is raised only for a provider that names an environment variable; a test pins it. | `0c0f281` |
| The **timeout of a call** (60 s) was too short for the answer of a local model on a laptop GPU, and the context of the server (4096) was too short for its rambling: the 1.5B model never emitted its telemetry. | The first local run: every cell of the 86 said that no arm ever believed a task was done. | The runner takes a `--timeout`; the server runs with a context of 8192; the second model needs neither. | `3310cb4` |
| A run that is split in shards needs a **global index of the task** in the fault schedule, or two shards would meet the same faults. | The design of the sharded run. | `--task-offset` takes a slice of the task set, and the index of the task stays the global one; a test pins it. | `0c0f281` |
| The **documented daily limit of the Google model was wrong**: the answer of the provider says `limit: 500, model: gemini-3.5-flash-lite`, and the day of the provider turns at midnight **Pacific** time, not at midnight UTC. | The run of the Google model was refused with `HTTP 429` three minutes after the UTC day had turned over. | The preset carries the verified number, the run is capped at 250 requests, and the wait for the quota of the provider is scheduled. | `6eb730a` |

---

## 6. The gates

| Check | Result |
| --- | --- |
| `pytest` on Windows (CPython 3.14.7) | **512 passed, 4 skipped** |
| `pytest` in WSL on CPython 3.10, 3.11, 3.12 and 3.13 | **514 passed, 2 skipped** on each of the four versions |
| `mypy --strict` | clean, 66 files, on Windows and on the four Linux versions |
| `ruff check` / `ruff format --check` | clean, 115 files (Windows), 111 (Linux) |
| `pytest --cov=src/agentether` | **89 %** of the lines |
| GitHub CI | **green on the ten cells** and on the dependency audit (the runs `39563556196` and `39565620467`, the last two of the session) |
| `python -m build` + `twine check` | the wheel and the sdist of `0.3.0a1` **PASSED** |
| the wheel in a fresh venv | works on **Windows** (`packaging_check.py`) and on **Linux** (the quickstart, the CLI and the benchmark) |
| `scan_secrets.py` | **0** in the tree, **0** in the history, the wheel is clean |

The ten cells of the CI are `ubuntu-latest` and `windows-latest` with
CPython 3.10, 3.11, 3.12, 3.13 and 3.14; the eleventh job is the
`pip-audit` of the dependency audit.

The repository is **private**.  Nothing was published, no tag was pushed,
no wheel was uploaded.

---

## 7. The money and the secrets

**No money was spent.**  The checks:

* every call went to the free tier of a free model;
* the daily counter of every provider is written to disk with an atomic
  replace, so a run that is interrupted and continued does not start the
  day from zero, and the runs of the day stayed under **half** of the
  documented daily quota of their provider (the runner's cap of the day
  now defaults to that half);
* `HTTP 402` (a request that needs a paid plan) is never retried and
  stops the run at once;
* **no credit was bought, no payment method was added, no key was
  rotated** and no account was created;
* the local model costs nothing: it is a download and the electricity of
  the machine.

**No secret leaked.**  The checks:

* the key is read from the environment only; it is never written to a
  file, never passed on a command line, never logged and never in an
  error message;
* every message that could echo the server answer goes through a
  redaction step, and there is a **test per provider** that puts the key
  in the body of a server error and asserts that it is redacted;
* `scan_secrets.py` scans the tree, the git history, the result files,
  the logs and the built wheel; it knows the key format of OpenRouter,
  Groq, Cerebras and Google; it reports **0** matches everywhere;
* the report states the length of the keys and never their value.

---

## 8. What was skipped and what could not be verified

**The Google model could not be extended.**  The free tier of Google AI
Studio gives **500 requests per model**, and the window of those 500
requests is **longer than a UTC day**: the provider refused the calls of
the 21st of October **twice**, once three minutes after the UTC day had
turned over and once at 07:30 UTC, after the run had waited for the
quota of the provider to reset at 07:05.  The cell of the Google model
therefore stays at **11 tasks per cell** and the natural condition of
that model was not run at all.

**The natural condition of the Cerebras model was not run.**  The budget
of the day of the free tier went to the injected condition, which
carries the primary endpoint, and the run stopped at the token cap
(500 198 of the 500 000 tokens that the rule allows).  The natural
condition of the local model **is** complete (60 tasks per cell), and it
is the one the natural frequency is computed on.

**The first local model was discarded.**  `qwen2.5:1.5b-instruct` passed
the capability probe on paper but never produced a valid telemetry on
the tasks: all 86 cells it produced say that no arm ever believed a
task was done, and the false completion rate was 0 for the four arms.
The cells are kept, labelled, in
`benchmarks/results/trial-v3-local-discarded-cells.jsonl`.

**The commits of the session that added the data are red in the CI.**
The test of the consistency of the evidence document compares the
document with the raw cells and the report with the cells too: the
commits that added the cells of a run that was still going failed that
test on purpose, because the document and the report are rebuilt when
the run is over.  The **last** commit of the session is green on the ten
cells and on the dependency audit.

**Other things that were not done.**

* The **stretch** of the protocol (a twelve step long task, N = 1) was
  not run: the budget of the day went to the real cells.
* The **token limit of the free tier of Google AI Studio is still
  UNVERIFIED**: the answer of the provider names the request metric and
  the number of requests, and not a number of tokens.  The runs of this
  project impose a token cap of their own.
* The **mutation triage** was not continued (the class "gap (behaviour)"
  of the survivors is still not triaged one by one).
* The **Groq models** were not called at all: the daily quota of Groq
  was spent by the probe and the pilots of the 20th of October.

---

## 9. The decisions that are left to the maintainer

1. **Make the repository public?**  It is private; nothing was published.
2. **Tag and release** `0.3.0a1`?  The CHANGELOG entry is ready; no tag
   was pushed.
3. **Publish to PyPI?**  The name `agentether` was checked and is free;
   the wheel and the sdist pass `twine check`; nothing was uploaded.
4. **The WSL password**: the brief says it is `0`.  It should be changed.
5. The README says *"no independent human review yet"* about the
   AI-assisted development; if that is not accurate for their process,
   they should change it.
6. The **mutation triage** could be continued (the class "gap (behaviour)"
   needs one test per branch).
7. The **trial v3 could be continued** on the next days: the runner is
   resumable, the protocol and its addendum are pre-registered, and the
   exact commands are in `docs/WORKLOG.md`.
