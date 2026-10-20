# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.2.x | yes |
| 0.1.x | no |

## Reporting a vulnerability

Please report security issues **privately** through GitHub's private
vulnerability reporting, which is enabled for this repository:

<https://github.com/abderrahimebenmessahel/context-guard/security/advisories/new>

Use that form instead of a public issue.  Include a description, the affected
version and a reproduction if you have one.  You can expect an
acknowledgement within a few working days.

There is deliberately no public email address for security reports: the
private advisory channel is the only one that is monitored.

## Threat model

ContextGuard runs **untrusted model output** and, optionally, **commands you
choose to verify**.  The following properties are deliberate:

* **No `eval`, no `exec`, no unpickling, no `shell=True`.**  The
  `command_succeeds` verifier takes an argv *list* and runs it without a
  shell.  The command still runs with the privileges of the current user, so
  only verify commands you trust; prefer commands that only read.
  `command_succeeds` runs the process with a minimal environment (PATH, LANG,
  LC_ALL, HOME and TMPDIR only; on Windows the system variables are kept as
  well because CPython does not start without them) and a hard timeout.
* **Paths from the model are untrusted.**  Every path taken from telemetry is
  resolved inside the work directory.  Absolute paths, `..` components and
  symlinks that point outside are rejected.
* **Sizes are bounded.**  Model input above 1,000,000 characters is refused,
  exception excerpts are truncated to 500 characters, the event log and the
  attempt log are size bounded and the memory that is injected into a prompt
  is compacted.
* **The state file is trusted, the agent is not.**  `PROJECT_MEMORY.md` is
  meant to be edited by a human.  If a human breaks the JSON block, the
  library raises `StateCorruptionError` instead of silently resetting the
  project.

## Single process assumption

ContextGuard serialises its writers with an `asyncio.Lock` **inside one
process**.  There is no cross-process locking.  Two orchestrators must not
share a memory directory: give each one its own directory.  Running the same
memory directory from two processes can corrupt the state file.

## Out of scope

* Vulnerabilities in a provider SDK, a model or a user supplied verifier.
* Denial of service caused by the model provider itself.
* Anything that requires the library to trust a path outside the work
  directory.
