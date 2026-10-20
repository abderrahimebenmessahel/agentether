# Architecture

ContextGuard supervises **one** worker function, one roadmap step at a time.
It is not a multi-agent framework, a workflow engine or an orchestration
platform: there is no scheduler, no graph, no queue and no cluster.

```text
                    CONTROL PATH  (deterministic code + files on disk)
  ┌──────────────────────────────────────────────────────────────────────┐
  │                                                                      │
  │   @orch.guard_step("research")                                       │
  │        │                                                             │
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

## The modules

| Module | Responsibility |
| --- | --- |
| `orchestrator.py` | The supervisor: roadmap, attempts, retries, drift checks, verifiers, budgets, breaker, events. |
| `state_manager.py` | The durable project memory: atomic writes, the state block, the human section, the attempt log, compaction. |
| `parser.py` | Extracting the telemetry object from untrusted text. |
| `verifier.py` | The built-in verifiers and the path confinement helper. |
| `loop_detector.py` | Fingerprints, Jaccard similarity, loop and stall detection. |
| `budget.py` | The budget tracker. |
| `policy.py` | The frozen configuration objects. |
| `events.py` | The event bus and the append-only event log. |
| `cli.py` | The `contextguard` command. |
| `benchmark.py` | The simulated benchmark. |
| `adapters/` | Optional provider helpers (lazy imports, never in the core path). |

## The life of one step

1. `guard_step` checks the roadmap, the circuit breaker, the strict order and
   the human input state.  A step that is already completed is returned from
   the memory (`resume=True`) unless `rerun()` is used.
2. For every attempt the memory is **re-read from disk**.  This is the
   external memory guarantee: the agent always sees the current state of the
   project, never a stale copy.
3. The worker is called under a timeout.  A synchronous worker runs in a
   thread; an asynchronous one is awaited.
4. The answer is parsed into a `Telemetry` object and checked against the
   contract: the step name, the status, the progress and (optionally, in
   strict mode) the next step.
5. The answer is fingerprinted and compared with the previous answers of the
   same step, and the telemetry is checked for a stall.
6. The verifiers check the completion claim against reality.
7. On success the step is persisted *before* the result is returned.  On
   failure the attempt is logged, a corrective hint is built and the step is
   retried after a full-jitter backoff.
8. When the attempts are exhausted the circuit breaker opens and is persisted,
   so the next process fails fast instead of looping again.

## Why the state lives on disk

The context window is the scarcest resource in an agent run, and the part
that matters least: a plan that has already been executed.  Keeping the plan
in a file means it survives the context window, it can be read by a human, it
can be edited by a human, and it can be inspected after a crash.
