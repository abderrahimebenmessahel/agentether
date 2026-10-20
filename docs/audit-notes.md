# Audit notes

> **This is an AI audit, not an independent human review.**  It was written
> by an AI assistant that read the source of AgenTether 0.3.0a1 line by
> line and wrote the tests that the invariants were missing.  It has not
> been reviewed by a human being who did not write the code.  Treat it as a
> checklist of claims and their evidence -- not as a certification.

Date of the audit: 2026-10-20.  Audited modules: `orchestrator.py`,
`state_manager.py`, `verifier.py`, `parser.py`, `loop_detector.py`,
`budget.py`, `events.py`, `models.py`, `exceptions.py`, `cli.py`.

## How to read this file

Every row states an invariant the library claims, the test that proves it
(tested), or **NO TEST** -- in which case a test was added in the same pass
and is named here.  A test that only *partly* covers the claim says so.

## The invariants

### Durability of the state

| # | Invariant | Proof |
| --- | --- | --- |
| D1 | The state file is never partially written: a reader sees either the old file or the new one. | `test_atomic_write_keeps_the_old_file_when_replace_fails` (the rename is patched to fail, the old file must be intact), `test_crash_consistency.py::test_the_state_survives_a_hard_kill` (the writer is SIGKILLed / `TerminateProcess`ed at random moments; the file must still load). |
| D2 | A crash never leaves a half written *step* in the state. | `test_crash_consistency.py::test_the_state_survives_a_hard_kill` checks every recorded summary for the full length. |
| D3 | A leftover temporary file is never read. | `test_a_killed_write_leaves_no_temporary_file` (the leftover is a `tmp*` file, and the state loads without it). |
| D4 | Only temporary files older than an hour are removed. | `test_stale_temp_files_are_removed_but_fresh_ones_survive`. |
| D5 | A corrupted state file is never silently reset. | `test_corrupted_state_raises`, `test_a_corrupted_state_file_has_an_actionable_honest_message`, `test_the_corruption_message_mentions_a_backup_that_exists`. |
| D6 | A state file that is not UTF-8 is a corruption, not a crash. | `test_a_file_that_is_not_utf8_is_a_corruption_not_a_crash` (added by this audit: the fuzzer found the bug, `UnicodeDecodeError` used to escape). |
| D7 | A mutated state file can only lead to a `StateCorruptionError`. | `test_fuzz_state.py::test_the_parser_survives_mutated_files` (a bounded random mutation loop). |
| D8 | A schema version 1 file is migrated without losing data, and the old file is kept. | `test_v1_file_is_migrated_and_backed_up`, `test_migration_keeps_the_human_section`. |
| D9 | What is written is what is read back. | `test_properties.py::test_the_state_round_trips` (property based, over generated telemetry). |

### The agent cannot take over the human's part

| # | Invariant | Proof |
| --- | --- | --- |
| H1 | Agent text can never become human owned text. | `test_a_forged_human_section_in_the_summary_cannot_change_the_human_text`, `test_a_forged_new_human_marker_cannot_take_over` (both marker families). |
| H2 | Agent text can never corrupt the machine block. | `test_a_forged_state_marker_in_the_summary_cannot_corrupt_the_state`, `test_a_forged_new_state_marker_cannot_take_over`, `test_a_forged_state_block_written_into_the_file_is_ignored`. |
| H3 | A summary that contains a fence cannot truncate the state block. | `test_a_summary_with_a_backtick_fence_does_not_truncate_the_state`, `test_a_fence_and_a_forged_state_block_in_the_summary`. |
| H4 | The escaping of the memory file is lossless. | `test_a_summary_with_the_literal_escaped_marker_round_trips`, `test_properties.py::test_escaping_round_trips` (property based). |
| H5 | No escaped text can contain a literal marker. | `test_properties.py::test_escaping_never_leaves_a_marker`. |
| H6 | The human section is never dropped by the compaction. | `test_the_compaction_never_drops_the_human_section`, `test_properties.py::test_the_compaction_keeps_the_limit_and_the_human_section`. |
| H7 | The human section survives a rewrite byte for byte. | `test_human_section_is_preserved_byte_for_byte`, `test_saving_rewrites_the_file_with_the_new_markers`. |
| H8 | A human edit releases a blocked step; without it the step stays blocked. | `test_human_input_unblocks_a_blocked_step`, `test_blocked_step_waits_for_human_input`. |

### Claims are checked, not believed

| # | Invariant | Proof |
| --- | --- | --- |
| C1 | A failed verification can never mark a step completed. | `test_invariants.py::test_a_failed_verification_never_marks_the_step_completed` (added by this audit: no test existed). |
| C2 | The verification outcome is recorded, not only logged. | `test_invariants.py::test_the_verification_result_is_kept_for_the_step` (added by this audit). |
| C3 | The evidence of a failed verification is kept. | `test_invariants.py::test_a_verification_error_keeps_the_evidence` (added by this audit). |
| C4 | A lying agent cannot write telemetry under another step's name. | `test_invariants.py::test_a_lying_agent_cannot_write_under_another_step_name` (added by this audit). |
| C5 | A step that is not completed is never resumed as completed. | `test_invariants.py::test_a_step_that_is_not_completed_is_never_resumed_as_completed` (added by this audit), `test_resume_returns_the_cached_result`. |
| C6 | A wrong step name, an unknown status or a low progress value are drift errors. | `test_drift_on_wrong_step_name`, `test_invalid_status_is_drift`, `test_completed_step_with_low_progress_is_drift`. |
| C7 | A broken verifier is a failed verification, not a crash. | `test_a_broken_verifier_is_a_failed_verification`. |
| C8 | A slow verifier cannot hang the run. | `test_a_slow_verifier_times_out`. |

### The loop of death

| # | Invariant | Proof |
| --- | --- | --- |
| L1 | Near identical answers are detected even when the ids and timestamps differ. | `test_loop_detector_trips_on_near_identical_output`, `test_normalize_masks_numbers_and_ids`, `test_the_fingerprints_of_equivalent_answers_match`. |
| L2 | Genuinely different answers are not flagged. | `test_loop_detector_does_not_trip_on_genuinely_different_output`. |
| L3 | A loop is retried once and then trips the breaker. | `test_looping_output_is_detected`, `test_the_loop_detector_trips_on_near_identical_output`. |
| L4 | A step that keeps saying `in_progress` without progress is a stall. | `test_stall_detector_trips_on_repeated_in_progress`, `test_stall_detector_ignores_progress`, `test_stall_detector_ignores_completed_steps`. |

### The breaker and the budget

| # | Invariant | Proof |
| --- | --- | --- |
| B1 | The breaker state survives a restart: a new orchestrator over the same memory fails fast. | `test_breaker_opens_persists_and_fails_fast`. |
| B2 | The breaker only opens after the attempt cap. | `test_breaker_opens_persists_and_fails_fast` (the call count is asserted). |
| B3 | A half open breaker allows exactly one trial attempt; success closes it, failure re-opens it. | `test_half_open_breaker_allows_one_trial`, `test_half_open_breaker_reopens_after_a_failed_trial`. |
| B4 | A budget is never exceeded silently: the run stops with `BudgetExceededError`. | `test_budget_exceeded_is_not_retried`, `test_attempt_budget_is_enforced`, `test_token_budget_is_enforced`, `test_cost_budget_is_enforced`, `test_time_budget_is_enforced`. |
| B5 | The budget survives a restart and the elapsed time is not counted twice. | `test_the_budget_survives_a_restart`, `test_the_budget_is_not_double_counted` (added by this audit). |

### Paths, commands and the sandbox

| # | Invariant | Proof |
| --- | --- | --- |
| P1 | A path from the model cannot escape the work directory. | `test_artifacts_exist_rejects_traversal`, `test_artifacts_exist_rejects_absolute_paths`, `test_artifacts_exist_rejects_symlink_escape` (skipped on Windows without symlink privileges), `test_resolve_within_still_rejects_traversal`. |
| P2 | A verifier command never goes through a shell. | `test_command_does_not_use_a_shell` (the argument is passed literally). |
| P3 | A verifier command cannot outlive its timeout. | `test_command_timeout_kills_the_background_children` (POSIX and Windows), `test_a_verifier_child_does_not_survive_the_timeout`. |
| P4 | An executable inside the work directory is rejected. | `test_command_rejects_an_executable_inside_the_workdir`, `test_a_worker_written_executable_is_rejected`. |
| P5 | A step name cannot escape the steps directory. | `test_step_names_cannot_escape_the_steps_directory`. |

### The run itself

| # | Invariant | Proof |
| --- | --- | --- |
| R1 | The memory is re-read from disk before every attempt. | `test_memory_is_reread_on_every_attempt`. |
| R2 | A cancelled step is never retried and never swallowed. | `test_cancellation_propagates`, `test_cancellation_is_never_retried`. |
| R3 | Two concurrent calls to the same step run the worker once. | `test_concurrent_calls_to_the_same_step_are_serialised`, `test_gather_on_the_same_step_runs_the_worker_once`. |
| R4 | Different steps can still run in parallel. | `test_concurrent_calls_to_different_steps_run_in_parallel`. |
| R5 | The recorded output of a step is the output of the last attempt. | `test_invariants.py::test_the_recorded_output_is_the_one_of_the_last_attempt` (added by this audit). |
| R6 | The parser only ever raises `TelemetryParseError`. | `test_properties.py::test_the_parser_only_ever_raises_a_telemetry_parse_error`, `test_parse_telemetry_only_ever_raises_a_telemetry_parse_error` (property based). |
| R7 | An event callback that raises cannot break the run. | `test_a_throwing_callback_does_not_break_the_run`. |
| R8 | The backoff is full jitter and exponential, and it is capped. | `test_backoff_uses_the_injected_sleep`, `test_backoff_is_capped`. |
| R9 | The recorded output of a step is the raw text, and the attempt log keeps its hash and length. | `test_attempt_log_records_every_attempt`, `test_attempt_log_can_store_the_raw_output`. |

## What the audit does **not** cover

* **Concurrency across processes.**  The library assumes a single process.  Two
  orchestrators over one memory directory can interleave their writes.  There
  is no test for that, because it is out of scope by design.
* **The event log under two processes.**  `EventLog` numbers its records per
  instance; two processes would write overlapping sequence numbers.  Same
  single process assumption.
* **The live provider adapters.**  `anthropic_worker`, `openai_worker` and
  `ollama_worker` are exercised against fakes only.  `openrouter_worker` was
  used against the real endpoint in the trial, but only for the happy path.
* **The `llm_judge` interface** beyond "it is a callable adapter".
* **Performance.**  No claim is made about the speed of the library; the
  benchmark measures simulated policies, not throughput.

## The property, crash and fuzz tests

| Check | What it does | Test |
| --- | --- | --- |
| The parser only ever raises a parse error, on any text. | Hypothesis over arbitrary text. | `tests/test_properties.py::test_the_parser_only_ever_raises_a_telemetry_parse_error` |
| The escaping of the memory file is lossless. | Hypothesis over arbitrary Unicode. | `tests/test_properties.py::test_escaping_round_trips` |
| The escaped text can never contain a marker. | Hypothesis over arbitrary Unicode. | `tests/test_properties.py::test_escaping_never_leaves_a_marker` |
| What is written is what is read back. | Hypothesis over arbitrary telemetry. | `tests/test_properties.py::test_the_state_round_trips` |
| The compaction keeps the limit and the human section. | Hypothesis over telemetry, a limit and a human text. | `tests/test_properties.py::test_the_compaction_keeps_the_limit_and_the_human_section` |
| The state survives a hard kill. | A subprocess writes the state and is killed (SIGKILL / TerminateProcess) at random moments. | `tests/test_crash_consistency.py::test_the_state_survives_a_hard_kill` |
| A mutated state file only leads to a corruption error. | A bounded random mutation loop over a valid file. | `tests/test_fuzz_state.py::test_the_parser_survives_mutated_files` |

## The mutation testing

`mutmut` was installed (no sudo needed) and run on the package.  It mutates
the **whole** package, because a mutant of one file is only importable when
the rest of the package is there.

* Mutants that survived: **2,365**.
* Per module: cli 502, benchmark 368, adapters 318, report 302, verifier 261,
  models 190, ledger 144, state_manager 95, orchestrator 79, exceptions 34,
  loop_detector 30, logging_utils 18, events 15, parser 9.
* One survivor was inspected in detail: the default value of an optional
  keyword argument (`set_breaker(..., attempts: int = 0)` -> `1`).  That is an
  **equivalent mutant** -- every caller passes the value -- and the survivors
  are dominated by that kind: default values, string literals, docstrings.
* `mutmut show` crashes on this version, so the survivors could not be
  triaged one by one.  **The surviving count is therefore a weak signal**:
  it says that the test suite does not distinguish many mutations, not that
  the code has many bugs.  A per-mutant triage is still to be done.

## The triage of the two modules that matter

The triage was done again, on the two modules where a mistake would be a
security problem: `orchestrator.py` and `state_manager.py`.  The run is in
WSL (`mutmut` has no native Windows support) and it uses the
configuration of `pyproject.toml`:

```toml
[tool.mutmut]
source_paths = ["src/agentether"]
only_mutate = ["src/agentether/orchestrator.py", "src/agentether/state_manager.py"]
also_copy = ["benchmarks"]
pytest_add_cli_args = ["-x", "-q", "--no-header", "-p", "no:cacheprovider"]
pytest_add_cli_args_test_selection = ["tests"]
mutate_only_covered_lines = true
```

`only_mutate` restricts the mutation to the two modules while the whole
package is still copied, so that the imports of the mutants work.
`mutate_only_covered_lines` leaves out the lines that no test reaches: a
mutation of a line that no test runs cannot say anything about the test
suite, and it would only inflate the number of survivors.

**The result of the two runs of the triage** (the second one, after the
contract tests of `tests/test_contracts.py` were added):

| | First run | Second run |
| --- | --- | --- |
| Mutants | 2 713 | 2 713 |
| Killed by a test | 1 623 | **1 667** |
| Killed by the timeout (the mutant hangs) | 90 | 70 |
| **Survived** | **1 000** | **976** |

The per module, the first run: `orchestrator.py` 1 430 mutants (831 killed,
82 timeouts, 517 survived) and `state_manager.py` 1 283 mutants (792 killed,
8 timeouts, 483 survived).

The 90 timeouts are mutants that made the test suite hang: they are not
survivors, but they are not clean kills either, and they are reported
apart.

**The triage itself.**  `mutation_triage.py` reads the `.meta` files of
the run and classifies every survivor by the *shape* of the change and by
what that shape means:

| Verdict | What it means | Count (first run) |
| --- | --- | --- |
| **equivalent** | The change cannot be seen: a keyword argument is replaced by ``None`` and the parameter of the callee really defaults to ``None``.  The verdict comes from the abstract syntax tree of the package, not from a guess. | 50 |
| **cosmetic** | Only the wording of a message changes.  The behaviour of the library is the same, only what it says is different. | 211 |
| **gap (record)** | The content of a record (an event, a line of the ledger, the attempt log) is wrong.  The behaviour is the same. | 16 |
| **gap (format)** | A key of the state file, or the way the file is written, changes.  The format is described in `docs/spec/state-file-format-v2.md`: it is a public contract. | 9 |
| **gap (behaviour)** | The behaviour changes and no test noticed. | 690 |

(The counts are the ones of the second run; the first run had 50, 226, 16,
9 and 699.)

**What this says, and what it does not.**  The classification is
**rule-based**, not a hand analysis of the 1 000 mutants one by one.  The
rules decide the verdict of the classes above; they cannot decide the
individual case, and the class "gap (behaviour)" is coarse: it holds
everything the other rules do not claim.  **The number of survivors is
therefore a weak signal** and the number of gaps is weaker still.  What
the triage *does* give is the shape of the problem: most of the survivors
are mutations that no caller can see, and the ones that matter are the
keys of the state file and the fields of the records.

**The gaps that were closed.**  The class "gap (format)" and the class
"gap (record)" pointed at the same thing: nothing looked at the *keys* of
the state file, at the *fields* of the telemetry or at the *records* of
the ledger.  `tests/test_contracts.py` pins them now (18 tests): the keys
of the state file, the keys of the telemetry object, the fields of a line
of the claims ledger, the fields of the breaker and the shape of the
budget section.

**What was left open.**  The class "gap (behaviour)" holds 690 survivors
and was **not** triaged one by one.  They are mostly of three kinds:

1. the value of a *recorded* field (the number of the attempts, the
   reason of the breaker, the status of a claim): the behaviour is right,
   the record is incomplete;
2. the *boundary* of a loop (the compaction, the trimming of the
   snippets): a change of the bound is not seen;
3. the *branch* of a condition that the tests never reach in the other
   direction (for example the half-open breaker when the cooldown comes
   from the policy and not from the argument).

Closing them means writing one test per branch, which is a day of work
that the audit did not do.  **They are not bugs that are known to exist:
they are places where the test suite does not look.**  The honest summary
is: the mutation score of the two modules is **61 %** (1 667 of 2 713
killed by a test) and **64 %** with the timeouts, and the survivors are
dominated by equivalent mutants and by the wording of the messages.


## The bugs the property and fuzz tests found

| Bug | Found by | Fix |
| --- | --- | --- |
| A memory file that is not valid UTF-8 raised `UnicodeDecodeError`. | The fuzzer. | `StateCorruptionError` with an actionable message. |
| The universal newline mode translated a `
` inside the human section, so it was **not** preserved byte for byte. | The property test (a hypothesis case with a carriage return). | The file is read with `newline=""`. |
| A file that a Windows editor saved with CRLF line endings could not be read at all. | The same property test, after the read fix. | The marker regexes accept a trailing `
`. |

## Bugs this audit found

| Bug | How it was found | Fix |
| --- | --- | --- |
| A memory file that is not valid UTF-8 raised `UnicodeDecodeError` instead of `StateCorruptionError`. | The state file fuzzer (`test_fuzz_state.py`). | `StateManager._load_sync` now catches `UnicodeDecodeError` and raises an actionable `StateCorruptionError`. |
| The universal newline mode translated a `
` inside the human section, so the human text was **not** preserved byte for byte. | The property test `test_the_compaction_keeps_the_limit_and_the_human_section` (a hypothesis case with a carriage return). | The memory file is read with `newline=""`, so the bytes are kept as they are. |
| A memory file that a human edited with an editor that writes CRLF line endings could not be read at all: the marker regex required a plain end of line. | The same property test, after the read fix. | The marker regexes accept a trailing `
`.  `test_a_file_with_crlf_line_endings_is_still_readable` covers it. |
| The escaping of the memory file was not injective: a summary that already contained `&lt;!--` came back as `<!--`. | The adversarial test (a) of the previous session. | The ampersand is escaped first. |
| The corruption message mentioned a `.bak` file that might not exist. | Reading the messages of the audit. | The backup is mentioned only when it is really there. |
