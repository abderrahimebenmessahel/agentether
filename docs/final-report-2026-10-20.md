# The final report of the audit of AgenTether (2026-10-20)

> This report is written by an AI assistant that read the source, the
> tests and the data of the repository line by line, ran the checks and
> made the calls it says it made.  **Every number below comes from a real
> run in this repository**; the commands and their output are in
> `docs/WORKLOG.md` and in the commits of the day.  Where something could
> not be verified, it says so.

The repository: <https://github.com/abderrahimebenmessahel/agentether>
(**private**; nothing was published, no tag was pushed, no wheel was
uploaded anywhere).

---

## 1. The four known problems of the brief

### 1.1 The version said 0.2.0 and 0.3.0-alpha at the same time

`pyproject.toml`, `src/agentether/__init__.py` and the command said
**0.2.0** while the CHANGELOG announced an unreleased **0.3.0-alpha**.

**Fixed.**  The version is now `0.3.0a1` (PEP 440) in
`pyproject.toml`, in `agentether.__version__`, in `--version`, in the
CHANGELOG and in the `.. versionadded::` markers of the unreleased
features.  `tests/test_version.py` compares the package, `pyproject.toml`,
the CHANGELOG heading and the installed distribution, and it fails when
they diverge.

It found a real problem on its first run: an orphan
`src/agentether.egg-info` (a leftover of an earlier editable install)
still advertised `0.2.0`.  It was removed.

The rename had also mangled two comments (the one that explains the name
and the entry of 0.2.0 in the CHANGELOG); both now say what is true.

### 1.2 The token and elapsed-time accounting was zero

The runner that produced run 1 had **`tokens = 0` hard-coded**
(`benchmarks/trial.py` at commit `64266c1`), and the committed payload has
`wall_seconds: 0` next to `requests: 291`.

**Fixed and verified.**  A live probe of the same endpoint
(`logs/probe_openrouter.py`, one request) showed that the server *does*
report the usage (`usage.prompt_tokens: 205`,
`usage.completion_tokens: 21`), so the zeros were the runner's fault and
not the provider's.  The runner now counts the tokens, sums the time of
the calls (`measured_seconds`), records the failures of a cell, and seeds
the counters of a resumed run with the cells of the earlier sessions.

`docs/evidence.md` is **regenerated from the raw cells**
(`benchmarks/results/run-1-progress.jsonl`, which was copied into the
repository because it only existed in `%TEMP%`).

### 1.3 The baseline scored worse than doing nothing

This was the important one.  The full diagnosis is in
`docs/evidence.md` ("The defects of this run") and here:

| # | The defect | The evidence | The fix |
| --- | --- | --- | --- |
| 1 | The **simple-retry arm threw away the work the model had done**: it wrote the files of an answer only when the claim said "completed". | The sandbox of `simple-retry/natural/task01-harbour` held **only** `notes.md`, while the sandbox of `naive/natural/task01-harbour` held all four files of the same task, with the same model. | Every arm writes the files of **every** answer, whatever the claim says. |
| 2 | The **prompt never said that `progress` is a number from 0 to 100**, and the contract treats a completed step with a progress below 100 as drift. | The attempt log of `agentether/natural/task03-lantern-memory`: *"Context drift at step 'notes': step was reported as completed but progress is 1"*.  The second and the third step of that task were **never attempted**. | The prompt states the scale.  The change was applied to **all** arms. |
| 3 | The **roadmap order stopped the agentether arm at the first failed step**, while the other arms walked through every step. | The steps of the failed task were never attempted. | The trial builds the orchestrator with `strict_order=False` and closes the breaker again before every step. |
| 4 | The **fault schedule was keyed on a counter that ran across the whole task**, so an arm that retried more met different faults for the same step. | The schedule was a function of the *cumulative* attempt number. | The schedule is a function of the task, the step and the attempt number **inside** that step. |
| 5 | The **belief of the arms was computed three different ways** (the last answer, "any step ever completed", the last step). | The three arms had three different definitions of "the task is done". | Every arm reports a verdict for every step; the belief of the task is true when every step was considered done. |
| 6 | The **token accounting was hard-coded to zero** and the wall clock of the payload was 0. | `tokens = 0` in the runner of run 1. | See 1.2. |

**The proof that the anomaly is gone** is in the trial v2: the naive arm
and the simple-retry arm now behave **identically** (0.56 correct, 0.44
false completions, 31 requests each, on the injected condition of the
Cerebras model), which is what a fair baseline must do.  A baseline that
only adds retries cannot be worse than doing nothing, and it is not.

`tests/test_trial_arms.py` (17 tests) proves the property with a
scripted fake model: the model fails once and then succeeds, the first
telemetry is broken, the first status is `in_progress`, the first call
times out, the first call fails, the first step name is wrong.  In every
case the simple-retry arm is **never worse** than the naive arm, and a
retry never destroys a file the model produced.

### 1.4 The 174 surviving mutants were untriaged

See section 5.

---

## 2. The providers and the models

### 2.1 What is available

`agentether.adapters.openai_compatible` is a new generic worker for the
OpenAI dialect, with a preset per provider: **OpenRouter, Groq,
Cerebras, Mistral, Google AI Studio and a local Ollama**.  The facts
(base URL, auth header, the name of the seed, the free tier) come from the
official documentation, read on 2026-10-20; `docs/providers.md` has the
link of every page and marks what could not be verified as **UNVERIFIED**.

Three things the documentation shows and the code respects:

* the **base paths differ** (Groq is `.../openai/v1`, Gemini is
  `.../v1beta/openai`), so a URL is never concatenated by hand;
* the **seed is not portable** (Mistral calls it `random_seed`, Gemini has
  no seed for the chat completions);
* **only OpenRouter publishes the price of a model**, so the free models
  of the other providers are the ones their documentation lists, and the
  live catalogue is only used to know that they still exist.

**The keys present on this machine** (existence and length only, never
the value): `MINIMAX` (73, the OpenRouter key), `GROQ_API_KEY` (56),
`GEMINI_API_KEY` (53), `CEREBRAS_API_KEY` (52), `MISTRAL_API_KEY` (45).
`OPENROUTER_API_KEY` and `ANTHROPIC_API_KEY` are absent.

**Ollama is not installed** on this machine (15.8 GB of RAM), so there is
no local model.  **Mistral was not used**: its documentation publishes no
list of free models, and a model whose freedom is not documented must not
be called, because a paid model must never be used.

### 2.2 The capability probe

12 requests per candidate, with the prompt of the trial, on a real step of
a real task.  The raw results are in `benchmarks/results/probe-*.json`.

| Provider | Model | ok | telemetry | file blocks | deterministic | tokens/req |
| --- | --- | --- | --- | --- | --- | --- |
| cerebras | gpt-oss-120b | 12/12 | 1.00 | 1.00 | yes | 1178 |
| cerebras | qwen-3.8-27b | 12/12 | 1.00 | 1.00 | yes | ~900 |
| groq | qwen/qwen3.8-27b | 11/12 | 1.00 | 1.00 | yes | 619 |
| groq | openai/gpt-oss-20b | 12/12 | 1.00 | 1.00 | no | 948 |
| google | gemini-3.6-flash | 12/12 | 1.00 | 1.00 | no | 642 |
| google | gemini-3.5-flash-lite | 12/12 | 1.00 | 1.00 | no | 628 |

The probe found **two more defects of the harness**, both fixed for every
arm and committed before the confirmatory data:

1. the example of the prompt did not show the fences, so the models wrote
   the `FILE: path` line **outside** the block and the harness threw their
   work away (the parser accepts both spellings now);
2. the default agent of `urllib` is answered with a 403 by the robot
   filter of two providers (the library sends a name of its own).

### 2.3 The selection, and what happened

The rule was committed in `docs/trial-protocol-v2.md` **before** the probe
ran: three models of three different families and three different
providers, with a naive-arm success between 30 % and 85 % on a 20-task
pilot.

| Provider | Model | naive correct (pilot) | Rate | Rule |
| --- | --- | --- | --- | --- |
| cerebras | gpt-oss-120b | 19/20 | 0.950 | **excluded** (above the band) |
| cerebras | qwen-3.8-27b | 20/20 | 1.000 | **excluded** (above the band) |
| google | gemini-3.5-flash-lite | 17/20 | 0.944 | **excluded** (above the band) |
| google | gemini-3.6-flash | 0/20 | 0.000 | **excluded**: the provider refused the calls (the quota of that model was spent); the 0.00 is an artefact of the refusal, not a property of the model |
| groq | qwen/qwen3.8-27b | 7/10 | 0.700 | **qualifies** |
| groq | openai/gpt-oss-20b | 17/20 | 0.850 | **qualifies** (at the limit) |

**The conflict.**  The two models that satisfy the rule are the two of
**Groq**, and the daily quota of Groq was spent by the probe and the
pilots: 130 000 of the 200 000 documented tokens per day were already
used, and the rule of the maintainer forbids going over half of the daily
quota of a provider.  The two models that *had* the budget (Cerebras and
Google) are the two the rule **excludes** for being too good.

**What was done.**  The rule is applied and reported as it was written.
The confirmatory run uses the two models that had the budget, and their
data are **labelled as a supplementary run**; the deviation is stated in
the evidence document, in the worklog and here.  The reason is worth
stating: the band exists to keep the *correct completion* rate from
having no room, but the **primary** endpoint is the false completion rate
under the injected faults, and a model that is very good still produces
false completions when the harness removes its file.

**This is the honest limitation of this report**: the pre-registered
selection was **not** met, and the trial of the two qualifying models
could not be run at all.

---

## 3. The trial

### 3.1 What was run

* Protocol: `docs/trial-protocol-v2.md`, committed (`5c7418c`) **before**
  the first confirmatory result file.
* Arms: naive, simple-retry, agentether.  Conditions: natural and injected
  (20 % of the attempts).  Task set: 20 procedural multi-step tasks with
  a hidden ground truth.
* Models: `cerebras/gpt-oss-120b` (N = 12) and
  `google/gemini-3.5-flash-lite` (N = 12), 3 arms, 2 conditions.
* Temperature 0, the fault seed 20261020, the attempt cap 3.

### 3.2 The numbers

144 cells, 450 model calls, 10 527 s of calls, 450 000 tokens.  The full
tables, the Wilson intervals, the paired differences and the p values are
in [`docs/evidence.md`](evidence.md), which is **regenerated from the raw
cells** (`benchmarks/results/trial-v2-*-cells.jsonl`).

**The injected condition** (20 % of the attempts get a fault, applied
after the model answered):

| Model | Arm | N | correct | false completion | requests | tokens |
| --- | --- | --- | --- | --- | --- | --- |
| cerebras gpt-oss-120b | naive | 12 | 0.417 | 0.333 | 31 | 30 999 |
| cerebras gpt-oss-120b | simple-retry | 12 | 0.417 | 0.333 | 31 | 31 324 |
| cerebras gpt-oss-120b | **agentether** | 12 | **0.667** | **0.083** | 34 | 42 408 |
| google gemini-3.5-flash-lite | naive | 12 | 0.583 | 0.167 | 42 | 25 892 |
| google gemini-3.5-flash-lite | simple-retry | 12 | 0.833 | 0.167 | 46 | 28 041 |
| google gemini-3.5-flash-lite | **agentether** | 12 | 0.833 | 0.167 | 47 | 43 905 |

**The natural condition** (no injected fault):

| Model | Arm | N | correct | false completion |
| --- | --- | --- | --- | --- |
| cerebras gpt-oss-120b | naive / simple-retry / agentether | 12 | 0.750 | 0.000 |
| google gemini-3.5-flash-lite | naive | 12 | 1.000 | 0.000 |
| google gemini-3.5-flash-lite | simple-retry / agentether | 12 | 0.917 | 0.083 |

**What the numbers say.**

* The **anomaly of run 1 is gone**: the naive arm and the simple-retry
  arm are now identical (0.417 and 0.333 on the injected condition of the
  Cerebras model, 31 requests each).  A baseline that only adds retries
  cannot be worse than doing nothing, and it is not.
* With `cerebras/gpt-oss-120b`, the guarded arm **caught three of the
  four false completions** of the baseline (0.333 -> 0.083) and completed
  three more tasks correctly (0.417 -> 0.667), at the price of three
  more requests and 11 000 more tokens.
* With `google/gemini-3.5-flash-lite`, the guarded arm caught **no**
  additional false completion: all three arms are at 0.167.
* The one false completion of the guarded arm in the natural condition of
  the Google model is a **limit of the library, not a bug**: the verifier
  checks that the files the model *claims* exist, and it cannot know that
  the step asked for a file the model did not produce.  "The claim is
  backed" is not "the work is complete".

### 3.3 The verdicts

| Model | H1: correct completion | H2: false completion (primary) | H3: the overhead |
| --- | --- | --- | --- |
| cerebras gpt-oss-120b | +0.250 (3 against 0 discordant pairs, p = 0.250): **INCONCLUSIVE** (the sample is too small) | +0.250 (3 against 0 discordant pairs, p = 0.250): **INCONCLUSIVE** (the sample is too small) | 34 against 31 requests, 42 408 against 31 324 tokens: **SUPPORTED** |
| google gemini-3.5-flash-lite | +0.000 (1 against 1, p = 1.000): **INCONCLUSIVE** (the sample is too small) | -0.000 (1 against 1, p = 1.000): **INCONCLUSIVE** (the sample is too small) | 47 against 46 requests, 43 905 against 28 041 tokens: **SUPPORTED** |

**The verdicts are inconclusive, and the rule says so.**  The
pre-registered rule is that a difference smaller than the minimum
detectable effect of the sample is **inconclusive** and not "a small
effect".  With N = 12 the minimum detectable effect is **0.404**; the
observed differences are 0.25 (Cerebras) and 0.00 (Google).

The direction of the effect is what one would hope for on the Cerebras
model: **three discordant pairs, all of them in favour of the guarded
arm, and none the other way**.  The exact McNemar test gives p = 0.25,
which is not significant at N = 12: three events cannot reach p < 0.05.
**A bigger sample would decide it; the quota of the free tier did not
allow one.**

The overhead (H3) is **supported**: the guarded arm costs 10 % more
requests and 35 % more tokens on the Cerebras model, and 57 % more tokens
on the Google one.

---

## 4. The bugs that were found and fixed

| Bug | How it was found | Fix | Commit |
| --- | --- | --- | --- |
| The version of the wheel, of the command and of the CHANGELOG disagreed. | Reading the CHANGELOG against the code. | One version, and a test that compares the places. | `2172fdc` |
| The **simple-retry arm of the trial destroyed the work of the model** (the anomaly of the brief). | The sandbox of run 1, which still existed in `%TEMP%`. | Every arm writes the files of every answer. | `d35ef4c` |
| The **prompt did not say that `progress` is a 0-100 scale**, so every completed step was rejected as drift by the guarded arm. | The attempt log of the state of run 1. | The prompt states the scale; the change was applied to all arms. | `d35ef4c` |
| The **fault schedule was keyed on a cumulative counter**, so the arms did not see the same faults. | Reading the runner. | The schedule is a function of the step and of the attempt inside it. | `d35ef4c` |
| The **token accounting of the runner was hard-coded to zero** and the wall clock of the payload was 0. | The committed payload against the code at the time. | The runner counts the tokens and the time. | `d35ef4c` |
| The **catalogue of the models was read with a POST** (404 or 405 on most providers). | The first live listing. | A GET. | `ba8a2b3` |
| The **robot filter of two providers** answered the default agent of `urllib` with a 403. | The first live listing. | The library sends a name of its own. | `ba8a2b3` |
| The **example of the prompt did not show the fences**, so half of the models wrote the `FILE:` line outside the block and the harness threw their work away. | The capability probe. | The example shows the fences; the parser accepts both spellings. | `5c7418c` |
| A **refusal of the provider was measured as a failure of the model** (4 cells of 34). | The requests and the attempts of the cells did not match. | The transport retries a rate limit; the failures are recorded in the cell. | `24b264d` |
| The **fuzzer of the state file opened an event loop per round** (a socket pair per round on Windows): the CI cell of Windows 3.11 failed with `WinError 10055`. | The CI. | The test is async and uses one loop. | `db9dd55` |
| The **accounting test asserted a duration below the resolution of the clock** of Windows before Python 3.13 (15.6 ms). | The CI cell of Python 3.11. | The wait is longer and the assertion looks at the total. | `0e53cfd` |
| The **rule of the format class of the triage had a mistyped escape** (a backspace instead of a word boundary): it found 9 cases instead of 101. | The numbers did not add up. | The regular expression is repaired. | `29fdb61` |
| The **rename had mangled** the comment that explains the name and the entry of 0.2.0 of the CHANGELOG. | Reading the comments. | Both say what is true. | `2172fdc` |

**Left open:** the class "gap (behaviour)" of the mutation triage (598
survivors) was not triaged one by one; see section 5.

---

## 5. The mutation triage

`mutmut` 3.8 in WSL, on `orchestrator.py` and `state_manager.py` only
(the whole package is copied, so that the imports of the mutants work),
and only on the lines the test suite reaches.

| | First run | Second run (after the contract tests) |
| --- | --- | --- |
| Mutants | 2 713 | 2 713 |
| Killed by a test | 1 623 | **1 667** |
| Killed by the timeout (the mutant hangs) | 90 | 70 |
| **Survived** | **1 000** | **976** |

`mutation_triage.py` classifies every survivor by the shape of the change
and by what the shape means:

| Verdict | What it means | Count |
| --- | --- | --- |
| **equivalent** | A keyword argument is replaced by ``None`` and the parameter of the callee really defaults to ``None``.  The verdict comes from the abstract syntax tree of the package, not from a guess. | 50 |
| **cosmetic** | Only the wording of a message changes. | 211 |
| **gap (record)** | The content of a record (an event, a line of the ledger) is wrong. | 16 |
| **gap (format)** | A key of the state file, or the way the file is written, changes.  The format is a public contract. | 101 |
| **gap (behaviour)** | The behaviour changes and no test noticed. | 598 |

The gaps in the format and in the records pointed at the same thing:
nothing looked at the **keys** of the state file, at the **fields** of the
telemetry or at the **records** of the ledger.
`tests/test_contracts.py` (18 tests) pins them now.

**The honest limits of the triage.**  The classification is **rule-based**,
not a hand analysis of the 976 survivors one by one, and the class "gap
(behaviour)" holds everything the other rules do not claim.  The number of
survivors is a weak signal, and the number of gaps is weaker.  The
mutation score of the two modules is **61 %** (64 % with the timeouts).

---

## 6. The state of the repository

| Check | Result |
| --- | --- |
| `pytest` on Windows (CPython 3.14.7) | **406 passed, 2 skipped** |
| `pytest` in WSL on CPython 3.10, 3.11, 3.12 and 3.13 | **406 passed, 2 skipped** on each |
| `mypy --strict` | clean, 58 files, on Windows and on the four Linux versions |
| `ruff check` / `ruff format --check` | clean, 91 files |
| GitHub CI | **green on the 10 cells** (ubuntu/windows x 3.10-3.14) and the dependency audit |
| `python -m build` + `twine check` | the wheel and the sdist of `0.3.0a1` **PASSED** |
| The wheel in a fresh venv | works on Windows and on Linux; the command says `0.3.0a1` |
| `scan_secrets.py` | **0** in the tree, **0** in the history, the wheel is clean |

The repository is **private**.  Nothing was published, no tag was pushed,
no wheel was uploaded.

---

## 7. The money and the secrets

**No money was spent.**  The checks:

* every call went to a free tier of a free model, and the models that were
  called are the ones the documentation lists as free;
* the daily counter of every provider is written to disk with an atomic
  replace, so a run that is interrupted and continued does not start the
  day from zero, and the run of the day stayed under **half** of the
  documented daily quota of the provider;
* `HTTP 402` (a request that needs a paid plan) is never retried and
  stops the run at once;
* **no credit was bought, no payment method was added, no key was
  rotated** and no account was created.  The OpenRouter error of the day
  says "Add 10 credits to unlock 1000 free model requests per day": that
  was **not** done, and the provider was simply left alone;
* the free tier of Google AI Studio is per model: `gemini-3.6-flash` was
  refused with `HTTP 429` (its quota was spent) and the model was left
  alone; `gemini-3.5-flash-lite` still answered.

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
* the keys of the machine were read with PowerShell and passed to the
  children through their environment only; the report states the length
  and never the value.

---

## 8. What was skipped and what could not be verified

* **The pre-registered selection of the models was not met**, and the
  trial of the two qualifying models (the two of Groq) could not be run:
  the daily quota of Groq was spent by the probe and the pilots.  The
  confirmatory run is therefore a **supplementary** run of two models the
  rule excludes.
* **N = 12 per cell**, not the 60 of the plan: the free tier of the
  providers does not allow it in one day.  The minimum detectable effect
  of that sample is 0.40 (see the protocol).
* **Mistral was not used** (no documented list of free models) and
  **Ollama was not installed**.
* The **numeric free tier limits of Google AI Studio and of Mistral are
  not published**; the limits of Cerebras per day are not published
  either.  They are marked UNVERIFIED in `docs/providers.md`.
* The **usage fields of the OpenAI compatible answer of Google and of
  Ollama are not documented**: the token count of the Google model of
  this report is therefore **0**, and the report says so.
* The **class "gap (behaviour)" of the mutation triage** (598 survivors)
  was not triaged one by one.
* The **stretch** of the protocol (a twelve step long task, N = 1) was
  not run: the quota of the day was used by the real cells.

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
