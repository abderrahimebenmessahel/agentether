# ContextGuard

[![PyPI](https://img.shields.io/badge/pypi-context--guard-blue)](https://pypi.org/project/context-guard/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)](CHANGELOG.md)
[![Typing](https://img.shields.io/badge/typing-mypy%20--strict-informational)](https://mypy-lang.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-success)](pyproject.toml)

**A tiny supervisor for LLM agent steps.**

ContextGuard wraps **one** function -- your LLM call -- and keeps the control
path (the plan, the state, the limits, the validation) in deterministic code
and in a Markdown file you can read.  It is **not** a multi-agent framework, a
workflow engine or an orchestration platform, and it does not try to be.

Four ideas, and nothing else:

1. **The agent's claims are verified, not trusted.**  A step that says
   `status: "completed"` can be checked against reality: does the file
   exist, is the JSON valid, does the command succeed?
2. **Loops and stalls are detected semantically**, not only by counting
   retries.  Three answers that look different but say the same thing are a
   loop, and the library says so.
3. **The project state is a human-readable, human-editable Markdown file.**
   The plan lives in `PROJECT_MEMORY.md`, not in the context window, and a
   human has their own section in it.
4. **It wraps one function.**  No graph, no roles, no message bus, no
   framework to adopt.

> **Status: Alpha.**  The API may still change.  Nothing here has been
> validated against live model providers -- the adapters are untested
> against live APIs (see [Provider adapters](#provider-adapters)).
>
> **TODO for the maintainer:** decide whether to state the development
> practice ("AI-assisted development; reviewed by humans") in this README,
> and fill in the PyPI name check below.

## The problem

An agent asked to "research X, then write the summary" forgets what it did,
because the plan lives in the context window, and the context window is the
scarcest resource in the run.  When the window fills up, the plan quietly
disappears.  When the model misunderstands the task, it says "completed" and
the supervisor believes it.  When it gets stuck, it produces slightly
different nonsense every time, and a retry counter happily burns the budget.

ContextGuard moves the plan out of the context window and into a file, and it
stops believing the agent.

## Architecture

```text
                    CONTROL PATH  (deterministic code + files on disk)
  ┌──────────────────────────────────────────────────────────────────────┐
  │   @orch.guard_step("research")                                       │
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

## Install

```bash
pip install context-guard              # from a package index
pip install -e ".[dev]"                # from a checkout, with the dev tooling
pip install "context-guard[anthropic]"  # optional provider adapter
```

ContextGuard is **standard library only** and requires Python 3.10 or newer.
The core package never imports a provider SDK.

> **Distribution name.**  The package is published as `context-guard`; the
> import name stays `context_guard` and the command is available as both
> `contextguard` and `context-guard`.  The shorter name `contextguard` is
> **taken** on PyPI by an unrelated project, so it is not used for the
> distribution.

## Quickstart

```python
from context_guard import AutoOrchestrator

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

Runnable examples:

| Example | What it shows |
| --- | --- |
| [`examples/quickstart.py`](examples/quickstart.py) | The basics, the cache and `rerun()`. |
| [`examples/verified_step.py`](examples/verified_step.py) | An agent that lies, and a verifier that catches it. |
| [`examples/human_in_the_loop.py`](examples/human_in_the_loop.py) | A blocked step waiting for a human answer. |
| [`examples/loop_detection.py`](examples/loop_detection.py) | A loop of equivalent answers. |
| [`examples/anthropic_agent.py`](examples/anthropic_agent.py) | The Anthropic adapter (needs the extra and a real API key). |

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

`step`, `status` and `summary` are required.  A wrong `step`, an unknown
`status` or `completed` with a `progress` below 100 is a drift error and is
retried.  A mismatching `next_step` is only a **warning** unless the
orchestrator was built with `strict_next_step=True`.

Full details: [`docs/telemetry-contract.md`](docs/telemetry-contract.md).

## Verification: trust, but check

```python
from context_guard import artifacts_exist, file_contains, json_file_valid


@orch.guard_step(
    "research",
    verify=[
        file_contains("notes.md", "Sources"),
        json_file_valid("notes.json", required_keys=["sources"]),
        artifacts_exist(),
    ],
)
async def research(ctx): ...
```

The verifiers run in order, all of them must pass, each has its own timeout,
and an exception inside a verifier is a *failed verification*, never a crash.
A failed verification is retried with the reason injected into the next
attempt: `"you reported completed but: the file does not exist: notes.md"`.

Built-in verifiers: `file_exists`, `file_contains`, `json_file_valid`,
`artifacts_exist`, `command_succeeds` (argv list, **no shell**, hard
timeout, minimal environment, the whole process tree is killed on a timeout),
`callable_verifier` and `llm_judge` (an interface only -- the core ships no
provider code).

Every path that comes from the model is untrusted: absolute paths, `..`
components and symlinks that escape the work directory are rejected.  The
**executable** of a verifier command is untrusted in the same way: by default
`command_succeeds` refuses an `argv[0]` that resolves inside the work
directory, because the agent could replace it.

Details and the security implications: [`docs/verifiers.md`](docs/verifiers.md).

## Failure handling

| Failure | Retryable? | Action |
| --- | --- | --- |
| `AgentTimeoutError` -- the call exceeded `timeout_seconds` | yes | Retry with a corrective hint ("produce a shorter answer") |
| `TelemetryParseError` -- no usable JSON telemetry | yes | Retry with a corrective hint describing what was wrong |
| `ContextDriftError` (in-step) -- wrong `step`, unknown `status`, `completed` with `progress < 100` | yes | Retry with a corrective hint naming the mismatch |
| `ContextDriftError` (roadmap) -- unknown step, or a step whose predecessors are unfinished | **no** | Raised immediately; this is a caller error |
| `VerificationFailedError` -- a verifier rejected the completion claim | yes | Retry with "you reported completed but: ..." |
| `LoopDetectedError` -- the answers are near-identical | once | Retry once with a strong hint, then the breaker trips |
| `AgentExecutionError` -- your function raised | yes | Retry with the original exception in the hint |
| `blocked` status | **no** | The reason is persisted, a "Needs human input" entry is written, the step waits for a human |
| `failed` status | **no** | The reason is persisted and raised as an `AgentExecutionError` |
| `BudgetExceededError` -- a budget is exhausted | **no** | The reason is persisted; the state stays resumable |
| `CircuitBreakerOpenError` | **no** | The breaker is open; call `await orch.reset_breaker()` |
| `StateCorruptionError` | **no** | The on-disk state is not trustworthy; it is never silently reset |
| `asyncio.CancelledError`, `KeyboardInterrupt` | **no** | Never swallowed, never retried |

When the attempts are exhausted the breaker opens and the error that is raised
is a `CircuitBreakerOpenError`; the original failure is chained as its
`__cause__` and `exc.reason` names the failure kind.

Which exceptions are retried is configurable:

```python
orch = AutoOrchestrator(..., retry_on=(TimeoutError,), no_retry_on=(MyFatalError,))
```

## The circuit breaker and resume

```python
try:
    await research()
except CircuitBreakerOpenError as exc:
    print("breaker open:", exc.reason, exc.last_error)
    await orch.reset_breaker()  # close it and continue
```

The breaker lives in `PROJECT_MEMORY.md`, so it survives a process restart:
an agent that keeps crashing does not get to start over from scratch every
time the supervisor is relaunched.  While the breaker is open, any
`guard_step` call fails fast -- the agent is not called at all.

With `breaker_cooldown_seconds=60` the breaker becomes *half open* after a
minute and allows exactly one trial attempt: success closes it, failure
re-opens it.

`resume=True` (the default) means a step that is already recorded as
completed is not executed again; the cached `StepResult` is returned with
`from_cache=True`.  To run it anyway, use the explicit API:

```python
result = await research.rerun()
```

## Budgets

```python
orch = AutoOrchestrator(
    ...,
    policy=GuardPolicy(
        budget=BudgetPolicy(max_total_seconds=600, max_total_attempts=20, max_total_tokens=100_000)
    ),
)
```

The budgets are **global per project, not per process**: the used attempts,
tokens, cost and elapsed seconds are written to the state file with every
attempt and restored when the orchestrator starts, so a run that was
interrupted and started again continues to spend the same budget.

A worker may report what it spent by returning a `WorkerOutput` instead of a
string:

```python
@orch.guard_step("research")
async def research(ctx) -> WorkerOutput:
    text, usage = await my_model_call(ctx.build_prompt("Research X"))
    return WorkerOutput(text=text, usage=Usage(input_tokens=..., output_tokens=..., cost=...))
```

Workers that return a plain string keep working unchanged; their tokens are
estimated with the configurable `token_counter` (by default a character
heuristic -- an approximation, not a tokenizer).

## Human in the loop

`PROJECT_MEMORY.md` has a section that belongs to you:

```markdown
<!-- contextguard:human:start -->
The customer wants bullet points, no more than five.
<!-- contextguard:human:end -->
```

The library never rewrites it.  It is injected into the agent's context with
the highest priority (truncated with a visible marker, and a warning, only
if it alone does not fit into the budget).  When a step ends `blocked`, a
"Needs human input" entry is written; as soon as you edit your section, the
step may run again and your text is injected as a hint.

## Events

```python
orch.on("attempt_failed", lambda payload: print("failed:", payload["step"]))
orch.on("step_completed", on_completed)  # sync or async callbacks
```

Seven events: `attempt_started`, `attempt_failed`, `step_completed`,
`breaker_opened`, `loop_detected`, `budget_exceeded`, `verification_failed`.
An exception inside a callback is logged and never breaks the run.  Every
event is also appended to `events.jsonl` in the memory directory, with a
monotonic sequence number and an ISO-8601 UTC timestamp.

## The command line

```bash
contextguard status ./memory            # roadmap progress, breaker, last error
contextguard doctor ./memory            # validate the state file, exit non-zero on problems
contextguard verify ./memory            # re-check the recorded artifacts
contextguard reset-breaker ./memory     # close an open breaker
contextguard benchmark --trials 1000 --seed 0
```

Every command supports `--json`.

## Simulated benchmark (not a real-world measurement)

> **This is a simulation.**  No LLM was called.  A seeded random number
> generator produces a *failure schedule* for a synthetic agent (hang, no
> JSON, wrong step name, "completed" without the artifact, near-identical
> output, partial progress) and two runners are compared over the very same
> schedules: a **naive** runner (retry blindly, trust the claim) and a
> **guarded** runner (ContextGuard with verifiers, loop detection and the
> breaker).  A fake clock makes the runs take a minute instead of a day.

Reproduce with `python -m context_guard benchmark --trials 1000 --seed 0`
(the committed result is in [`benchmarks/results/seed-0.json`](benchmarks/results/seed-0.json)).

| Metric | naive | guarded |
| --- | --- | --- |
| tasks | 1000 | 1000 |
| **correct completion rate** (reported *and* really finished) | 0.294 | **0.438** |
| reported completion rate (the claim alone) | 0.597 | 0.438 |
| false completion rate (claimed, not done) | 0.303 | **0.000** |
| mean attempts per step | 1.696 | 1.808 |
| total attempts | 5088 | 5425 |
| repeated attempts (answer ~ previous answer) | 1140 | 1276 |
| simulated cost (tokens) | 4,070,400 | 4,340,000 |
| mean time to halt (s) | 10.176 | 10.850 |

**Read this honestly.**  The *correct completion rate* is the headline: a
task counts only when the runner finished it **and** every artifact is really
there.  The naive runner reports more tasks as finished (0.597 against
0.438), but 30.3% of its "finished" tasks were not really done -- it believed
claims the agent had not earned.  On the metric that counts only real work,
the naive runner reaches 0.294 and the guarded runner 0.438.

The guarded runner also spends slightly more attempts, tokens and time, and it
does *more* repeated work (1276 against 1140): it refuses the false
completion and keeps trying, while the naive runner "finishes" the task --
wrongly -- after fewer attempts.  The loop detector stops the guarded runner
from repeating forever; it does not make the agent smarter.

**What this does and does not show.**

* It shows how the two *policies* behave on the same failure schedule.
* It does **not** show that the library works with a real model, that a real
  agent fails this way, or that the numbers generalise beyond the documented
  parameters.
* The parameters are part of the result: 3 steps per task, 4 attempts per
  step, a 45% chance that an attempt succeeds, and the failure mix
  `malformed 0.25, drift 0.15, lie 0.15, loop 0.15, partial 0.10, hang 0.10`
  with a 15% chance that a step can never be completed.  Change them and the
  numbers change.

## Real trial (tiny sample, one model)

> **This is a tiny sample from a single free model on a single day.**  It is
> not a benchmark and it does not show that the library works in general.
> The numbers below were observed once, with the model
> `minimax/minimax-m3.1-flash:free` through OpenRouter, on ten synthetic
> three-step tasks.  Nothing here generalises to other models, other tasks or
> a real codebase.

The harness gives the model a tiny protocol (it returns file contents in
`FILE: path` blocks, the harness writes them into a sandbox) and runs the
same tasks twice: once **unguarded** (one call per step, the claim is
trusted) and once **guarded** (ContextGuard with the artifact and content
verifiers, the loop detector and a budget).  The raw result is in
[`benchmarks/results/`](benchmarks/results/).

| Metric | unguarded | guarded |
| --- | --- | --- |
| tasks run | 10 | 10 |
| correct completions (the files really exist and are valid) | 8 | 10 |
| false completions (claimed, not done) | 1 | 0 |
| model calls | 30 | 33 |
| input tokens | 13,200 | 14,480 |
| output tokens | 16,301 | 23,493 |
| verifier rejections | 0 | 0 |
| loop detections | 0 | 0 |
| wall seconds | 243 | 320 |

63 HTTP requests in total (the cap was 150, the rate limit 15/minute); the
trial was not halted early.

**Read this honestly.**  The guarded arm finished all ten tasks and the
unguarded arm eight, and the unguarded arm once claimed a task was done
while `README.md` did not mention the script it was supposed to.  But the
verifiers *never fired* in this run (0 rejections): the guarded arm's
advantage came from **retrying** a step whose answer had no parseable
telemetry, not from catching a lie.  With ten easy tasks and a cooperative
model, this says almost nothing about a real project.  The difference between
the simulated benchmark above and this trial is that the simulation
manufactures failures on purpose, while this trial asked a model to do
boring work.

## How this differs from

ContextGuard is not the only tool in this space, and it is not the best
tool for every job.  What the alternatives do **better**:

* **[tenacity](https://github.com/jd/tenacity)** is the reference for retrying
  a call: more stop strategies, better composability, a bigger community.
  ContextGuard adds the plan, the memory, the contract, the verifiers and the
  semantic loop detection.
* **[Temporal](https://temporal.io/), Restate, Airflow, Prefect** are durable
  execution engines.  They are much better at **scale and durability**: they
  persist every step, replay after a crash, run thousands of workers across
  a cluster, and give you operational tooling.  ContextGuard is one process,
  one directory, no server, no database, no daemon -- and its state is a
  Markdown file you can read and edit.
* **[LangGraph](https://github.com/langchain-ai/langgraph), CrewAI, AutoGen,
  Semantic Kernel** are frameworks.  They are much better at **multi-agent
  topologies**, tool registries, streaming into their own UI and integration
  ecosystems.  ContextGuard wraps **one function** and adds no abstraction
  you have to adopt; you can put a `guard_step` inside a LangGraph node.
* **Other agent-reliability libraries** (guardrails-style output checkers,
  LLM judges, evaluation harnesses) check the *content* of an answer.
  ContextGuard checks the *claim* against the filesystem and the roadmap, and
  it is dependency free.

More in [`docs/faq.md`](docs/faq.md).

## Limitations

Honest list of what this library does **not** do:

* **Single process only.**  Writers are serialised with an `asyncio.Lock`
  *within* one process.  There is no cross-process locking.  Two
  orchestrators must not share a memory directory.
* **A sync function cannot be killed on timeout.**  A thread is not
  interruptible: when a synchronous worker exceeds `timeout_seconds`, the
  supervisor stops *waiting*, but the thread keeps running in the background.
* **`max_memory_chars` counts characters, not tokens**, and the default token
  counter is a character heuristic.  Both are approximations.
* **Parsing is best effort.**  The extractor is forgiving about prose and
  strict about JSON.  It cannot repair invalid JSON and it takes the last
  valid object when there are several.
* **The model can still lie.**  ContextGuard validates the *shape* and the
  *consistency* of the telemetry and can check the claim against the
  filesystem.  It cannot tell whether the work is any good.
* **The memory file is protected against marker injection, not against a
  malicious human.**  Every string the model controls is escaped when it is
  written, so it can never forge a marker; the human section is trusted.
* **A verifier that asks a model is not a check.**  `llm_judge` is an
  interface; the judgement inherits the unreliability of the model.
* **`command_succeeds` runs a subprocess** with your privileges.  Only
  verify commands you trust, and keep them **outside** the agent writable
  work directory (the default rejects an executable inside it).
* **The benchmark is simulated.**  It compares policies, not real models.
* **The provider adapters are untested against live APIs** unless you set
  `CONTEXTGUARD_LIVE_TESTS=1` and run the opt-in test.

## Development

Developed by Abderrahime BENMESSAHEL with substantial AI assistance
(LLM-generated code, verified through automated tests and adversarial checks;
limited independent human code review).

```bash
pip install -e ".[dev]"
pytest --cov=src/context_guard --cov-report=term-missing
ruff check .
ruff format --check .
mypy .
```

The test suite is offline and deterministic: no network, no real model, and
no test waits for real time (the clock and the backoff sleep are injectable).
The CI matrix runs Python 3.10 to 3.13 on Linux and Windows.

## Provider adapters

`context_guard.adapters` contains `anthropic_worker`, `openai_worker`,
`ollama_worker` and `openrouter_worker`.  They turn a provider call into a
worker that returns a `WorkerOutput` with usage information, so the token and
cost budgets work with real providers.

```python
from context_guard.adapters import anthropic_worker

worker = anthropic_worker(model="claude-3-5-sonnet-latest")
```

The OpenRouter adapter needs no third party package at all:

```python
from context_guard.adapters import openrouter_worker

worker = openrouter_worker(model="minimax/minimax-m3.1-flash:free")
```

It reads the key from the environment (`minimax`, `MINIMAX`,
`MINIMAX_API_KEY` or `OPENROUTER_API_KEY`, case insensitively), never logs
it, never puts it in an error message, honours `Retry-After` on a rate limit
and never retries a rejected key.

The SDKs are optional extras and are imported lazily; the core package never
imports them.  **These adapters are untested against live APIs** unless
`CONTEXTGUARD_LIVE_TESTS=1` is set and the opt-in live test is run.  API
keys are read from the environment only, and never logged.

## Documentation

* [`docs/architecture.md`](docs/architecture.md) -- the modules and the life
  of one step.
* [`docs/state-file-format.md`](docs/state-file-format.md) -- the state file
  format (schema version 2) and the migration.
* [`docs/telemetry-contract.md`](docs/telemetry-contract.md) -- what the
  agent must emit and what is checked.
* [`docs/verifiers.md`](docs/verifiers.md) -- the verifier guide.
* [`docs/faq.md`](docs/faq.md) -- "Why not X?".

## Roadmap

* [x] Roadmap enforcement, telemetry contract, retries, circuit breaker
* [x] Durable, human editable project memory with atomic writes
* [x] Resume from the project memory and the explicit `rerun()` API
* [x] Independent verification of the completion claim
* [x] Semantic loop and stall detection
* [x] Budgets for seconds, attempts, tokens and cost
* [x] Human in the loop
* [x] Event hooks and an append-only event log
* [x] A `contextguard` command line interface
* [ ] Pluggable storage backends behind the `StateManager` API
* [ ] Token accurate memory budgeting (a real tokenizer)
* [ ] A `contextguard doctor --repair` that rebuilds the file from the backup

## License

MIT -- see [LICENSE](LICENSE).
