# Evidence

> **A tiny sample from free models on a single day.**  This is not a
> benchmark and it does not show that AgenTether works in general.  The
> protocol was pre-registered and committed before the first result file
> existed: [`docs/trial-protocol-v2.md`](trial-protocol-v2.md).

## Trial v2 (2026-10-20)

> **Status: A PARTIAL confirmatory run.  The pre-registered selection was NOT met: the two models that satisfy the band of the selection rule are the two of Groq, whose daily quota was spent by the probe and the pilots, and the two models that had the quota are the two the band excludes.  The run below uses the two models that had the quota; their data are a SUPPLEMENTARY run and the deviation is stated here and in docs/WORKLOG.md.**

## What was run

- Cells completed: 144
- Time the calls took: 10527.1 s
- Model calls: 450
- Fault rate: 0.2 (the injected condition only)
- Attempt cap per step: 3
- Halted: no

## The models of the run

| Provider | Model | Pilot (naive, natural) | Qualifies | N per cell | MDE of the paired difference |
| --- | --- | --- | --- | --- | --- |
| cerebras | gpt-oss-120b | 19/20 = 0.950 | excluded (0.95 > 0.85) | 12 | 0.404 |
| google | gemini-3.5-flash-lite | 17/20 = 0.850 | excluded (0.85 is the limit of the band; the pilot ended at 0.944) | 12 | 0.404 |
| groq | qwen/qwen3.8-27b | 7/10 = 0.700 | qualifies | 0 | not measured |
| groq | openai/gpt-oss-20b | 17/20 = 0.850 | qualifies | 0 | not measured |

- **gpt-oss-120b**: the model solves the tasks of the pilot too well for the band of the selection rule; it is reported as a supplementary run.  The daily quota of the provider is 1 000 000 tokens; the pilot, the probe and this run stay under half of it.
- **gemini-3.5-flash-lite**: the quota of the free tier of this model is per model: gemini-3.6-flash was refused by the provider during its pilot (HTTP 429) and the rate limit of the free tier is not published.
- **qwen/qwen3.8-27b**: the model satisfies the rule, but the daily quota of Groq (200 000 tokens) was spent by the probe and the pilots: 130 000 tokens were already used, and the rule of the maintainer forbids going over half of the daily quota of the provider.  No cell of this model was run.
- **openai/gpt-oss-20b**: the model satisfies the rule, but the daily quota of Groq was spent by the probe and the pilots (see above).  No cell of this model was run.

## The request and token totals

| Model | Requests | Tokens | Wall clock (s) |
| --- | --- | --- | --- |
| gemini-3.5-flash-lite | 261 | 188346 | 7930.1 |
| gpt-oss-120b | 189 | 206605 | 2597.0 |

## The arms

| Arm | What it does |
| --- | --- |
| naive | One call per step; the claim is trusted. |
| simple-retry | The baseline most people would write: retry on a contract failure, an exception or a timeout. No verification, no loop detection, no drift check. |
| agentether | The full library: the contract, the drift checks, the verifiers, the loop detector, the budget and the breaker. |

## Condition: injected

| Model | Arm | N | Correct completion rate (95% CI) | False completion rate (95% CI) | Believed done | Requests | Wall s | Rejections | Loops |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | agentether | 12 | 0.833 [0.552, 0.953] | 0.167 [0.047, 0.448] | 12 | 47 | 1679.36 | 3 | 0 |
| gemini-3.5-flash-lite | naive | 12 | 0.583 [0.320, 0.807] | 0.167 [0.047, 0.448] | 9 | 42 | 1166.01 | 0 | 0 |
| gemini-3.5-flash-lite | simple-retry | 12 | 0.833 [0.552, 0.953] | 0.167 [0.047, 0.448] | 12 | 46 | 1611.07 | 0 | 0 |
| gpt-oss-120b | agentether | 12 | 0.667 [0.391, 0.862] | 0.083 [0.015, 0.354] | 9 | 34 | 458.93 | 2 | 0 |
| gpt-oss-120b | naive | 12 | 0.417 [0.193, 0.680] | 0.333 [0.138, 0.609] | 9 | 31 | 420.83 | 0 | 0 |
| gpt-oss-120b | simple-retry | 12 | 0.417 [0.193, 0.680] | 0.333 [0.138, 0.609] | 9 | 31 | 449.62 | 0 | 0 |

## Condition: natural

| Model | Arm | N | Correct completion rate (95% CI) | False completion rate (95% CI) | Believed done | Requests | Wall s | Rejections | Loops |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | agentether | 12 | 0.917 [0.646, 0.985] | 0.083 [0.015, 0.354] | 12 | 42 | 1325.62 | 0 | 0 |
| gemini-3.5-flash-lite | naive | 12 | 1.000 [0.757, 1.000] | 0.000 [0.000, 0.243] | 12 | 42 | 963.31 | 0 | 0 |
| gemini-3.5-flash-lite | simple-retry | 12 | 0.917 [0.646, 0.985] | 0.083 [0.015, 0.354] | 12 | 42 | 1184.75 | 0 | 0 |
| gpt-oss-120b | agentether | 12 | 0.750 [0.468, 0.911] | 0.000 [0.000, 0.243] | 9 | 31 | 446.57 | 0 | 0 |
| gpt-oss-120b | naive | 12 | 0.750 [0.468, 0.911] | 0.000 [0.000, 0.243] | 9 | 31 | 371.3 | 0 | 0 |
| gpt-oss-120b | simple-retry | 12 | 0.750 [0.468, 0.911] | 0.000 [0.000, 0.243] | 9 | 31 | 449.75 | 0 | 0 |

## The paired differences

Every arm saw the same tasks and the same fault schedule, so the
comparison is paired.  The difference is the share of the tasks where
one arm was right and the other was not.

| Model | Condition | Comparison | Only A | Only B | Both | Neither | Difference |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | correct completion (agentether vs naive) | 4 | 1 | 6 | 1 | +0.250 |
| gemini-3.5-flash-lite | injected | false completion (agentether vs naive) | 1 | 1 | 1 | 9 | +0.000 |
| gemini-3.5-flash-lite | injected | correct completion (agentether vs simple-retry) | 1 | 1 | 9 | 1 | +0.000 |
| gemini-3.5-flash-lite | injected | false completion (agentether vs simple-retry) | 1 | 1 | 1 | 9 | +0.000 |
| gemini-3.5-flash-lite | natural | correct completion (agentether vs naive) | 0 | 1 | 11 | 0 | -0.083 |
| gemini-3.5-flash-lite | natural | false completion (agentether vs naive) | 1 | 0 | 0 | 11 | +0.083 |
| gemini-3.5-flash-lite | natural | correct completion (agentether vs simple-retry) | 0 | 0 | 11 | 1 | +0.000 |
| gemini-3.5-flash-lite | natural | false completion (agentether vs simple-retry) | 0 | 0 | 1 | 11 | +0.000 |
| gpt-oss-120b | injected | correct completion (agentether vs naive) | 3 | 0 | 5 | 4 | +0.250 |
| gpt-oss-120b | injected | false completion (agentether vs naive) | 0 | 3 | 1 | 8 | -0.250 |
| gpt-oss-120b | injected | correct completion (agentether vs simple-retry) | 3 | 0 | 5 | 4 | +0.250 |
| gpt-oss-120b | injected | false completion (agentether vs simple-retry) | 0 | 3 | 1 | 8 | -0.250 |
| gpt-oss-120b | natural | correct completion (agentether vs naive) | 0 | 0 | 9 | 3 | +0.000 |
| gpt-oss-120b | natural | false completion (agentether vs naive) | 0 | 0 | 0 | 12 | +0.000 |
| gpt-oss-120b | natural | correct completion (agentether vs simple-retry) | 0 | 0 | 9 | 3 | +0.000 |
| gpt-oss-120b | natural | false completion (agentether vs simple-retry) | 0 | 0 | 0 | 12 | +0.000 |

## The hypotheses

H1: the guarded arm completes more tasks correctly.  H2: the guarded arm
catches more false completions (the primary endpoint).  The paired
difference is the share of the tasks where one arm was right and the
other was not.

| Model | Condition | agentether | naive | H1 (paired) | H2 (paired) |
| --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | 0.833 | 0.583 | +0.250 | -0.000 |
| gemini-3.5-flash-lite | natural | 0.917 | 1.000 | -0.083 | -0.083 |
| gpt-oss-120b | injected | 0.667 | 0.417 | +0.250 | +0.250 |
| gpt-oss-120b | natural | 0.750 | 0.750 | +0.000 | -0.000 |

## The verdicts

H1: under the injected faults, the guarded arm completes more tasks
correctly than the baseline.  H2 (the primary endpoint): the guarded
arm catches more false completions.  H3: the guarded arm costs more.

The verdict of a hypothesis is **INCONCLUSIVE** when the difference is
smaller than the minimum detectable effect of the sample: the sample
is then too small to say anything, which is not the same as "no
effect".  The p value is the exact two sided McNemar test of the
discordant pairs.

| Model | H1: correct completion | H2: false completion (primary) | H3: the overhead |
| --- | --- | --- | --- |
| gemini-3.5-flash-lite | +0.000 (1 against 1 discordant pairs, p = 1.000): INCONCLUSIVE (the sample is too small) | -0.000 (1 against 1 discordant pairs, p = 1.000): INCONCLUSIVE (the sample is too small) | 47 against 46 requests, 43905 against 28041 tokens: SUPPORTED |
| gpt-oss-120b | +0.250 (3 against 0 discordant pairs, p = 0.250): INCONCLUSIVE (the sample is too small) | +0.250 (3 against 0 discordant pairs, p = 0.250): INCONCLUSIVE (the sample is too small) | 34 against 31 requests, 42408 against 31324 tokens: SUPPORTED |

## What this shows and what it does not

**It shows** how three policies behave on the same tasks with the
same injected faults, for a few free models, on one day.

**It does not show** that AgenTether makes agents reliable in
general.  The sample is small, the tasks are synthetic, the models
are free tier models with their own limits, and the ground truth
checks are the ones the author of the library wrote.

A null result is reported as a null result: where the paired
difference is smaller than the interval, the table says so.
