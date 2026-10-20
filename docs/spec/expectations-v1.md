# The declarative expectations of a step (draft)

> **Status: draft.**  This document describes the contract that AgenTether
> enforces when a step declares what it must produce.  It is written so that
> another implementation could interoperate with AgenTether: the same
> declaration, the same semantics.  It is not a standard and it is not
> stable yet.

Version: 1.0 (draft) -- applies to AgenTether 0.3.0a1.

## The problem

A verifier checks what the agent **claimed**.  The agent says
`status: "completed"` and lists the files it produced; `artifacts_exist()`
checks that those files exist.  Two things can go wrong and neither is
caught:

1. the agent **did not produce** a file the step asked for, and simply did
   not list it -- the verifier has nothing to compare against;
2. the agent **produced a damaged file** -- a file that exists but whose
   content is cut in the middle -- and the existence check passes.

The analysis of the false completions of the trial v2
(`docs/false-completions.md`) found both: the guarded arm caught the false
completions whose artifact was **missing** and could not catch the ones
whose artifact was **damaged but present**.

## The declaration

A step declares what it must produce:

```python
from agentether import AutoOrchestrator, Expectation

orch = AutoOrchestrator(roadmap=["write"], memory_dir="./memory", timeout_seconds=60, max_retries=3)


@orch.guard_step(
    "write",
    expects=[
        "README.md",  # must exist, not empty
        Expectation("data.json", json_keys=("a", "b")),  # must be a JSON with a and b
        Expectation("build.py", python_valid=True, contains=("def build",)),
        Expectation("docs/guide.md", markdown_headings=("## Install",)),
    ],
)
async def write(ctx):
    return await my_llm(ctx.build_prompt("Write the documentation"))
```

A plain string is a shorthand for `Expectation(path)`: the file must exist
and must not be empty.

## The fields of an expectation

| Field | Type | Meaning |
| --- | --- | --- |
| `path` | string | The path of the file, relative to the work directory. |
| `contains` | tuple of strings | The regular expressions the file must contain. |
| `json_keys` | tuple of strings | The keys the file must have when it is a JSON object. |
| `json_valid` | bool | Whether the file must be valid JSON. |
| `python_valid` | bool | Whether the file must compile (it is never executed). |
| `markdown_headings` | tuple of strings | The headings the file must have. |
| `non_empty` | bool | Whether the file must have a size greater than zero. |

The checks of the content are the verifiers of `agentether.verifier`
(`file_contains`, `json_file_valid`, `python_syntax_valid`,
`markdown_has_headings`); the expectation only says which ones apply to
which file.

## The confinement of the paths

* an absolute path is refused;
* a path with a `..` component is refused;
* a path that leaves the work directory through a symbolic link is refused;
* a path is refused **when the step is declared**, not only when it runs: a
  path that is not allowed is a programming error and must be found at once.

The refusal is a `ConfigurationError`.

## The semantics

1. The expectations of a step are evaluated **after every attempt**,
   whatever the agent claimed.
2. A step **cannot complete** while a declared expectation is unmet.  When
   the agent claims `completed` and an expectation is unmet, the attempt
   fails with a `VerificationFailedError` (retryable by default) and the
   step is retried.
3. When the agent does **not** claim to be done, the step fails for its own
   reason (`in_progress`, `blocked`, `failed`) and the expectations only
   add to the corrective hint.
4. The reason of the failure names the **missing** files and the files
   whose content does not satisfy the declaration:

   ```text
   the step must produce these files: data.json; the content of these
   files does not satisfy the declaration: build.py (is not valid Python)
   ```

5. The corrective hint of the next attempt names the missing files:

   ```text
   the step did not produce what it declared: the step must produce these
   files: data.json; write the missing files (or fix them) and only then
   report the step as done. The missing files are: data.json
   ```

6. The expectations are checked **before** the verifiers of `verify=[...]`:
   a file that does not exist is the more actionable failure.
7. The result of the check is persisted in the project memory and in the
   claims ledger, like the result of any other verification.

## What an expectation cannot do

An expectation checks the **shape** of a file, not its meaning:

* a JSON file that parses may hold the wrong number;
* a Markdown file that has its headings may say the wrong thing;
* a Python file that compiles may do the wrong thing;
* a file that exists may be the file of another step.

A semantic check needs a judge (`agentether.verifier.llm_judge`) or a check
of your own (`callable_verifier`).  An expectation is a **floor**, not a
proof, and the documentation of the library says so where it is used.

## The relation to the verifiers

| | The verifiers of `verify=[...]` | The expectations of `expects=[...]` |
| --- | --- | --- |
| What they check | the claim of the agent | the contract of the step |
| What they know | the files the agent listed | the files the step declared |
| When they run | when the agent claims `completed` | after every attempt |
| Who writes them | you, with the helpers of the library | you, with the helpers of the library |

The two are complementary: the verifiers catch a claim that is not backed by
reality, the expectations catch a step that did not produce what it owes.
