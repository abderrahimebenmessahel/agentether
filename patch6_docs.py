"""One-off patch script: documentation updates for the security fixes."""

import pathlib

# ------------------------------------------------------------ verifiers.md ---
p = pathlib.Path("docs/verifiers.md")
t = p.read_text(encoding="utf-8")

old = """### `command_succeeds` and the security implications

```python
command_succeeds([sys.executable, "-m", "pytest", "-q"], timeout=60)
```

* The command is an **argv list**.  There is no `shell=True`, so no quoting,
  globbing or injection happens: `["echo", "$HOME"]` prints the literal
  string `$HOME`.
* The process gets a **minimal environment**: `PATH`, `LANG`, `LC_ALL`, `HOME`
  and `TMPDIR` only.
* The process is killed after the timeout.
* The output is truncated before it is stored as evidence.

**The command still runs with the privileges of the current user.**  Only
verify commands you trust, and prefer commands that only read.  Never build
an argv list out of model output."""
new = """### `command_succeeds` and the security implications

```python
command_succeeds([sys.executable, "-m", "pytest", "-q"], timeout=60)
```

* The command is an **argv list**.  There is no `shell=True`, so no quoting,
  globbing or injection happens: `["echo", "$HOME"]` prints the literal
  string `$HOME`.
* The process gets a **minimal environment**: `PATH`, `LANG`, `LC_ALL`, `HOME`
  and `TMPDIR` only.
* The process is killed after the timeout -- and **the whole process tree is
  killed**, not just the direct child.  On POSIX the command runs in its own
  session, so the entire process group is killed; on Windows `taskkill /T`
  kills the tree.  A background child cannot survive the timeout.
* The output is truncated before it is stored as evidence.

**The command still runs with the privileges of the current user.**  Only
verify commands you trust, and prefer commands that only read.  Never build
an argv list out of model output.

**The command must live outside the agent writable work directory.**  The
agent can write into the work directory, so an executable inside it could be
replaced by the agent and would then run with your privileges.  By default
`command_succeeds` rejects an `argv[0]` that resolves inside the work
directory:

```python
command_succeeds(["./run-tests.sh"], timeout=60)
# -> fails: "the executable './run-tests.sh' is inside the work directory;
#            verifier commands must live outside it"
```

Use an absolute path outside the work directory, or
`allow_workdir_executables=True` if the work directory really is not
writable by the agent."""
assert old in t
t = t.replace(old, new)

old = """* Every path that comes from the model is untrusted: absolute paths, `..`
  components and symlinks that point outside the work directory are rejected."""
new = """* Every path that comes from the model is untrusted: absolute paths, `..`
  components and symlinks that point outside the work directory are rejected.
* The **executable** of a verifier command is untrusted in the same way: by
  default it may not live inside the work directory."""
assert old in t
t = t.replace(old, new)
p.write_text(t, encoding="utf-8")

# ------------------------------------------------------------- SECURITY.md ---
p = pathlib.Path("SECURITY.md")
t = p.read_text(encoding="utf-8")

old = """* **No `eval`, no `exec`, no unpickling, no `shell=True`.**  The
  `command_succeeds` verifier takes an argv *list* and runs it without a
  shell.  The command still runs with the privileges of the current user, so
  only verify commands you trust; prefer commands that only read.
  `command_succeeds` runs the process with a minimal environment (PATH, LANG,
  LC_ALL, HOME and TMPDIR only) and a hard timeout."""
new = """* **No `eval`, no `exec`, no unpickling, no `shell=True`.**  The
  `command_succeeds` verifier takes an argv *list* and runs it without a
  shell.  The command still runs with the privileges of the current user, so
  only verify commands you trust; prefer commands that only read.
  `command_succeeds` runs the process with a minimal environment (PATH, LANG,
  LC_ALL, HOME and TMPDIR only) and a hard timeout.  On a timeout the
  **whole process tree** is killed (a new process group on POSIX, `taskkill /T`
  on Windows), so a background child cannot outlive the verifier.
* **Verifier commands must live outside the agent writable work directory.**
  The agent can write into the work directory, so an executable inside it
  could be replaced by the agent.  `command_succeeds` therefore rejects an
  `argv[0]` that resolves inside the work directory
  (`allow_workdir_executables=True` lifts the check).
* **The memory file cannot be hijacked by the model.**  Every string the
  model controls (the summary, the step name, the artifact paths, the
  failure reasons) is escaped when it is written, so it can never contain a
  literal `<!--` and therefore never a marker of the library.  The parser
  additionally takes the machine block from the *last* state marker and the
  human section from the region the library itself wrote."""
assert old in t
t = t.replace(old, new)
p.write_text(t, encoding="utf-8")

# ---------------------------------------------------------- architecture.md ---
p = pathlib.Path("docs/architecture.md")
t = p.read_text(encoding="utf-8")

old = """7. On success the step is persisted *before* the result is returned.  On
   failure the attempt is logged, a corrective hint is built and the step is
   retried after a full-jitter backoff.
8. When the attempts are exhausted the circuit breaker opens and is persisted,
   so the next process fails fast instead of looping again."""
new = """7. On success the step is persisted *before* the result is returned.  On
   failure the attempt is logged, a corrective hint is built and the step is
   retried after a full-jitter backoff.
8. When the attempts are exhausted the circuit breaker opens and is persisted,
   so the next process fails fast instead of looping again.

Two more rules apply to the whole run:

* **The budgets are global per project, not per process.**  The used
  attempts, tokens, cost and elapsed seconds are written to the state file
  with every attempt and restored when the orchestrator starts, so a run that
  was interrupted and started again continues to spend the same budget.
* **A step is executed by one caller at a time.**  There is one
  `asyncio.Lock` per step name: two concurrent calls to the same step are
  serialised, and the second one finds the cached result instead of running
  the agent a second time.  Different steps still run in parallel."""
assert old in t
t = t.replace(old, new)
p.write_text(t, encoding="utf-8")
print("docs patched")
