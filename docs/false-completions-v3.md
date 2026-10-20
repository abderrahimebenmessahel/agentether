# The cause of every false completion of the trial v3

> This document is **generated** by `benchmarks/analyze_false.py` from
> the raw cells, the sandboxes and the attempt logs of the run.  No
> model was called to produce it.

A **false completion** is a cell whose arm believes the task is done
while the ground truth says it is not.  The belief of an arm and the
ground truth are two separate columns of the cells and they are never
mixed.

## The causes

| Code | The cause |
| --- | --- |
| **(i)** | an injected fault damaged an artifact and the arm did not catch it |
| **(ii)** | a required file was never produced and the claim did not mention it |
| **(iii)** | something else |

The four injected faults that damage an artifact are
`drop_file_block`, `truncate_file`, `lie` and `replay_previous`.
The other two (`corrupt_telemetry` and `wrong_step`) break the
telemetry and not the files, and they cannot produce a false
completion: the arm does not believe the task is done.

## The false completions, one table per arm

### The arm naive

| Model | Condition | Task | The check that failed | The fault | Cause | Why |
| --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | task02-clinic | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| gemini-3.5-flash-lite | injected | task03-depot | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| gemini-3.5-flash-lite | injected | task04-forge | file_exists notes.md | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| gemini-3.5-flash-lite | injected | task04-forge | headings notes.md '## Context' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| gemini-3.5-flash-lite | injected | task04-forge | headings notes.md '## Findings' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| gemini-3.5-flash-lite | injected | task04-forge | headings notes.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| gemini-3.5-flash-lite | injected | task04-forge | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| gemini-3.5-flash-lite | injected | task07-nursery | headings notes.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task02-clinic | file_exists report.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task02-clinic | headings report.md '## Summary' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task02-clinic | contains report.md '33' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task03-depot | file_exists build.py | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task03-depot | python_valid build.py | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task03-depot | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task03-depot | contains README.md 'build_depot' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task03-depot | contains README.md '34' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task04-forge | file_exists notes.md | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task04-forge | headings notes.md '## Context' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task04-forge | headings notes.md '## Findings' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task04-forge | headings notes.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |

### The arm simple-retry

| Model | Condition | Task | The check that failed | The fault | Cause | Why |
| --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | task04-forge | headings notes.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task02-clinic | file_exists report.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task02-clinic | headings report.md '## Summary' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task02-clinic | contains report.md '33' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task03-depot | file_exists build.py | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task03-depot | python_valid build.py | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task03-depot | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task03-depot | contains README.md 'build_depot' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task03-depot | contains README.md '34' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task04-forge | file_exists notes.md | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task04-forge | headings notes.md '## Context' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task04-forge | headings notes.md '## Findings' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task04-forge | headings notes.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |

### The arm agentether-claims-only

| Model | Condition | Task | The check that failed | The fault | Cause | Why |
| --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | task04-forge | headings notes.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task04-forge | headings notes.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |

### The arm agentether

| Model | Condition | Task | The check that failed | The fault | Cause | Why |
| --- | --- | --- | --- | --- | --- | --- |

## The counts of the causes

| Cause | The false completions | The failing checks |
| --- | --- | --- |
| (i) an injected fault damaged an artifact and the arm did not catch it | 7 | 16 |
| (ii) a required file was never produced and the claim did not mention it | 4 | 16 |
| (iii) something else | 2 | 3 |

## What the guarded arm caught, and what it could not

The table compares the false completions of the naive arm (the arm
that trusts every claim) with the false completions of the guarded
arm, task by task, on the same tasks and the same fault schedule.

| Model | Condition | The false completions of the naive arm | The guarded arm caught | It could not catch | The guarded arm added |
| --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | 4 | task02-clinic (iii), task03-depot (iii), task04-forge (i), task07-nursery (i) | none | none |
| gpt-oss-120b | injected | 3 | task02-clinic (ii), task03-depot (ii), task04-forge (i) | none | none |

## Why the guarded arm caught what it caught

The verifier of the claims-only arm is `artifacts_exist()`: it checks
that the files the model **claims** exist.  It does not look at their
content, and it cannot know what the step asked for.  The arm that
declares what the step owes checks the **declaration** of the step:
the file must exist, and its content must satisfy the declaration.
Three cases follow, and they are the whole explanation:

* a false completion whose artifact is **missing** is caught by both:
  the check fails, the step is retried and the arm does not believe
  the task is done;
* a false completion whose artifact **exists but is damaged** is
  caught only by the declaration: the existence check passes;
* a false completion whose artifact was **never produced and never
  claimed** is caught only by the declaration: the check of the
  claimed files passes.

* **gemini-3.5-flash-lite, injected.**
  * the false completion of task02-clinic was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task03-depot was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task04-forge was **caught**: the injected fault 'truncate_file' of the attempt 1 removed the file.
  * the false completion of task07-nursery was **caught**: the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer.
* **gpt-oss-120b, injected.**
  * the false completion of task02-clinic was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task03-depot was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task04-forge was **caught**: the injected fault 'truncate_file' of the attempt 1 removed the file.

### The defect of the harness

The harness closes a file on the next fence, even when that fence
opens a code block **of the file itself** (a Markdown file that shows
how to run the script is the common case).  The file is then cut in
the middle, the rest of it is lost, and the ground truth fails.  The
answer of the model was complete: the proof is in the answer that the
guarded arm recorded in its project memory.

| Model | Condition | Task | The arms that lost it |
| --- | --- | --- | --- |

The baseline (`simple-retry`) keeps no log of the answers of the
model, so the proof comes from the answers of the guarded arm; the
file of the baseline carries the same signature (a content cut in
the middle).  The naive arm was right on those tasks by luck: the
Google model is not deterministic (the capability probe says so),
and its answer for that task did not hold a code block.

**The fix belongs to the harness, not to the library.**  The parser
must close a file on a fence that closes it and not on a fence that
opens a block, and the trial v3 runs with the repaired parser (the
data of the trial v2 stay as they are: they are a supplementary
run).


### What the run of the day shows

The run of the day is **partial**: the budget of the day of the free tier
allowed six tasks per cell on Cerebras and six (seven for two arms) on
Google, and the provider of Google refused the calls of the afternoon with
`HTTP 429 - You exceeded your current quota`.  The sample is far below
the sixty tasks per cell of the protocol, and every verdict that depends
on the size of the sample is **inconclusive**.

What the data show is the **direction**, and it is the same in the two
models:

* the naive arm and the baseline believed the task was done while the
  ground truth said it was not, on three tasks (Cerebras) and on one task
  (Google);
* the arm that only checks the **claimed** files caught two of them
  (Cerebras) and one (Google);
* the arm that **declares** what the step must produce caught **all** of
  them, in the two models.

The causes of the false completions are the ones the trial v3 was built
to measure: the file was removed (`hide_file`, `lie`, `drop_file_block`),
the file was cut in the middle (`truncate_file`), or the file was never
produced and the claim mentioned only the files the model did produce.
The declaration of the step sees the three cases; the check of the
claimed files sees the first one only.

