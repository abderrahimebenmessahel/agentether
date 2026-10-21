# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0a1] - unreleased

Status: **Alpha**.  The version follows PEP 440: `0.3.0a1` is the first
alpha of the 0.3.0 series.

### Changed

- **The project is now AgenTether.**  The distribution is `agentether`, the
  import package is `agentether` and the command is `agentether`.  The
  previous names were `context-guard` / `context_guard` / `contextguard`.
  The name was changed because `contextguard` is taken on PyPI by an unrelated
  project and because "context" does not describe what the library does: it
  supervises the *claims* of an agent step, not its context.
- **The state file markers are now `agentether:*`.**  A memory file written
  with the old `contextguard:*` markers is still read -- including its human
  section -- and is rewritten with the new markers on the next save.  The
  old markers are never written again.
- **The environment variable prefix is now `AGENTETHER_*`**
  (`AGENTETHER_LIVE_TESTS=1` enables the opt-in live tests).
- The state file schema is still version 2; the marker change is a file
  format detail, not a schema change.

### Added

- **The declarative expectations of a step.**  A step can now declare what
  it **must** produce, and the library checks that declaration instead of
  only the claim of the agent:

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

  The expectations are evaluated after **every** attempt, whatever the agent
  claimed, and **a step cannot complete while a declared expectation is
  unmet**.  An unmet expectation is a retryable `VerificationFailedError`,
  and the corrective hint of the next attempt names the missing files.  The
  paths are confined to the work directory: an absolute path, a `..`
  component and a symbolic link that escapes the directory are refused when
  the step is declared.

  An expectation checks the **shape** of a file, not its meaning: a JSON
  that parses may hold the wrong number.  The contract is in
  `docs/spec/expectations-v1.md` and the guide in `docs/verifiers.md`.

  The feature exists because the analysis of the false completions of the
  trial v2 found that a verifier that only checks the files the agent
  **claims** cannot catch a file that exists but is damaged, and cannot see
  a file the agent never produced.

- Python 3.14 in the CI matrix (Linux and Windows).
- A non-blocking `pip-audit` job, a Dependabot configuration and a
  pre-commit configuration (ruff, ruff-format, mypy and the repository's own
  secret scanner).

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
  between `<!-- agentether:human:start -->` and
  `<!-- agentether:human:end -->`.  The library never rewrites it, and a
  blocked step is released as soon as the human edits that section.
- **Event hooks.**  `orch.on(event, callback)` for seven events, plus an
  append-only `events.jsonl` in the memory directory with a monotonic sequence
  number and size based rotation.
- **Half-open circuit breaker.**  `breaker_cooldown_seconds` allows exactly
  one trial attempt after the cooldown; success closes the breaker, failure
  re-opens it.
- **Retry classification.**  `retry_on` and `no_retry_on` make the set of
  retryable exceptions explicit.
- **A `agentether` command line interface**: `status`, `reset-breaker`,
  `doctor`, `verify` and `benchmark`, all with `--json`.
- **A simulated benchmark** (`agentether benchmark --trials N --seed S`).
  It is a simulation: no LLM is called.
- **Optional provider adapters** (`anthropic`, `openai`, `ollama`,
  `openrouter`) in `agentether.adapters`.  The core package never imports
  a provider SDK.  The OpenRouter adapter is standard library only: it reads
  the key from the environment, never logs it, never puts it in an error
  message, retries a rate limit with `Retry-After` and jittered backoff and
  never retries a rejected key.
- **The distribution was published as `context-guard`.**  The shorter name
  `contextguard` is taken on PyPI by an unrelated project.  The import name
  stays `context_guard`; the command is installed as `context-guard`.  (The
  whole project was renamed to AgenTether in 0.3.0a1, below.)
- `GuardPolicy` with `loop`, `stall`, `budget`, `retry` and `breaker`
  sub-policies.  The flat constructor arguments of 0.1 still work and are
  mapped onto the policy.

### Fixed

- **A local provider that needs no key is not refused any more.**  The
  generic OpenAI-compatible worker raised a configuration error when a key
  resolver was passed and the resolver answered with an empty string, which
  is exactly what a local provider (Ollama) does.  The error is now raised
  only for a provider that names an environment variable, and the message
  names the variables of the provider.
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
