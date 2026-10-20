"""Independent verification of what the agent claims.

The agent reports ``status: "completed"``.  That is a *claim*.  A verifier
checks the claim against reality: does the file exist, does the JSON parse,
does the command succeed, did the artifacts actually appear?

Every path that comes out of the model is untrusted.  Paths are resolved
inside ``workdir`` only: absolute paths, ``..`` components and symlinks that
point outside the work directory are rejected.

.. warning::
   ``command_succeeds`` runs a subprocess.  It never uses ``shell=True`` and
   only accepts an argv *list*, but the command itself still runs with your
   user's privileges.  Only verify commands you trust.

.. versionadded:: 0.2.0
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import os
import re
import shutil
import signal
import subprocess
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import Any

from .models import Verifier, VerifyContext, VerifyResult

__all__ = [
    "artifacts_exist",
    "callable_verifier",
    "command_succeeds",
    "file_contains",
    "file_exists",
    "json_file_valid",
    "llm_judge",
    "resolve_within",
]


class PathNotAllowedError(ValueError):
    """Raised when a path is not allowed to be used.

    Absolute paths, ``..`` components and symlinks that escape the base
    directory are rejected.
    """


def resolve_within(base: Path, candidate: str) -> Path:
    """Resolve ``candidate`` inside ``base``.

    Args:
        base: The directory the result must stay inside.
        candidate: The untrusted path.

    Returns:
        The resolved, confined path.

    Raises:
        PathNotAllowedError: If the path is empty, absolute, contains a
            ``..`` component, or resolves (through symlinks) outside ``base``.
    """
    if not candidate or not candidate.strip():
        raise PathNotAllowedError("empty path")
    raw = Path(candidate)
    if raw.is_absolute() or raw.drive or raw.root:
        raise PathNotAllowedError(f"absolute paths are not allowed: {candidate!r}")
    if ".." in raw.parts:
        raise PathNotAllowedError(f"'..' is not allowed in paths: {candidate!r}")
    base_resolved = base.resolve()
    resolved = (base_resolved / raw).resolve()
    if not resolved.is_relative_to(base_resolved):
        raise PathNotAllowedError(f"path escapes the working directory: {candidate!r}")
    return resolved


def _verifier_error(reason: str, **evidence: Any) -> VerifyResult:
    return VerifyResult(ok=False, reason=reason, evidence=dict(evidence))


def executable_is_inside_workdir(executable: str, workdir: Path) -> bool:
    """Return whether the executable resolves inside the work directory.

    A path with a separator is resolved relative to the work directory, a
    bare name is looked up in ``PATH``.  Either way, the result is compared
    with the work directory itself (symlinks resolved).
    """
    base = workdir.resolve()
    if os.sep in executable or (os.altsep and os.altsep in executable):
        candidate = (base / executable).resolve()
        return candidate.is_relative_to(base)
    found = shutil.which(executable)
    if found is None:
        return False
    try:
        resolved = Path(found).resolve()
    except OSError:  # pragma: no cover - unreadable path
        return False
    return resolved.is_relative_to(base)


#: The variables that are kept on Windows.  CPython cannot start without
#: them ("_HashRandomization_Init: failed to get random numbers"), and none
#: of them carries a secret.
_WINDOWS_ENVIRONMENT = (
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "TEMP",
    "TMP",
    "NUMBER_OF_PROCESSORS",
    "PROCESSOR_ARCHITECTURE",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "ProgramData",
)


def _child_environment(base: Path) -> dict[str, str]:
    """The environment a verifier command runs with.

    It is deliberately small: only the variables a command needs to find its
    tools and to write temporary files.  On Windows the system variables are
    kept as well, because CPython does not even start without them.
    """
    env = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "HOME": str(base),
        "TMPDIR": str(base),
    }
    if os.name == "nt":
        for name in _WINDOWS_ENVIRONMENT:
            value = os.environ.get(name)
            if value:
                env[name] = value
    return env


def kill_process_tree(process: asyncio.subprocess.Process) -> None:
    """Kill a verifier command *and every process it started*.

    On POSIX the command runs in its own session, so the whole process group
    is killed.  On Windows ``taskkill /T`` kills the process tree.  Killing
    only the direct child would leave its children running.
    """
    pid = process.pid
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                check=False,
                capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError:  # pragma: no cover - taskkill is missing
            with contextlib.suppress(OSError):
                pass
    else:
        # ``os.killpg`` and friends only exist on POSIX; they are looked up
        # dynamically so that the module type checks on every platform.
        killpg = getattr(os, "killpg", None)
        getpgid = getattr(os, "getpgid", None)
        sigkill = getattr(signal, "SIGKILL", None)
        if killpg is not None and getpgid is not None and sigkill is not None:
            with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
                killpg(getpgid(pid), sigkill)
    with contextlib.suppress(ProcessLookupError, OSError):  # already gone
        process.kill()


def file_exists(path: str, *, non_empty: bool = True) -> Verifier:
    """Verify that a file exists (and is not empty).

    Args:
        path: Path relative to the work directory.
        non_empty: When true the file must have a size greater than zero.

    Returns:
        A verifier that fails with a readable reason.
    """

    async def verify(ctx: VerifyContext) -> VerifyResult:
        try:
            resolved = resolve_within(ctx.workdir, path)
        except PathNotAllowedError as exc:
            return _verifier_error(str(exc), path=path)
        if not resolved.exists():
            return _verifier_error(f"expected file does not exist: {path}", path=path)
        if not resolved.is_file():
            return _verifier_error(f"expected path is not a file: {path}", path=path)
        size = resolved.stat().st_size
        if non_empty and size == 0:
            return _verifier_error(f"file is empty: {path}", path=path, size=size)
        return VerifyResult.success(path=path, size=size)

    return verify


def file_contains(path: str, pattern: str) -> Verifier:
    """Verify that a file contains ``pattern`` (a regular expression).

    Args:
        path: Path relative to the work directory.
        pattern: Regular expression that must match somewhere in the file.

    Returns:
        A verifier that fails with a readable reason.
    """

    async def verify(ctx: VerifyContext) -> VerifyResult:
        try:
            resolved = resolve_within(ctx.workdir, path)
        except PathNotAllowedError as exc:
            return _verifier_error(str(exc), path=path)
        if not resolved.is_file():
            return _verifier_error(f"expected file does not exist: {path}", path=path)
        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return _verifier_error(f"could not read {path}: {exc}", path=path)
        if not re.search(pattern, content):
            return _verifier_error(
                f"file {path} does not contain {pattern!r}", path=path, pattern=pattern
            )
        return VerifyResult.success(path=path, pattern=pattern)

    return verify


def json_file_valid(path: str, required_keys: Sequence[str] = ()) -> Verifier:
    """Verify that a file contains valid JSON (with optional required keys).

    Args:
        path: Path relative to the work directory.
        required_keys: Keys that must be present in the top level object.

    Returns:
        A verifier that fails with a readable reason.
    """

    async def verify(ctx: VerifyContext) -> VerifyResult:
        try:
            resolved = resolve_within(ctx.workdir, path)
        except PathNotAllowedError as exc:
            return _verifier_error(str(exc), path=path)
        if not resolved.is_file():
            return _verifier_error(f"expected file does not exist: {path}", path=path)
        try:
            data = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return _verifier_error(f"{path} is not valid JSON: {exc}", path=path)
        missing = [key for key in required_keys if not isinstance(data, dict) or key not in data]
        if missing:
            return _verifier_error(
                f"{path} is missing required keys: {', '.join(missing)}",
                path=path,
                missing=missing,
            )
        return VerifyResult.success(path=path, keys=sorted(required_keys))

    return verify


def artifacts_exist() -> Verifier:
    """Verify that every artifact the agent listed really exists.

    Paths are resolved inside the work directory.  Absolute paths, ``..``
    components and escaping symlinks are rejected -- a model must not be able
    to claim a file outside of its sandbox.
    """

    async def verify(ctx: VerifyContext) -> VerifyResult:
        artifacts = list(ctx.telemetry.artifacts)
        if not artifacts:
            return _verifier_error("the agent did not list any artifact to verify")
        missing: list[str] = []
        rejected: list[str] = []
        checked: list[str] = []
        for artifact in artifacts:
            try:
                resolved = resolve_within(ctx.workdir, artifact)
            except PathNotAllowedError:
                rejected.append(artifact)
                continue
            checked.append(artifact)
            if not resolved.exists():
                missing.append(artifact)
        if rejected:
            return _verifier_error(
                f"artifact paths are not allowed: {', '.join(rejected)}",
                rejected=rejected,
                missing=missing,
            )
        if missing:
            return _verifier_error(
                f"claimed artifacts do not exist: {', '.join(missing)}",
                missing=missing,
                checked=checked,
            )
        return VerifyResult.success(checked=checked)

    return verify


def command_succeeds(
    argv: Sequence[str],
    timeout: float = 30.0,
    cwd: str | None = None,
    max_output_chars: int = 2000,
    allow_workdir_executables: bool = False,
) -> Verifier:
    """Verify that a command exits successfully.

    The command is executed with ``argv`` as a list -- **never** through a
    shell, so no quoting, globbing or injection happens.  The process runs
    with a minimal environment and a hard timeout; on timeout the **whole
    process tree** is killed (the command runs in its own process group on
    POSIX, ``taskkill /T`` on Windows), so a background child cannot survive
    the timeout.

    .. warning::
       The command runs with the privileges of the current user.  Only verify
       commands that you trust, and prefer commands that only read.

    .. warning::
       The command must live **outside** the agent writable work directory.
       Otherwise the agent could replace the executable and run code of its
       own choosing.  By default an ``argv[0]`` that resolves inside the
       work directory is rejected; set ``allow_workdir_executables=True`` to
       lift that check (only sensible when the work directory is not
       writable by the agent).

    Args:
        argv: The command and its arguments, as a list.
        timeout: Hard timeout in seconds.
        cwd: Working directory relative to the work directory.
        max_output_chars: How much of the output is kept as evidence.
        allow_workdir_executables: Allow an executable inside the work
            directory.

    Returns:
        A verifier that fails with a readable reason.
    """
    command = [str(part) for part in argv]

    async def verify(ctx: VerifyContext) -> VerifyResult:
        if not command:
            return _verifier_error("no command given")
        base = ctx.workdir
        if cwd is not None:
            try:
                base = resolve_within(ctx.workdir, cwd)
            except PathNotAllowedError as exc:
                return _verifier_error(str(exc), cwd=cwd)
        if not allow_workdir_executables and executable_is_inside_workdir(command[0], ctx.workdir):
            return _verifier_error(
                f"the executable {command[0]!r} is inside the work directory; "
                "verifier commands must live outside it",
                argv=command,
            )
        env = _child_environment(base)
        spawn_kwargs: dict[str, Any] = {}
        if os.name == "nt":
            spawn_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            # A new session makes the child a process group leader, so the
            # whole group can be killed on a timeout.
            spawn_kwargs["start_new_session"] = True
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(base),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **spawn_kwargs,
            )
        except (OSError, ValueError) as exc:
            return _verifier_error(f"could not run {command[0]!r}: {exc}", argv=command)
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
        except asyncio.TimeoutError:
            kill_process_tree(process)
            await process.wait()
            return _verifier_error(
                f"command timed out after {timeout}s: {' '.join(command)}",
                argv=command,
                timeout=timeout,
            )
        out = stdout.decode("utf-8", errors="replace")[:max_output_chars]
        err = stderr.decode("utf-8", errors="replace")[:max_output_chars]
        if process.returncode != 0:
            return _verifier_error(
                f"command failed with exit code {process.returncode}: {' '.join(command)}",
                argv=command,
                returncode=process.returncode,
                stdout=out,
                stderr=err,
            )
        return VerifyResult.success(
            argv=command, returncode=process.returncode, stdout=out, stderr=err
        )

    return verify


def callable_verifier(
    fn: Callable[[VerifyContext], Any] | Callable[[VerifyContext], Awaitable[Any]],
) -> Verifier:
    """Adapt a user supplied function into a :class:`Verifier`.

    The function receives the :class:`VerifyContext` and may return:

    * a :class:`VerifyResult` -- used as is;
    * ``True`` / ``False`` -- the boolean is the verdict;
    * a string -- a non-empty string is a failure reason, an empty string
      means success.

    Synchronous and asynchronous functions are both supported.  Exceptions
    raised inside the function are turned into a failed verification.

    Args:
        fn: The user function.

    Returns:
        A verifier.
    """

    async def verify(ctx: VerifyContext) -> VerifyResult:
        try:
            outcome = fn(ctx)
            if inspect.isawaitable(outcome):
                outcome = await outcome
        except Exception as exc:
            return _verifier_error(f"verifier raised {type(exc).__name__}: {exc}")
        return _coerce_verdict(outcome)

    return verify


def llm_judge(
    judge_fn: Callable[[VerifyContext], Any] | Callable[[VerifyContext], Awaitable[Any]],
) -> Verifier:
    """Interface for a model based judge.

    **Interface only.**  AgenTether ships no provider code in the core
    package: you pass a callable that asks your own model whether the answer
    is acceptable.  The callable follows the same contract as
    :func:`callable_verifier` and may be synchronous or asynchronous.

    .. warning::
       A judge is still a model.  It can be wrong in the same ways the agent
       can be wrong, and it must never be the only guard for anything that
       matters.

    Args:
        judge_fn: The user supplied judge.

    Returns:
        A verifier.
    """
    return callable_verifier(judge_fn)


def _coerce_verdict(outcome: Any) -> VerifyResult:
    """Turn the many shapes a user function may return into a VerifyResult."""
    if isinstance(outcome, VerifyResult):
        return outcome
    if isinstance(outcome, bool):
        if outcome:
            return VerifyResult.success()
        return _verifier_error("verifier returned False")
    if isinstance(outcome, str):
        if outcome.strip():
            return _verifier_error(outcome)
        return VerifyResult.success()
    if outcome is None:
        return VerifyResult.success()
    return _verifier_error(f"unsupported verifier result: {outcome!r}")
