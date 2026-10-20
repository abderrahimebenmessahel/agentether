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

### NEXT ACTION

The confirmatory run of the trial v2 is running (`logs/trial-v2-cerebras`,
`logs/trial-v2-google`, N = 12 per cell).  Then the mutation triage, then
the report.




