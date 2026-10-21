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
| gpt-oss-120b | injected | task07-nursery | headings notes.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task09-refinery | file_exists data.json | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task09-refinery | json_keys data.json 'a,b,c' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task09-refinery | json_value data.json 'a=40' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task09-refinery | json_value data.json 'b=refinery' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task11-tannery | file_exists build.py | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task11-tannery | python_valid build.py | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task11-tannery | file_exists README.md | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task11-tannery | contains README.md 'build_tannery' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task11-tannery | contains README.md '42' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | file_exists build.py | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | python_valid build.py | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | file_exists README.md | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | contains README.md 'build_vineyard' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | contains README.md '43' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | file_exists report.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | headings report.md '## Summary' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | contains report.md '43' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | file_exists data.json | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | json_keys data.json 'a,b,c' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | json_value data.json 'a=45' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | json_value data.json 'b=wharf' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | file_exists build.py | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | python_valid build.py | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | file_exists README.md | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | contains README.md 'build_wharf' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | contains README.md '45' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task18-brewery | file_exists notes.md | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task18-brewery | headings notes.md '## Context' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task18-brewery | headings notes.md '## Findings' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task18-brewery | headings notes.md '## Next steps' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task20-distillery | json_keys data.json 'a,b,c' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task20-distillery | json_value data.json 'a=51' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task20-distillery | json_value data.json 'b=distillery' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task20-distillery | file_exists report.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task20-distillery | headings report.md '## Summary' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task20-distillery | contains report.md '51' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task21-factory | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task21-factory | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task21-factory | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task21-factory | headings summary.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task22-boatyard | file_exists main.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task22-boatyard | python_valid main.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task22-boatyard | file_exists GUIDE.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task22-boatyard | contains GUIDE.md 'compile_boatyard' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task22-boatyard | contains GUIDE.md '169' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task23-elevator | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task23-elevator | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task23-elevator | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task23-elevator | headings summary.md '## Actions' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task24-gristmill | file_exists report.md | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task24-gristmill | headings report.md '## Overview' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task24-gristmill | contains report.md '165' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task02-clinic | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task02-clinic | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task02-clinic | headings notes.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task02-clinic | headings notes.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task02-clinic | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task02-clinic | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task02-clinic | json_value data.json 'a=33' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task02-clinic | json_value data.json 'b=clinic' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task05-garden | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task05-garden | json_value data.json 'a=36' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task05-garden | json_value data.json 'b=garden' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task07-nursery | file_exists notes.md | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task07-nursery | headings notes.md '## Context' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task07-nursery | headings notes.md '## Findings' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task07-nursery | headings notes.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task08-paddock | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task08-paddock | json_value data.json 'a=39' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task08-paddock | json_value data.json 'b=paddock' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task08-paddock | contains README.md 'build_paddock' | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task08-paddock | contains README.md '39' | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task09-refinery | file_exists data.json | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | json_keys data.json 'a,b,c' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | json_value data.json 'a=40' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | json_value data.json 'b=refinery' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task16-ziggurat | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task16-ziggurat | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task16-ziggurat | json_value data.json 'a=47' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task16-ziggurat | json_value data.json 'b=ziggurat' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task17-apiary | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task17-apiary | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task17-apiary | json_value data.json 'a=48' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task17-apiary | json_value data.json 'b=apiary' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task17-apiary | python_valid build.py | truncate_file | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task17-apiary | file_exists README.md | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task17-apiary | contains README.md 'build_apiary' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task17-apiary | contains README.md '48' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task18-brewery | file_exists notes.md | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task18-brewery | headings notes.md '## Context' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task18-brewery | headings notes.md '## Findings' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task18-brewery | headings notes.md '## Next steps' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task18-brewery | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task18-brewery | json_value data.json 'a=49' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task18-brewery | json_value data.json 'b=brewery' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task19-cannery | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task19-cannery | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task19-cannery | json_value data.json 'a=50' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task19-cannery | json_value data.json 'b=cannery' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task22-boatyard | file_exists main.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task22-boatyard | python_valid main.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task22-boatyard | file_exists GUIDE.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task22-boatyard | contains GUIDE.md 'compile_boatyard' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task22-boatyard | contains GUIDE.md '169' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task23-elevator | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | headings summary.md '## Actions' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | file_exists data.json | wrong_step | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | json_keys data.json 'a,b,c' | wrong_step | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | json_value data.json 'a=176' | wrong_step | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | json_value data.json 'b=elevator' | wrong_step | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task23-elevator | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | contains README.md 'render_elevator' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | contains README.md '176' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | headings notes.md '## Context' | replay_previous | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task24-gristmill | headings notes.md '## Findings' | replay_previous | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task24-gristmill | headings notes.md '## Next steps' | replay_previous | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task24-gristmill | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | json_value data.json 'a=165' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | json_value data.json 'b=gristmill' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | file_exists main.py | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | python_valid main.py | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | file_exists GUIDE.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | contains GUIDE.md 'draft_gristmill' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | contains GUIDE.md '165' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | file_exists report.md | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | headings report.md '## Overview' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | contains report.md '165' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task35-workshop | python_valid main.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task35-workshop | file_exists GUIDE.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task35-workshop | contains GUIDE.md 'draft_workshop' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task35-workshop | contains GUIDE.md '158' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | file_exists build.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | python_valid build.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | file_exists README.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | contains README.md 'plan_taphouse' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | contains README.md '82' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task38-woodyard | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task38-woodyard | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task38-woodyard | headings notes.md '## Observations' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task38-woodyard | headings notes.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task38-woodyard | file_exists build.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task38-woodyard | python_valid build.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task38-woodyard | file_exists README.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task38-woodyard | contains README.md 'design_woodyard' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task38-woodyard | contains README.md '81' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task46-laundry | headings notes.md '## Context' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task46-laundry | headings notes.md '## Findings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task46-laundry | headings notes.md '## Actions' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task46-laundry | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task46-laundry | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task46-laundry | json_value data.json 'a=128' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task46-laundry | json_value data.json 'b=laundry' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task47-cardroom | file_exists data.json | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task47-cardroom | json_keys data.json 'a,b,c' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task47-cardroom | json_value data.json 'a=67' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task47-cardroom | json_value data.json 'b=cardroom' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task49-parlour | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task49-parlour | json_value data.json 'a=75' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task49-parlour | json_value data.json 'b=parlour' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task49-parlour | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task49-parlour | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task49-parlour | contains README.md 'design_parlour' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task49-parlour | contains README.md '75' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task51-tinsmith | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task51-tinsmith | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task51-tinsmith | headings summary.md '## Observations' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task51-tinsmith | headings summary.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task51-tinsmith | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task51-tinsmith | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task51-tinsmith | contains README.md 'build_tinsmith' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task51-tinsmith | contains README.md '193' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task52-moor | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task52-moor | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task52-moor | contains README.md 'compose_moor' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task52-moor | contains README.md '99' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task53-quern | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task53-quern | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task53-quern | headings notes.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task53-quern | headings notes.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task53-quern | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task53-quern | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task53-quern | json_value data.json 'a=145' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task53-quern | json_value data.json 'b=quern' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task53-quern | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task53-quern | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task53-quern | contains README.md 'prepare_quern' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task53-quern | contains README.md '145' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task54-brickyard | python_valid build.py | wrong_step | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task54-brickyard | file_exists README.md | wrong_step | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task54-brickyard | contains README.md 'make_brickyard' | wrong_step | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task54-brickyard | contains README.md '138' | wrong_step | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task55-millrace | headings notes.md '## Context' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task55-millrace | headings notes.md '## Findings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task55-millrace | headings notes.md '## Actions' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task55-millrace | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task55-millrace | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task55-millrace | json_value data.json 'a=189' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task55-millrace | json_value data.json 'b=millrace' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task55-millrace | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task55-millrace | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task55-millrace | contains README.md 'compile_millrace' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task55-millrace | contains README.md '189' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |

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
| gpt-oss-120b | injected | task07-nursery | headings notes.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task09-refinery | file_exists data.json | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task09-refinery | json_keys data.json 'a,b,c' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task09-refinery | json_value data.json 'a=40' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task09-refinery | json_value data.json 'b=refinery' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task11-tannery | file_exists build.py | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task11-tannery | python_valid build.py | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task11-tannery | file_exists README.md | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task11-tannery | contains README.md 'build_tannery' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task11-tannery | contains README.md '42' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | file_exists build.py | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | python_valid build.py | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | file_exists README.md | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | contains README.md 'build_vineyard' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | contains README.md '43' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | file_exists report.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | headings report.md '## Summary' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task12-vineyard | contains report.md '43' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | file_exists data.json | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | json_keys data.json 'a,b,c' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | json_value data.json 'a=45' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | json_value data.json 'b=wharf' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | file_exists build.py | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | python_valid build.py | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | file_exists README.md | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | contains README.md 'build_wharf' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | contains README.md '45' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task18-brewery | file_exists notes.md | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task18-brewery | headings notes.md '## Context' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task18-brewery | headings notes.md '## Findings' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task18-brewery | headings notes.md '## Next steps' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task20-distillery | json_keys data.json 'a,b,c' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task20-distillery | json_value data.json 'a=51' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task20-distillery | json_value data.json 'b=distillery' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task20-distillery | file_exists report.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task20-distillery | headings report.md '## Summary' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task20-distillery | contains report.md '51' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task21-factory | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task21-factory | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task21-factory | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task21-factory | headings summary.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task22-boatyard | file_exists main.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task22-boatyard | python_valid main.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task22-boatyard | file_exists GUIDE.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task22-boatyard | contains GUIDE.md 'compile_boatyard' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task22-boatyard | contains GUIDE.md '169' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task23-elevator | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task23-elevator | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task23-elevator | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task23-elevator | headings summary.md '## Actions' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| gpt-oss-120b | injected | task24-gristmill | file_exists report.md | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task24-gristmill | headings report.md '## Overview' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task24-gristmill | contains report.md '165' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task01-bakery | headings notes.md '## Context' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task01-bakery | headings notes.md '## Findings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task01-bakery | headings notes.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task01-bakery | contains README.md 'build_bakery' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task01-bakery | contains README.md '32' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task02-clinic | headings notes.md '## Context' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task02-clinic | headings notes.md '## Findings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task02-clinic | headings notes.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task02-clinic | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task02-clinic | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task02-clinic | json_value data.json 'a=33' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task02-clinic | json_value data.json 'b=clinic' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task03-depot | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task03-depot | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task03-depot | json_value data.json 'a=34' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task03-depot | json_value data.json 'b=depot' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task04-forge | headings notes.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| qwen2.5:3b-instruct | injected | task06-mill | headings notes.md '## Findings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task06-mill | headings notes.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task07-nursery | headings notes.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| qwen2.5:3b-instruct | injected | task07-nursery | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task07-nursery | json_value data.json 'a=38' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task07-nursery | json_value data.json 'b=nursery' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task08-paddock | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task08-paddock | json_value data.json 'a=39' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task08-paddock | json_value data.json 'b=paddock' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task09-refinery | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | headings notes.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | headings notes.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | file_exists data.json | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | json_keys data.json 'a,b,c' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | json_value data.json 'a=40' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | json_value data.json 'b=refinery' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | file_exists build.py | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | python_valid build.py | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | contains README.md 'build_refinery' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | contains README.md '40' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task16-ziggurat | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task16-ziggurat | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task16-ziggurat | json_value data.json 'a=47' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task16-ziggurat | json_value data.json 'b=ziggurat' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task17-apiary | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task17-apiary | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task17-apiary | json_value data.json 'a=48' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task17-apiary | json_value data.json 'b=apiary' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task17-apiary | python_valid build.py | truncate_file | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task17-apiary | file_exists README.md | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task17-apiary | contains README.md 'build_apiary' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task17-apiary | contains README.md '48' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task18-brewery | file_exists notes.md | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task18-brewery | headings notes.md '## Context' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task18-brewery | headings notes.md '## Findings' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task18-brewery | headings notes.md '## Next steps' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task18-brewery | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task18-brewery | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task18-brewery | contains README.md 'build_brewery' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task18-brewery | contains README.md '49' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task19-cannery | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task19-cannery | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task19-cannery | json_value data.json 'a=50' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task19-cannery | json_value data.json 'b=cannery' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task20-distillery | json_keys data.json 'a,b,c' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| qwen2.5:3b-instruct | injected | task20-distillery | json_value data.json 'a=51' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| qwen2.5:3b-instruct | injected | task20-distillery | json_value data.json 'b=distillery' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| qwen2.5:3b-instruct | injected | task21-factory | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task21-factory | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task21-factory | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task21-factory | headings summary.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task21-factory | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task21-factory | json_value data.json 'a=186' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task21-factory | json_value data.json 'b=factory' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task21-factory | contains README.md 'make_factory' | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task21-factory | contains README.md '186' | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task22-boatyard | file_exists main.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task22-boatyard | python_valid main.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task22-boatyard | file_exists GUIDE.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task22-boatyard | contains GUIDE.md 'compile_boatyard' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task22-boatyard | contains GUIDE.md '169' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task23-elevator | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | headings summary.md '## Actions' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | file_exists data.json | wrong_step | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | json_keys data.json 'a,b,c' | wrong_step | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | json_value data.json 'a=176' | wrong_step | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | json_value data.json 'b=elevator' | wrong_step | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task23-elevator | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | contains README.md 'render_elevator' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task23-elevator | contains README.md '176' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task31-foundry | file_exists summary.md | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task31-foundry | headings summary.md '## Context' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task31-foundry | headings summary.md '## Findings' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task31-foundry | headings summary.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task31-foundry | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task31-foundry | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task31-foundry | contains README.md 'prepare_foundry' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task31-foundry | contains README.md '184' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task34-lighthouse | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task34-lighthouse | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task34-lighthouse | contains README.md 'render_lighthouse' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task34-lighthouse | contains README.md '173' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task35-workshop | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task35-workshop | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task35-workshop | json_value data.json 'a=158' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task35-workshop | json_value data.json 'b=workshop' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task35-workshop | python_valid main.py | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task35-workshop | file_exists GUIDE.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task35-workshop | contains GUIDE.md 'draft_workshop' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task35-workshop | contains GUIDE.md '158' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | headings notes.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | headings notes.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | json_value data.json 'a=82' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | json_value data.json 'b=taphouse' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | file_exists build.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | python_valid build.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | file_exists README.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | contains README.md 'plan_taphouse' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task36-taphouse | contains README.md '82' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task37-estate | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task37-estate | json_value data.json 'a=194' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task37-estate | json_value data.json 'b=estate' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task38-woodyard | file_exists build.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task38-woodyard | python_valid build.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task38-woodyard | file_exists README.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task38-woodyard | contains README.md 'design_woodyard' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task38-woodyard | contains README.md '81' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task40-masons | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task40-masons | json_value data.json 'a=70' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task40-masons | json_value data.json 'b=masons' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task40-masons | file_exists GUIDE.md | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task40-masons | contains GUIDE.md 'build_masons' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task40-masons | contains GUIDE.md '70' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task41-lumberyard | headings notes.md '## Observations' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task41-lumberyard | headings notes.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task41-lumberyard | python_valid main.py | lie | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task41-lumberyard | file_exists GUIDE.md | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task41-lumberyard | contains GUIDE.md 'compose_lumberyard' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task41-lumberyard | contains GUIDE.md '156' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task42-anchorage | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task42-anchorage | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task42-anchorage | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task42-anchorage | headings summary.md '## Actions' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task42-anchorage | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task42-anchorage | json_value data.json 'a=114' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task42-anchorage | json_value data.json 'b=anchorage' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task46-laundry | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task46-laundry | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task46-laundry | contains README.md 'draft_laundry' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task46-laundry | contains README.md '128' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task47-cardroom | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task47-cardroom | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task47-cardroom | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task47-cardroom | headings summary.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task47-cardroom | file_exists data.json | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task47-cardroom | json_keys data.json 'a,b,c' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task47-cardroom | json_value data.json 'a=67' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task47-cardroom | json_value data.json 'b=cardroom' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task48-packhouse | file_exists data.json | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task48-packhouse | json_keys data.json 'a,b,c' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task48-packhouse | json_value data.json 'a=168' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task48-packhouse | json_value data.json 'b=packhouse' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task48-packhouse | python_valid main.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task48-packhouse | file_exists GUIDE.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task48-packhouse | contains GUIDE.md 'assemble_packhouse' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task48-packhouse | contains GUIDE.md '168' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task49-parlour | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task49-parlour | json_value data.json 'a=75' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task49-parlour | json_value data.json 'b=parlour' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task49-parlour | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task49-parlour | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task49-parlour | contains README.md 'design_parlour' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task49-parlour | contains README.md '75' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task51-tinsmith | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task51-tinsmith | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task51-tinsmith | headings summary.md '## Observations' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task51-tinsmith | headings summary.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task51-tinsmith | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task51-tinsmith | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task51-tinsmith | contains README.md 'build_tinsmith' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task51-tinsmith | contains README.md '193' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task52-moor | headings notes.md '## Observations' | wrong_step | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task52-moor | headings notes.md '## Next steps' | wrong_step | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task52-moor | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task52-moor | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task52-moor | contains README.md 'compose_moor' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task52-moor | contains README.md '99' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task53-quern | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task53-quern | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task53-quern | contains README.md 'prepare_quern' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task53-quern | contains README.md '145' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task54-brickyard | python_valid build.py | wrong_step | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task54-brickyard | file_exists README.md | wrong_step | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task54-brickyard | contains README.md 'make_brickyard' | wrong_step | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task54-brickyard | contains README.md '138' | wrong_step | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |

### The arm agentether-claims-only

| Model | Condition | Task | The check that failed | The fault | Cause | Why |
| --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | task04-forge | headings notes.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task04-forge | headings notes.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task07-nursery | headings notes.md '## Next steps' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer |
| gpt-oss-120b | injected | task11-tannery | file_exists build.py | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task11-tannery | python_valid build.py | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| gpt-oss-120b | injected | task14-wharf | python_valid build.py | drop_file_block | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task20-distillery | headings notes.md '## Findings' | replay_previous | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task20-distillery | headings notes.md '## Next steps' | replay_previous | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task21-factory | headings summary.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task32-hangar | headings notes.md '## Observations' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task32-hangar | headings notes.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task36-taphouse | python_valid build.py | replay_previous | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task37-estate | headings notes.md '## Context' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task37-estate | headings notes.md '## Findings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task37-estate | headings notes.md '## Actions' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task39-ironworks | headings notes.md '## Findings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task39-ironworks | headings notes.md '## Actions' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task51-tinsmith | headings summary.md '## Context' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task51-tinsmith | headings summary.md '## Observations' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task51-tinsmith | headings summary.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |

### The arm agentether

| Model | Condition | Task | The check that failed | The fault | Cause | Why |
| --- | --- | --- | --- | --- | --- | --- |
| qwen2.5:3b-instruct | injected | task08-paddock | headings notes.md '## Findings' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task08-paddock | headings notes.md '## Next steps' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task08-paddock | json_keys data.json 'a,b,c' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task08-paddock | json_value data.json 'a=39' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task08-paddock | json_value data.json 'b=paddock' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task08-paddock | python_valid build.py | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task08-paddock | contains README.md 'build_paddock' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task08-paddock | contains README.md '39' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task18-brewery | headings notes.md '## Findings' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task18-brewery | headings notes.md '## Next steps' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task21-factory | headings summary.md '## Next steps' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task39-ironworks | headings notes.md '## Findings' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task39-ironworks | headings notes.md '## Actions' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task46-laundry | headings notes.md '## Context' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task46-laundry | headings notes.md '## Findings' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task46-laundry | headings notes.md '## Actions' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task46-laundry | json_keys data.json 'a,b,c' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task46-laundry | json_value data.json 'a=128' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task46-laundry | json_value data.json 'b=laundry' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task46-laundry | contains README.md 'draft_laundry' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | injected | task46-laundry | contains README.md '128' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |

## The counts of the causes

| Cause | The false completions | The failing checks |
| --- | --- | --- |
| (i) an injected fault damaged an artifact and the arm did not catch it | 41 | 173 |
| (ii) a required file was never produced and the claim did not mention it | 40 | 240 |
| (iii) something else | 25 | 122 |

## What the guarded arm caught, and what it could not

The table compares the false completions of the naive arm (the arm
that trusts every claim) with the false completions of the guarded
arm, task by task, on the same tasks and the same fault schedule.

| Model | Condition | The false completions of the naive arm | The guarded arm caught | It could not catch | The guarded arm added |
| --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | 4 | task02-clinic (iii), task03-depot (iii), task04-forge (i), task07-nursery (i) | none | none |
| gpt-oss-120b | injected | 14 | task02-clinic (ii), task03-depot (ii), task04-forge (i), task07-nursery (i), task09-refinery (ii), task11-tannery (i), task12-vineyard (i), task14-wharf (i), task18-brewery (i), task20-distillery (i), task21-factory (ii), task22-boatyard (i), task23-elevator (ii), task24-gristmill (i) | none | none |
| qwen2.5:3b-instruct | injected | 23 | task02-clinic (ii), task05-garden (iii), task07-nursery (i), task09-refinery (ii), task16-ziggurat (ii), task17-apiary (ii), task19-cannery (ii), task22-boatyard (i), task23-elevator (ii), task24-gristmill (ii), task35-workshop (ii), task36-taphouse (i), task38-woodyard (i), task47-cardroom (i), task49-parlour (iii), task51-tinsmith (ii), task52-moor (ii), task53-quern (ii), task54-brickyard (ii), task55-millrace (ii) | task08-paddock (iii), task18-brewery (i), task46-laundry (ii) | task21-factory (iii), task39-ironworks (iii) |

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
  * the false completion of task07-nursery was **caught**: the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer.
  * the false completion of task09-refinery was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task11-tannery was **caught**: the injected fault 'lie' of the attempt 1 removed the file.
  * the false completion of task12-vineyard was **caught**: the injected fault 'drop_file_block' of the attempt 1 removed the file.
  * the false completion of task14-wharf was **caught**: the injected fault 'replay_previous' of the attempt 1 removed the file.
  * the false completion of task18-brewery was **caught**: the injected fault 'drop_file_block' of the attempt 1 removed the file.
  * the false completion of task20-distillery was **caught**: the injected fault 'truncate_file' of the attempt 1 cut the answer, and the file on disk is a faithful copy of the cut answer.
  * the false completion of task21-factory was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task22-boatyard was **caught**: the injected fault 'replay_previous' of the attempt 1 removed the file.
  * the false completion of task23-elevator was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task24-gristmill was **caught**: the injected fault 'lie' of the attempt 1 removed the file.
* **qwen2.5:3b-instruct, injected.**
  * the false completion of task02-clinic was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task05-garden was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task07-nursery was **caught**: the injected fault 'truncate_file' of the attempt 1 removed the file.
  * the false completion of task09-refinery was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task16-ziggurat was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task17-apiary was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task19-cannery was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task22-boatyard was **caught**: the injected fault 'replay_previous' of the attempt 1 removed the file.
  * the false completion of task23-elevator was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task24-gristmill was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task35-workshop was **caught**: the file exists but its content does not satisfy the check.
  * the false completion of task36-taphouse was **caught**: the injected fault 'replay_previous' of the attempt 1 removed the file.
  * the false completion of task38-woodyard was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task47-cardroom was **caught**: the injected fault 'replay_previous' of the attempt 1 removed the file.
  * the false completion of task49-parlour was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task51-tinsmith was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task52-moor was **caught**: the file exists but its content does not satisfy the check.
  * the false completion of task53-quern was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task54-brickyard was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task55-millrace was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task08-paddock was **not** caught: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task18-brewery was **not** caught: the injected fault 'drop_file_block' of the attempt 1 removed the file.
  * the false completion of task46-laundry was **not** caught: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the guarded arm **added** a false completion of its own on task21-factory: the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it  This one is a defect of the harness and not of the library: the file on disk is a faithful copy of what the harness wrote, so no verifier of the library could see it.
  * the guarded arm **added** a false completion of its own on task39-ironworks: the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it  This one is a defect of the harness and not of the library: the file on disk is a faithful copy of what the harness wrote, so no verifier of the library could see it.

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

