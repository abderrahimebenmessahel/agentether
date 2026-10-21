# Evidence

> **A tiny sample from free models on a single day.**  This is not a
> benchmark and it does not show that AgenTether works in general.  The
> protocol of every run was pre-registered and committed before the
> first result file of that run existed.

> The protocol of this run: [`docs/trial-protocol-v3.md`](trial-protocol-v3.md).

> The protocol of this run: [`docs/trial-protocol-v2.md`](trial-protocol-v2.md).

## The sign convention

Every paired difference of this document is **arm A minus arm B**, and
A is the first arm of the comparison (the guarded arm is always the
first).  What the sign means depends on the metric:

* for the **correct completion rate**, a **positive** difference is an
  improvement: the first arm completed more tasks correctly;
* for the **false completion rate**, a **NEGATIVE** difference is an
  improvement: the first arm had fewer false completions.

The same rule applies to the hypotheses, to the verdicts and to the
tables of the report.

## Trial v3 (2026-10-20 and 2026-10-21)

> **Status: A PARTIAL confirmatory run, continued on the 21st of October.  The protocol of the trial v3 is docs/trial-protocol-v3.md and its addendum is docs/trial-protocol-v3-addendum.md; both were committed before the first result file.  The selection rule of the protocol v2 (a band on the naive success rate) was NOT satisfiable by the models that had quota, and the rule of the v3 is the capability probe and the quota, with no band; the deviation was decided BEFORE the new data.  The task set was extended from twenty to sixty tasks by a seeded procedural generator, and the first twenty tasks and the data collected on them are untouched.  Every rate is computed on the COMMON SET of the tasks that every arm of a cell completed.  The verdicts that depend on the size of the sample are INCONCLUSIVE, and the data show the direction only.**

### What was run

- Cells completed: 621
- Time the calls took: 66937.2 s
- Model calls: 2746
- Fault rate: 0.2 (the injected condition only)
- Attempt cap per step: 3
- Halted: the token cap of the day of the Cerebras model (500198 of the 500000 tokens that the rule of the maintainer allows), and the daily quota of the Google model: the provider refused the calls with HTTP 429 twice (quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 500, model: gemini-3.5-flash-lite), once three minutes after the UTC day had turned over and once at 07:30 UTC, the day of the provider turning at midnight Pacific time and the window of the 500 requests being longer than a UTC day

### The models of the run

| Provider | Model | Pilot (naive, natural) | Qualifies | N per cell | MDE of the paired difference |
| --- | --- | --- | --- | --- | --- |
| cerebras | gpt-oss-120b | 19/20 = 0.950 | passes the capability probe; no band (the rule of the v3) | 23 | 0.292 |
| google | gemini-3.5-flash-lite | 17/20 = 0.850 | passes the capability probe; no band (the rule of the v3) | 11 | 0.422 |
| ollama | qwen2.5:3b-instruct | not run | passes the capability probe (1.000 on the telemetry, the name of the step, the progress, the file blocks and the artifacts); no band and no quota: the compute is local and free | 60 | 0.181 |

- **gpt-oss-120b**: the free tier of the provider: 1000 requests and 1000000 tokens per day; the rule of the maintainer is half of it, and the run of the 21st of October stopped at the token cap (500198 tokens) after 415 requests
- **gemini-3.5-flash-lite**: the daily limit of the free tier is 500 requests PER MODEL, and the answer of the provider says so when the quota is spent; the day of the provider turns at midnight Pacific time (07:00 UTC), not at midnight UTC, and the window of the 500 requests is longer than a UTC day, so the run of the 21st of October was refused twice and the model stays at 11 tasks per cell
- **qwen2.5:3b-instruct**: a local model on the GeForce RTX 3050 of the machine: a download of 1.9 GB, no quota, no key, and the comparison is paired on the task and the fault schedule and not on the answer of the model, because it is not deterministic at temperature 0 (the GPU is not)

### The request and token totals

| Model | Requests | Tokens | Wall clock (s) |
| --- | --- | --- | --- |
| gemini-3.5-flash-lite | 186 | 145475 | 1769.8 |
| gpt-oss-120b | 412 | 496363 | 6345.9 |
| qwen2.5:3b-instruct | 2148 | 1713435 | 58821.4 |
| **total** | **2746** | **2355273** | **66937.1** |

### The arms

| Arm | What it does |
| --- | --- |
| agentether | The full library with the declarative expectations of the step: the contract, the drift checks, the verifiers, the loop detector, the budget and the breaker. |
| agentether-claims-only | The full library, but the step declares no expectation: only the files the agent claims are checked. It isolates the contribution of the declarative expectations. |
| naive | One call per step; the claim is trusted. |
| simple-retry | The baseline most people would write: retry on a contract failure, an exception or a timeout. No verification, no loop detection, no drift check. |

### Condition: injected

Every rate below is computed on the **common set** of the tasks of the
cell: the tasks that **every** arm of that model and of that condition
completed.  The column "Dropped" is the number of tasks the arm had
beyond that set.

| Model | Arm | N | Dropped | Correct completion rate (95% CI) | False completion rate (95% CI) | Believed done | Requests | Wall s | Rejections | Loops |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | agentether | 11 | 0 | 0.909 [0.623, 0.984] | 0.000 [0.000, 0.259] | 10 | 46 | 454.76 | 7 | 0 |
| gemini-3.5-flash-lite | agentether-claims-only | 11 | 0 | 0.727 [0.434, 0.903] | 0.273 [0.097, 0.566] | 11 | 43 | 365.18 | 2 | 0 |
| gemini-3.5-flash-lite | naive | 11 | 1 | 0.364 [0.152, 0.646] | 0.455 [0.213, 0.720] | 9 | 38 | 475.57 | 0 | 0 |
| gemini-3.5-flash-lite | simple-retry | 11 | 2 | 0.636 [0.354, 0.848] | 0.273 [0.097, 0.566] | 10 | 44 | 373.65 | 0 | 0 |
| gpt-oss-120b | agentether | 23 | 0 | 0.696 [0.491, 0.844] | 0.000 [0.000, 0.143] | 15 | 120 | 1776.36 | 39 | 0 |
| gpt-oss-120b | agentether-claims-only | 23 | 0 | 0.609 [0.408, 0.778] | 0.174 [0.070, 0.371] | 17 | 123 | 1887.15 | 39 | 0 |
| gpt-oss-120b | naive | 23 | 1 | 0.435 [0.256, 0.632] | 0.565 [0.368, 0.744] | 22 | 80 | 1180.71 | 0 | 0 |
| gpt-oss-120b | simple-retry | 23 | 1 | 0.435 [0.256, 0.632] | 0.565 [0.368, 0.744] | 23 | 81 | 1163.1 | 0 | 0 |
| qwen2.5:3b-instruct | agentether | 60 | 0 | 0.750 [0.628, 0.842] | 0.083 [0.036, 0.181] | 41 | 326 | 8318.42 | 86 | 0 |
| qwen2.5:3b-instruct | agentether-claims-only | 60 | 0 | 0.600 [0.474, 0.714] | 0.133 [0.069, 0.242] | 35 | 325 | 7032.17 | 97 | 0 |
| qwen2.5:3b-instruct | naive | 60 | 0 | 0.117 [0.058, 0.222] | 0.567 [0.441, 0.684] | 37 | 210 | 5578.76 | 0 | 0 |
| qwen2.5:3b-instruct | simple-retry | 60 | 0 | 0.133 [0.069, 0.242] | 0.817 [0.701, 0.894] | 55 | 251 | 7208.35 | 0 | 0 |

### Condition: natural

Every rate below is computed on the **common set** of the tasks of the
cell: the tasks that **every** arm of that model and of that condition
completed.  The column "Dropped" is the number of tasks the arm had
beyond that set.

| Model | Arm | N | Dropped | Correct completion rate (95% CI) | False completion rate (95% CI) | Believed done | Requests | Wall s | Rejections | Loops |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen2.5:3b-instruct | agentether | 60 | 0 | 0.667 [0.541, 0.773] | 0.200 [0.118, 0.318] | 47 | 285 | 6764.19 | 73 | 0 |
| qwen2.5:3b-instruct | agentether-claims-only | 60 | 0 | 0.550 [0.425, 0.669] | 0.217 [0.131, 0.336] | 44 | 280 | 6636.58 | 69 | 0 |
| qwen2.5:3b-instruct | naive | 60 | 0 | 0.083 [0.036, 0.181] | 0.617 [0.490, 0.729] | 40 | 210 | 7659.87 | 0 | 0 |
| qwen2.5:3b-instruct | simple-retry | 60 | 0 | 0.117 [0.058, 0.222] | 0.683 [0.558, 0.787] | 48 | 261 | 9623.07 | 0 | 0 |

### The paired differences

Every arm saw the same tasks and the same fault schedule, so the
comparison is paired.  The difference is the share of the tasks where
one arm was right and the other was not, with the sign convention of
the section above (A minus B).  The comparison is made on the common
set of the tasks of the cell, the same set the rates above use.

| Model | Condition | Comparison | N | Only A | Only B | Both | Neither | Difference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | correct completion (agentether vs agentether-claims-only) | 11 | 2 | 0 | 8 | 1 | +0.182 |
| gemini-3.5-flash-lite | injected | false completion (agentether vs agentether-claims-only) | 11 | 0 | 3 | 0 | 8 | -0.273 |
| gemini-3.5-flash-lite | injected | correct completion (agentether vs naive) | 11 | 6 | 0 | 4 | 1 | +0.545 |
| gemini-3.5-flash-lite | injected | false completion (agentether vs naive) | 11 | 0 | 5 | 0 | 6 | -0.455 |
| gemini-3.5-flash-lite | injected | correct completion (agentether vs simple-retry) | 11 | 3 | 0 | 7 | 1 | +0.273 |
| gemini-3.5-flash-lite | injected | false completion (agentether vs simple-retry) | 11 | 0 | 3 | 0 | 8 | -0.273 |
| gpt-oss-120b | injected | correct completion (agentether vs agentether-claims-only) | 23 | 6 | 4 | 10 | 3 | +0.087 |
| gpt-oss-120b | injected | false completion (agentether vs agentether-claims-only) | 23 | 0 | 4 | 0 | 19 | -0.174 |
| gpt-oss-120b | injected | correct completion (agentether vs naive) | 23 | 9 | 3 | 7 | 4 | +0.261 |
| gpt-oss-120b | injected | false completion (agentether vs naive) | 23 | 0 | 13 | 0 | 10 | -0.565 |
| gpt-oss-120b | injected | correct completion (agentether vs simple-retry) | 23 | 9 | 3 | 7 | 4 | +0.261 |
| gpt-oss-120b | injected | false completion (agentether vs simple-retry) | 23 | 0 | 13 | 0 | 10 | -0.565 |
| qwen2.5:3b-instruct | injected | correct completion (agentether vs agentether-claims-only) | 60 | 16 | 7 | 29 | 8 | +0.150 |
| qwen2.5:3b-instruct | injected | false completion (agentether vs agentether-claims-only) | 60 | 3 | 6 | 2 | 49 | -0.050 |
| qwen2.5:3b-instruct | injected | correct completion (agentether vs naive) | 60 | 40 | 2 | 5 | 13 | +0.633 |
| qwen2.5:3b-instruct | injected | false completion (agentether vs naive) | 60 | 2 | 31 | 3 | 24 | -0.483 |
| qwen2.5:3b-instruct | injected | correct completion (agentether vs simple-retry) | 60 | 38 | 1 | 7 | 14 | +0.617 |
| qwen2.5:3b-instruct | injected | false completion (agentether vs simple-retry) | 60 | 1 | 45 | 4 | 10 | -0.733 |
| qwen2.5:3b-instruct | natural | correct completion (agentether vs agentether-claims-only) | 60 | 16 | 9 | 24 | 11 | +0.117 |
| qwen2.5:3b-instruct | natural | false completion (agentether vs agentether-claims-only) | 60 | 8 | 9 | 4 | 39 | -0.017 |
| qwen2.5:3b-instruct | natural | correct completion (agentether vs naive) | 60 | 38 | 3 | 2 | 17 | +0.583 |
| qwen2.5:3b-instruct | natural | false completion (agentether vs naive) | 60 | 5 | 30 | 7 | 18 | -0.417 |
| qwen2.5:3b-instruct | natural | correct completion (agentether vs simple-retry) | 60 | 35 | 2 | 5 | 18 | +0.550 |
| qwen2.5:3b-instruct | natural | false completion (agentether vs simple-retry) | 60 | 4 | 33 | 8 | 15 | -0.483 |

### The hypotheses

H1: the guarded arm completes more tasks correctly.  H2: the guarded arm
catches more false completions (the primary endpoint).  The paired
differences follow the sign convention of the section above: the
guarded arm minus the naive arm, a **positive** H1 is an improvement
and a **negative** H2 is an improvement.

| Model | Condition | agentether | naive | H1 (paired) | H2 (paired) |
| --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | 0.909 | 0.364 | +0.545 | -0.455 |
| gpt-oss-120b | injected | 0.696 | 0.435 | +0.261 | -0.565 |
| qwen2.5:3b-instruct | injected | 0.750 | 0.117 | +0.633 | -0.483 |
| qwen2.5:3b-instruct | natural | 0.667 | 0.083 | +0.583 | -0.417 |

### The verdicts

H1: under the injected faults, the guarded arm completes more tasks
correctly than the baseline.  H2 (the primary endpoint): the guarded
arm catches more false completions.  H3: the guarded arm costs more.

The verdict of a hypothesis is **INCONCLUSIVE** when the difference is
smaller than the minimum detectable effect of the sample: the sample
is then too small to say anything, which is not the same as "no
effect".  The p value is the exact two sided McNemar test of the
discordant pairs.

The MDE of a cell is `1.4 / sqrt(N)` with the **achieved** N: the
number of the tasks that every arm of the cell completed.

| Model | N | MDE | H1: correct completion | H2: false completion (primary) | H3: the overhead |
| --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | 11 | 0.422 | +0.273 (in 3 tasks only the guarded arm completed, in 0 tasks only the comparator; p = 0.250): INCONCLUSIVE (the sample is too small) | -0.273 (in 0 tasks only the guarded arm falsely completed, in 3 tasks only the comparator; p = 0.250): INCONCLUSIVE (the sample is too small) | 46 against 44 requests, 45438 against 25418 tokens: SUPPORTED |
| gpt-oss-120b | 23 | 0.292 | +0.261 (in 9 tasks only the guarded arm completed, in 3 tasks only the comparator; p = 0.146): INCONCLUSIVE (the sample is too small) | -0.565 (in 0 tasks only the guarded arm falsely completed, in 13 tasks only the comparator; p = 0.000): SUPPORTED | 120 against 81 requests, 160091 against 83277 tokens: SUPPORTED |
| qwen2.5:3b-instruct | 60 | 0.181 | +0.617 (in 38 tasks only the guarded arm completed, in 1 task only the comparator; p = 0.000): SUPPORTED | -0.733 (in 1 task only the guarded arm falsely completed, in 45 tasks only the comparator; p = 0.000): SUPPORTED | 326 against 251 requests, 293990 against 164874 tokens: SUPPORTED |

### The verdicts against the naive arm

The hypotheses of the protocol are stated against the simple-retry
baseline, and the table above is the verdict against it.  The **naive**
arm (one call per step, the claim is trusted) is the second
comparator, and it is reported here because the baseline is not always
a fair one: a baseline that retries writes the files of **every**
answer, and the last one wins, so with a model that is not
deterministic a retry can overwrite a good file with a worse one.

| Model | N | MDE | H1: correct completion | H2: false completion (primary) |
| --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | 11 | 0.422 | +0.545 (in 6 tasks only the guarded arm completed, in 0 tasks only the naive arm; p = 0.031): SUPPORTED | -0.455 (in 0 tasks only the guarded arm falsely completed, in 5 tasks only the naive arm; p = 0.062): NOT SUPPORTED |
| gpt-oss-120b | 23 | 0.292 | +0.261 (in 9 tasks only the guarded arm completed, in 3 tasks only the naive arm; p = 0.146): INCONCLUSIVE (the sample is too small) | -0.565 (in 0 tasks only the guarded arm falsely completed, in 13 tasks only the naive arm; p = 0.000): SUPPORTED |
| qwen2.5:3b-instruct | 60 | 0.181 | +0.633 (in 40 tasks only the guarded arm completed, in 2 tasks only the naive arm; p = 0.000): SUPPORTED | -0.483 (in 2 tasks only the guarded arm falsely completed, in 31 tasks only the naive arm; p = 0.000): SUPPORTED |

### The contribution of the declarative expectations (H4)

H4: the arm that **declares** what the step must produce has fewer
false completions than the arm that only checks the files the agent
claims.  The difference is the false completion rate of the guarded
arm minus the one of the claims-only arm: a **negative** value is an
improvement.

| Model | Condition | H4 (paired) | The verdict |
| --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | -0.273 (in 0 tasks only the guarded arm falsely completed, in 3 only the claims-only arm; p = 0.250) | INCONCLUSIVE (the sample is too small) |
| gpt-oss-120b | injected | -0.174 (in 0 tasks only the guarded arm falsely completed, in 4 only the claims-only arm; p = 0.125) | INCONCLUSIVE (the sample is too small) |
| qwen2.5:3b-instruct | injected | -0.050 (in 3 tasks only the guarded arm falsely completed, in 6 only the claims-only arm; p = 0.508) | INCONCLUSIVE (the sample is too small) |
| qwen2.5:3b-instruct | natural | -0.017 (in 8 tasks only the guarded arm falsely completed, in 9 only the claims-only arm; p = 1.000) | INCONCLUSIVE (the sample is too small) |

### The cost of honesty

The guard of AgenTether prevents false claims; it does not by
itself make a task succeed.  A task the model cannot finish is a
failure either way, but the naive arm reports it as a success and
the guarded arm reports it as a failure: the difference is honest,
and it has a price.

The **honest "not completed"** are the tasks the arm did not claim
to have finished while the ground truth says they were not finished.
The column **converted** counts the ones that were a false
completion of the simple-retry baseline: a false "done" turned into
a visible failure.

| Model | Condition | Arm | N | Correct | False completion | Honest "not completed" | Converted | Rate of the honest failures (95% CI) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | agentether | 11 | 10 | 0 | 1 | 1 | 0.091 [0.016, 0.377] |
| gemini-3.5-flash-lite | injected | agentether-claims-only | 11 | 8 | 3 | 0 | 0 | 0.000 [0.000, 0.259] |
| gemini-3.5-flash-lite | injected | naive | 11 | 4 | 5 | 2 | 1 | 0.182 [0.051, 0.477] |
| gemini-3.5-flash-lite | injected | simple-retry | 11 | 7 | 3 | 1 | 0 | 0.091 [0.016, 0.377] |
| gpt-oss-120b | injected | agentether | 23 | 16 | 0 | 7 | 4 | 0.304 [0.156, 0.509] |
| gpt-oss-120b | injected | agentether-claims-only | 23 | 14 | 4 | 5 | 3 | 0.217 [0.097, 0.419] |
| gpt-oss-120b | injected | naive | 23 | 10 | 13 | 0 | 0 | 0.000 [0.000, 0.143] |
| gpt-oss-120b | injected | simple-retry | 23 | 10 | 13 | 0 | 0 | 0.000 [0.000, 0.143] |
| qwen2.5:3b-instruct | injected | agentether | 60 | 45 | 5 | 10 | 9 | 0.167 [0.093, 0.280] |
| qwen2.5:3b-instruct | injected | agentether-claims-only | 60 | 36 | 8 | 16 | 14 | 0.267 [0.171, 0.390] |
| qwen2.5:3b-instruct | injected | naive | 60 | 7 | 34 | 19 | 13 | 0.317 [0.213, 0.442] |
| qwen2.5:3b-instruct | injected | simple-retry | 60 | 8 | 49 | 3 | 0 | 0.050 [0.017, 0.137] |
| qwen2.5:3b-instruct | natural | agentether | 60 | 40 | 12 | 8 | 7 | 0.133 [0.069, 0.242] |
| qwen2.5:3b-instruct | natural | agentether-claims-only | 60 | 33 | 13 | 14 | 12 | 0.233 [0.144, 0.354] |
| qwen2.5:3b-instruct | natural | naive | 60 | 5 | 37 | 18 | 11 | 0.300 [0.199, 0.425] |
| qwen2.5:3b-instruct | natural | simple-retry | 60 | 7 | 41 | 12 | 0 | 0.200 [0.118, 0.318] |

## Trial v2 (2026-10-20)

> **Status: A PARTIAL confirmatory run.  The pre-registered selection was NOT met: the two models that satisfy the band of the selection rule are the two of Groq, whose daily quota was spent by the probe and the pilots, and the two models that had the quota are the two the band excludes.  The run below uses the two models that had the quota; their data are a SUPPLEMENTARY run and the deviation is stated here and in docs/WORKLOG.md.**

### What was run

- Cells completed: 144
- Time the calls took: 10527.1 s
- Model calls: 450
- Fault rate: 0.2 (the injected condition only)
- Attempt cap per step: 3
- Halted: no

### The models of the run

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

### The request and token totals

| Model | Requests | Tokens | Wall clock (s) |
| --- | --- | --- | --- |
| gemini-3.5-flash-lite | 261 | 188346 | 7930.1 |
| gpt-oss-120b | 189 | 206605 | 2597.0 |
| **total** | **450** | **394951** | **10527.1** |

### The arms

| Arm | What it does |
| --- | --- |
| agentether | The full library with the declarative expectations of the step: the contract, the drift checks, the verifiers, the loop detector, the budget and the breaker. |
| naive | One call per step; the claim is trusted. |
| simple-retry | The baseline most people would write: retry on a contract failure, an exception or a timeout. No verification, no loop detection, no drift check. |

### Condition: injected

Every rate below is computed on the **common set** of the tasks of the
cell: the tasks that **every** arm of that model and of that condition
completed.  The column "Dropped" is the number of tasks the arm had
beyond that set.

| Model | Arm | N | Dropped | Correct completion rate (95% CI) | False completion rate (95% CI) | Believed done | Requests | Wall s | Rejections | Loops |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | agentether | 12 | 0 | 0.833 [0.552, 0.953] | 0.167 [0.047, 0.448] | 12 | 47 | 1679.36 | 3 | 0 |
| gemini-3.5-flash-lite | naive | 12 | 0 | 0.583 [0.320, 0.807] | 0.167 [0.047, 0.448] | 9 | 42 | 1166.01 | 0 | 0 |
| gemini-3.5-flash-lite | simple-retry | 12 | 0 | 0.833 [0.552, 0.953] | 0.167 [0.047, 0.448] | 12 | 46 | 1611.07 | 0 | 0 |
| gpt-oss-120b | agentether | 12 | 0 | 0.667 [0.391, 0.862] | 0.083 [0.015, 0.354] | 9 | 34 | 458.93 | 2 | 0 |
| gpt-oss-120b | naive | 12 | 0 | 0.417 [0.193, 0.680] | 0.333 [0.138, 0.609] | 9 | 31 | 420.83 | 0 | 0 |
| gpt-oss-120b | simple-retry | 12 | 0 | 0.417 [0.193, 0.680] | 0.333 [0.138, 0.609] | 9 | 31 | 449.62 | 0 | 0 |

### Condition: natural

Every rate below is computed on the **common set** of the tasks of the
cell: the tasks that **every** arm of that model and of that condition
completed.  The column "Dropped" is the number of tasks the arm had
beyond that set.

| Model | Arm | N | Dropped | Correct completion rate (95% CI) | False completion rate (95% CI) | Believed done | Requests | Wall s | Rejections | Loops |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | agentether | 12 | 0 | 0.917 [0.646, 0.985] | 0.083 [0.015, 0.354] | 12 | 42 | 1325.62 | 0 | 0 |
| gemini-3.5-flash-lite | naive | 12 | 0 | 1.000 [0.757, 1.000] | 0.000 [0.000, 0.243] | 12 | 42 | 963.31 | 0 | 0 |
| gemini-3.5-flash-lite | simple-retry | 12 | 0 | 0.917 [0.646, 0.985] | 0.083 [0.015, 0.354] | 12 | 42 | 1184.75 | 0 | 0 |
| gpt-oss-120b | agentether | 12 | 0 | 0.750 [0.468, 0.911] | 0.000 [0.000, 0.243] | 9 | 31 | 446.57 | 0 | 0 |
| gpt-oss-120b | naive | 12 | 0 | 0.750 [0.468, 0.911] | 0.000 [0.000, 0.243] | 9 | 31 | 371.3 | 0 | 0 |
| gpt-oss-120b | simple-retry | 12 | 0 | 0.750 [0.468, 0.911] | 0.000 [0.000, 0.243] | 9 | 31 | 449.75 | 0 | 0 |

### The paired differences

Every arm saw the same tasks and the same fault schedule, so the
comparison is paired.  The difference is the share of the tasks where
one arm was right and the other was not, with the sign convention of
the section above (A minus B).  The comparison is made on the common
set of the tasks of the cell, the same set the rates above use.

| Model | Condition | Comparison | N | Only A | Only B | Both | Neither | Difference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | correct completion (agentether vs naive) | 12 | 4 | 1 | 6 | 1 | +0.250 |
| gemini-3.5-flash-lite | injected | false completion (agentether vs naive) | 12 | 1 | 1 | 1 | 9 | +0.000 |
| gemini-3.5-flash-lite | injected | correct completion (agentether vs simple-retry) | 12 | 1 | 1 | 9 | 1 | +0.000 |
| gemini-3.5-flash-lite | injected | false completion (agentether vs simple-retry) | 12 | 1 | 1 | 1 | 9 | +0.000 |
| gemini-3.5-flash-lite | natural | correct completion (agentether vs naive) | 12 | 0 | 1 | 11 | 0 | -0.083 |
| gemini-3.5-flash-lite | natural | false completion (agentether vs naive) | 12 | 1 | 0 | 0 | 11 | +0.083 |
| gemini-3.5-flash-lite | natural | correct completion (agentether vs simple-retry) | 12 | 0 | 0 | 11 | 1 | +0.000 |
| gemini-3.5-flash-lite | natural | false completion (agentether vs simple-retry) | 12 | 0 | 0 | 1 | 11 | +0.000 |
| gpt-oss-120b | injected | correct completion (agentether vs naive) | 12 | 3 | 0 | 5 | 4 | +0.250 |
| gpt-oss-120b | injected | false completion (agentether vs naive) | 12 | 0 | 3 | 1 | 8 | -0.250 |
| gpt-oss-120b | injected | correct completion (agentether vs simple-retry) | 12 | 3 | 0 | 5 | 4 | +0.250 |
| gpt-oss-120b | injected | false completion (agentether vs simple-retry) | 12 | 0 | 3 | 1 | 8 | -0.250 |
| gpt-oss-120b | natural | correct completion (agentether vs naive) | 12 | 0 | 0 | 9 | 3 | +0.000 |
| gpt-oss-120b | natural | false completion (agentether vs naive) | 12 | 0 | 0 | 0 | 12 | +0.000 |
| gpt-oss-120b | natural | correct completion (agentether vs simple-retry) | 12 | 0 | 0 | 9 | 3 | +0.000 |
| gpt-oss-120b | natural | false completion (agentether vs simple-retry) | 12 | 0 | 0 | 0 | 12 | +0.000 |

### The hypotheses

H1: the guarded arm completes more tasks correctly.  H2: the guarded arm
catches more false completions (the primary endpoint).  The paired
differences follow the sign convention of the section above: the
guarded arm minus the naive arm, a **positive** H1 is an improvement
and a **negative** H2 is an improvement.

| Model | Condition | agentether | naive | H1 (paired) | H2 (paired) |
| --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | 0.833 | 0.583 | +0.250 | +0.000 |
| gemini-3.5-flash-lite | natural | 0.917 | 1.000 | -0.083 | +0.083 |
| gpt-oss-120b | injected | 0.667 | 0.417 | +0.250 | -0.250 |
| gpt-oss-120b | natural | 0.750 | 0.750 | +0.000 | +0.000 |

### The verdicts

H1: under the injected faults, the guarded arm completes more tasks
correctly than the baseline.  H2 (the primary endpoint): the guarded
arm catches more false completions.  H3: the guarded arm costs more.

The verdict of a hypothesis is **INCONCLUSIVE** when the difference is
smaller than the minimum detectable effect of the sample: the sample
is then too small to say anything, which is not the same as "no
effect".  The p value is the exact two sided McNemar test of the
discordant pairs.

The MDE of a cell is `1.4 / sqrt(N)` with the **achieved** N: the
number of the tasks that every arm of the cell completed.

| Model | N | MDE | H1: correct completion | H2: false completion (primary) | H3: the overhead |
| --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | 12 | 0.404 | +0.000 (in 1 task only the guarded arm completed, in 1 task only the comparator; p = 1.000): INCONCLUSIVE (the sample is too small) | +0.000 (in 1 task only the guarded arm falsely completed, in 1 task only the comparator; p = 1.000): INCONCLUSIVE (the sample is too small) | 47 against 46 requests, 43905 against 28041 tokens: SUPPORTED |
| gpt-oss-120b | 12 | 0.404 | +0.250 (in 3 tasks only the guarded arm completed, in 0 tasks only the comparator; p = 0.250): INCONCLUSIVE (the sample is too small) | -0.250 (in 0 tasks only the guarded arm falsely completed, in 3 tasks only the comparator; p = 0.250): INCONCLUSIVE (the sample is too small) | 34 against 31 requests, 42408 against 31324 tokens: SUPPORTED |

### The verdicts against the naive arm

The hypotheses of the protocol are stated against the simple-retry
baseline, and the table above is the verdict against it.  The **naive**
arm (one call per step, the claim is trusted) is the second
comparator, and it is reported here because the baseline is not always
a fair one: a baseline that retries writes the files of **every**
answer, and the last one wins, so with a model that is not
deterministic a retry can overwrite a good file with a worse one.

| Model | N | MDE | H1: correct completion | H2: false completion (primary) |
| --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | 12 | 0.404 | +0.250 (in 4 tasks only the guarded arm completed, in 1 task only the naive arm; p = 0.375): INCONCLUSIVE (the sample is too small) | +0.000 (in 1 task only the guarded arm falsely completed, in 1 task only the naive arm; p = 1.000): INCONCLUSIVE (the sample is too small) |
| gpt-oss-120b | 12 | 0.404 | +0.250 (in 3 tasks only the guarded arm completed, in 0 tasks only the naive arm; p = 0.250): INCONCLUSIVE (the sample is too small) | -0.250 (in 0 tasks only the guarded arm falsely completed, in 3 tasks only the naive arm; p = 0.250): INCONCLUSIVE (the sample is too small) |

### The cost of honesty

The guard of AgenTether prevents false claims; it does not by
itself make a task succeed.  A task the model cannot finish is a
failure either way, but the naive arm reports it as a success and
the guarded arm reports it as a failure: the difference is honest,
and it has a price.

The **honest "not completed"** are the tasks the arm did not claim
to have finished while the ground truth says they were not finished.
The column **converted** counts the ones that were a false
completion of the simple-retry baseline: a false "done" turned into
a visible failure.

| Model | Condition | Arm | N | Correct | False completion | Honest "not completed" | Converted | Rate of the honest failures (95% CI) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | agentether | 12 | 10 | 2 | 0 | 0 | 0.000 [0.000, 0.243] |
| gemini-3.5-flash-lite | injected | naive | 12 | 7 | 2 | 3 | 0 | 0.250 [0.089, 0.532] |
| gemini-3.5-flash-lite | injected | simple-retry | 12 | 10 | 2 | 0 | 0 | 0.000 [0.000, 0.243] |
| gemini-3.5-flash-lite | natural | agentether | 12 | 11 | 1 | 0 | 0 | 0.000 [0.000, 0.243] |
| gemini-3.5-flash-lite | natural | naive | 12 | 12 | 0 | 0 | 0 | 0.000 [0.000, 0.243] |
| gemini-3.5-flash-lite | natural | simple-retry | 12 | 11 | 1 | 0 | 0 | 0.000 [0.000, 0.243] |
| gpt-oss-120b | injected | agentether | 12 | 8 | 1 | 3 | 0 | 0.250 [0.089, 0.532] |
| gpt-oss-120b | injected | naive | 12 | 5 | 4 | 3 | 0 | 0.250 [0.089, 0.532] |
| gpt-oss-120b | injected | simple-retry | 12 | 5 | 4 | 3 | 0 | 0.250 [0.089, 0.532] |
| gpt-oss-120b | natural | agentether | 12 | 9 | 0 | 3 | 0 | 0.250 [0.089, 0.532] |
| gpt-oss-120b | natural | naive | 12 | 9 | 0 | 3 | 0 | 0.250 [0.089, 0.532] |
| gpt-oss-120b | natural | simple-retry | 12 | 9 | 0 | 3 | 0 | 0.250 [0.089, 0.532] |

## What this shows and what it does not

**It shows** how a few policies behave on the same tasks with the
same injected faults, for a few free models, on one day.

**It does not show** that AgenTether makes agents reliable in
general.  The sample is small, the tasks are synthetic, the models
are free tier models with their own limits, and the ground truth
checks are the ones the author of the library wrote.

A null result is reported as a null result: where the paired
difference is smaller than the interval, the table says so.
