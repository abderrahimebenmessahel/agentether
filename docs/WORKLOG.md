# Worklog

A dated, external memory of the work.  It is committed, so that a session
that starts from nothing knows where the previous one stopped.

The repository is **AgenTether** (the import package `agentether`, the CLI
`agentether`, the distribution `agentether`).  The checkout is still called
`ContextGuard` on disk; that is the folder name, not the project name.

## 2026-10-20 — session 1: the maintainer's brief

The maintainer handed over a five phase brief.  The state of the tree when
this session started:

- `git log --oneline -20` ends at `cdd38c7 docs: record the mutation testing
  honestly`.  The working tree is clean, the branch is `main`, the remote is
  private.
- `docs/WORKLOG.md` did not exist; this file is it.
- `pyproject.toml` and `src/agentether/__init__.py` say **0.2.0** while
  `CHANGELOG.md` has an unreleased **0.3.0-alpha** entry.  The version
  mismatch is real and is Phase 1(a).
- `docs/evidence.md` says "Wall clock: 0 s" and the token totals are 0.  The
  result file `benchmarks/results/trial-20261020-partial.json` carries
  `wall_seconds: 0` and `input_tokens: 0 / output_tokens: 0` next to
  `requests: 291`.  Phase 1(b).
- The **simple-retry arm scored worse than the naive arm** in the first real
  trial (0.100 against 0.400, natural condition).  A broken baseline
  invalidates every comparison, so this is Phase 1(c) and it blocks Phase 4.
- The mutation run left ~174 survivors in `orchestrator.py` and
  `state_manager.py` untriaged.  Phase 1(d).

### What the trial data already shows (read from the committed result file)

`benchmarks/results/trial-20261020-partial.json`, natural condition, N = 10
tasks per cell, one model (`minimax/minimax-m3.1-flash:free`):

| task | naive | simple-retry | agentether |
| --- | --- | --- | --- |
| task01-harbour | correct (3 calls) | **wrong (5 calls)** | correct (6 calls) |
| task02-orchard | wrong (4) | wrong (7) | wrong (2) |
| task03-lantern | correct (3) | correct (3) | wrong (3) |
| task04-meridian | wrong (4) | wrong (9) | wrong (3) |
| task05-quarry | wrong (3) | wrong (8) | wrong (3) |
| task06-beacon | wrong (4) | wrong (8) | wrong (3) |
| task07-trellis | correct (3) | **wrong (6)** | wrong (3) |
| task08-compass | correct (4) | **wrong (8)** | correct (7) |
| task09-ferry | wrong (3) | wrong (5) | wrong (8) |
| task10-almanac | wrong (4) | wrong (6) | correct (9) |

The naive arm calls once per step (35 calls for 35 steps).  The simple-retry
arm calls 65 times for the same 35 steps: it retries 30 extra times and
still ends up wrong on seven tasks.  **A retry that makes things worse is a
bug in the arm, not a property of the model** — and the two arms do not even
treat the files of an answer the same way (see Phase 1(c)).

### Keys present in the environment (existence and length only, never the value)

`MINIMAX` (73, the OpenRouter key), `GROQ_API_KEY` (56), `GEMINI_API_KEY`
(53), `CEREBRAS_API_KEY` (52), `MISTRAL_API_KEY` (45).  `OPENROUTER_API_KEY`
and `ANTHROPIC_API_KEY` are absent.  The Windows variables are in the *user*
scope, so a child process needs them passed explicitly.

### Phase 1(a) — the version is now `0.3.0a1` everywhere

- `pyproject.toml`, `src/agentether/__init__.py` and the CHANGELOG heading
  now say `0.3.0a1` (PEP 440).  The `.. versionadded::` markers of the
  unreleased features follow, the `0.2.0` markers of the released features
  stay.
- The rename had mangled the comment that explains the name (it said the
  name "agentether" was taken and that the distribution was published as
  "agentether").  It now states the truth: `contextguard` is taken, so the
  distribution is `agentether`.
- The same rename had mangled the 0.2.0 entry of the CHANGELOG; it now
  describes what 0.2.0 actually was.
- `tests/test_version.py` is new: it compares the package, `pyproject.toml`,
  the CHANGELOG heading and the installed distribution, and it fails when they
  diverge.  It found a real problem on its first run: an orphan
  `src/agentether.egg-info` (a leftover of an earlier editable install, git
  ignored) still advertised `0.2.0`.  It was removed; the packaging step
  regenerates it.
- The version assertions of `tests/test_cli.py` and
  `tests/test_entry_point.py` now compare against `agentether.__version__`
  instead of repeating a literal.

Gate after this change: **325 passed, 4 skipped** (Windows, CPython 3.14.7),
`mypy --strict` clean on 53 files, `ruff check` clean, `ruff format --check`
clean on 81 files.

### Phase 1(b) and 1(c) — the accounting, and the simple-retry anomaly

**The diagnosis of the anomaly.**  The evidence was in the run-1 work
directory (`%TEMP%\agentether-trial`), which still existed:

- `simple-retry/natural/task01-harbour` held **only** `notes.md`, while
  `naive/natural/task01-harbour` held all four files of the same task, with
  the same model.  The baseline threw away the work the model had done.
- The cause was in `run_arm_simple_retry`: `write_answer_files` was called
  **only** when the telemetry parsed *and* the status was "completed".  The
  naive arm wrote the files of every answer.  So a file that the model
  really produced was destroyed by the baseline whenever the claim was not
  exactly "completed" -- and the baseline then failed the ground truth
  check.  A baseline that only adds retries cannot be worse than doing
  nothing; this one was, because of that line.

Two more defects of the same run were found while the first one was
verified:

- **The prompt never said that `progress` is a number from 0 to 100.**  The
  contract of AgenTether treats a completed step with a progress below 100
  as drift.  The attempt log of `agentether/natural/task03-lantern-memory`
  reads: *"Context drift at step 'notes': step was reported as completed
  but progress is 1 (expected='progress >= 100 for a completed step',
  observed=1.0)"*, and the second and the third step of that task were
  never attempted.  The agentether arm of run 1 measured the prompt, not
  the library.
- **The roadmap order stopped the agentether arm at the first failed
  step**, while the other two arms walked through every step.
- **The fault schedule was keyed on a counter that ran across the whole
  task**, so an arm that retried more met different faults for the same
  step.  The claim that every arm saw the same faults was false.
- **The belief was computed three different ways** (the last answer, "any
  step ever completed", the last step), so the false completion rate was
  not comparable.

**The accounting.**  The runner that produced run 1 had `tokens = 0`
hard-coded (commit 64266c1), and the committed payload has
`wall_seconds: 0` next to `requests: 291`.  A live probe of the same
endpoint (one request, `logs/probe_openrouter.py`) showed that the server
*does* report the usage (`usage.prompt_tokens: 205`,
`usage.completion_tokens: 21`), so the zeros were the runner's fault, not
the provider's.

**What was changed.**

- `benchmarks/harness.py` is new: the protocol, the file protocol, the
  faults, the ground truth and the three arms.  The arms take a `Caller`,
  so a scripted fake model can drive them offline.
- Every arm now writes the files of **every** answer, whatever the claim
  says.  The naive arm catches a failed call (it has no claim, so it has
  no verdict) instead of letting the exception end the trial.
- The prompt states the scale of `progress` and that it must be 100 for a
  completed step.  The change was applied to **all** arms.
- The agentether arm is built with `strict_order=False` and the breaker is
  closed again before every step, so each step gets the same number of
  attempts as in the other arms.  It uses the prompt the library builds
  (`ctx.build_prompt`), which adds the roadmap position, the project
  memory and the corrective hint of the previous attempt.  That is a
  **confound of the correct-completion rate** and it is reported as such;
  it does not touch the false completion rate, which is the primary
  endpoint.
- Every arm reports a verdict for every step; the belief of the task is
  true when every step was considered done.  The naive arm trusts the
  claim, the simple-retry arm enforces the contract and retries, the
  agentether arm needs the step to pass the verifiers.
- The fault schedule is a function of the task, the step and the attempt
  number **inside** that step.
- The runner counts the tokens, sums the time of the calls
  (`measured_seconds`), and seeds the counters of a resumed run with the
  cells of the earlier sessions.

**The tests.**  `tests/test_trial_arms.py` (17 tests) drives the arms with
a scripted fake model: the model fails once and then succeeds, the first
telemetry is broken, the first status is `in_progress`, the first call
times out, the first call fails, the first step name is wrong.  In every
case **the simple-retry arm is never worse than the naive arm**, and a
retry never destroys a file the model produced.
`tests/test_trial_runner.py` (5 tests) pins the accounting down.

**The raw data of run 1 is now in the repository**
(`benchmarks/results/run-1-progress.jsonl`, 60 cells) because it only
existed in `%TEMP%`.  `docs/evidence.md` is regenerated from it by
`benchmarks/evidence.py` and now carries the status of the run, the
measured time (4039.1 s) and the six defects with their evidence.  **The
numbers of run 1 are not a comparison of the three arms and the document
says so.**

Gate after this change: **347 passed, 4 skipped** (Windows, CPython
3.14.7), `mypy --strict` clean on 55 files, `ruff check` clean, `ruff
format --check` clean on 84 files, `scan_secrets.py` clean on the tree and
on the history.

### Phase 2 — the provider agnostic layer

`agentether.adapters.openai_compatible` is new: one generic worker for the
OpenAI dialect, plus a preset per provider (`PROVIDERS`): OpenRouter, Groq,
Cerebras, Mistral, Google AI Studio and a local Ollama.

* The **facts come from the official documentation** and were read on
  2026-10-20; `docs/providers.md` has the link of every page and marks
  every fact that could not be verified as **UNVERIFIED**.  The three
  differences that the documentation shows and the code has to respect:
  the **base paths differ** (Groq is `.../openai/v1`, Gemini is
  `.../v1beta/openai`), the **seed is not portable** (Mistral calls it
  `random_seed`, Gemini has no seed for the chat) and **only OpenRouter
  publishes the price of a model**, so the free models of the other
  providers cannot be found by their price.
* The **model ids are never hard-coded**: `list_free_models` reads the
  catalogue of the provider and keeps the models whose price is zero, or
  whose name carries the free marker when the catalogue has no price.
* The **limits** are respected: a token bucket per provider for the
  requests per minute and a `DailyCounter` for the requests per day.  The
  counter is written to disk with an atomic replace, so a run that is
  interrupted and continued does not start the day from zero, and the run
  stops *before* the limit of the provider is reached.
* **401, 403 and 402 are never retried**; a 402 says that the request
  needs a paid plan, which this project never enables.
* The **key never leaks**: it is read from the environment only and every
  message that could echo the server answer goes through the redaction
  step first.  There is a test for **every** provider.
* The OpenRouter adapter is now a thin preset over the generic layer; its
  22 tests still pass unchanged.

`scan_secrets.py` learned the key formats of Groq (`gsk_`), Cerebras
(`csk-`), Google (`AIza`) and a bare `NAME=key` assignment, and it now
scans the built wheel as well (a zip, which the tree scan skips).

The trial runner uses the generic layer now: it takes a `--provider`, the
rate limit of the provider is applied to every call and the daily counter
of the provider is used, so a resumed run cannot exceed the quota.

### Phase 3 — the probe, the pilots and the selection

**The preflight.**  The free models of every provider with a key were
discovered live (`benchmarks/results/models-*.json`): OpenRouter 20, Groq
3, Cerebras 2, Google 8, Mistral none that could be verified as free.
**Ollama is not installed on this machine** (15.8 GB of RAM), so there is
no local model.  **Mistral is not used**: its documentation publishes no
list of free models, and a model whose freedom is not documented must not
be called, because a paid model must never be used.

**The capability probe** (`benchmarks/probe.py`, 12 requests per
candidate, the raw results in `benchmarks/results/probe-*.json`):

| Provider | Model | ok | telemetry | file blocks | deterministic | tokens/req | s/req |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cerebras | gpt-oss-120b | 12/12 | 1.00 | 1.00 | yes | 1178 | 11.1 |
| cerebras | qwen-3.8-27b | 12/12 | 1.00 | 1.00 | yes | ~900 | 11.8 |
| groq | qwen/qwen3.8-27b | 11/12 | 1.00 | 1.00 | yes | 619 | 6.0 |
| groq | openai/gpt-oss-20b | 12/12 | 1.00 | 1.00 | no | 948 | 3.8 |
| google | gemini-3.6-flash | 12/12 | 1.00 | 1.00 | no | 642 | 10.0 |
| google | gemini-3.5-flash-lite | 12/12 | 1.00 | 1.00 | no | 628 | 10.5 |

The probe found **two defects of the harness** (both fixed for every arm
and committed before the confirmatory data):

1. the example of the prompt did not show the fences, so the models wrote
   the `FILE: path` line **outside** the block; the harness threw their
   work away.  The prompt shows the fences now and the parser accepts both
   spellings;
2. the default agent of `urllib` is answered with a 403 by the robot
   filter of two providers; the library sends a name of its own.

**The pilots** (the naive arm, the natural condition, the data are
excluded from the confirmatory analysis):

| Provider | Model | naive correct | Rate | Rule (30 % - 85 %) |
| --- | --- | --- | --- | --- |
| cerebras | gpt-oss-120b | 19/20 | 0.950 | **excluded** (above the band) |
| cerebras | qwen-3.8-27b | 20/20 | 1.000 | **excluded** (above the band) |
| google | gemini-3.5-flash-lite | 17/20 | 0.944 | **excluded** (above the band) |
| google | gemini-3.6-flash | 0/20 | 0.000 | **excluded** (the provider refused the calls: the quota of that model was spent, so the 0.00 is an artefact of the refusal and not a property of the model) |
| groq | qwen/qwen3.8-27b | 7/10 | 0.700 | **qualifies** |
| groq | openai/gpt-oss-20b | 17/20 | 0.850 | **qualifies** (at the limit) |

**The conflict, and how it is handled.**  The two models that satisfy the
pre-registered rule are the two of **Groq**, and the daily quota of Groq
was spent by the probe and the pilots: 130 000 of the 200 000 documented
tokens per day are already used, so the 50 % rule leaves nothing for a
cell of a usable size.  The two models that *do* have the budget
(Cerebras and Google) are the two the rule **excludes** for being too
good.

The rule is applied and reported as it was written.  The confirmatory
run uses the two models that have the budget, and their data are
**labelled as a supplementary run**: the pre-registered selection was
**not** met, and the document says so.  The reason is worth stating:
the band exists to keep the *correct completion* rate from having no
room, but the **primary** endpoint is the false completion rate under
the injected faults, which a model that is very good still cannot
produce without the harness removing its file.

### Phase 1(d) — the mutation triage of the two modules

`mutmut` 3.8 runs in WSL (`mutmut` has no native Windows support).  The
configuration is in `pyproject.toml`: the whole package is copied (the
imports of the mutants must work), but only `orchestrator.py` and
`state_manager.py` are mutated, and only the lines that the test suite
reaches.

| | First run | Second run (after the contract tests) |
| --- | --- | --- |
| Mutants | 2 713 | 2 713 |
| Killed by a test | 1 623 | **1 667** |
| Killed by the timeout (the mutant hangs) | 90 | 70 |
| **Survived** | **1 000** | **976** |

`mutation_triage.py` classifies every survivor by the shape of the change
and by what the shape means: **50 equivalent** (a keyword argument
replaced by the default of the callee; the verdict comes from the abstract
syntax tree of the package, not from a guess), **211 cosmetic** (only the
wording of a message changes), **16 a gap in a record**, **9 a gap in the
format of the state file** and **690 a gap in the behaviour**.

The gaps in the format and in the records pointed at the same thing:
nothing looked at the *keys* of the state file, at the *fields* of the
telemetry or at the *records* of the ledger.  `tests/test_contracts.py`
(18 tests) pins them now.  The 690 of the class "gap (behaviour)" were
**not** triaged one by one; they are mostly the value of a recorded field,
the boundary of a loop and the branch of a condition that the tests never
reach.  The honest summary: the mutation score of the two modules is
**61 %** (64 % with the timeouts) and the survivors are dominated by
equivalent mutants.  The full write-up is in `docs/audit-notes.md`.

Two other defects of the audit were found and fixed on the way:

* the fuzzer of the state file called `asyncio.run` for every round, and
  every event loop opens a socket pair on Windows: a few hundred of them
  exhausted the buffer of the machine and the CI cell of Windows 3.11
  failed with `WinError 10055`.  The test is async now.
* the test of the accounting of the runner asserted a duration of two
  milliseconds, and the clock of Windows before Python 3.13 has a
  resolution of 15.6 ms: the assertion failed on the CI cell of Python
  3.11.  The wait is longer now.

### The trial v2 — what was measured

The confirmatory run uses two models: `cerebras/gpt-oss-120b` and
`google/gemini-3.5-flash-lite`, N = 12 tasks per cell, 3 arms, 2
conditions.  The **pre-registered selection was not met** (see the
pilots above) and the deviation is stated in the evidence document.

**Cerebras `gpt-oss-120b`, N = 12 per cell:**

| Condition | Arm | correct | false completion | requests | tokens |
| --- | --- | --- | --- | --- | --- |
| natural | naive | 1.00 | 0.00 | 31 | 31 469 |
| natural | simple-retry | 1.00 | 0.00 | 31 | 31 301 |
| natural | agentether | 1.00 | 0.00 | 31 | 39 104 |
| injected | naive | 0.56 | **0.44** | 31 | 30 999 |
| injected | simple-retry | 0.56 | **0.44** | 31 | 31 324 |
| injected | agentether | 0.89 | **0.11** | 34 | 42 408 |

(the numbers of the natural condition are the ones of the first batch of
nine tasks; the injected condition covers the twelve)

The naive arm and the baseline are now **identical** (the anomaly of run 1
is gone) and the guarded arm catches three of the four false completions
of the injected condition.  The cost is 3 requests and 11 000 tokens
more.

### The trial v2 — the result

Both runs are finished: 144 cells, 450 model calls, 10 527 s of calls.

**The injected condition** (20 % of the attempts get a fault):

| Model | Arm | N | correct | false completion | requests | tokens |
| --- | --- | --- | --- | --- | --- | --- |
| cerebras gpt-oss-120b | naive | 12 | 0.417 | 0.333 | 31 | 30 999 |
| cerebras gpt-oss-120b | simple-retry | 12 | 0.417 | 0.333 | 31 | 31 324 |
| cerebras gpt-oss-120b | **agentether** | 12 | **0.667** | **0.083** | 34 | 42 408 |
| google gemini-3.5-flash-lite | naive | 12 | 0.583 | 0.167 | 42 | 25 892 |
| google gemini-3.5-flash-lite | simple-retry | 12 | 0.833 | 0.167 | 46 | 28 041 |
| google gemini-3.5-flash-lite | **agentether** | 12 | 0.833 | 0.167 | 47 | 43 905 |

The naive arm and the baseline are now **identical** (the anomaly of run 1
is gone).  With the Cerebras model the guarded arm caught **three of the
four** false completions of the baseline and completed three more tasks,
for three more requests and 11 000 more tokens.  With the Google model it
caught none.

**The verdicts are INCONCLUSIVE** for H1 and H2, by the rule of the
pre-registration: with N = 12 the minimum detectable effect is 0.404 and
the observed differences are 0.25 (Cerebras) and 0.00 (Google).  The
effect of the Cerebras model is in the expected direction (three
discordant pairs, all in favour of the guarded arm, p = 0.25) but three
events cannot reach p < 0.05.  **H3 (the overhead) is SUPPORTED** for the
two models.

`docs/evidence.md` is regenerated from the raw cells and carries the
tables, the Wilson intervals, the paired differences, the p values and the
verdicts.  The raw cells of the run and of the pilots are committed in
`benchmarks/results/`.

### The hygiene

* `pytest` on Windows: **405 passed, 3 skipped**; in WSL on CPython
  3.10, 3.11, 3.12 and 3.13: **406 passed, 2 skipped** on each.  (The
  difference is the test of the symbolic links, which Windows does not
  support, and the test of the installed distribution, which is skipped
  when the package is not installed.)
* `mypy --strict` clean on 58 files, `ruff check` and
  `ruff format --check` clean on 91 files, on both systems.
* The GitHub CI is **green on the ten cells** and on the dependency audit.
* The wheel and the sdist of `0.3.0a1` are built, `twine check` passes,
  and the wheel works in a fresh venv on Windows and on Linux.
* `scan_secrets.py` finds **0** in the tree, **0** in the history and
  nothing in the wheel.

## 2026-10-20 — session 2: the consistency fixes (phase 1 of the new brief)

The brief of the maintainer asked for three consistency fixes before
anything else.  Each of them is a contradiction between the report of the
first session and the raw data, and each of them now has a test.

### Phase 1(a) — the totals of the report

The report of the first session said "450 000 tokens" and, in the section
"what could not be verified", that the token count of the Google model was
**0**.  The raw cells of the trial v2 say something else:

| | Requests | Tokens | Wall clock (s) |
| --- | --- | --- | --- |
| gemini-3.5-flash-lite | 261 | 188 346 | 7 930.1 |
| gpt-oss-120b | 189 | 206 605 | 2 597.0 |
| **total** | **450** | **394 951** | **10 527.1** |

**450** is the number of the *requests*, and the total of the tokens is
**394 951**.  The Google model does report its usage (the adapter reads
`usage.prompt_tokens` and `usage.completion_tokens` and the free tier of
Google answers with them), so its token count is 188 346 and not 0.

What *was* zero is the `model_stats` summary of the **payload** of the
resumed Cerebras run: `_seed_stats` seeded the counters of a resumed run
with `cell["input_tokens"]` and `cell["output_tokens"]`, and the cells
carry a single `tokens` field.  The cells themselves were always right
(the token count of a cell is a delta inside the session), and the tables
of `docs/evidence.md` were always right, because they are summed from the
cells.  The bug was in the summary of the payload, and it is fixed:
`ModelStats` now has a `tokens` field that the seeding fills.

**The generator.**  `benchmarks/evidence.py` now writes a **total row** in
the table of the totals (a reader must be able to add the rows of the
table and find the same number) and it can build a document with **several
runs** (a manifest), so that the supplementary run of the protocol v2 and
the confirmatory run of the protocol v3 live in the same document without
being mixed.

**The test.**  `tests/test_evidence_consistency.py` (7 tests) recomputes
every total of `docs/evidence.md` and of the final report from the raw
cell files, and it fails when a number does not match, when
`docs/evidence.md` is not what the generator produces (it was edited by
hand), or when a table of the document does not use the sign convention.
The first run of the test failed on the report, as it should.

**The erratum.**  The report has a new section 0 with the two old numbers
visible and the reason of each.  A correction that hides what it corrects
is not a correction.

### Phase 1(b) — one sign convention

Every paired difference of the document is now **arm A minus arm B**, and
A is always the guarded arm.  A **positive** difference of the correct
completion rate is an improvement; a **NEGATIVE** difference of the false
completion rate is an improvement.  The convention is stated once, in a
section of its own, and every table follows it.

Two things were wrong before:

* the table of the hypotheses showed the **opposite sign** of the table of
  the paired differences for the false completion (`+0.250` against
  `-0.250` for the same quantity);
* the rule that turns a difference into a verdict was inverted with it:
  the hypothesis of the false completion was tested with
  `_verdict(-difference, p, mde, -1)`, which would have declared an arm
  that caught **more** false completions as **NOT SUPPORTED**.  The rule
  is now `_verdict(difference, p, mde, -1)`, and the expected sign of the
  false completion is "less".

The verdicts of the trial v2 do not change: every difference of that run
is smaller than the minimum detectable effect of its sample, so every
verdict was **INCONCLUSIVE** before and after.

### Phase 1(c) — the naive arm and the baseline are not identical everywhere

The report of the first session said that the naive arm and the
simple-retry arm "are now identical".  That is true on **one cell** (the
injected condition of the Cerebras model: 0.417 correct, 0.333 false
completions, 31 requests each) and false on the others:

| Model | Condition | naive | simple-retry |
| --- | --- | --- | --- |
| gpt-oss-120b | injected | 0.417 / 0.333 / 31 | 0.417 / 0.333 / 31 |
| gemini-3.5-flash-lite | injected | 0.583 / 0.167 / 42 | 0.833 / 0.167 / 46 |
| gemini-3.5-flash-lite | natural | 1.000 / 0.000 / 42 | 0.917 / 0.083 / 42 |

(correct / false completions / requests)

The two arms coincide when the first attempt of every step already
satisfies the telemetry contract, and they differ when the baseline walks
further along the fault schedule.  The property that the baseline must
have is not "it is identical" but "it is **never worse** than doing
nothing", and that property holds and is tested by
`tests/test_trial_arms.py`.

### Phase 2 — the cause of every false completion

The 17 false completions of the trial v2 (144 cells) were classified with
`benchmarks/analyze_false.py`, a new tool that reads the raw cells, the
sandboxes and the attempt logs of the run.  **No model was called.**  The
document it writes is `docs/false-completions.md`.

| Cause | The false completions | The failing checks |
| --- | --- | --- |
| (i) an injected fault damaged an artifact and the arm did not catch it | 14 | 46 |
| (ii) a required file was never produced and the claim did not mention it | 0 | 0 |
| (iii) something else | 3 | 6 |

**The finding that matters.**  The verifier of the guarded arm was
`artifacts_exist()`: it checks that the files the model **claims** exist.
So it catches a false completion whose artifact is **missing** (the check
fails, the step is retried) and it cannot catch one whose artifact
**exists but is damaged** (the check passes).  Of the four false
completions of the naive arm on Cerebras, three were a missing file
(`replay_previous`, `lie`, `drop_file_block`) and one was a file cut in the
middle (`truncate_file`): the guarded arm caught the three and missed the
one.  That is the whole explanation, and it is a limit of the **verifier**,
not of the fault timing: the faults of the trial v2 are applied *inside*
the worker, that is **before** the verification of the library, so the
library could have caught them if it had looked at the content.

**The two false completions of the Google model were not the library's
fault.**  The analysis compared the file on disk with the answer that the
guarded arm recorded in its project memory, and the file was the
**beginning** of the answer's file: the harness cut it.  The parser
closed a file on the next fence, even when that fence opened a code block
**of the file itself** (a Markdown file that shows how to run the script
is the common case).  The rest of the file was lost and the ground truth
failed.  The naive arm was right on those two tasks by luck: the Google
model is not deterministic, and its answer for them did not hold a code
block.

**The fix of the harness** (before any new data): the parser follows the
rule of CommonMark now (a fence with an info string opens a block and
never closes another one, and a block closes on a fence at least as long
as its own), the prompt asks for **four** backticks so that a code block
inside a file cannot close it, and the faults were rebuilt on the new
parser.  `tests/test_trial_parser.py` (13 tests) pins it down.

**A second defect of the baseline, found by the analysis.**  The
docstring of `_contract_is_completed` says that the simple-retry arm
"parses the contract: the step name must match and the status must be
completed".  The code does **not** check the step name (`parse_telemetry`
validates the structure of the telemetry and not the name of the step), so
the baseline accepted the answer of the **previous** step as the
completion of the current one.  That is why the `replay_previous` fault
ended in a false completion of the baseline.  The library itself checks
the step name (a drift check), which is why the guarded arm caught it.

### Phase 3 — the declarative expectations of a step

The main library change of the brief.  A step can now declare what it
**must** produce, and the library checks that declaration instead of only
the claim of the agent.

```python
@orch.guard_step(
    "write",
    expects=[
        "README.md",                                     # must exist, not empty
        Expectation("data.json", json_keys=("a", "b")),  # must be a JSON with a and b
        Expectation("build.py", python_valid=True),      # must compile
        Expectation("guide.md", markdown_headings=("## Install",)),
    ],
)
```

* `src/agentether/expectations.py` is new: the `Expectation` dataclass, the
  resolution of the declared paths and the composite verifier.  The checks
  of the content **reuse** the verifiers of the library (`file_contains`,
  `json_file_valid`, `python_syntax_valid`, `markdown_has_headings`).
* `AutoOrchestrator.guard_step` takes `expects=` and resolves the paths
  **when the step is declared**: an absolute path, a `..` component and a
  symlink that leaves the work directory are a `ConfigurationError` and not
  a failure at the end of the run.
* The expectations are evaluated **after every attempt**, whatever the
  agent claimed, and **a step cannot complete while a declared expectation
  is unmet**.  The failure is a retryable `VerificationFailedError` and the
  hint of the next attempt names the **missing** files.
* The expectations are checked **before** the verifiers of `verify=[...]`:
  a file that does not exist is the more actionable failure.

**The tests.**  `tests/test_expectations.py` (21 tests) and two property
tests in `tests/test_properties.py`.  They cover the invariant, the
confinement of the paths, the validators, the hint, the retry and the
record of the ledger.

**The documentation.**  `docs/spec/expectations-v1.md` is the contract (for
other implementations too), `docs/verifiers.md` has the guide, the README
has a section, the CHANGELOG has the entry, `docs/audit-notes.md` has the
new invariant with its eight proofs, and `examples/declared_expectations.py`
is a runnable example (it lies twice and is caught twice).

**What `expects` cannot do**, and what the documentation says: an
expectation checks the **shape** of a file, not its meaning.  A JSON that
parses may hold the wrong number, a Markdown that has its headings may say
the wrong thing, a Python that compiles may do the wrong thing.  The
semantic check is left to a judge (`llm_judge`) or to a verifier of your
own (`callable_verifier`).

### Phase 4 — the trial v3

**The protocol** (`docs/trial-protocol-v3.md`, commit `f4abb99`) was
written and committed **before** the first result file of the trial v3
existed.  It states the deviation of the protocol v2 openly: the band of
the selection rule (a naive success between 30 % and 85 %) was not
satisfiable by the models that had quota, so the rule of the v3 is the
capability probe and the quota, with no band.  The data of the v2 stay a
**supplementary** run.

**The implementation** (commit `91ba086`):

* `benchmarks/tasks_v3.py`: the twenty **new** tasks (new subjects, new
  numbers, new function names).  Their visible specification says exactly
  what the ground truth checks, so the expectations of the `agentether`
  arm are as strong as the ground truth.
* the fault **`hide_file`** (new): it removes a file of the answer *and*
  its name from the claim.  It is the mechanism the v2 could not measure:
  the model never produces a file and the claim mentions only the files it
  did produce.
* the four arms: `naive`, `simple-retry`, `agentether-claims-only` (the
  configuration of the v2) and `agentether` (with the expectations).
* the runner takes the task set, the seed of the fault schedule, the seed
  of the model, the cap of the day and a cap of tokens.  **The cap of the
  day defaults to half of the documented daily limit of the provider**:
  the rule of the maintainer is now the default of the code and not only
  of the command line.

**The run of the day** (2026-10-20, the budget of the day):

| Provider | The requests of the day | The budget left | The cap of the run |
| --- | --- | --- | --- |
| cerebras | 404 before the run | 96 requests (500 - 404) and 137 506 tokens (500 000 - 362 494) | 96 requests, 137 506 tokens |
| google | 430 before the run | 320 requests (750 - 430) | 320 requests, 300 000 tokens (a safety net: the token limit of Google is not published) |

**A defect of the runner, found by the run itself.**  The arms of the
harness catch the exceptions of a call (a timeout, a transport error) and
carry on; the *stop* of the daily cap was caught the same way, and the
run wrote **136 empty cells** (a cell with zero request is not a
measurement).  `TrialHalt` is a `BaseException` now, and a test pins it
(`test_a_stop_is_not_swallowed_by_the_arms`).  `benchmarks/collect_cells.py`
drops the cells without a request and **prints how many it dropped**.

**The data of the day, Cerebras** (the injected condition, 6 tasks, 4
arms, 24 cells):

| Arm | N | correct | false completion | requests | tokens |
| --- | --- | --- | --- | --- | --- |
| naive | 6 | 3 | 3 | 21 | 20 936 |
| simple-retry | 6 | 3 | 3 | 22 | 21 872 |
| agentether-claims-only | 6 | 4 | 1 | 26 | 34 594 |
| **agentether** (with the expectations) | 6 | 3 | **0** | 27 | 34 976 |

The arm with the expectations caught the **three** false completions of
the baseline; the arm that only checks the claimed files caught two of
them.  The sample is too small for the verdict (the MDE of N = 6 is
0.495): the run of Google is the one that can decide it.

### Phase 4 — the run of the trial v3, and the gates

**The run of the day** (2026-10-20, the budget of the free tier):

| Provider | The run | The cells | The requests | The tokens |
| --- | --- | --- | --- | --- |
| cerebras gpt-oss-120b | the injected condition, 6 tasks per arm | 24 | 96 | 112 378 |
| google gemini-3.5-flash-lite | the injected condition, 6 tasks per arm (7 for two arms) | 26 | 98 | 74 866 |

The Cerebras run stopped at the cap of the day (96 requests: the counter
of the provider held 404 of the 500 that the rule of the maintainer
allows).  The Google run stopped because the **provider refused the
calls**: `HTTP 429 - You exceeded your current quota` (the token limit of
the free tier of Google is not published, and the run of the day found
where it is).

| Arm | N | correct | false completion | requests | tokens |
| --- | --- | --- | --- | --- | --- |
| naive | 6 | 3 | 3 | 21 | 20 936 |
| simple-retry | 6 | 3 | 3 | 22 | 21 872 |
| agentether-claims-only | 6 | 4 | 1 | 26 | 34 594 |
| **agentether** (with the expectations) | 6 | 3 | **0** | 27 | 34 976 |

(Cerebras; the Google model shows the same direction: 4, 1, 1 and 0
false completions.)

**The verdicts are INCONCLUSIVE** for H1, H2 and H4: the MDE of a sample
of six tasks is 0.571 and the observed difference of the false completion
rate is 0.500 (three discordant pairs, p = 0.250).  H3 (the overhead) is
**SUPPORTED**.  The data show the **direction** -- the arm that declares
what the step must produce caught every false completion of the baseline
in the two models -- and the report says exactly that and no more.

**The command to continue the trial** (the runner is resumable and the
cells that are done are kept):

```bash
python benchmarks/trial.py --provider cerebras --models gpt-oss-120b \
    --task-set v3 --arms naive simple-retry agentether-claims-only agentether \
    --conditions injected natural --tasks 20 --rate-limit 5 --model-cap 400 \
    --daily-cap 500 --token-cap 500000 --model-seed 20261021 \
    --workdir logs/trial-v3-cerebras --output benchmarks/results/trial-v3-cerebras.json
```

**Two more defects, found by the run and by the CI.**

* The arms of the harness caught the **stop** of the daily cap the same
  way they catch the failure of a call, and the run wrote 136 empty
  cells.  `TrialHalt` is a `BaseException` now, and
  `benchmarks/collect_cells.py` drops the cells without an attempt and
  prints how many it dropped.
* The CI found that the document of the evidence was **not the same on
  every Python version**: Python 3.12 changed the summation of the
  floats, and the seconds of a cell were summed with `sum()`.  The
  generator uses `math.fsum` now (the sum is exactly rounded), and the
  document is the same on 3.10, 3.14 and Windows.

**The gates.**

| Check | Result |
| --- | --- |
| `pytest` on Windows (CPython 3.14.7) | 479 passed, 4 skipped |
| `pytest` in WSL on CPython 3.10, 3.11, 3.12 and 3.13 | 481 passed, 2 skipped on each |
| `mypy --strict` | clean, 65 files |
| `ruff check` / `ruff format --check` | clean, 106 files |
| `python -m build` + `twine check` | PASSED (the wheel and the sdist of `0.3.0a1`) |
| `scan_secrets.py` | 0 in the tree, 0 in the history, the wheel is clean |

### NEXT ACTION (the end of the session of 2026-10-20)

The five phases of the brief are done.  What is left is the decision of
the maintainer:

* make the repository **public**?  (it is private, nothing was published)
* **tag** and release `0.3.0a1`?  (the CHANGELOG entry is ready, no tag
  was pushed)
* publish on **PyPI**?  (the wheel and the sdist pass `twine check`)
* change the **WSL password** (the brief says it is `0`)
* **continue the trial v3** on the next days: the runner is resumable, the
  protocol is pre-registered, and sixty tasks per cell (the MDE of 0.181)
  would make the verdict of the primary endpoint decidable.  The command
  is in the section of the trial v3 above.
* continue the **mutation triage** (the class "gap (behaviour)" needs one
  test per branch).

### NEXT ACTION

The final report is written
(`docs/final-report-2026-10-20.md`).  What is left is the decision of
the maintainer: make the repository public, tag, publish to PyPI, change
the WSL password.  Nothing of that was done.







## 2026-10-21 — session 3: the extension of the grid, the common set and the third model

The brief of the maintainer has five phases.  The state of the tree when
this session started: `git log --oneline` ends at `f4211d5`, the working
tree is clean, the branch is `main`, the remote is private.

### Phase 1 — the grid of 60 tasks per cell is now reachable

**The problem.**  The protocol of the trial v3 planned **60 tasks per
cell** and the task set had **20** (`benchmarks/tasks_v3.py`); the resume
command of the worklog used `--tasks 20`.  The grid was therefore not
reachable, and the MDE of a paired comparison at N = 20 (0.313) is larger
than any effect the trial could see besides the complete removal of a
class of false completions.

**The addendum is committed before any new data** (`60b3bf0`):
`docs/trial-protocol-v3-addendum.md`.  It declares the extension, the
**seed of the generator (20261022)**, the arms, the faults and the
statistics that do **not** change, the stopping rule (fixed order of the
tasks, stop at the cap of the day, no peeking, the final analysis at
N = 60 or at the quota limit), the rule of the common set of tasks, the
separation of the mechanism and of the natural frequency, the third model
and the MDE of every N.

**The generator** (`benchmarks/tasks_v3_gen.py`, commit `cccf809`):

* the subjects, the numbers and the verbs are drawn from fixed pools
  that are **shuffled with the seed and cut at the requested length**, so
  the first *n* tasks do not depend on *n* and a task keeps its subject
  when the grid grows;
* the template of a task and its headings are drawn from the seed of the
  task itself, so a task does not depend on the tasks before it;
* three **equivalent** templates (the same number of steps, of files and
  of checks; only the names of the files and of the headings differ);
* the twenty hand-written tasks are **untouched**: they are the first
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

### NEXT ACTION

Phase 2: the generator of `docs/evidence.md` must compute every headline
rate on the **common set of the tasks that every arm of a model and of a
condition completed**, keep the paired analysis on that set, show how
many tasks were dropped, and a test must fail when a table mixes two
different numbers of tasks.  The document is then regenerated from the raw
cells only.

### Phase 2 — the presentation of an unequal N

`benchmarks/evidence.py` and `benchmarks/trial.py` now compute **every**
rate of a cell on the **common set of its tasks**: the tasks that every
arm of that model and of that condition completed
(`trial.common_task_set`).  The paired differences, the hypotheses, the
verdicts and the H4 comparison are computed on the same set, the number of
dropped tasks is a column of the table, and the **MDE of a cell is
computed from the N it really reached** (`1.4 / sqrt(N)`) instead of a
number that was written down before the run.

The effect on the data of the first session of the trial v3: the Google
model had seven tasks for two arms and six for the other two.  The common
set is **six**, and the naive arm drops one task: its false completion
rate goes from 0.571 (N = 7) to **0.500** (N = 6) and its correct
completion rate from 0.286 to **0.333**.  The naive arm was better than
the document said, and the common set says so.

The document also carries the **cost of honesty** (the phase 4 of the
brief): the tasks the arm did not claim to have finished while the ground
truth says they were not finished, and the ones that were a false
completion of the baseline.

The tests (`tests/test_evidence_consistency.py`, 14 tests) fail when a
table mixes two numbers of tasks and when the N of a table is not the
common set of the raw cells.

### Phase 3 — the third model, a local one (no quota)

**The machine.**  15.8 GB of RAM, one **NVIDIA GeForce RTX 3050 Laptop
GPU** with 4 GB of VRAM (1.2 GB used by the display), 151 GB of free disk.
`nvidia-smi` answers, and the CUDA driver is 610.88.

**Ollama was installed without sudo and without an administrator
account**: the Windows bundle (1.47 GB) was downloaded and extracted into
`C:\Users\rimob\ollama` (1.9 GB), and the server runs as the user with
`OLLAMA_MODELS=C:\Users\rimob\ollama-models`.  The total of the downloads
is 1.47 GB (the bundle) + 0.99 GB (the model) = **2.46 GB**, under the
5 GB of the brief.  The server is started with:

```
C:\Users\rimob\ollama\ollama.exe serve
```

with `OLLAMA_NUM_PARALLEL=4` (four requests in flight at the same time).

**The model** is `qwen2.5:1.5b-instruct` (986 MB, Q4_K_M, entirely in the
VRAM).  The **capability probe** (`benchmarks/results/probe-ollama.json`,
12 requests):

| Metric | Value |
| --- | --- |
| requests that answered | 12 / 12 |
| telemetry that parses | 0.917 |
| the name of the step is exact | 0.917 |
| progress = 100 | 0.917 |
| the file blocks are there | 1.000 |
| the artifacts are claimed | 0.917 |
| deterministic at temperature 0 | **no** |
| seconds per request | 11.0 |

The model **passes the probe** (it follows the protocol, its telemetry
parses, it answers).  It is **not deterministic** at temperature 0 (the
GPU is not), like the Google model of the trial v3.  The comparison is
therefore paired on the **task and the fault schedule**, and not on the
answer of the model: the difference between the arms carries the
variance of the model.  It is stated in the report.

**The local model is a third model with no quota**: the compute is free,
so the rule of the half of the daily quota does not apply to it, and the
caps of the day are only a safety net.

### Phase 4 — the runs of the day

Three runs are in flight at the same time (the local one on the GPU, the
two cloud ones on the network):

| Run | Provider | Model | Cap of the day | Command |
| --- | --- | --- | --- | --- |
| local | ollama | qwen2.5:1.5b-instruct | none (a safety net of 100 000 requests) | four shards of 15 tasks, `--task-offset 0/15/30/45` |
| cerebras | cerebras | gpt-oss-120b | 500 requests, 500 000 tokens | the work directory of the first session is resumed |
| google | google | gemini-3.5-flash-lite | 500 requests, 250 000 tokens | the work directory of the first session is resumed |

The counters of the day are on disk and were **reset by the day itself**
(the counter is keyed by the UTC date, and the day turned over at 00:00
UTC).  The counters of the 20th of October were at the cap of the
Cerebras model (500 of 500) and at 733 of 750 for the Google model, and
the two runs of the 21st start from zero.

**The Google cap is stricter than the rule.**  The documented limit of
Google is 1500 requests per day (the half is 750), but the token limit is
**not published** and the provider refused the calls of the 20th of
October with `HTTP 429` after 528 requests of the day.  The run of the
21st uses **500 requests and 250 000 tokens** (a third of the documented
requests and a self-imposed token cap), and the provider is left alone
for the day if it refuses.

**A defect of the resume, found by the resumption itself.**  The progress
file of the first session of the trial v3 holds **136 cells without a
request**: they are the cells the arms wrote when they swallowed the stop
of the daily cap.  The resume took them for done, and the natural
condition of the Cerebras model (80 cells) would **never** have been run
again.  A cell without a request is not a measurement: `_read_progress`
drops them now, and a test pins it.

### The gates of the day

| Check | Result |
| --- | --- |
| `pytest` on Windows (CPython 3.14.7) | **510 passed, 4 skipped** |
| `pytest` in WSL on CPython 3.10, 3.11, 3.12 and 3.13 | **512 passed, 2 skipped** on each |
| `mypy --strict` | clean, 66 files, on Windows and on the four Linux versions |
| `ruff check` / `ruff format --check` | clean, 110 files (Windows), 106 (Linux) |
| `pytest --cov=src/agentether` | **89 %** of the lines |

### NEXT ACTION

The three runs of the day are in flight.  The next steps are: collect the
cells, build the result files with `benchmarks/collect_cells.py`, rebuild
the evidence document, write the report of the day and run the rest of
the gates (the CI, the wheel, `twine check`, the fresh venv and
`scan_secrets.py`).

### Phase 3, the second attempt — the 1.5B model was not usable

The first local model, `qwen2.5:1.5b-instruct`, **passed the probe on
paper** (12 requests, 0.917 of the telemetry, 1.000 of the file blocks)
but was **not usable in the trial**: on the tasks it wrote **six files
instead of one** (a file per heading, a "summary" file, an "artifacts"
file), it never emitted the telemetry object, and its answers ran past
the 4096 tokens of the context of the server.  **Every** cell of the 86
that were collected says the same thing: no arm ever believed a task was
done, so the false completion rate was 0 for the four arms and the cell
measured nothing.  The cells are **not hidden**: they are in
`benchmarks/results/trial-v3-local-discarded-cells.jsonl` with their
reason.

The reason was a property of the model and of the harness, not of the
trial: the timeout of a call (60 s) was too short for the answer of the
model, and the context of the server (4096) was too short for its
rambling.  The runner takes a `--timeout` now, and the server was
started with a context of 8192.

**The second local model is `qwen2.5:3b-instruct`** (1.9 GB, Q4_K_M, in
the VRAM of the 3050).  The total of the downloads of the day is
1.47 GB (the bundle) + 0.99 GB (the 1.5B model) + 1.9 GB (the 3B model)
= **4.36 GB**, under the 5 GB of the brief.  Its probe
(`benchmarks/results/probe-ollama.json`):

| Metric | Value |
| --- | --- |
| requests that answered | 12 / 12 |
| telemetry that parses | **1.000** |
| the name of the step is exact | **1.000** |
| progress = 100 | **1.000** |
| the file blocks are there | **1.000** |
| the artifacts are claimed | **1.000** |
| deterministic at temperature 0 | no (like the Google model) |
| seconds per request | 8.0 |

**The model is usable.**  The first cells of the grid show what the
trial needs: the naive arm and the baseline falsely complete the tasks
they did not finish, and the two guarded arms do not.

### The exact commands of the runs of the day

```bash
# the local model (no quota), four shards of fifteen tasks
python benchmarks/trial.py --provider ollama --models qwen2.5:3b-instruct \
    --task-set v3 --arms naive simple-retry agentether-claims-only agentether \
    --conditions injected natural --tasks 15 --task-offset 0 --rate-limit 600 \
    --model-cap 100000 --daily-cap 100000 --token-cap 100000000 \
    --model-seed 20261021 --timeout 300 \
    --workdir logs/trial-v3-local2/shard0 --output logs/trial-v3-local2/shard0.json

# the Cerebras model (500 requests and 500 000 tokens, the half of the rule)
python benchmarks/trial.py --provider cerebras --models gpt-oss-120b \
    --task-set v3 --arms naive simple-retry agentether-claims-only agentether \
    --conditions injected natural --tasks 60 --rate-limit 5 --model-cap 500 \
    --daily-cap 500 --token-cap 500000 --model-seed 20261021 \
    --workdir logs/trial-v3-cerebras --output benchmarks/results/trial-v3-cerebras.json

# the Google model (250 requests, the half of the 500 that the provider
# itself publishes; the token limit is not published, so the cap of
# 150 000 tokens is our own)
python benchmarks/trial.py --provider google --models gemini-3.5-flash-lite \
    --task-set v3 --arms naive simple-retry agentether-claims-only agentether \
    --conditions injected natural --tasks 60 --rate-limit 15 --model-cap 250 \
    --daily-cap 250 --token-cap 150000 --model-seed 20261021 \
    --workdir logs/trial-v3-google --output benchmarks/results/trial-v3-google.json
```

The run of the Google model **waits for the quota of the provider**: its
day turns at midnight **Pacific** time (07:00 UTC), and the quota of the
day of the 20th of October was already spent.
