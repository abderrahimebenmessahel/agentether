# Simulated benchmark (not a real-world measurement)

> **This is a simulation.** No LLM was called. A seeded random number
> generator produces a failure schedule for a synthetic agent and both
> runners are compared over the very same schedules. The numbers
> describe the *policies*, not the real-world behaviour of any model.

## Parameters

| Parameter | Value |
| --- | --- |
| `max_attempts` | `4` |
| `p_unrecoverable_step` | `0.15` |
| `probabilities` | `{'malformed': 0.25, 'drift': 0.15, 'lie': 0.15, 'loop': 0.15, 'partial': 0.1, 'hang': 0.1}` |
| `seconds_per_attempt` | `2.0` |
| `seed` | `0` |
| `steps` | `3` |
| `tokens_per_attempt` | `800` |
| `trials` | `1000` |

## Results

| Metric | naive | guarded |
| --- | --- | --- |
| tasks | 1000 | 1000 |
| **correct completion rate** (done *and* really finished) | 0.294 | 0.438 |
| reported completion rate (claims only) | 0.597 | 0.438 |
| false completion rate (claimed, not done) | 0.303 | 0.000 |
| mean attempts per step | 1.696 | 1.808 |
| total attempts | 5088 | 5425 |
| repeated attempts (answer ~ previous answer) | 1140 | 1276 |
| simulated cost (tokens) | 4070400 | 4340000 |
| mean time to halt (s) | 10.176 | 10.850 |

## What this does and does not show

- It shows how the two *policies* behave on the same failure
  schedule: the naive runner trusts the agent, the guarded runner
  checks the claim.
- It does **not** show that the library works with a real model,
  that a real agent fails this way, or that these numbers
  generalise beyond the documented parameters.
- The guarded runner can use *more* attempts than the naive one:
  it refuses to accept a claim that a verifier rejected, and that
  is a deliberate trade-off, not a win.
- The headline metric is the *correct* completion rate: a task
  counts only when the runner finished it **and** every artifact
  is really there.  The naive runner's higher reported completion
  rate is made of tasks that were never really done.
