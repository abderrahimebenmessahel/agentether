# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-20

Status: **Alpha**. The public API of 0.1 is mostly preserved, but there are
breaking changes. They are listed below.

### Breaking changes

- **The dual-typed circuit breaker error is gone.**  In 0.1 a breaker trip
  raised a dynamically created class that inherited from both
  `CircuitBreakerOpenError` *and* the original error class.  That was clever
  and surprising.  `CircuitBreakerOpenError` is a plain class again; the
  original exception is chained as `__cause__` and the new `reason` attribute
  names the failure kind.

  ```python
  # 0.1
  except (ContextDriftError, CircuitBreakerOpenError):
      ...

  # 0.2
  except CircuitBreakerOpenError as exc:
      cause = exc.__cause__          # the original ContextDriftError
      print(exc.reason)               # "drift"
  ```

- **`force=True` is gone.**  The magic keyword argument on the decorated
  callable is replaced by an explicit `rerun()` method:

  ```python
  # 0.1
  await research(force=True)

  # 0.2
  await research.rerun()
  ```

  `rerun()` is part of the typed `GuardedStep` protocol, so type checkers know
  about it.  The keyword `force` is now free for your own use.

- **The state file schema moved from version 1 to version 2.**  A version 1
  file is migrated automatically the first time it is read: a copy of the old
  file is written to `PROJECT_MEMORY.md.bak` before anything is changed, and
  no data is lost.  The migration is covered by tests.

- **`render_context` is token aware.**  `StateManager` accepts
  `max_memory_tokens` (and a `token_counter`).  When it is set, it takes
  precedence over `max_memory_chars`, which is kept for compatibility.  The
  default token counter is a character heuristic and is documented as an
  approximation.

### Added

- **Independent verification.**  `@orch.guard_step("name", verify=[...])` runs
  verifiers against the agent's completion claim.  Built-in verifiers:
  `file_exists`, `file_contains`, `json_file_valid`, `artifacts_exist`,
  `command_succeeds`, `callable_verifier` and `llm_judge` (an interface only —
  the core ships no provider code).  A failed verification raises the new
  `VerificationFailedError` and is retried with a corrective hint.
- **Semantic loop and stall detection.**  Answers are normalised (numbers, ids
  and timestamps are masked), hashed into shingles and compared with the
  Jaccard similarity.  Three near-identical answers trip the detector; the
  step is retried once with a strong hint and then the breaker trips.  The new
  `LoopDetectedError` is raised.
- **Budgets.**  `BudgetPolicy` limits the total seconds, attempts, tokens and
  cost of a run.  Workers may return a `WorkerOutput` with a `Usage` object;
  plain `str` workers keep working unchanged.  Exceeding a budget raises the
  new `BudgetExceededError` and is never retried.
- **Human in the loop.**  `PROJECT_MEMORY.md` has a human owned section
  between `<!-- contextguard:human:start -->` and
  `<!-- contextguard:human:end -->`.  The library never rewrites it, and a
  blocked step is released as soon as the human edits that section.
- **Event hooks.**  `orch.on(event, callback)` for seven events, plus an
  append-only `events.jsonl` in the memory directory with a monotonic sequence
  number and size based rotation.
- **Half-open circuit breaker.**  `breaker_cooldown_seconds` allows exactly
  one trial attempt after the cooldown; success closes the breaker, failure
  re-opens it.
- **Retry classification.**  `retry_on` and `no_retry_on` make the set of
  retryable exceptions explicit.
- **A `contextguard` command line interface**: `status`, `reset-breaker`,
  `doctor`, `verify` and `benchmark`, all with `--json`.
- **A simulated benchmark** (`contextguard benchmark --trials N --seed S`).
  It is a simulation: no LLM is called.
- **Optional provider adapters** (`anthropic`, `openai`, `ollama`) in
  `context_guard.adapters`.  The core package never imports a provider SDK.
- `GuardPolicy` with `loop`, `stall`, `budget`, `retry` and `breaker`
  sub-policies.  The flat constructor arguments of 0.1 still work and are
  mapped onto the policy.

### Fixed

- **Marker injection into the project memory is closed.**  Every string the
  model controls (the summary, the step name, the artifact paths, the failure
  reasons) is escaped when it is written, so it can never contain a literal
  `<!--` and therefore never a marker of the library.  The parser
  additionally takes the machine block from the *last* state marker and the
  human section from the region the library itself wrote, and a summary that
  contains ` ``` ` can no longer truncate the state block.
- **A verifier command no longer leaves orphans behind.**  On a timeout the
  whole process tree is killed (a new process group on POSIX, `taskkill /T`
  on Windows).  In addition `command_succeeds` rejects by default an
  executable that resolves inside the agent writable work directory
  (`allow_workdir_executables=True` lifts the check).
- **The budgets survive a restart.**  The used attempts, tokens, cost and
  elapsed seconds are persisted in the state file and restored, so the limits
  are global per project and not per process.
- **A step is executed by one caller at a time.**  There is one lock per step
  name: two concurrent calls to the same step are serialised and the second
  one gets the cached result.
- The directory `fsync` after an atomic write is no longer swallowed
  silently: only the platform-unsupported cases (Windows, `EINVAL`,
  `ENOTSUP`) are ignored, everything else is logged as a warning.
- The human section no longer grows by one newline on every write.

## [0.1.0] - 2026-10-19

First release: roadmap enforcement, the telemetry contract, retries with
full-jitter backoff, a persisted circuit breaker, a human readable project
memory with atomic writes, and resume from the project memory.
