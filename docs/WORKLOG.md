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

### NEXT ACTION

Phase 1(d): the mutation triage of `orchestrator.py` and
`state_manager.py` (mutmut runs in WSL), then Phase 2 (the provider
agnostic layer and `docs/providers.md`).


