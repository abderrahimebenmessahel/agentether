# FAQ: "Why not X?"

ContextGuard is small on purpose.  This page says what the alternatives do
**better**, so that you can pick the right tool.

## Why not tenacity?

[tenacity](https://github.com/jd/tenacity) is the reference for retrying a
call: exponential backoff, jitter, stop conditions, callbacks.  It is
excellent at what it does.

**What tenacity does better:** it is mature, it has more stop strategies
(`stop_after_delay`, `stop_after_attempt`, `wait_exponential_jitter`, ...),
it composes with any callable, and it has a bigger community.

**What ContextGuard adds:** tenacity retries a *call*.  ContextGuard
supervises a *step of a plan*: it knows the roadmap, it re-reads the project
memory before every attempt, it validates the structured answer, it checks
the completion claim against reality with verifiers, it detects a loop
semantically, and it persists a circuit breaker that survives a restart.

Use tenacity when you want "retry this function until it works".  Use
ContextGuard when you want "run this plan, and do not believe the agent when
it says it is done".

## Why not Temporal, Airflow, Prefect or another durable execution engine?

A durable execution engine (Temporal, Restate, Airflow, Prefect) is built
for **processes that must not lose their work**: they persist the state of
every step, replay it after a crash, scale to thousands of concurrent
workflows, give you a UI, and support days-long workflows with timers and
signals.

**What they do better:** durability at scale, distributed workers, scheduling,
retries over hours and days, operational tooling, and a much bigger
ecosystem.  If you run workflows across a cluster, Temporal wins and
ContextGuard is the wrong tool.

**What ContextGuard does differently:** it is a single process, in-process, in
one directory, with no server, no worker fleet, no database and no daemon.
It is a few hundred lines of standard library that you can read in an
afternoon.  Its state is a Markdown file you can open, read, edit and commit
to git -- which is exactly what a durable engine is *not*.

ContextGuard deliberately has **no cross-process locking**.  Two orchestrators
must not share a memory directory.

## Why not LangGraph, CrewAI, AutoGen, Semantic Kernel or another agent framework?

Those are **frameworks**: they define a graph, a role system, a message
protocol or a conversation loop, and they expect you to adopt their
abstractions for the whole application.

**What they do better:** multi-agent topologies, tool registries, streaming
events into their own UI, model-agnostic plumbing, and a lot of built-in
integrations.

**What ContextGuard does differently:** it wraps **one function**.  There is
no graph, no role, no message bus, no runtime.  You keep your own code, your
own models and your own structure; ContextGuard only adds a supervisor
around the step you already have.  It is also dependency free, so it does not
conflict with the framework you already use -- you can put a
`@orch.guard_step("x")` inside a LangGraph node.

## Why not just write a `while` loop?

Because a `while` loop cannot tell the difference between "the model is
trying again with a new strategy" and "the model is going in circles".  It
retries the same way until the cap is reached, and it has no idea whether
the agent's claim of success is true.

ContextGuard's loop detector compares the *meaning* of the answers, and the
verifiers compare the *claim* with the filesystem.

## Why is the state a Markdown file instead of a database?

Because the state of an agent run is something a human wants to read: which
steps are done, what the summaries are, what is blocked, what the agent was
told.  A JSON blob in a database is not.  A Markdown file can be committed,
diffed, reviewed and edited -- and the human section of it is a first class
part of the contract.

The price is honest: no concurrent access from several processes, and no
querying.  If you need that, use a database (or a durable engine).

## Does ContextGuard make my agent reliable?

No.  It makes the *supervision* of your agent more honest:

* a wrong step name, an unknown status or an unfinished progress value are
  caught;
* a completion claim can be checked against reality with verifiers;
* a loop of equivalent answers is detected before it burns the budget;
* the breaker stops a run that cannot make progress, and it stays open after
  a restart.

It cannot make the model smarter, and a verifier that asks the model is
exactly as unreliable as the model.

## Why is the benchmark simulated?

Because a benchmark that calls a real model is expensive, slow and
non-deterministic, and because publishing numbers that cannot be reproduced
is worse than publishing no numbers.  The simulated benchmark compares two
*policies* on the same seeded failure schedule.  It says nothing about how
well the library works with a real model -- see the README section "Simulated
benchmark (not a real-world measurement)".
