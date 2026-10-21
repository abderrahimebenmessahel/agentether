# The natural frequency of the false completions of the trial v3

> The **natural** frequency of the false completions of the kind (ii):
> *a required file was never produced and the claim did not mention it*.
> No fault is injected in the natural condition, so every failure is the
> failure of the model.  The primary endpoint of the trial v3 is the
> false completion rate under the **injected** faults; the two numbers
> are reported **separately**, and the evidence for the value of the
> declarative expectations does not rest on a fault that only they can
> catch.

Every rate is computed on the **common set** of the tasks of the cell:
the tasks that every arm of that model and of that condition completed.

## gemini-3.5-flash-lite -- injected

| Arm | N | False completions | Of which (ii) | Rate of (ii) (95% CI) |
| --- | --- | --- | --- | --- |
| agentether | 6 | 0 | 0 | 0.000 [0.000, 0.390] |
| agentether-claims-only | 6 | 1 | 0 | 0.000 [0.000, 0.390] |
| naive | 6 | 3 | 0 | 0.000 [0.000, 0.390] |
| simple-retry | 6 | 1 | 0 | 0.000 [0.000, 0.390] |

## gpt-oss-120b -- injected

| Arm | N | False completions | Of which (ii) | Rate of (ii) (95% CI) |
| --- | --- | --- | --- | --- |
| agentether | 23 | 0 | 0 | 0.000 [0.000, 0.143] |
| agentether-claims-only | 23 | 4 | 0 | 0.000 [0.000, 0.143] |
| naive | 23 | 13 | 5 | 0.217 [0.097, 0.419] |
| simple-retry | 23 | 13 | 5 | 0.217 [0.097, 0.419] |

## qwen2.5:3b-instruct -- injected

| Arm | N | False completions | Of which (ii) | Rate of (ii) (95% CI) |
| --- | --- | --- | --- | --- |
| agentether | 60 | 5 | 0 | 0.000 [0.000, 0.060] |
| agentether-claims-only | 60 | 8 | 0 | 0.000 [0.000, 0.060] |
| naive | 60 | 34 | 20 | 0.333 [0.227, 0.459] |
| simple-retry | 60 | 49 | 21 | 0.350 [0.242, 0.476] |

## qwen2.5:3b-instruct -- natural

| Arm | N | False completions | Of which (ii) | Rate of (ii) (95% CI) |
| --- | --- | --- | --- | --- |
| agentether | 59 | 12 | 0 | 0.000 [0.000, 0.061] |
| agentether-claims-only | 59 | 12 | 0 | 0.000 [0.000, 0.061] |
| naive | 59 | 37 | 28 | 0.475 [0.353, 0.600] |
| simple-retry | 59 | 41 | 22 | 0.373 [0.261, 0.500] |

## What this shows and what it does not

**It shows** how often a model of the trial failed to produce a file
it claimed to have produced, with nothing injected: the frequency of
the failure that the declarative expectations exist for.

**It does not show** that the library fixes it.  The rate of the
guarded arm in the same table is the answer to that question, and the
verdicts of the trial (with the Wilson intervals and the McNemar
tests) are in `docs/evidence.md`.
