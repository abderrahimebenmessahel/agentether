# How AgenTether differs from the alternatives

> Every statement in the "what it is" column was taken from the project's
> **own** documentation or repository, on **2026-10-20**.  The links are the
> pages that were read.  Where I could not verify something, it says
> "unverified".

AgenTether is a small supervisor for **one** function that a project already
has.  It is not a framework, not a runtime and not a platform.  The projects
below are all bigger than AgenTether, and most of them are better at
something important.  The table says what.

| Project | What it is (from its own docs) | What it does **better** than AgenTether |
| --- | --- | --- |
| [tenacity](https://tenacity.readthedocs.io/en/latest/) | "a general-purpose retrying library" to "simplify the task of adding retry behavior to just about anything"; it retries "a flaky function whenever an Exception occurs until a value is returned". It has stop conditions (`stop_after_attempt`, `stop_after_delay`), waiting strategies (fixed, random, exponential, jittered), selective retries, `TryAgain`, callbacks and a `Retrying` context manager. | **Retry vocabulary.** More stop and wait strategies, selective retries by exception *or* return value, and it works with any callable. AgenTether only retries the failures of a *step* and adds the contract, the checks and the state on top. |
| [Temporal](https://docs.temporal.io/) | "the open source Durable Execution platform for crash-proof applications and AI agents". Execution "resume[s] exactly where they left off" and continues after "crashes, network failures, or infrastructure outages", "even when the interruption lasts seconds, days, or even years later". | **Durability and scale.** A server, a database, cross-process and cross-day workflows, and an ecosystem with a UI. AgenTether is a single process with a single directory and no server: it survives a crash of the *process*, not of the *machine*, and it cannot resume a workflow that ran for three days. |
| [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) | "a low-level orchestration framework and runtime for building, managing, and deploying long-running, stateful agents"; a graph of nodes and edges over a shared state, so that you can "combine hand-coded, deterministic logic with LLM-driven decision-making in a single graph". It persists "through failures and can run for extended periods, resuming from where they left off", and it lets you "incorporate human oversight by inspecting and modifying agent state at any point". | **A whole runtime.** Graphs, conditional edges, streaming, checkpoints with savers and threads, and a large ecosystem. AgenTether has no graph, no streaming and no state store: it supervises the step you already wrote. |
| [Dapr Agents](https://github.com/dapr/dapr-agents) | "a developer framework designed to build production-grade resilient AI agent systems that operate at scale", built on Dapr, with built-in observability and stateful workflow execution. It "automatically retries agentic workflows", is Kubernetes-native, supports multi-agent systems and connects to many data sources. | **Scale and operations.** Thousands of agents across a fleet, Kubernetes, multi-agent collaboration, the Dapr platform and its observability. AgenTether runs in one process and writes one Markdown file. |
| [Pyantra](https://github.com/Eskaykaushik/pyantra) | "a Python framework for building AI agent workflows as typed graphs of nodes and edges ... small, composable, and dependency-free, with reliability and observability built in by default". It has typed workflows, state merging with per-field reducers, compile-time validation, parallel fan-out, per-node retry with backoff, timeouts and circuit breakers, durable checkpoints (memory or SQLite), `interrupt()`/`resume()` for human-in-the-loop, and a rich event trace. | **A graph runtime with typed state.** Parallel fan-out with reducers, durable checkpoints, a real interrupt/resume. This is the closest project to AgenTether in size and spirit, and it is more mature: 0 GitHub stars, but a broader feature set. AgenTether's answer is the *file*: the state is a Markdown document a human reads and edits. |
| [AgentRaft](https://github.com/kitavidavis/agentraft) | "Distributed reliability layer for agentic AI. Raft-inspired, step-level consensus for multi-step agent pipelines -- verify every step before it commits, and roll back to the last good checkpoint on failure". A cheap verifier "judges each step's output *before* it's committed", and the "verification asymmetry" is used to guard a large agent with a small one. | **Checkpoint rollback and distributed agreement.** AgenTether rejects a false claim and retries; it does not roll a pipeline back to a previous checkpoint, and it has no notion of consensus. |

## The short version

* **tenacity** is a better retry library.  Use it when "retry this function"
  is the whole problem.
* **Temporal, Dapr Agents** are better at scale and durability.  Use them when
  the workflow must survive a cluster, not a process.
* **LangGraph, Pyantra** are better runtimes: graphs, typed state, streaming,
  checkpoints.  Use them when you want a framework to own the shape of the
  application.
* **AgentRaft** is closer to the idea of "verify before you commit" and goes
  further with consensus and rollback.

AgenTether is for the case where the shape of the application is *yours*
already, the state should be *readable*, the checks should be *deterministic
and free*, and the whole thing should fit in a few hundred lines that you can
read.  It wraps one function.  It does not own your architecture.

## The three ideas that are AgenTether's own

1. **A claim is checked against reality, not against a model.**  The built-in
   verifiers look at the filesystem (`artifacts_exist`, `file_exists`,
   `file_contains`, `json_file_valid`, `json_schema_subset`,
   `markdown_has_headings`, `python_syntax_valid`).  A judge model is
   available, but it is an *interface*, not the default.
2. **A loop is detected by meaning, not by counting.**  The answers are
   normalised (numbers, ids and timestamps masked), hashed into shingles and
   compared with the Jaccard similarity.  Three answers that say the same
   thing with different ids are a loop.
3. **The state is a Markdown file with a human owned section.**  A human can
   read the plan, edit it, and the next attempt sees the edit as a hint.

## What AgenTether does worse

* **No scale, no durability, no server.**  One process, one directory, no
  cross-process locking.
* **No graph, no streaming, no typed state.**  You keep your own structure.
* **A much smaller ecosystem and a much younger project.**  It is
  [Alpha](../CHANGELOG.md): the API may still change, and the audit in
  [`audit-notes.md`](audit-notes.md) was written by an AI, not by an
  independent human reviewer.
* **The evidence is small.**  The trial in
  [`evidence.md`](evidence.md) is a tiny sample from three free models; it
  is not evidence of real world effectiveness.
