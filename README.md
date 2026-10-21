# AgenTether

[![PyPI](https://img.shields.io/badge/pypi-agentether-blue)](https://pypi.org/project/agentether/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)](CHANGELOG.md)
[![Typing](https://img.shields.io/badge/typing-mypy%20--strict-informational)](https://mypy-lang.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-success)](pyproject.toml)

**A tiny supervisor for LLM agent steps: it checks the agent's claims against
reality, detects loops semantically, and keeps the project state in a
human-readable Markdown file.**

AgenTether wraps **one** function -- your LLM call -- and keeps the control
path (the plan, the state, the limits, the validation) in deterministic code
and on disk.  It is not a multi-agent framework, a workflow engine or an
orchestration platform, and it does not try to be.  It is standard library
only and Python 3.10+.

Four ideas, and nothing else:

1. **The agent's claims are verified, not trusted.**  A step that says
   `status: "completed"` can be checked against the filesystem: does the file
   exist, is the JSON valid, does the script compile?
2. **Loops and stalls are detected semantically**, not only by counting
   retries.  Three answers that look different but say the same thing are a
   loop.
3. **The project state is a human-readable, human-editable Markdown file**
   -- with a section that belongs to *you*, which the library never rewrites.
4. **It wraps one function.**  No graph, no roles, no message bus, no
   framework to adopt.

> **Status: Alpha.**  The API may still change.  The audit in
> [`docs/audit-notes.md`](docs/audit-notes.md) was written by an AI, not by
> an independent human reviewer, and the evidence below comes from a tiny
> sample of three free models.  Read
> [Known limitations](#known-limitations) before you rely on it.

## 60 seconds, no API key

```bash
git clone https://github.com/abderrahimebenmessahel/agentether.git
cd agentether && pip install -e ".[dev]"
python examples/demo.py
```

The demo's "agent" claims to have written a file it never wrote.  The real
output:

```text
step      : notes
status    : completed
attempts  : 2
summary   : I wrote the notes for real.
the file  : True
the first claim was rejected: the file did not exist yet
the memory file: C:\Users\rimob\AppData\Local\Temp\tmp1sr8sq_i\memory\PROJECT_MEMORY.md
```

The first attempt claimed success; the verifier found that the file was not
there, the agent was told why, and the second attempt did the work.

## The 5 line quickstart

```python
from agentether import AutoOrchestrator

orch = AutoOrchestrator(
    roadmap=["research", "write"], memory_dir="./memory", timeout_seconds=60, max_retries=3
)


@orch.guard_step("research")
async def research(ctx):
    return await my_llm(ctx.build_prompt("Research X"))


result = await research()  # StepResult with validated telemetry
```

`ctx` is injected by the decorator; the decorated function returns the raw
text of the model.  The decorated callable is always awaited, even when the
wrapped function is a plain `def` (synchronous workers run in a thread).

## What it does

```text
                    CONTROL PATH  (deterministic code + files on disk)
  ┌──────────────────────────────────────────────────────────────────────┐
  │   @orch.guard_step("research", verify=[...])                        │
  │        ▼                                                             │
  │   ┌────────────────────┐   read     ┌─────────────────────────────┐   │
  │   │  AutoOrchestrator  │──────────►│  PROJECT_MEMORY.md          │   │
  │   │  • roadmap order   │◄──────────│  • roadmap checklist        │   │
  │   │  • timeouts        │  persist  │  • completed step summaries │   │
  │   │  • retries+jitter  │           │  • human owned section      │   │
  │   │  • drift checks    │           │  • attempt log              │   │
  │   │  • verifiers       │           │  • machine readable JSON    │   │
  │   │  • loop detection  │           │  • circuit breaker state    │   │
  │   │  • budgets         │           └─────────────────────────────┘   │
  │   │  • circuit breaker │                                            │
  │   └─────────┬──────────┘                                            │
  │             │ build_prompt()                                         │
  └─────────────┼──────────────────────────────────────────────────────┘
                │
  ┌─────────────▼──────────────────────────────────────────────────────┐
  │             │                    DATA PATH  (untrusted)              │
  │   ┌─────────┴──────────┐  text  ┌──────────────────────────────┐    │
  │   │   your LLM call    │───────►│  telemetry JSON → validated  │    │
  │   └────────────────────┘        └──────────────────────────────┘    │
  └──────────────────────────────────────────────────────────────────────┘
```

More in [`docs/architecture.md`](docs/architecture.md).

## The telemetry contract

The answer must end with a single JSON object.  Prose before it is fine; a
second JSON object later is ignored -- the last valid one wins.

```json
{
  "step": "research",
  "status": "in_progress | completed | blocked | failed",
  "summary": "<one short paragraph: what you did and what you found>",
  "progress": 100,
  "next_step": "write",
  "artifacts": ["notes/research.md"]
}
```

A wrong `step`, an unknown `status` or `completed` with a `progress` below
100 is a drift error and is retried.  A mismatching `next_step` is only a
**warning** unless the orchestrator was built with `strict_next_step=True`.

The full contract (draft, for other implementations) is in
[`docs/spec/telemetry-contract-v1.md`](docs/spec/telemetry-contract-v1.md).

## Verification: trust, but check

```python
from agentether import artifacts_exist, file_contains, json_file_valid


@orch.guard_step(
    "research",
    verify=[
        file_contains("notes.md", "## Findings"),
        json_file_valid("notes.json", required_keys=["sources"]),
        artifacts_exist(),
    ],
)
async def research(ctx): ...
```

The verifiers run in order, all of them must pass, each has its own timeout,
and an exception inside a verifier is a *failed verification*, not a crash.  A
failed verification is retried with the reason injected into the next attempt:
`"you reported completed but: the file does not exist: notes.md"`.

Built in: `file_exists`, `file_contains`, `json_file_valid`,
`json_schema_subset`, `markdown_has_headings`, `python_syntax_valid`,
`artifacts_exist`, `command_succeeds` (argv list, **no shell**, the whole
process tree is killed on a timeout), `callable_verifier` and `llm_judge` (an
interface only -- the core ships no provider code).

Every path that comes from the model is untrusted: absolute paths, `..`
components and symlinks that escape the work directory are rejected.

## Declaring what a step must produce

A verifier checks what the agent **claimed**.  An **expectation** checks
what the step **owes**: the agent can claim to be done while it never wrote
half of the files the step asked for, and the check of the claimed files
passes.

```python
from agentether import Expectation


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

The expectations are checked after **every** attempt, whatever the agent
claimed, and a step cannot complete while one of them is unmet.  An unmet
expectation is a retryable `VerificationFailedError`, and the hint of the
next attempt names the missing files: *"the step did not produce what it
declared: the step must produce these files: data.json"*.

The paths are confined to the work directory (an absolute path, a `..`
component and a symlink that escapes it are refused when the step is
declared).  An expectation checks the **shape** of a file, not its meaning:
a JSON that parses may hold the wrong number.  For the meaning you need a
judge (`llm_judge`) or a check of your own (`callable_verifier`).

The full contract is in [`docs/spec/expectations-v1.md`](docs/spec/expectations-v1.md).

## The claims ledger and the "reliability meter"

Every attempt that produced a claim is recorded in `claims.jsonl`: the status
the agent reported, the artifacts it claimed, the summary and the outcome of
the verification.

```console
$ agentether stats ./memory
claims recorded : 12
claims completed: 9
verified true   : 7
verified false  : 2
false claim rate: 0.222

per step:
  research: claims=8 completed=6 verified_true=5 verified_false=1
```

`agentether audit ./memory` verifies the hash chain of the event and claim
logs (each line carries the SHA-256 of the previous one, and a head file
carries the hash of the last line).  It detects accidental or naive tampering
-- **not** an attacker who rewrites the whole chain.

`agentether report ./memory --format html` builds a self-contained report of
the run (the agent text is escaped, so a report can never carry a script into
your browser).

## Human in the loop

`PROJECT_MEMORY.md` has a section that belongs to you:

```markdown
<!-- contextguard:human:start -->
Write it in bullet points, no more than five.
<!-- contextguard:human:end -->
```

The library never rewrites it.  It is injected into the agent's context with
the highest priority.  When a step ends `blocked`, a "Needs human input"
entry is written; as soon as you edit your section, the step may run again
and your text is injected as a hint.

## The evidence

### The simulated benchmark (not a real world measurement)

> **This is a simulation.**  No LLM was called.  A seeded random number
> generator produces a failure schedule for a synthetic agent, and two runners
> are compared over the very same schedules.  The numbers describe the
> *policies*, not the behaviour of any model.

```console
$ python -m agentether benchmark --trials 1000 --seed 0
| Metric | naive | guarded |
| --- | --- | --- |
| tasks | 1000 | 1000 |
| **correct completion rate** (done *and* really finished) | 0.294 | 0.438 |
| reported completion rate (claims only) | 0.597 | 0.438 |
| false completion rate (claimed, not done) | 0.303 | 0.000 |
| mean attempts per step | 1.696 | 1.808 |
| total attempts | 5088 | 5425 |
| repeated attempts (answer ~ previous answer) | 1140 | 1276 |
| simulated cost (tokens) | 4070400 | 4340000 |
| mean time to halt (s) | 10.176 | 10.850 |
```

The naive runner "completes" more tasks, but 30.3% of them were never really
done: it believed claims the agent had not earned.  The guarded runner
refuses to count them, so its completion rate drops and its cost rises
slightly.  That is the trade, stated plainly.  The result is reproducible
(identical on Linux and Windows) and is committed in
[`benchmarks/results/seed-0.json`](benchmarks/results/seed-0.json).

### The real model trial (tiny sample, one day)

Three trials were run, with the protocol **pre-registered and committed
before the first result file exists**
([`docs/trial-protocol-v2.md`](docs/trial-protocol-v2.md),
[`docs/trial-protocol-v3.md`](docs/trial-protocol-v3.md) and its
[addendum](docs/trial-protocol-v3-addendum.md)).  The full tables, the
Wilson intervals, the paired differences and the p values are in
[`docs/evidence.md`](docs/evidence.md), which is **generated from the
raw cells** and checked by a test.

**The trial v3 (the confirmatory run).**  Four arms (naive, simple-retry,
agentether-claims-only and agentether with the **declarative
expectations**), the injected faults (20 % of the attempts) and **three
models**: two of a free tier (`cerebras/gpt-oss-120b` and
`google/gemini-3.5-flash-lite`) and one **local** (`ollama/qwen2.5:3b-instruct`,
which has **no quota** at all).  Every rate below is computed on the
**common set** of the tasks of the cell: the tasks that every arm of the
cell completed.

The **injected** condition, the primary endpoint:

| Model | N | naive | simple-retry | agentether-claims-only | **agentether** (with `expects`) |
| --- | --- | --- | --- | --- | --- |
| `cerebras/gpt-oss-120b` | 23 | 0.565 | 0.565 | 0.174 | **0.000** |
| `ollama/qwen2.5:3b-instruct` | 35 | 0.543 | 0.829 | 0.200 | **0.114** |
| `google/gemini-3.5-flash-lite` | 6 | 0.500 | 0.167 | 0.167 | **0.000** |

(the false completion rate; the correct completion rate, the Wilson
intervals, the paired differences and the p values are in
[`docs/evidence.md`](docs/evidence.md))

**Two of the three cells decide the primary endpoint.**  For the
Cerebras model the guarded arm has **no** false completion against 0.565
of the baseline (13 tasks in favour of the guarded arm, the exact
McNemar test gives p < 0.001, and the difference is above the minimum
detectable effect of the sample): **H2 is SUPPORTED**.  For the local
model the difference is -0.714 (26 tasks in favour, p < 0.001) and the
correct completion rate is also better (+0.543, p < 0.001): **H1 and H2
are SUPPORTED**.  For the Google model the sample is still too small
(N = 6): every verdict is **INCONCLUSIVE**.

**The cost of honesty is in the evidence.**  The guard does not make a
task succeed; it makes a false "done" visible.  For the Cerebras model
the guarded arm ends **7** tasks of the 23 as an honest "not completed"
(the ground truth says they were not finished and the arm says so), and
**4** of them were false completions of the baseline.  The naive arm has
**0** honest failures and **13** false completions: the same tasks,
reported as successes.

**What the data do NOT show.**  The sample is still small (23 to 35
tasks per cell, not the 60 of the protocol), the tasks are synthetic, the
ground truth checks are the ones the author of the library wrote, and two
of the three models are free tier models with their own limits.  The
local model is **not deterministic** at temperature 0 (the GPU is not),
so the comparison is paired on the task and the fault schedule and not
on the answer of the model.

**The trial v2 (the supplementary run).**  Three arms and two conditions,
N = 12 tasks per cell, two models.  The selection rule of that protocol
(a band on the naive success rate) was **not** met: the two models that
satisfy it are the two of Groq, whose daily quota was spent by the probe
and the pilots, and the two models that had the quota are the two the
rule excludes.  The run is therefore a **supplementary** run, and the
deviation is stated in [`docs/evidence.md`](docs/evidence.md) and in
[`docs/WORKLOG.md`](docs/WORKLOG.md).

## When **not** to use AgenTether

* **When the workflow must survive a cluster.**  Use Temporal or Dapr Agents.
* **When you want a framework to own the shape of the application.**  Use
  LangGraph or Pyantra; AgenTether has no graph, no streaming, no typed
  state.
* **When "retry this function" is the whole problem.**  Use tenacity; it has
  a much richer retry vocabulary.
* **When you need cross-process locking or a shared state store.**  AgenTether
  is a single process with a single directory, on purpose.
* **When the check needs a model.**  A judge model is available
  (`llm_judge`), but a judge inherits the unreliability of the model.  Use a
  deterministic check where you can.
* **When you need an audit trail for a compliance requirement.**  The hash
  chain is a tripwire, not a signature.

The full comparison, with what each project does better, is in
[`docs/comparison.md`](docs/comparison.md).

## Known limitations

* **Single process only.**  Writers are serialised with an `asyncio.Lock`
  within one process.  There is no cross-process locking: two orchestrators
  must not share a memory directory.
* **A sync function cannot be killed on timeout.**  A thread is not
  interruptible: when a synchronous worker exceeds `timeout_seconds`, the
  supervisor stops *waiting*, but the thread keeps running.
* **`max_memory_chars` counts characters, not tokens**, and the default token
  counter is a character heuristic.  Both are approximations.
* **The loop detector compares text, not meaning.**  It catches answers that
  are near identical after the normalisation; it can miss a loop whose answers
  are lexically diverse but semantically equal, and it can flag answers that
  share most of their shingles.
* **The model can still lie.**  AgenTether validates the shape and the
  consistency of the telemetry and can check a claim against the filesystem.
  It cannot tell whether the work is any good.
* **A verifier that asks a model is not a check.**  `llm_judge` is an
  interface; the judgement inherits the unreliability of the model.
* **`command_succeeds` runs a subprocess** with your privileges.  Only
  verify commands you trust, and keep them outside the agent writable work
  directory (the default rejects an executable inside it).
* **The evidence is small.**  The trial is a tiny sample from two free
  models on one day, and the hypotheses it tests came out **inconclusive**
  (the sample is too small to reach the minimum detectable effect).  The
  run is also a *supplementary* one: the selection rule of the protocol
  was not met, for the reason given in
  [`docs/evidence.md`](docs/evidence.md).
* **The audit was written by an AI.**  There is no independent human review
  of this code yet.

## Development

Developed by Abderrahime BENMESSAHEL with substantial AI assistance
(LLM-generated code, verified through automated tests, an AI audit and CI;
**no independent human review yet**).

```bash
pip install -e ".[dev]"
pytest --cov=src/agentether --cov-report=term-missing
ruff check .
ruff format --check .
mypy .
```

The test suite is offline and deterministic: no network, no real model, and
no test waits for real time (the clock and the backoff sleep are injectable).
The CI matrix runs Python 3.10 to 3.14 on Linux and Windows.

How to add a verifier: write an async function that takes a
`VerifyContext` and returns a `VerifyResult`, and add it to
`src/agentether/verifier.py`.  See
[`docs/verifiers.md`](docs/verifiers.md).

How to reproduce the evidence: see
[`docs/trial-protocol-v2.md`](docs/trial-protocol-v2.md) and
[`docs/evidence.md`](docs/evidence.md).

## Documentation

| Document | What is in it |
| --- | --- |
| [`docs/architecture.md`](docs/architecture.md) | The modules and the life of one step. |
| [`docs/audit-notes.md`](docs/audit-notes.md) | Every invariant, the test that proves it, and the bugs the audit found. |
| [`docs/telemetry-contract.md`](docs/telemetry-contract.md) | What the agent must emit and what is checked. |
| [`docs/verifiers.md`](docs/verifiers.md) | The verifier guide and the security notes. |
| [`docs/state-file-format.md`](docs/state-file-format.md) | The state file (schema version 2). |
| [`docs/spec/`](docs/spec/) | The draft specs for other implementations. |
| [`docs/comparison.md`](docs/comparison.md) | How AgenTether differs from the alternatives. |
| [`docs/faq.md`](docs/faq.md) | "Why not X?" |
| [`docs/trial-protocol.md`](docs/trial-protocol.md) | The pre-registration of the first trial (run 1). |
| [`docs/trial-protocol-v2.md`](docs/trial-protocol-v2.md) | The pre-registration of the trial v2. |
| [`docs/providers.md`](docs/providers.md) | The providers of the free tier and their limits. |
| [`docs/final-report-2026-10-20.md`](docs/final-report-2026-10-20.md) | The report of the audit of 2026-10-20. |
| [`docs/evidence.md`](docs/evidence.md) | The results of the trial. |

## Examples

| Example | What it shows |
| --- | --- |
| [`examples/demo.py`](examples/demo.py) | The 60 second demo, without an API key. |
| [`examples/quickstart.py`](examples/quickstart.py) | The basics, the cache and `rerun()`. |
| [`examples/verified_step.py`](examples/verified_step.py) | An agent that lies, and a verifier that catches it. |
| [`examples/declared_expectations.py`](examples/declared_expectations.py) | A step that declares what it must produce, and an agent that does not. |
| [`examples/human_in_the_loop.py`](examples/human_in_the_loop.py) | A blocked step waiting for a human answer. |
| [`examples/loop_detection.py`](examples/loop_detection.py) | A loop of equivalent answers. |
| [`examples/anthropic_agent.py`](examples/anthropic_agent.py) | The Anthropic adapter (needs the extra and a real key). |

## License

MIT -- see [LICENSE](LICENSE).
