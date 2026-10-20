# Audit notes

> **This is an AI audit, not an independent human review.**  It was written
> by an AI assistant that read the source of AgenTether 0.3.0-alpha line by
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

## Bugs this audit found

| Bug | How it was found | Fix |
| --- | --- | --- |
| A memory file that is not valid UTF-8 raised `UnicodeDecodeError` instead of `StateCorruptionError`. | The state file fuzzer (`test_fuzz_state.py`). | `StateManager._load_sync` now catches `UnicodeDecodeError` and raises an actionable `StateCorruptionError`. |
| The universal newline mode translated a `` inside the human section, so the human text was **not** preserved byte for byte. | The property test `test_the_compaction_keeps_the_limit_and_the_human_section` (a hypothesis case with a carriage return). | The memory file is read with `newline=""`, so the bytes are kept as they are. |
| A memory file that a human edited with an editor that writes CRLF line endings could not be read at all: the marker regex required a plain end of line. | The same property test, after the read fix. | The marker regexes accept a trailing ``.  `test_a_file_with_crlf_line_endings_is_still_readable` covers it. |
| The escaping of the memory file was not injective: a summary that already contained `&lt;!--` came back as `<!--`. | The adversarial test (a) of the previous session. | The ampersand is escaped first. |
| The corruption message mentioned a `.bak` file that might not exist. | Reading the messages of the audit. | The backup is mentioned only when it is really there. |
