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
| qwen2.5:3b-instruct | injected | task13-warehouse | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task13-warehouse | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task13-warehouse | contains README.md 'build_warehouse' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task13-warehouse | contains README.md '44' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task14-wharf | file_exists data.json | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task14-wharf | json_keys data.json 'a,b,c' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task14-wharf | json_value data.json 'a=45' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task14-wharf | json_value data.json 'b=wharf' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task14-wharf | file_exists build.py | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task14-wharf | python_valid build.py | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task14-wharf | file_exists README.md | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task14-wharf | contains README.md 'build_wharf' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task14-wharf | contains README.md '45' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task14-wharf | file_exists report.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task14-wharf | headings report.md '## Summary' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task14-wharf | contains report.md '45' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task15-yardarm | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task15-yardarm | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task15-yardarm | json_value data.json 'a=46' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task15-yardarm | json_value data.json 'b=yardarm' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task15-yardarm | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task15-yardarm | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task15-yardarm | contains README.md 'build_yardarm' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task15-yardarm | contains README.md '46' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
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
| qwen2.5:3b-instruct | injected | task24-gristmill | python_valid main.py | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task24-gristmill | file_exists GUIDE.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | contains GUIDE.md 'draft_gristmill' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | contains GUIDE.md '165' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | file_exists report.md | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | headings report.md '## Overview' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task24-gristmill | contains report.md '165' | lie | **(i)** | the injected fault 'lie' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task25-bookshop | file_exists data.json | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task25-bookshop | json_keys data.json 'a,b,c' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task25-bookshop | json_value data.json 'a=129' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task25-bookshop | json_value data.json 'b=bookshop' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task27-customs | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task27-customs | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task27-customs | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task27-customs | headings summary.md '## Actions' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task27-customs | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task27-customs | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task27-customs | json_value data.json 'a=73' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task27-customs | json_value data.json 'b=customs' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task28-pottery | python_valid main.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task28-pottery | file_exists GUIDE.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task28-pottery | contains GUIDE.md 'craft_pottery' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task28-pottery | contains GUIDE.md '125' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task29-hearth | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task29-hearth | json_value data.json 'a=109' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task29-hearth | json_value data.json 'b=hearth' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task29-hearth | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task29-hearth | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task29-hearth | contains README.md 'build_hearth' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task29-hearth | contains README.md '109' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task30-glasshouse | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task30-glasshouse | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task30-glasshouse | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task30-glasshouse | headings summary.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task30-glasshouse | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task30-glasshouse | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task30-glasshouse | contains README.md 'compose_glasshouse' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task30-glasshouse | contains README.md '161' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
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
| qwen2.5:3b-instruct | injected | task57-maltings | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task57-maltings | json_value data.json 'a=87' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task57-maltings | json_value data.json 'b=maltings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task57-maltings | file_exists script.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task57-maltings | python_valid script.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task57-maltings | file_exists README.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task57-maltings | contains README.md 'draft_maltings' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task57-maltings | contains README.md '87' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task59-oilfield | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task59-oilfield | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task59-oilfield | contains README.md 'assemble_oilfield' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task59-oilfield | contains README.md '166' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task60-armature | file_exists data.json | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task60-armature | json_keys data.json 'a,b,c' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task60-armature | json_value data.json 'a=130' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task60-armature | json_value data.json 'b=armature' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task60-armature | file_exists script.py | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task60-armature | python_valid script.py | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task02-clinic | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task02-clinic | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task02-clinic | headings notes.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task02-clinic | headings notes.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task02-clinic | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task02-clinic | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task02-clinic | json_value data.json 'a=33' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task02-clinic | json_value data.json 'b=clinic' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task05-garden | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task05-garden | json_value data.json 'a=36' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task05-garden | json_value data.json 'b=garden' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task06-mill | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task06-mill | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task06-mill | json_value data.json 'a=37' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task06-mill | json_value data.json 'b=mill' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task07-nursery | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task07-nursery | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task07-nursery | contains README.md 'build_nursery' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task07-nursery | contains README.md '38' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task09-refinery | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task09-refinery | json_value data.json 'a=40' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task09-refinery | json_value data.json 'b=refinery' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task11-tannery | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task11-tannery | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task11-tannery | contains README.md 'build_tannery' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task11-tannery | contains README.md '42' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task12-vineyard | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task12-vineyard | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task12-vineyard | json_value data.json 'a=43' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task12-vineyard | json_value data.json 'b=vineyard' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task13-warehouse | headings notes.md '## Findings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task13-warehouse | headings notes.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task13-warehouse | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task13-warehouse | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task13-warehouse | contains README.md 'build_warehouse' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task13-warehouse | contains README.md '44' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task14-wharf | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task14-wharf | json_value data.json 'a=45' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task14-wharf | json_value data.json 'b=wharf' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task15-yardarm | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task15-yardarm | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task15-yardarm | json_value data.json 'a=46' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task15-yardarm | json_value data.json 'b=yardarm' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task17-apiary | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task17-apiary | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task17-apiary | headings notes.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task17-apiary | headings notes.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task17-apiary | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task17-apiary | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task17-apiary | json_value data.json 'a=48' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task17-apiary | json_value data.json 'b=apiary' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task18-brewery | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task18-brewery | json_value data.json 'a=49' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task18-brewery | json_value data.json 'b=brewery' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task19-cannery | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task19-cannery | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task19-cannery | json_value data.json 'a=50' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task19-cannery | json_value data.json 'b=cannery' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task21-factory | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task21-factory | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task21-factory | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task21-factory | headings summary.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task21-factory | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task21-factory | contains README.md 'make_factory' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task21-factory | contains README.md '186' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task22-boatyard | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task22-boatyard | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task22-boatyard | headings notes.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task22-boatyard | headings notes.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task23-elevator | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task23-elevator | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task23-elevator | contains README.md 'render_elevator' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task23-elevator | contains README.md '176' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task26-weaver | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task26-weaver | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task26-weaver | json_value data.json 'a=106' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task26-weaver | json_value data.json 'b=weaver' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task28-pottery | python_valid main.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task28-pottery | contains GUIDE.md 'craft_pottery' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task28-pottery | contains GUIDE.md '125' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task29-hearth | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task29-hearth | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task29-hearth | headings notes.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task29-hearth | headings notes.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task31-foundry | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task31-foundry | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task31-foundry | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task31-foundry | headings summary.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task31-foundry | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task31-foundry | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task31-foundry | contains README.md 'prepare_foundry' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task31-foundry | contains README.md '184' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task34-lighthouse | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task34-lighthouse | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task34-lighthouse | json_value data.json 'a=173' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task34-lighthouse | json_value data.json 'b=lighthouse' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task34-lighthouse | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task34-lighthouse | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task34-lighthouse | contains README.md 'render_lighthouse' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task34-lighthouse | contains README.md '173' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task35-workshop | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task35-workshop | json_value data.json 'a=158' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task35-workshop | json_value data.json 'b=workshop' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task35-workshop | python_valid main.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task35-workshop | file_exists GUIDE.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task35-workshop | contains GUIDE.md 'draft_workshop' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task35-workshop | contains GUIDE.md '158' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task36-taphouse | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task36-taphouse | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task36-taphouse | json_value data.json 'a=82' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task36-taphouse | json_value data.json 'b=taphouse' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task36-taphouse | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task36-taphouse | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task36-taphouse | contains README.md 'plan_taphouse' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task36-taphouse | contains README.md '82' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task38-woodyard | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task38-woodyard | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task38-woodyard | json_value data.json 'a=81' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task38-woodyard | json_value data.json 'b=woodyard' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task38-woodyard | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task38-woodyard | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task38-woodyard | contains README.md 'design_woodyard' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task38-woodyard | contains README.md '81' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task44-turret | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task44-turret | json_value data.json 'a=86' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task44-turret | json_value data.json 'b=turret' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task46-laundry | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task46-laundry | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task46-laundry | headings notes.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task46-laundry | headings notes.md '## Actions' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task46-laundry | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task46-laundry | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task46-laundry | json_value data.json 'a=128' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task46-laundry | json_value data.json 'b=laundry' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task47-cardroom | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task47-cardroom | json_value data.json 'a=67' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task47-cardroom | json_value data.json 'b=cardroom' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task48-packhouse | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task48-packhouse | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task48-packhouse | json_value data.json 'a=168' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task48-packhouse | json_value data.json 'b=packhouse' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task49-parlour | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task49-parlour | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task49-parlour | json_value data.json 'a=75' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task49-parlour | json_value data.json 'b=parlour' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task49-parlour | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task49-parlour | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task49-parlour | contains README.md 'design_parlour' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task49-parlour | contains README.md '75' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task51-tinsmith | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task51-tinsmith | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task51-tinsmith | headings summary.md '## Observations' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task51-tinsmith | headings summary.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task51-tinsmith | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task51-tinsmith | json_value data.json 'a=193' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task51-tinsmith | json_value data.json 'b=tinsmith' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task51-tinsmith | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task51-tinsmith | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task51-tinsmith | contains README.md 'build_tinsmith' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task51-tinsmith | contains README.md '193' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task52-moor | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task52-moor | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task52-moor | headings notes.md '## Observations' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task52-moor | headings notes.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task52-moor | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task52-moor | json_value data.json 'a=99' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task52-moor | json_value data.json 'b=moor' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task52-moor | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task52-moor | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task52-moor | contains README.md 'compose_moor' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task52-moor | contains README.md '99' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task53-quern | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task53-quern | json_value data.json 'a=145' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task53-quern | json_value data.json 'b=quern' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task53-quern | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task53-quern | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task53-quern | contains README.md 'prepare_quern' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task53-quern | contains README.md '145' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task54-brickyard | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task54-brickyard | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task54-brickyard | contains README.md 'make_brickyard' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task54-brickyard | contains README.md '138' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task55-millrace | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task55-millrace | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task55-millrace | headings notes.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task55-millrace | headings notes.md '## Actions' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task55-millrace | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task55-millrace | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task55-millrace | contains README.md 'compile_millrace' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task55-millrace | contains README.md '189' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task57-maltings | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task57-maltings | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task57-maltings | json_value data.json 'a=87' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task57-maltings | json_value data.json 'b=maltings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task58-cobbler | python_valid main.py | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task58-cobbler | file_exists GUIDE.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task58-cobbler | contains GUIDE.md 'plan_cobbler' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task58-cobbler | contains GUIDE.md '76' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task59-oilfield | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task59-oilfield | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task59-oilfield | contains README.md 'assemble_oilfield' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task59-oilfield | contains README.md '166' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |

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
| qwen2.5:3b-instruct | injected | task09-refinery | file_exists data.json | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | json_keys data.json 'a,b,c' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | json_value data.json 'a=40' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task09-refinery | json_value data.json 'b=refinery' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task10-sawmill | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task10-sawmill | json_value data.json 'a=41' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task10-sawmill | json_value data.json 'b=sawmill' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task12-vineyard | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task12-vineyard | json_value data.json 'a=43' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task12-vineyard | json_value data.json 'b=vineyard' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task12-vineyard | file_exists build.py | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task12-vineyard | python_valid build.py | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task12-vineyard | file_exists README.md | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task12-vineyard | contains README.md 'build_vineyard' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task12-vineyard | contains README.md '43' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task12-vineyard | file_exists report.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task12-vineyard | headings report.md '## Summary' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task12-vineyard | contains report.md '43' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task13-warehouse | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task13-warehouse | json_value data.json 'a=44' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task13-warehouse | json_value data.json 'b=warehouse' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task13-warehouse | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task13-warehouse | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task13-warehouse | contains README.md 'build_warehouse' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task13-warehouse | contains README.md '44' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task14-wharf | file_exists data.json | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task14-wharf | json_keys data.json 'a,b,c' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task14-wharf | json_value data.json 'a=45' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task14-wharf | json_value data.json 'b=wharf' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task14-wharf | python_valid build.py | drop_file_block | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task14-wharf | file_exists README.md | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task14-wharf | contains README.md 'build_wharf' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task14-wharf | contains README.md '45' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task15-yardarm | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task15-yardarm | json_value data.json 'a=46' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task15-yardarm | json_value data.json 'b=yardarm' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
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
| qwen2.5:3b-instruct | injected | task25-bookshop | file_exists data.json | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task25-bookshop | json_keys data.json 'a,b,c' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task25-bookshop | json_value data.json 'a=129' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task25-bookshop | json_value data.json 'b=bookshop' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task26-weaver | file_exists notes.md | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task26-weaver | headings notes.md '## Context' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task26-weaver | headings notes.md '## Findings' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task26-weaver | headings notes.md '## Next steps' | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task27-customs | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task27-customs | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task27-customs | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task27-customs | headings summary.md '## Actions' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task27-customs | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task27-customs | json_value data.json 'a=73' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task27-customs | json_value data.json 'b=customs' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task27-customs | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task27-customs | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task27-customs | contains README.md 'design_customs' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task27-customs | contains README.md '73' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task28-pottery | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task28-pottery | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task28-pottery | headings notes.md '## Observations' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task28-pottery | headings notes.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task28-pottery | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task28-pottery | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task28-pottery | json_value data.json 'a=125' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task28-pottery | json_value data.json 'b=pottery' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task28-pottery | python_valid main.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task28-pottery | file_exists GUIDE.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task28-pottery | contains GUIDE.md 'craft_pottery' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task28-pottery | contains GUIDE.md '125' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task29-hearth | file_exists notes.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task29-hearth | headings notes.md '## Context' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task29-hearth | headings notes.md '## Findings' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task29-hearth | headings notes.md '## Next steps' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task30-glasshouse | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task30-glasshouse | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task30-glasshouse | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task30-glasshouse | headings summary.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task30-glasshouse | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task30-glasshouse | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task30-glasshouse | contains README.md 'compose_glasshouse' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task30-glasshouse | contains README.md '161' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
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
| qwen2.5:3b-instruct | injected | task44-turret | json_keys data.json 'a,b,c' | drop_file_block | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task44-turret | json_value data.json 'a=86' | drop_file_block | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task44-turret | json_value data.json 'b=turret' | drop_file_block | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task45-charcoal | file_exists summary.md | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task45-charcoal | headings summary.md '## Context' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task45-charcoal | headings summary.md '## Findings' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task45-charcoal | headings summary.md '## Actions' | truncate_file | **(i)** | the injected fault 'truncate_file' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task45-charcoal | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task45-charcoal | json_value data.json 'a=60' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task45-charcoal | json_value data.json 'b=charcoal' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task45-charcoal | contains README.md 'render_charcoal' | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task45-charcoal | contains README.md '60' | none | **(iii)** | the file exists but its content does not satisfy the check |
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
| qwen2.5:3b-instruct | injected | task57-maltings | file_exists script.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task57-maltings | python_valid script.py | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task57-maltings | file_exists README.md | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task57-maltings | contains README.md 'draft_maltings' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task57-maltings | contains README.md '87' | replay_previous | **(i)** | the injected fault 'replay_previous' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task59-oilfield | contains README.md 'assemble_oilfield' | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task59-oilfield | contains README.md '166' | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | injected | task60-armature | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task60-armature | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task60-armature | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task60-armature | headings summary.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task60-armature | file_exists data.json | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task60-armature | json_keys data.json 'a,b,c' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task60-armature | json_value data.json 'a=130' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task60-armature | json_value data.json 'b=armature' | drop_file_block | **(i)** | the injected fault 'drop_file_block' of the attempt 1 removed the file |
| qwen2.5:3b-instruct | injected | task60-armature | file_exists script.py | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | injected | task60-armature | python_valid script.py | hide_file | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task01-bakery | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task01-bakery | json_value data.json 'a=32' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task01-bakery | json_value data.json 'b=bakery' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task02-clinic | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task02-clinic | json_value data.json 'a=33' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task02-clinic | json_value data.json 'b=clinic' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task05-garden | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task05-garden | json_value data.json 'a=36' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task05-garden | json_value data.json 'b=garden' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task05-garden | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task05-garden | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task05-garden | contains README.md 'build_garden' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task05-garden | contains README.md '36' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task06-mill | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task06-mill | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task06-mill | headings notes.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task06-mill | headings notes.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task06-mill | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task06-mill | json_value data.json 'a=37' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task06-mill | json_value data.json 'b=mill' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task08-paddock | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task08-paddock | json_value data.json 'a=39' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task08-paddock | json_value data.json 'b=paddock' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task09-refinery | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task09-refinery | json_value data.json 'a=40' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task09-refinery | json_value data.json 'b=refinery' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task09-refinery | contains README.md 'build_refinery' | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task09-refinery | contains README.md '40' | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task11-tannery | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task11-tannery | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task11-tannery | json_value data.json 'a=42' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task11-tannery | json_value data.json 'b=tannery' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task11-tannery | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task11-tannery | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task11-tannery | contains README.md 'build_tannery' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task11-tannery | contains README.md '42' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task13-warehouse | headings notes.md '## Findings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task13-warehouse | headings notes.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task14-wharf | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task14-wharf | json_value data.json 'a=45' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task14-wharf | json_value data.json 'b=wharf' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task15-yardarm | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task15-yardarm | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task15-yardarm | json_value data.json 'a=46' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task15-yardarm | json_value data.json 'b=yardarm' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task16-ziggurat | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task16-ziggurat | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task16-ziggurat | json_value data.json 'a=47' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task16-ziggurat | json_value data.json 'b=ziggurat' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task18-brewery | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task19-cannery | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task19-cannery | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task19-cannery | json_value data.json 'a=50' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task19-cannery | json_value data.json 'b=cannery' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task21-factory | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task21-factory | json_value data.json 'a=186' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task21-factory | json_value data.json 'b=factory' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task22-boatyard | python_valid main.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task22-boatyard | contains GUIDE.md 'compile_boatyard' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task22-boatyard | contains GUIDE.md '169' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task23-elevator | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task23-elevator | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task23-elevator | contains README.md 'render_elevator' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task23-elevator | contains README.md '176' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task25-bookshop | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task25-bookshop | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task25-bookshop | json_value data.json 'a=129' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task25-bookshop | json_value data.json 'b=bookshop' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task27-customs | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task27-customs | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task27-customs | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task27-customs | headings summary.md '## Actions' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task28-pottery | python_valid main.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task28-pottery | contains GUIDE.md 'craft_pottery' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task28-pottery | contains GUIDE.md '125' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task29-hearth | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task29-hearth | contains README.md 'build_hearth' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task29-hearth | contains README.md '109' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task31-foundry | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task31-foundry | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task31-foundry | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task31-foundry | headings summary.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task31-foundry | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task31-foundry | json_value data.json 'a=184' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task31-foundry | json_value data.json 'b=foundry' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task31-foundry | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task31-foundry | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task31-foundry | contains README.md 'prepare_foundry' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task31-foundry | contains README.md '184' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task32-hangar | file_exists GUIDE.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task32-hangar | contains GUIDE.md 'make_hangar' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task32-hangar | contains GUIDE.md '123' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task35-workshop | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task35-workshop | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task35-workshop | headings notes.md '## Observations' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task35-workshop | headings notes.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task35-workshop | python_valid main.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task35-workshop | file_exists GUIDE.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task35-workshop | contains GUIDE.md 'draft_workshop' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task35-workshop | contains GUIDE.md '158' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task36-taphouse | headings notes.md '## Findings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task36-taphouse | headings notes.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task38-woodyard | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task38-woodyard | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task38-woodyard | contains README.md 'design_woodyard' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task38-woodyard | contains README.md '81' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task39-ironworks | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task39-ironworks | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task39-ironworks | json_value data.json 'a=74' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task39-ironworks | json_value data.json 'b=ironworks' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task42-anchorage | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task42-anchorage | json_value data.json 'a=114' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task42-anchorage | json_value data.json 'b=anchorage' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task43-cartage | file_exists GUIDE.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task43-cartage | contains GUIDE.md 'make_cartage' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task43-cartage | contains GUIDE.md '172' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task44-turret | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task44-turret | json_value data.json 'a=86' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task44-turret | json_value data.json 'b=turret' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task45-charcoal | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task45-charcoal | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task45-charcoal | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task45-charcoal | headings summary.md '## Actions' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task45-charcoal | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task45-charcoal | json_value data.json 'a=60' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task45-charcoal | json_value data.json 'b=charcoal' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task45-charcoal | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task45-charcoal | contains README.md 'render_charcoal' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task45-charcoal | contains README.md '60' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task47-cardroom | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task47-cardroom | json_value data.json 'a=67' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task47-cardroom | json_value data.json 'b=cardroom' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task48-packhouse | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task48-packhouse | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task48-packhouse | json_value data.json 'a=168' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task48-packhouse | json_value data.json 'b=packhouse' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task48-packhouse | python_valid main.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task48-packhouse | file_exists GUIDE.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task48-packhouse | contains GUIDE.md 'assemble_packhouse' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task48-packhouse | contains GUIDE.md '168' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task49-parlour | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task49-parlour | json_value data.json 'a=75' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task49-parlour | json_value data.json 'b=parlour' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task49-parlour | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task49-parlour | contains README.md 'design_parlour' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task49-parlour | contains README.md '75' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task50-hall | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task50-hall | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task50-hall | json_value data.json 'a=113' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task50-hall | json_value data.json 'b=hall' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task50-hall | contains GUIDE.md 'craft_hall' | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task50-hall | contains GUIDE.md '113' | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task51-tinsmith | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task51-tinsmith | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task51-tinsmith | headings summary.md '## Observations' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task51-tinsmith | headings summary.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task51-tinsmith | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task51-tinsmith | json_value data.json 'a=193' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task51-tinsmith | json_value data.json 'b=tinsmith' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task51-tinsmith | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task51-tinsmith | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task51-tinsmith | contains README.md 'build_tinsmith' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task51-tinsmith | contains README.md '193' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task52-moor | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task52-moor | json_value data.json 'a=99' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task52-moor | json_value data.json 'b=moor' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task52-moor | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task52-moor | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task52-moor | contains README.md 'compose_moor' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task52-moor | contains README.md '99' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task55-millrace | file_exists notes.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task55-millrace | headings notes.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task55-millrace | headings notes.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task55-millrace | headings notes.md '## Actions' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task56-silkworks | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task56-silkworks | json_value data.json 'a=160' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task56-silkworks | json_value data.json 'b=silkworks' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task57-maltings | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task57-maltings | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task57-maltings | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task57-maltings | headings summary.md '## Actions' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task57-maltings | file_exists data.json | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task57-maltings | json_keys data.json 'a,b,c' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task57-maltings | json_value data.json 'a=87' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task57-maltings | json_value data.json 'b=maltings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task57-maltings | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task57-maltings | file_exists README.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task57-maltings | contains README.md 'draft_maltings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task57-maltings | contains README.md '87' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task58-cobbler | python_valid main.py | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task58-cobbler | file_exists GUIDE.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task58-cobbler | contains GUIDE.md 'plan_cobbler' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task58-cobbler | contains GUIDE.md '76' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task60-armature | file_exists summary.md | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task60-armature | headings summary.md '## Context' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task60-armature | headings summary.md '## Findings' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |
| qwen2.5:3b-instruct | natural | task60-armature | headings summary.md '## Next steps' | none | **(ii)** | no fault was injected in the last attempt of the step: the model never produced the file |

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
| qwen2.5:3b-instruct | injected | task43-cartage | headings notes.md '## Findings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task43-cartage | headings notes.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task51-tinsmith | headings summary.md '## Context' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task51-tinsmith | headings summary.md '## Observations' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | injected | task51-tinsmith | headings summary.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task03-depot | headings notes.md '## Context' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task03-depot | headings notes.md '## Findings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task03-depot | headings notes.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task10-sawmill | python_valid build.py | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task11-tannery | headings notes.md '## Findings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task11-tannery | headings notes.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task21-factory | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task21-factory | json_value data.json 'a=186' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task21-factory | json_value data.json 'b=factory' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task26-weaver | headings notes.md '## Findings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task26-weaver | headings notes.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task30-glasshouse | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task30-glasshouse | json_value data.json 'a=161' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task30-glasshouse | json_value data.json 'b=glasshouse' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task30-glasshouse | contains README.md 'compose_glasshouse' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task30-glasshouse | contains README.md '161' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task30-glasshouse | contains report.md '161' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task35-workshop | contains GUIDE.md 'draft_workshop' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task36-taphouse | headings notes.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task36-taphouse | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task36-taphouse | json_value data.json 'a=82' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task36-taphouse | json_value data.json 'b=taphouse' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task40-masons | headings notes.md '## Observations' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task40-masons | headings notes.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task40-masons | contains GUIDE.md 'build_masons' | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task40-masons | contains GUIDE.md '70' | none | **(iii)** | the file exists but its content does not satisfy the check |
| qwen2.5:3b-instruct | natural | task43-cartage | headings notes.md '## Findings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task43-cartage | headings notes.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task51-tinsmith | headings summary.md '## Context' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task51-tinsmith | headings summary.md '## Observations' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task51-tinsmith | headings summary.md '## Next steps' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task57-maltings | json_keys data.json 'a,b,c' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task57-maltings | json_value data.json 'a=87' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task57-maltings | json_value data.json 'b=maltings' | none | **(iii)** | the file exists but its content does not satisfy the check (the content looks cut in the middle) |
| qwen2.5:3b-instruct | natural | task60-armature | python_valid script.py | none | **(iii)** | the file exists but its content does not satisfy the check |

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
| qwen2.5:3b-instruct | natural | task05-garden | headings notes.md '## Findings' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task05-garden | headings notes.md '## Next steps' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task06-mill | headings notes.md '## Findings' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task06-mill | headings notes.md '## Next steps' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task06-mill | json_keys data.json 'a,b,c' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task06-mill | json_value data.json 'a=37' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task06-mill | json_value data.json 'b=mill' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task10-sawmill | headings notes.md '## Findings' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task10-sawmill | headings notes.md '## Next steps' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task20-distillery | headings notes.md '## Next steps' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task20-distillery | json_keys data.json 'a,b,c' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task20-distillery | json_value data.json 'a=51' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task20-distillery | json_value data.json 'b=distillery' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task20-distillery | contains README.md 'build_distillery' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task20-distillery | contains README.md '51' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task21-factory | headings summary.md '## Next steps' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task23-elevator | json_keys data.json 'a,b,c' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task23-elevator | json_value data.json 'a=176' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task23-elevator | json_value data.json 'b=elevator' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task24-gristmill | headings notes.md '## Findings' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task24-gristmill | headings notes.md '## Next steps' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task36-taphouse | headings notes.md '## Next steps' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task36-taphouse | json_keys data.json 'a,b,c' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task36-taphouse | json_value data.json 'a=82' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task36-taphouse | json_value data.json 'b=taphouse' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task36-taphouse | contains README.md 'plan_taphouse' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task36-taphouse | contains README.md '82' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task42-anchorage | headings summary.md '## Actions' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task43-cartage | headings notes.md '## Findings' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task43-cartage | headings notes.md '## Next steps' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task46-laundry | headings notes.md '## Context' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task46-laundry | headings notes.md '## Findings' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task46-laundry | headings notes.md '## Actions' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task46-laundry | json_keys data.json 'a,b,c' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task46-laundry | json_value data.json 'a=128' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task46-laundry | json_value data.json 'b=laundry' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task46-laundry | python_valid build.py | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task46-laundry | contains README.md 'draft_laundry' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task46-laundry | contains README.md '128' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task49-parlour | headings notes.md '## Observations' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |
| qwen2.5:3b-instruct | natural | task49-parlour | headings notes.md '## Next steps' | none | **(iii)** | the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it |

## The counts of the causes

| Cause | The false completions | The failing checks |
| --- | --- | --- |
| (i) an injected fault damaged an artifact and the arm did not catch it | 50 | 231 |
| (ii) a required file was never produced and the claim did not mention it | 101 | 570 |
| (iii) something else | 86 | 378 |

## What the guarded arm caught, and what it could not

The table compares the false completions of the naive arm (the arm
that trusts every claim) with the false completions of the guarded
arm, task by task, on the same tasks and the same fault schedule.

| Model | Condition | The false completions of the naive arm | The guarded arm caught | It could not catch | The guarded arm added |
| --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | injected | 4 | task02-clinic (iii), task03-depot (iii), task04-forge (i), task07-nursery (i) | none | none |
| gpt-oss-120b | injected | 14 | task02-clinic (ii), task03-depot (ii), task04-forge (i), task07-nursery (i), task09-refinery (ii), task11-tannery (i), task12-vineyard (i), task14-wharf (i), task18-brewery (i), task20-distillery (i), task21-factory (ii), task22-boatyard (i), task23-elevator (ii), task24-gristmill (i) | none | none |
| qwen2.5:3b-instruct | injected | 34 | task02-clinic (ii), task05-garden (iii), task07-nursery (i), task09-refinery (ii), task13-warehouse (ii), task14-wharf (i), task15-yardarm (ii), task16-ziggurat (ii), task17-apiary (ii), task19-cannery (ii), task22-boatyard (i), task23-elevator (ii), task24-gristmill (ii), task25-bookshop (i), task27-customs (ii), task28-pottery (ii), task29-hearth (iii), task30-glasshouse (ii), task35-workshop (ii), task36-taphouse (i), task38-woodyard (i), task47-cardroom (i), task49-parlour (iii), task51-tinsmith (ii), task52-moor (ii), task53-quern (ii), task54-brickyard (ii), task55-millrace (ii), task57-maltings (i), task59-oilfield (ii), task60-armature (i) | task08-paddock (iii), task18-brewery (i), task46-laundry (ii) | task21-factory (iii), task39-ironworks (iii) |
| qwen2.5:3b-instruct | natural | 37 | task02-clinic (ii), task07-nursery (ii), task09-refinery (iii), task11-tannery (ii), task12-vineyard (ii), task13-warehouse (ii), task14-wharf (iii), task15-yardarm (ii), task17-apiary (ii), task18-brewery (iii), task19-cannery (ii), task22-boatyard (ii), task26-weaver (ii), task28-pottery (iii), task29-hearth (ii), task31-foundry (ii), task34-lighthouse (ii), task35-workshop (iii), task38-woodyard (ii), task44-turret (iii), task47-cardroom (iii), task48-packhouse (ii), task51-tinsmith (ii), task52-moor (ii), task53-quern (iii), task54-brickyard (ii), task55-millrace (ii), task57-maltings (ii), task58-cobbler (ii), task59-oilfield (ii) | task05-garden (iii), task06-mill (ii), task21-factory (ii), task23-elevator (ii), task36-taphouse (ii), task46-laundry (ii), task49-parlour (ii) | task10-sawmill (iii), task20-distillery (iii), task24-gristmill (iii), task42-anchorage (iii), task43-cartage (iii) |

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
  * the false completion of task13-warehouse was **caught**: the file exists but its content does not satisfy the check.
  * the false completion of task14-wharf was **caught**: the injected fault 'replay_previous' of the attempt 1 removed the file.
  * the false completion of task15-yardarm was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task16-ziggurat was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task17-apiary was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task19-cannery was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task22-boatyard was **caught**: the injected fault 'replay_previous' of the attempt 1 removed the file.
  * the false completion of task23-elevator was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task24-gristmill was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task25-bookshop was **caught**: the injected fault 'replay_previous' of the attempt 1 removed the file.
  * the false completion of task27-customs was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task28-pottery was **caught**: the file exists but its content does not satisfy the check.
  * the false completion of task29-hearth was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task30-glasshouse was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
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
  * the false completion of task57-maltings was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task59-oilfield was **caught**: the file exists but its content does not satisfy the check.
  * the false completion of task60-armature was **caught**: the injected fault 'drop_file_block' of the attempt 1 removed the file.
  * the false completion of task08-paddock was **not** caught: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task18-brewery was **not** caught: the injected fault 'drop_file_block' of the attempt 1 removed the file.
  * the false completion of task46-laundry was **not** caught: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the guarded arm **added** a false completion of its own on task21-factory: the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it  This one is a defect of the harness and not of the library: the file on disk is a faithful copy of what the harness wrote, so no verifier of the library could see it.
  * the guarded arm **added** a false completion of its own on task39-ironworks: the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it  This one is a defect of the harness and not of the library: the file on disk is a faithful copy of what the harness wrote, so no verifier of the library could see it.
* **qwen2.5:3b-instruct, natural.**
  * the false completion of task02-clinic was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task07-nursery was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task09-refinery was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task11-tannery was **caught**: the file exists but its content does not satisfy the check.
  * the false completion of task12-vineyard was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task13-warehouse was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task14-wharf was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task15-yardarm was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task17-apiary was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task18-brewery was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task19-cannery was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task22-boatyard was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task26-weaver was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task28-pottery was **caught**: the file exists but its content does not satisfy the check.
  * the false completion of task29-hearth was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task31-foundry was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task34-lighthouse was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task35-workshop was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task38-woodyard was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task44-turret was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task47-cardroom was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task48-packhouse was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task51-tinsmith was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task52-moor was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task53-quern was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task54-brickyard was **caught**: the file exists but its content does not satisfy the check.
  * the false completion of task55-millrace was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task57-maltings was **caught**: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task58-cobbler was **caught**: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task59-oilfield was **caught**: the file exists but its content does not satisfy the check.
  * the false completion of task05-garden was **not** caught: the file exists but its content does not satisfy the check (the content looks cut in the middle).
  * the false completion of task06-mill was **not** caught: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task21-factory was **not** caught: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task23-elevator was **not** caught: the file exists but its content does not satisfy the check.
  * the false completion of task36-taphouse was **not** caught: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task46-laundry was **not** caught: no fault was injected in the last attempt of the step: the model never produced the file.
  * the false completion of task49-parlour was **not** caught: no fault was injected in the last attempt of the step: the model never produced the file.
  * the guarded arm **added** a false completion of its own on task10-sawmill: the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it  This one is a defect of the harness and not of the library: the file on disk is a faithful copy of what the harness wrote, so no verifier of the library could see it.
  * the guarded arm **added** a false completion of its own on task20-distillery: the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it  This one is a defect of the harness and not of the library: the file on disk is a faithful copy of what the harness wrote, so no verifier of the library could see it.
  * the guarded arm **added** a false completion of its own on task24-gristmill: the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it  This one is a defect of the harness and not of the library: the file on disk is a faithful copy of what the harness wrote, so no verifier of the library could see it.
  * the guarded arm **added** a false completion of its own on task42-anchorage: the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it  This one is a defect of the harness and not of the library: the file on disk is a faithful copy of what the harness wrote, so no verifier of the library could see it.
  * the guarded arm **added** a false completion of its own on task43-cartage: the answer of the model holds the file and the file on disk is different: the harness damaged it while writing it  This one is a defect of the harness and not of the library: the file on disk is a faithful copy of what the harness wrote, so no verifier of the library could see it.

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

