# Evidence

> **A tiny sample from free models on a single day.**  This is not a
> benchmark and it does not show that AgenTether works in general.  The
> protocol was pre-registered and committed before the first result file
> existed: [`docs/trial-protocol.md`](trial-protocol.md).

## What was run

- Tasks per cell: 10
- Cells completed: 60 of the planned grid
- Wall clock: 0 s
- Fault rate: 0.2 (the injected condition only)
- Attempt cap per step: 3
- Halted: the free tier returned HTTP 429 (free-models-per-day, limit 50, remaining 0) after the first model; the other two models were not run

### The request and token totals

| Model | Requests | Input tokens | Output tokens |
| --- | --- | --- | --- |
| minimax/minimax-m3.1-flash:free | 291 | 0 | 0 |

## The arms

| Arm | What it does |
| --- | --- |
| naive | One call per step; the claim is trusted. |
| simple-retry | The baseline most people would write: retry on a parse failure, an exception or a timeout. No verification, no loop detection, no drift check. |
| agentether | The full library: the contract, the drift checks, the verifiers, the loop detector, the budget and the breaker. |

## Condition: natural

| Model | Arm | N | Correct completion rate (95% CI) | False completion rate | Requests | Wall s | Rejections | Loops |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| minimax/minimax-m3.1-flash:free | naive | 10 | 0.400 [0.168, 0.687] | 0.000 | 35 | 415.6 | 0 | 0 |
| minimax/minimax-m3.1-flash:free | simple-retry | 10 | 0.100 [0.018, 0.404] | 0.000 | 65 | 839.44 | 0 | 0 |
| minimax/minimax-m3.1-flash:free | agentether | 10 | 0.300 [0.108, 0.603] | 0.000 | 48 | 803.91 | 2 | 0 |

## Condition: injected

| Model | Arm | N | Correct completion rate (95% CI) | False completion rate | Requests | Wall s | Rejections | Loops |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| minimax/minimax-m3.1-flash:free | naive | 10 | 0.300 [0.108, 0.603] | 0.000 | 35 | 437.48 | 0 | 0 |
| minimax/minimax-m3.1-flash:free | simple-retry | 10 | 0.200 [0.057, 0.510] | 0.000 | 65 | 873.44 | 0 | 0 |
| minimax/minimax-m3.1-flash:free | agentether | 10 | 0.300 [0.108, 0.603] | 0.000 | 43 | 669.24 | 4 | 0 |

## The paired differences

Every arm saw the same tasks and the same injected faults, so the
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

## Two limitations of this run, stated plainly

1. **Only one model ran.**  The free tier of OpenRouter answered
   `HTTP 429: Rate limit exceeded: free-models-per-day` (limit 50, remaining
   0) after the first model.  The runner is resumable; the exact command is
   below.  The other two models (`google/gemma-4-31b-it:free` and
   `nvidia/nemotron-3-super-120b-a12b:free`) were **not** run, so this
   document says nothing about them.
2. **The false completion rate cannot be evaluated from this run.**  The
   runner recorded the *ground truth* in the `reported_complete` column
   instead of the *belief* of the arm, so the "false completion" column is
   0 everywhere -- it is the same number as the ground truth, not a
   measurement.  The two were separated in the runner afterwards (the
   `artifacts_present` column was added); the results of this run are kept
   as they are, and the change is recorded in the protocol.

   The resume command runs the corrected runner, so a resumed run measures
   the false completion rate properly.

   ```bash
   python benchmarks/trial.py --workdir <the same workdir> --tasks 10        --rate-limit 30 --model-cap 400 --output benchmarks/results/trial-<date>.json
   ```

## What this shows and what it does not

**It shows** how three policies behave on the same tasks with the
same injected faults, for a few free models, on one day.

**It does not show** that AgenTether makes agents reliable in
general.  The sample is small, the tasks are synthetic, the models
are free tier models with their own limits, and the ground truth
checks are the ones the author of the library wrote.

A null result is reported as a null result: where the paired
difference is smaller than the interval, the table says so.
