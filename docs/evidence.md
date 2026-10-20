# Evidence

> **A tiny sample from free models on a single day.**  This is not a
> benchmark and it does not show that AgenTether works in general.  The
> protocol was pre-registered and committed before the first result file
> existed: [`docs/trial-protocol.md`](trial-protocol.md).

## Run 1 (2026-10-20)

> **Status: NOT a valid comparison of the three arms: two of them were hobbled by defects of the harness, and the numbers below must not be read as a comparison of the policies.**

> The `wall_seconds` of the committed payload of run 1 was 0.  The time the calls really took is the sum of the per cell seconds: it is reported below as the measured time.

## What was run

- Tasks per cell: 10
- Cells completed: 60
- Time the calls took: 4039.1 s
- Model calls: 291
- Fault rate: 0.2 (the injected condition only)
- Attempt cap per step: 3
- Halted: the free tier returned HTTP 429 (free-models-per-day) after the first model; the other two planned models were not run

## The request and token totals

| Model | Requests | Input tokens | Output tokens |
| --- | --- | --- | --- |
| minimax/minimax-m3.1-flash:free | 291 | not recorded | not recorded |

> The runner of run 1 had `tokens = 0` hard-coded (commit 64266c1), so the token columns of this run are empty.  A live probe of the same endpoint on 2026-10-20 confirmed that the server does report the usage (`usage.prompt_tokens` and `usage.completion_tokens`), so the zeros were a defect of the runner and not of the provider.  The runner counts the tokens since then.

## The arms

| Arm | What it does |
| --- | --- |
| naive | One call per step; the claim is trusted. |
| simple-retry | The baseline most people would write: retry on a contract failure, an exception or a timeout. No verification, no loop detection, no drift check. |
| agentether | The full library: the contract, the drift checks, the verifiers, the loop detector, the budget and the breaker. |

## Condition: natural

| Model | Arm | N | Correct completion rate (95% CI) | False completion rate (95% CI) | Believed done | Requests | Wall s | Rejections | Loops |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| minimax/minimax-m3.1-flash:free | naive | 10 | 0.400 [0.168, 0.687] | 0.000 [0.000, 0.278] | 4 | 35 | 415.6 | 0 | 0 |
| minimax/minimax-m3.1-flash:free | simple-retry | 10 | 0.100 [0.018, 0.404] | 0.000 [0.000, 0.278] | 1 | 65 | 839.44 | 0 | 0 |
| minimax/minimax-m3.1-flash:free | agentether | 10 | 0.300 [0.108, 0.603] | 0.000 [0.000, 0.278] | 3 | 48 | 803.91 | 2 | 0 |

## Condition: injected

| Model | Arm | N | Correct completion rate (95% CI) | False completion rate (95% CI) | Believed done | Requests | Wall s | Rejections | Loops |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| minimax/minimax-m3.1-flash:free | naive | 10 | 0.300 [0.108, 0.603] | 0.000 [0.000, 0.278] | 3 | 35 | 437.48 | 0 | 0 |
| minimax/minimax-m3.1-flash:free | simple-retry | 10 | 0.200 [0.057, 0.510] | 0.000 [0.000, 0.278] | 2 | 65 | 873.44 | 0 | 0 |
| minimax/minimax-m3.1-flash:free | agentether | 10 | 0.300 [0.108, 0.603] | 0.000 [0.000, 0.278] | 3 | 43 | 669.24 | 4 | 0 |

## The paired differences

Every arm saw the same tasks and the same fault schedule, so the
comparison is paired.  The difference is the share of the tasks where
one arm was right and the other was not.

| Model | Condition | Comparison | Only A | Only B | Both | Neither | Difference |
| --- | --- | --- | --- | --- | --- | --- | --- |
| minimax/minimax-m3.1-flash:free | natural | correct completion (agentether vs naive) | 1 | 2 | 2 | 5 | -0.100 |
| minimax/minimax-m3.1-flash:free | natural | false completion (agentether vs naive) | 0 | 0 | 0 | 10 | +0.000 |
| minimax/minimax-m3.1-flash:free | natural | correct completion (agentether vs simple-retry) | 3 | 1 | 0 | 6 | +0.200 |
| minimax/minimax-m3.1-flash:free | natural | false completion (agentether vs simple-retry) | 0 | 0 | 0 | 10 | +0.000 |
| minimax/minimax-m3.1-flash:free | injected | correct completion (agentether vs naive) | 2 | 2 | 1 | 5 | +0.000 |
| minimax/minimax-m3.1-flash:free | injected | false completion (agentether vs naive) | 0 | 0 | 0 | 10 | +0.000 |
| minimax/minimax-m3.1-flash:free | injected | correct completion (agentether vs simple-retry) | 3 | 2 | 0 | 5 | +0.100 |
| minimax/minimax-m3.1-flash:free | injected | false completion (agentether vs simple-retry) | 0 | 0 | 0 | 10 | +0.000 |

## The hypotheses

H1: the guarded arm completes more tasks correctly.  H2: the guarded arm
catches more false completions.  The paired difference is the share of
the tasks where one arm was right and the other was not.

| Model | Condition | agentether | naive | H1 (paired) | H2 (paired) |
| --- | --- | --- | --- | --- | --- |
| minimax/minimax-m3.1-flash:free | natural | 0.300 | 0.400 | -0.100 | -0.000 |
| minimax/minimax-m3.1-flash:free | injected | 0.300 | 0.300 | +0.000 | -0.000 |

## The defects of this run

A run whose harness treats the arms differently does not measure the
arms.  The defects below were found in the harness of this run, and
each of them changed the numbers of the tables above.

### 1. The simple-retry arm threw away the work the model had done.

- **Evidence.** The runner wrote the files of an answer only when the claim said "completed".  The sandbox of `simple-retry/natural/task01-harbour` holds only `notes.md`, while the sandbox of `naive/natural/task01-harbour` holds all four files of the same task, with the same model.
- **Effect.** The baseline scored worse than doing nothing (0.100 against 0.400).  This is the anomaly the maintainer flagged.
- **Fix.** Every arm now writes the files of every answer, whatever the claim says.  `tests/test_trial_arms.py` pins it down.

### 2. The prompt never told the model that `progress` is a number from 0 to 100.

- **Evidence.** The contract of AgenTether treats a completed step with a progress below 100 as drift.  The attempt log of `agentether/natural/task03-lantern-memory` reads: "Context drift at step 'notes': step was reported as completed but progress is 1 (expected='progress >= 100 for a completed step', observed=1.0)".  The second and the third step of that task were never even attempted.
- **Effect.** The agentether arm was rejected on steps the other two arms accepted.  Its rate measures the prompt, not the library.
- **Fix.** The prompt states the scale of `progress` and that it must be 100 for a completed step.  The change was applied to every arm.

### 3. The roadmap order stopped the agentether arm at the first failed step.

- **Evidence.** The orchestrator refuses a step whose predecessors are not completed.  The other two arms walk through every step whatever happened.
- **Effect.** The two arms did not even make the same number of calls for the same task.
- **Fix.** The trial builds the orchestrator with `strict_order=False` and closes the breaker again before every step, so each step gets the same number of attempts as in the other arms.

### 4. The injected fault schedule was keyed on a counter that ran across the whole task.

- **Evidence.** `fault_for(task_index, step_index, attempts)` was called with the cumulative number of attempts of the task, so an arm that retried more met different faults for the same step.  The claim that every arm saw the same faults was therefore false.
- **Effect.** The injected condition was not paired.
- **Fix.** The schedule is a function of the task, the step and the attempt number *inside* that step.

### 5. The belief of the arms was computed three different ways.

- **Evidence.** The naive arm took the status of the last answer, the simple-retry arm remembered that *any* step had ever completed, and the agentether arm took the status of the last step.
- **Effect.** The false completion rate was not comparable between the arms.
- **Fix.** Every arm now reports a verdict for every step, and the belief of the task is true when every step was considered done.

### 6. The token accounting was hard-coded to zero and the wall clock of the payload was 0.

- **Evidence.** The runner of run 1 had `tokens = 0` in the body of the loop, and the committed payload has `wall_seconds: 0` next to `requests: 291`.
- **Effect.** The overhead of the arms could not be reported in tokens.
- **Fix.** The runner counts the tokens of the usage the server reports, sums the time of the calls, and seeds the counters of a resumed run with the cells of the earlier sessions.

## What this shows and what it does not

**It shows** how three policies behave on the same tasks with the
same injected faults, for a few free models, on one day.

**It does not show** that AgenTether makes agents reliable in
general.  The sample is small, the tasks are synthetic, the models
are free tier models with their own limits, and the ground truth
checks are the ones the author of the library wrote.

A null result is reported as a null result: where the paired
difference is smaller than the interval, the table says so.
