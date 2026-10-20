# The cause of every false completion of the trial v2

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
| gemini-3.5-flash-lite | injected | task02-orchard | file_exists report.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gemini-3.5-flash-lite | injected | task02-orchard | headings report.md '## Summary' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gemini-3.5-flash-lite | injected | task02-orchard | contains report.md '12' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gemini-3.5-flash-lite | injected | task07-trellis | json_keys data.json 'a,b,c' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gemini-3.5-flash-lite | injected | task07-trellis | json_value data.json 'a=17' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gemini-3.5-flash-lite | injected | task07-trellis | json_value data.json 'b=trellis' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task02-orchard | file_exists report.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task02-orchard | headings report.md '## Summary' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task02-orchard | contains report.md '12' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task04-meridian | file_exists data.json | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task04-meridian | json_keys data.json 'a,b,c' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task04-meridian | json_value data.json 'a=14' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task04-meridian | json_value data.json 'b=meridian' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task07-trellis | json_keys data.json 'a,b,c' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task07-trellis | json_value data.json 'a=17' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task07-trellis | json_value data.json 'b=trellis' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task08-compass | file_exists data.json | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task08-compass | json_keys data.json 'a,b,c' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task08-compass | json_value data.json 'a=18' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task08-compass | json_value data.json 'b=compass' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |

### The arm simple-retry

| Model | Condition | Task | The check that failed | The fault | Cause | Why |
| --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | task02-orchard | file_exists report.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gemini-3.5-flash-lite | injected | task02-orchard | headings report.md '## Summary' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gemini-3.5-flash-lite | injected | task02-orchard | contains report.md '12' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gemini-3.5-flash-lite | injected | task07-trellis | json_keys data.json 'a,b,c' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gemini-3.5-flash-lite | injected | task07-trellis | json_value data.json 'a=17' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gemini-3.5-flash-lite | injected | task07-trellis | json_value data.json 'b=trellis' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gemini-3.5-flash-lite | natural | task11-vellum | contains README.md 'build_vellum' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| gemini-3.5-flash-lite | natural | task11-vellum | contains README.md '21' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| gpt-oss-120b | injected | task02-orchard | file_exists report.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task02-orchard | headings report.md '## Summary' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task02-orchard | contains report.md '12' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task04-meridian | file_exists data.json | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task04-meridian | json_keys data.json 'a,b,c' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task04-meridian | json_value data.json 'a=14' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task04-meridian | json_value data.json 'b=meridian' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task07-trellis | json_keys data.json 'a,b,c' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task07-trellis | json_value data.json 'a=17' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task07-trellis | json_value data.json 'b=trellis' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task08-compass | file_exists data.json | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task08-compass | json_keys data.json 'a,b,c' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task08-compass | json_value data.json 'a=18' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task08-compass | json_value data.json 'b=compass' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |

### The arm agentether

| Model | Condition | Task | The check that failed | The fault | Cause | Why |
| --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | task05-quarry | contains README.md 'build_quarry' | none | **(iii)** | the answer of the model holds more than the file on disk: the harness cut the file while writing it (the answer holds a code block inside the file, and the parser closes the file on the fence of that block) |
| gemini-3.5-flash-lite | injected | task05-quarry | contains README.md '15' | none | **(iii)** | the answer of the model holds more than the file on disk: the harness cut the file while writing it (the answer holds a code block inside the file, and the parser closes the file on the fence of that block) |
| gemini-3.5-flash-lite | injected | task07-trellis | json_keys data.json 'a,b,c' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gemini-3.5-flash-lite | injected | task07-trellis | json_value data.json 'a=17' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gemini-3.5-flash-lite | injected | task07-trellis | json_value data.json 'b=trellis' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gemini-3.5-flash-lite | natural | task11-vellum | contains README.md 'build_vellum' | none | **(iii)** | the answer of the model holds more than the file on disk: the harness cut the file while writing it (the answer holds a code block inside the file, and the parser closes the file on the fence of that block) |
| gemini-3.5-flash-lite | natural | task11-vellum | contains README.md '21' | none | **(iii)** | the answer of the model holds more than the file on disk: the harness cut the file while writing it (the answer holds a code block inside the file, and the parser closes the file on the fence of that block) |
| gpt-oss-120b | injected | task07-trellis | json_keys data.json 'a,b,c' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task07-trellis | json_value data.json 'a=17' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task07-trellis | json_value data.json 'b=trellis' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |

## The counts of the causes

| Cause | The false completions | The failing checks |
| --- | --- | --- |
| (i) an injected fault damaged an artifact and the arm did not catch it | 14 | 46 |
| (ii) a required file was never produced and the claim did not mention it | 0 | 0 |
| (iii) something else | 3 | 6 |

## What the guarded arm caught, and what it could not

The table compares the false completions of the naive arm (the arm
that trusts every claim) with the false completions of the guarded
arm, task by task, on the same tasks and the same fault schedule.

| Model | Condition | The false completions of the naive arm | The guarded arm caught | It could not catch | The guarded arm added |
| --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | 2 | task02-orchard (i) | task07-trellis (i) | task05-quarry (iii) |
| gemini-3.5-flash-lite | natural | 0 | none | none | task11-vellum (iii) |
| gpt-oss-120b | injected | 4 | task02-orchard (i), task04-meridian (i), task08-compass (i) | task07-trellis (i) | none |

## Why the guarded arm caught three of the four on Cerebras and none on Gemini

The verifier of the guarded arm in the trial v2 is
`artifacts_exist()`: it checks that the files the model **claims**
exist.  It does not look at their content, and it cannot know what the
step asked for.  Two consequences follow, and they are the whole
explanation:

* a false completion whose artifact is **missing** is caught: the
  existence check fails, the step is retried and the arm does not
  believe the task is done;
* a false completion whose artifact **exists but is damaged** is not
  caught: the check passes, the step completes and the ground truth
  fails behind the back of the arm.

* **gemini-3.5-flash-lite, injected.**
  * the false completion of task02-orchard was **caught**: the injected fault 'replay_previous' removed the file, the existence check failed and the step was retried.
  * the false completion of task07-trellis was **not** caught: the injected fault 'truncate_file' left a file that exists but is cut in the middle, and the existence check cannot see it.
  * the guarded arm **added** a false completion of its own on task05-quarry: the answer of the model holds more than the file on disk: the harness cut the file while writing it (the answer holds a code block inside the file, and the parser closes the file on the fence of that block)  This one is a defect of the harness and not of the library: the file on disk is a faithful copy of what the harness wrote, so no verifier of the library could see it.
* **gemini-3.5-flash-lite, natural.**
  * the guarded arm **added** a false completion of its own on task11-vellum: the answer of the model holds more than the file on disk: the harness cut the file while writing it (the answer holds a code block inside the file, and the parser closes the file on the fence of that block)  This one is a defect of the harness and not of the library: the file on disk is a faithful copy of what the harness wrote, so no verifier of the library could see it.
* **gpt-oss-120b, injected.**
  * the false completion of task02-orchard was **caught**: the injected fault 'replay_previous' removed the file, the existence check failed and the step was retried.
  * the false completion of task04-meridian was **caught**: the injected fault 'lie' removed the file, the existence check failed and the step was retried.
  * the false completion of task08-compass was **caught**: the injected fault 'drop_file_block' removed the file, the existence check failed and the step was retried.
  * the false completion of task07-trellis was **not** caught: the injected fault 'truncate_file' left a file that exists but is cut in the middle, and the existence check cannot see it.

So the two results are not the same kind of result.  On Cerebras
the guarded arm caught the three false completions whose artifact
was **missing** and could not catch the one whose artifact was
**damaged but present**.  On Gemini it caught the missing one and
missed the damaged one, but it also lost a task of its own to a
defect of the harness, and the two effects cancelled each other in
the rate (0.167 against 0.167).  The honest reading of the two
cells is therefore **not** "the library works on Cerebras and not
on Gemini": it is "the library catches a missing artifact and does
not catch a damaged one", and the harness must not damage the
files.

### The defect of the harness

The harness closes a file on the next fence, even when that fence
opens a code block **of the file itself** (a Markdown file that shows
how to run the script is the common case).  The file is then cut in
the middle, the rest of it is lost, and the ground truth fails.  The
answer of the model was complete: the proof is in the answer that the
guarded arm recorded in its project memory.

| Model | Condition | Task | The arms that lost it |
| --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | task05-quarry | agentether |
| gemini-3.5-flash-lite | natural | task11-vellum | agentether |

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

**What the fix is.**  A step that declares what it must produce
(`expects`) is checked against that declaration and not only
against the claim of the agent: the file must exist **and** be
valid (a JSON that parses, a Python that compiles, a Markdown
that has its headings).  A file that is cut in the middle then
fails the declaration, the step is retried and the false
completion disappears.  See `docs/verifiers.md`.

