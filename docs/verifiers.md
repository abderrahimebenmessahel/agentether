# Verifier guide

A verifier checks what the agent *claimed*.  The agent says
`status: "completed"`; the verifier looks at the file, the JSON, the command
and decides whether the claim is true.

```python
from agentether import AutoOrchestrator, artifacts_exist, file_contains

orch = AutoOrchestrator(
    roadmap=["research"],
    memory_dir="./memory",
    timeout_seconds=60,
    max_retries=3,
    workdir="./work",  # every claimed path is resolved inside it
)


@orch.guard_step("research", verify=[file_contains("notes.md", "Sources"), artifacts_exist()])
async def research(ctx):
    return await my_llm(ctx.build_prompt("Research X"))
```

## The protocol

```python
class Verifier(Protocol):
    async def __call__(self, ctx: VerifyContext) -> VerifyResult: ...
```

`VerifyContext` carries the `step`, the `telemetry`, the `raw_output`, the
`memory_dir` and the `workdir`.  `VerifyResult` carries `ok`, a `reason` and
an `evidence` dictionary.

The rules:

* the verifiers of a step run **in order**, and **all** of them must pass;
* every verifier has its own timeout (`verify_timeout_seconds`, 30 seconds by
  default);
* an exception inside a verifier is a **failed verification**, never a crash
  of the run;
* a failed verification raises `VerificationFailedError` and is retried, with
  the reason injected into the next attempt as
  `"you reported completed but: <reason>"`;
* the result of the last verification of every step is persisted and
  summarised in `PROJECT_MEMORY.md`.

## The built-in verifiers

| Verifier | What it checks |
| --- | --- |
| `file_exists(path, non_empty=True)` | The file exists (and is not empty). |
| `file_contains(path, pattern)` | The file matches a regular expression. |
| `json_file_valid(path, required_keys=())` | The file is valid JSON (with the given top level keys). |
| `artifacts_exist()` | Every path in `telemetry.artifacts` exists. |
| `command_succeeds(argv, timeout=30, cwd=None)` | The command exits with 0. |
| `callable_verifier(fn)` | Your own function. |
| `llm_judge(judge_fn)` | Your own model based judge -- an interface only. |

### Path confinement

Every path that comes from the model is untrusted.  `artifacts_exist()` and
the file verifiers resolve the path inside `workdir` and reject:

* absolute paths (`/etc/passwd`, `C:\Windows\...`),
* the **executable** of a verifier command is untrusted in the same way: by
  default it may not live inside the work directory,
* paths with a `..` component,
* symlinks that point outside the work directory.

A rejected path is a **failed verification**, not an exception.

### `command_succeeds` and the security implications

```python
command_succeeds([sys.executable, "-m", "pytest", "-q"], timeout=60)
```

* The command is an **argv list**.  There is no `shell=True`, so no quoting,
  globbing or injection happens: `["echo", "$HOME"]` prints the literal
  string `$HOME`.
* The process gets a **minimal environment**: `PATH`, `LANG`, `LC_ALL`, `HOME`
  and `TMPDIR` only.  On Windows the system variables (`SYSTEMROOT`, `WINDIR`,
  `COMSPEC`, ...) are kept as well, because CPython does not start without
  them; none of them carries a secret.
* The process is killed after the timeout.
* The output is truncated before it is stored as evidence.

**The command still runs with the privileges of the current user.**  Only
verify commands you trust, and prefer commands that only read.  Never build
an argv list out of model output.

### `callable_verifier` and `llm_judge`

```python
def my_check(ctx: VerifyContext) -> bool:
    return (ctx.workdir / "report.md").exists()


verifier = callable_verifier(my_check)
```

The function may return a `VerifyResult`, a `bool` or a string (a non-empty
string is a failure reason).  It may be synchronous or asynchronous.  A
`llm_judge` is the same thing, with the intention that you ask a model
whether the answer is acceptable.

A judge is still a model: it can be wrong in the same ways the agent can be
wrong.  Never make a judge the only guard for something that matters.

## Writing your own verifier

A verifier should be **cheap, deterministic and about reality**.  "Does the
file exist", "does the JSON have the right keys", "does the build pass".

A verifier that asks the model "is this good?" is a judge, not a check, and
it inherits the unreliability of the model.

## The declarative expectations of a step

A verifier checks what the agent **claimed**.  An **expectation** checks
what the step **owes**.  The agent can claim to be done while it never
wrote half of the files the step asked for, and the existence check of the
claimed files passes: the claim is backed, the work is not complete.

```python
from agentether import AutoOrchestrator, Expectation

orch = AutoOrchestrator(
    roadmap=["write"],
    memory_dir="./memory",
    timeout_seconds=60,
    max_retries=3,
    workdir="./work",
)


@orch.guard_step(
    "write",
    expects=[
        "README.md",  # must exist, not empty
        Expectation("data.json", json_keys=("a", "b")),  # must be a JSON with a and b
        Expectation("build.py", python_valid=True),  # must compile
        Expectation("guide.md", markdown_headings=("## Install",)),
    ],
)
async def write(ctx):
    return await my_llm(ctx.build_prompt("Write the documentation"))
```

| Field | What it checks |
| --- | --- |
| `path` | The file exists (and is not empty when `non_empty` is true). |
| `contains` | The file matches every regular expression. |
| `json_keys` | The file is a JSON object with those keys. |
| `json_valid` | The file is valid JSON. |
| `python_valid` | The file compiles (it is never executed). |
| `markdown_headings` | The file has those headings. |

A plain string in the list is a shorthand for `Expectation(path)`.

**The rules.**

* The expectations are evaluated **after every attempt**, whatever the agent
  claimed.  A step cannot complete while a declared expectation is unmet.
* An unmet expectation is a **retryable** `VerificationFailedError`, and the
  corrective hint of the next attempt **names the missing files**.
* The paths are confined to the work directory: an absolute path, a `..`
  component and a symbolic link that leaves the directory are refused
  **when the step is declared** (a `ConfigurationError`).
* The expectations are checked **before** the verifiers of `verify=[...]`:
  a file that does not exist is the more actionable failure.

**What an expectation cannot do.**  It checks the **shape** of a file, not
its meaning.  A JSON file that parses may hold the wrong number, a Markdown
file that has its headings may say the wrong thing, and a Python file that
compiles may do the wrong thing.  For the meaning you need a judge
(`llm_judge`) or a check of your own (`callable_verifier`).  An expectation
is a floor, not a proof.

The full contract is in [`docs/spec/expectations-v1.md`](spec/expectations-v1.md).
