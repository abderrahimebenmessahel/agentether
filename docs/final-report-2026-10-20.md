# The final report of the audit of AgenTether (2026-10-20)

> This report is written by an AI assistant that read the source, the
> tests and the data of the repository line by line, ran the checks and
> made the calls it says it made.  **Every number below comes from a real
> run in this repository**; the commands and their output are in
> `docs/WORKLOG.md` and in the commits of the day.  Where something could
> not be verified, it says so.
>
> This is the **second** report of the day: the first one audited the
> library and ran the trial v2.  The brief of the maintainer asked for
> five things: the consistency of the numbers, the cause of the false
> completions, the declarative expectations of a step, a new confirmatory
> trial and the gates.  This report covers the five.

The repository: <https://github.com/abderrahimebenmessahel/agentether>
(**private**; nothing was published, no tag was pushed, no wheel was
uploaded anywhere).

---

## 0. The erratum of the first version of this report

> The first version of this report (the commit `be84cca`) contained two
> numbers that the raw data does not support.  They are corrected here and
> the old values are kept visible, because a correction that hides what it
> corrects is not a correction.

| What | The first version said | The raw cells say | Why |
| --- | --- | --- | --- |
| The total of the tokens of the trial v2 | "450 000 tokens" | **394 951 tokens** (188 346 for the Google model, 206 605 for the Cerebras model) | The total was read off the wrong place.  `docs/evidence.md` is generated from the raw cells and always carried the right numbers. |
| The token count of the Google model | "0" | **188 346** | The claim came from the note that the usage fields of the OpenAI compatible answer of Google are not documented.  The adapter reads `usage.prompt_tokens` and `usage.completion_tokens` anyway, and the free tier of Google reports them.  What *was* zero is the `model_stats` summary of the **payload** of the resumed Cerebras run: the seeding of the counter of a resumed run read a field that the cells do not have.  That is a bug of the runner, fixed in `benchmarks/trial.py`; it never touched the cells and never touched the tables. |

**The sign convention.**  Every paired difference of this report and of
`docs/evidence.md` is **the guarded arm minus the comparator**.  A
**positive** difference of the correct completion rate is an improvement; a
**NEGATIVE** difference of the false completion rate is an improvement.  The
first version of the report showed the false completion with the opposite
sign in the table of the verdicts ("+0.250" where the table of the paired
differences showed "-0.250"), and the rule that turns a difference into a
verdict was inverted with it: the hypothesis of the false completion was
tested with the wrong sign, and an arm that caught **more** false
completions would have been declared **NOT SUPPORTED**.  Both are
corrected.  The verdicts of the trial v2 do not change, because every
difference of that run is smaller than the minimum detectable effect of its
sample and every verdict was **INCONCLUSIVE** anyway.

**A test prevents the repetition.**
`tests/test_evidence_consistency.py` recomputes every total of
`docs/evidence.md` and of this report from the raw cell files, and it
fails when a number does not match, when `docs/evidence.md` is not what
`benchmarks/evidence.py` produces, or when the tables of the document do
not use one sign convention.

---

## 1. The consistency fixes

Three contradictions between the report of the first session and the raw
data were fixed, each with a test.

### 1.1 The totals

The raw cells of the two runs say:

| Run | Requests | Tokens | Wall clock (s) |
| --- | --- | --- | --- |
| trial v2 (the supplementary run) | 450 | 394 951 | 10 527.1 |
| trial v3 (the confirmatory run) | 194 | 187 244 | 2 487.8 |
| **total** | **644** | **582 195** | **13 014.9** |

**450** is the number of the *requests* of the trial v2, and the total of
its tokens is **394 951**.  The generator now writes a **total row** in
the table of the totals (a reader must be able to add the rows of the
table and find the same number) and it can build a document with several
runs, so that the supplementary run of the protocol v2 and the
confirmatory run of the protocol v3 live in the same document without
being mixed.

The bug of the runner that carried a total of zero into the summary of
the payload of a resumed run is fixed: `ModelStats` has a `seeded_tokens`
field, and the seeding of the counters of a resumed run reads the
`tokens` field of the cells (the field the cells really have) instead of
the `input_tokens` and `output_tokens` fields (the fields they do not
have).  A test pins it.

### 1.2 One sign convention

The convention is stated **once**, in a section of its own of
`docs/evidence.md`, and every table follows it.  Two things were wrong
before: the table of the hypotheses showed the **opposite sign** of the
table of the paired differences for the false completion, and the rule
that turns a difference into a verdict was inverted with it (the
hypothesis of the false completion was tested with
`_verdict(-difference, p, mde, -1)`, which would have declared an arm
that caught **more** false completions as **NOT SUPPORTED**).

### 1.3 The two arms are not identical everywhere

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
further along the fault schedule.  The property the baseline must have is
not "it is identical" but "it is **never worse** than doing nothing", and
that property holds and is tested by `tests/test_trial_arms.py`.

---

## 2. The cause of every false completion

The analysis is in [`docs/false-completions.md`](false-completions.md)
(the trial v2) and [`docs/false-completions-v3.md`](false-completions-v3.md)
(the trial v3).  Both are **generated** by `benchmarks/analyze_false.py`
from the raw cells, the sandboxes and the attempt logs of the runs.  **No
model was called.**

| Cause | The trial v2 (17 false completions) | The trial v3 (13 false completions) |
| --- | --- | --- |
| **(i)** an injected fault damaged an artifact and the arm did not catch it | 14 | 7 |
| **(ii)** a required file was never produced and the claim did not mention it | 0 | 4 |
| **(iii)** something else | 3 | 2 |

**The finding that matters.**  The verifier of the guarded arm of the
trial v2 was `artifacts_exist()`: it checks that the files the model
**claims** exist.  So it catches a false completion whose artifact is
**missing** (the check fails, the step is retried) and it cannot catch
one whose artifact **exists but is damaged** (the check passes).  Of the
four false completions of the naive arm on Cerebras, three were a missing
file (`replay_previous`, `lie`, `drop_file_block`) and one was a file cut
in the middle (`truncate_file`): the guarded arm caught the three and
missed the one.

**This is a limit of the verifier, not of the timing of the faults.**  The
faults of the trials are applied *inside* the worker, that is **before**
the verification of the library, so the library could have caught them if
it had looked at the content.  The harness order is right; the verifier
was too weak.

**Why the guarded arm caught three of the four on Cerebras and none on
Google.**  The two cells are not the same kind of result.  On Cerebras
the three caught false completions were a **missing** file and the one it
missed was a **damaged** file.  On Google the guarded arm caught the
missing one and missed the damaged one, but it **added** a false
completion of its own: the answer of the model held a complete file and
the file on disk was its beginning, because the parser of the harness
closed the file on the fence of a code block **inside** the file (a
Markdown file that shows how to run the script is the common case).  The
rest of the file was lost and the ground truth failed.  The naive arm was
right on those two tasks by luck: the Google model is not deterministic,
and its answer for them did not hold a code block.

**That defect was in the harness, and it is fixed**: the parser follows
the rule of CommonMark now (a fence with an info string opens a block and
never closes another one, and a block closes on a fence at least as long
as its own), the prompt of the trial v3 asks for **four** backticks, and
`tests/test_trial_parser.py` (13 tests) pins it down.  The three false
completions of the trial v2 that it caused are **not** corrected: the
data of the trial v2 stay as they are, and they are a supplementary run.

**A second defect of the baseline, found by the analysis.**  The
docstring of `_contract_is_completed` says that the simple-retry arm
"parses the contract: the step name must match and the status must be
completed".  The code does **not** check the step name (`parse_telemetry`
validates the structure of the telemetry and not the name of the step),
so the baseline accepted the answer of the **previous** step as the
completion of the current one.  That is why the `replay_previous` fault
ended in a false completion of the baseline.  The library itself checks
the step name (a drift check), which is why the guarded arm caught it.

---

## 3. The declarative expectations of a step

The main change of the library.  A step can now declare what it **must**
produce, and the library checks that declaration instead of only the
claim of the agent:

```python
@orch.guard_step(
    "write",
    expects=[
        "README.md",  # must exist, not empty
        Expectation("data.json", json_keys=("a", "b")),  # must be a JSON with a and b
        Expectation("build.py", python_valid=True),  # must compile
        Expectation("guide.md", markdown_headings=("## Install",)),
    ],
)
async def write(ctx): ...
```

| What | How it works |
| --- | --- |
| The declaration | `src/agentether/expectations.py` is new: the `Expectation` dataclass, the resolution of the declared paths and the composite verifier. |
| The validators | The checks of the content **reuse** the verifiers of the library (`file_contains`, `json_file_valid`, `python_syntax_valid`, `markdown_has_headings`). |
| The confinement | The paths are resolved inside the work directory when the step is **declared**: an absolute path, a `..` component and a symbolic link that leaves the directory are a `ConfigurationError` and not a failure at the end of the run. |
| The evaluation | The expectations are evaluated after **every** attempt, whatever the agent claimed.  **A step cannot complete while a declared expectation is unmet.** |
| The failure | A retryable `VerificationFailedError`, and the corrective hint of the next attempt **names the missing files**. |
| The order | The expectations are checked **before** the verifiers of `verify=[...]`: a file that does not exist is the more actionable failure. |

**The tests.**  `tests/test_expectations.py` (21 tests) and two property
tests in `tests/test_properties.py`.  They cover the invariant, the
confinement of the paths, the validators, the hint, the retry and the
record of the ledger.  `docs/audit-notes.md` has the new invariant with
its eight proofs (E1 to E8).

**The documentation.**  `docs/spec/expectations-v1.md` is the contract (it
is written so that another implementation could interoperate),
`docs/verifiers.md` has the guide, the README has a section, the CHANGELOG
has the entry and `examples/declared_expectations.py` is a runnable
example (it lies twice and is caught twice).

**What `expects` cannot do**, and what the documentation says: an
expectation checks the **shape** of a file, not its meaning.  A JSON that
parses may hold the wrong number, a Markdown that has its headings may say
the wrong thing, a Python that compiles may do the wrong thing.  The
semantic check is left to a judge (`llm_judge`) or to a verifier of your
own (`callable_verifier`).

---

## 4. The trial v3

### 4.1 What was run

* Protocol: [`docs/trial-protocol-v3.md`](trial-protocol-v3.md), committed
  (`f4abb99`) **before** the first result file of the run.
* Arms: naive, simple-retry, agentether-claims-only (the configuration of
  the trial v2) and agentether (with the declarative expectations).
* Conditions: **injected** (20 % of the attempts, applied after the model
  answered and before the library verifies the step).  The natural
  condition did not fit in the budget of the day.
* Tasks: **new** (`benchmarks/tasks_v3.py`): twenty new tasks, new
  subjects, new numbers, new function names, a new fault seed (20261021)
  and a new fault (`hide_file`).
* Models: `cerebras/gpt-oss-120b` and `google/gemini-3.5-flash-lite`,
  temperature 0, the seed 20261021 where the provider takes one (Google
  has no seed for the chat completions).

**The deviation, decided before the new data.**  The band of the selection
rule of the trial v2 (a naive success between 30 % and 85 %) was **not
satisfiable** by the models that had quota: the two models that satisfied
it were the two of Groq, whose daily quota was spent by the probe and the
pilots, and the two models that had the budget were excluded by the band
for being too good.  The rule of the trial v3 is the **capability probe
and the quota, with no band**, because the primary endpoint (the false
completion rate under the injected faults) is not hidden by a ceiling
effect on the naive success.  The data of the trial v2 stay a
**supplementary** run.

**The budget of the day, and why the run is partial.**

| Provider | The requests of the day before the run | What was left under the rule (half of the daily quota) | What the run did |
| --- | --- | --- | --- |
| cerebras | 404 | 96 requests (500 - 404) and 137 506 tokens (500 000 - 362 494) | 96 requests, 112 378 tokens, 6 tasks per cell |
| google | 430 | 320 requests (750 - 430) | 98 requests, 74 866 tokens, 6 tasks per cell (7 for two arms); the provider refused the calls of the afternoon with `HTTP 429 - You exceeded your current quota` |

The full grid of the protocol (60 tasks per cell, 4 arms, 2 conditions, 2
models, 960 cells) needs about **1 500 requests and 1.4 million tokens**
for Cerebras and about **1 900 requests** for Google: **three provider
days per model**.  The run of the day is the first slice of it.

### 4.2 The numbers

**The injected condition** (the primary endpoint), 50 cells, 194 model
calls, 2 487.8 s of calls, 187 244 tokens:

| Model | Arm | N | correct | false completion | requests | tokens |
| --- | --- | --- | --- | --- | --- | --- |
| cerebras gpt-oss-120b | naive | 6 | 0.500 | 0.500 | 21 | 20 936 |
| cerebras gpt-oss-120b | simple-retry | 6 | 0.500 | 0.500 | 22 | 21 872 |
| cerebras gpt-oss-120b | agentether-claims-only | 6 | 0.667 | 0.167 | 26 | 34 594 |
| cerebras gpt-oss-120b | **agentether** | 6 | 0.500 | **0.000** | 27 | 34 976 |
| google gemini-3.5-flash-lite | naive | 7 | 0.286 | 0.571 | 24 | 15 864 |
| google gemini-3.5-flash-lite | simple-retry | 7 | 0.714 | 0.143 | 29 | 15 187 |
| google gemini-3.5-flash-lite | agentether-claims-only | 6 | 0.833 | 0.167 | 22 | 21 377 |
| google gemini-3.5-flash-lite | **agentether** | 6 | **1.000** | **0.000** | 23 | 22 438 |

The Wilson intervals, the paired differences, the p values and the
verdicts are in [`docs/evidence.md`](evidence.md), which is generated from
the raw cells and checked by a test.

### 4.3 The verdicts

The rule of the pre-registration: a difference smaller than the minimum
detectable effect of the sample is **inconclusive**, not "a small effect".
With N = 6 the MDE of the paired difference is **0.571**.

| Model | H1: correct completion | H2: false completion (primary) | H3: the overhead | H4: the expectations |
| --- | --- | --- | --- | --- |
| cerebras gpt-oss-120b | +0.000 (p = 1.000): **INCONCLUSIVE** | **-0.500** (3 tasks in favour of the guarded arm, p = 0.250): **INCONCLUSIVE** | 27 against 22 requests, 34 976 against 21 872 tokens: **SUPPORTED** | -0.167 (p = 1.000): **INCONCLUSIVE** |
| google gemini-3.5-flash-lite | +0.167 (p = 1.000): **INCONCLUSIVE** | **-0.167** (1 task in favour of the guarded arm, p = 1.000): **INCONCLUSIVE** | 23 against 29 requests, 22 438 against 15 187 tokens: **SUPPORTED** | -0.167 (p = 1.000): **INCONCLUSIVE** |

**What the verdicts mean, stated plainly.**  Every hypothesis that
depends on the size of the sample is **inconclusive**: the run of the day
reached six tasks per cell, and the quota of the free tier of the day was
not enough for the sixty of the protocol.  Three events cannot reach
p < 0.05, and a difference of 0.500 is below the MDE of 0.571.

**What the data show anyway** is the **direction**, and it is the same in
the two models and in the two trials:

* the naive arm and the baseline believed the task was done while the
  ground truth said it was not, on three tasks (Cerebras) and on one
  (Google);
* the arm that only checks the **claimed** files caught two of them
  (Cerebras) and one (Google);
* the arm that **declares** what the step must produce caught **all** of
  them, in the two models.

The causes of those false completions are the three cases of the
analysis: the file was removed (`hide_file`, `lie`, `drop_file_block`),
the file was cut in the middle (`truncate_file`), or the file was never
produced and the claim mentioned only the files the model did produce.
The declaration of the step sees the three cases; the check of the claimed
files sees the first one only.  **That is the mechanism the feature was
built for, and the data of the day are consistent with it** -- but six
tasks per cell cannot make it a statistical result, and the report does
not pretend otherwise.

### 4.4 What the trial v3 does NOT show

* It does not show that the library makes agents reliable in general: the
  tasks are synthetic, the models are free tier models with their own
  limits, the sample is six tasks per cell and the ground truth checks
  are the ones the author of the library wrote.
* It does not show a **significant** effect: every verdict is
  inconclusive.
* It does not show the effect in the **natural** condition: the budget of
  the day did not reach it.  The command to continue is in the worklog.
* It does not show anything about a model whose free tier is exhausted:
  the two models of Groq were not called at all, as in the trial v2.

---

## 5. The bugs that were found and fixed

| Bug | How it was found | Fix | Commit |
| --- | --- | --- | --- |
| The token total of the report was wrong (450 000 against 394 951) and the token count of the Google model was said to be 0. | Comparing the report with the raw cells. | The runner seeds the tokens of the cells of an earlier session; the generator writes a total row; a test compares every total with the raw cells. | `0974ee7` |
| Two tables of the evidence document used **opposite signs** for the same quantity, and the verdict rule of the false completion was inverted with them. | Reading the tables of the report against the tables of the evidence document. | One sign convention, stated once; the verdict rule uses the raw difference with the expected sign. | `0974ee7` |
| The report said the naive arm and the baseline are identical; they are identical on one cell only. | Recomputing the cells per arm. | The report says what the data say, and the property that matters (the baseline is never worse) is tested. | `0974ee7` |
| The parser of the harness cut a file that holds a code block, and three of the seventeen false completions of the trial v2 were caused by it. | The analysis of the false completions, comparing the file on disk with the answer the model recorded. | The rule of CommonMark; the prompt asks for four backticks; the faults were rebuilt on the new parser. | `66e03a0` |
| The docstring of the baseline said it checks the name of the step; the code does not, so it accepted the answer of the previous step. | The analysis of the false completions. | Documented as a defect of the harness of the trial v2 (the data stay as they are).  The library itself checks the name of the step. | `66e03a0` |
| The arms of the harness swallowed the **stop** of the daily cap and the run wrote 136 empty cells. | The run of the trial v3 itself. | `TrialHalt` is a `BaseException`; a test pins it; `collect_cells.py` drops the cells without an attempt and prints how many it dropped. | `c3edf5b` |
| A path of the shape `C:\Windows\system.ini` was a legal file name on Linux (the confinement refused an absolute path only on the platform that ran it). | The WSL matrix of the CI. | The pattern of a drive letter is refused on every platform. | `23302d7`, `f40221d` |
| The runner had no cap of tokens, only a cap of requests; a provider whose quota is a number of tokens could have been over-quota. | Reading the runner before the trial v3. | A cap of tokens, and the cap of the day **defaults to half** of the documented daily limit of the provider. | `829d36e` |
| The arms of the trial ran task by task, so a run that stopped at the cap left some tasks with some arms and some without. | The run of the trial v3. | The arms run **inside** the tasks: the tasks that are done are complete. | `5dc2790` |

**Left open.**

* The class "gap (behaviour)" of the mutation triage (598 survivors of
  the second run) is still not triaged one by one; the mutation score of
  the two modules is still **61 %**.
* The **natural** condition of the trial v3 was not run (the budget of
  the day).  The runner is resumable and the command is in the worklog.
* The trial v3 reached six tasks per cell, not the sixty of the protocol.
  The remaining **three provider days per model** are not done.
* The token limit of the free tier of Google AI Studio is still not
  published: the provider refused the calls with `HTTP 429` and the
  limit stays **UNVERIFIED** in `docs/providers.md`.

---

## 6. The state of the repository

| Check | Result |
| --- | --- |
| `pytest` on Windows (CPython 3.14.7) | **479 passed, 4 skipped** |
| `pytest` in WSL on CPython 3.10, 3.11, 3.12 and 3.13 | **481 passed, 2 skipped** on each |
| `mypy --strict` | clean, 65 files, on Windows and on the four Linux versions |
| `ruff check` / `ruff format --check` | clean, 106 files |
| `pytest --cov=src/agentether` | **89 %** of the lines (the new module `expectations.py`: 97 %) |
| GitHub CI | **green on the ten cells** and on the dependency audit (the run `39497811414`) |
| `python -m build` + `twine check` | the wheel and the sdist of `0.3.0a1` **PASSED** |
| the wheel in a fresh venv | works on Windows (`packaging_check.py`) and on Linux (the quickstart and the command) |
| `scan_secrets.py` | **0** in the tree, **0** in the history, the wheel is clean |

The ten cells of the CI are `ubuntu-latest` and `windows-latest` with
CPython 3.10, 3.11, 3.12, 3.13 and 3.14; the eleventh job is the
`pip-audit` of the dependency audit.

The repository is **private**.  Nothing was published, no tag was pushed,
no wheel was uploaded.

---

## 7. The money and the secrets

**No money was spent.**  The checks:

* every call went to a free tier of a free model, and the models that were
  called are the ones the documentation lists as free; Mistral was not
  called at all (its documentation publishes no list of free models);
* the daily counter of every provider is written to disk with an atomic
  replace, so a run that is interrupted and continued does not start the
  day from zero, and the run of the day stayed under **half** of the
  documented daily quota of the provider (the runner's cap of the day now
  **defaults** to that half);
* `HTTP 402` (a request that needs a paid plan) is never retried and
  stops the run at once;
* **no credit was bought, no payment method was added, no key was
  rotated** and no account was created.  The OpenRouter error of the day
  says "Add 10 credits to unlock 1000 free model requests per day": that
  was **not** done, and the provider was simply left alone;
* the free tier of Google AI Studio is per model: `gemini-3.6-flash` was
  refused with `HTTP 429` (its quota was spent) and the model was left
  alone; `gemini-3.5-flash-lite` answered until **its** quota was spent
  in the afternoon, and the run stopped cleanly.

**No secret leaked.**  The checks:

* the key is read from the environment only; it is never written to a
  file, never passed on a command line, never logged and never in an
  error message; the keys were read with PowerShell and passed to the
  children through their environment only;
* every message that could echo the server answer goes through a
  redaction step, and there is a **test per provider** that puts the key
  in the body of a server error and asserts that it is redacted;
* `scan_secrets.py` scans the tree, the git history, the result files,
  the logs and the built wheel; it knows the key format of OpenRouter,
  Groq, Cerebras and Google; it reports **0** matches everywhere;
* the report states the length of the keys and never their value.

---

## 8. What was skipped and what could not be verified

* **The natural condition of the trial v3** was not run: the budget of the
  day of the free tier was spent on the injected condition, which carries
  the primary endpoint.  The runner is resumable and the exact command is
  in `docs/WORKLOG.md`.
* **N = 6 tasks per cell** (7 for two arms of the Google model), not the
  60 of the protocol: the free tier of the providers does not allow it in
  one day.  The full grid needs three provider days per model.  The
  MDE of the sample is 0.571 and every verdict that depends on the size
  of the sample is **inconclusive**.
* **Groq was not called at all**: its daily quota (200 000 tokens) was
  spent by the probe and the pilots of the day, and the rule of the
  maintainer forbids going over half of it.
* The **numeric free tier limits of Google AI Studio and of Mistral are
  not published**; the limits of Cerebras per day are not published
  either.  They are marked UNVERIFIED in `docs/providers.md`.  The Google
  provider refused the calls of the afternoon with `HTTP 429` and the
  limit it enforces is not documented.
* **Mistral was not used** (no documented list of free models) and
  **Ollama was not installed**.
* The **class "gap (behaviour)" of the mutation triage** (598 survivors)
  was not triaged one by one.
* The **stretch** of the protocol (a twelve step long task, N = 1) was
  not run: the quota of the day was used by the real cells.

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
   resumable, the protocol is pre-registered, and the remaining grid is
   three provider days per model.  Sixty tasks per cell would make the
   verdict of the primary endpoint decidable (the MDE of N = 60 is 0.181).
