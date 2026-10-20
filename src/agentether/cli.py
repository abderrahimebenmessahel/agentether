"""The ``agentether`` command line interface.

Standard library only (``argparse``).  Every command accepts ``--json`` for
machine readable output and returns a process exit code:

* ``0`` -- everything is fine;
* ``1`` -- the command found a problem (for example a corrupted memory file);
* ``2`` -- the command line itself was wrong (argparse uses this too).

.. versionadded:: 0.2.0
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

from .benchmark import BenchmarkResult, run_benchmark
from .exceptions import AgenTetherError
from .state_manager import (
    MEMORY_FILENAME,
    SCHEMA_VERSION,
    STATE_MARKER,
    StateManager,
    sha256_text,
)
from .verifier import PathNotAllowedError, resolve_within

__all__ = ["build_parser", "main"]

EXIT_OK = 0
EXIT_PROBLEM = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser of the ``agentether`` command."""
    parser = argparse.ArgumentParser(
        prog="agentether",
        description="Inspect and repair a AgenTether project memory.",
    )
    parser.add_argument("--version", action="store_true", help="print the version and exit")
    sub = parser.add_subparsers(dest="command")

    status = sub.add_parser("status", help="show the progress of a project")
    status.add_argument("memory_dir", help="the project memory directory")
    status.add_argument("--json", action="store_true", help="machine readable output")

    reset = sub.add_parser("reset-breaker", help="close an open circuit breaker")
    reset.add_argument("memory_dir", help="the project memory directory")
    reset.add_argument("--json", action="store_true", help="machine readable output")

    doctor = sub.add_parser("doctor", help="check the project memory for problems")
    doctor.add_argument("memory_dir", help="the project memory directory")
    doctor.add_argument("--json", action="store_true", help="machine readable output")

    verify = sub.add_parser("verify", help="re-check the recorded artifacts")
    verify.add_argument("memory_dir", help="the project memory directory")
    verify.add_argument(
        "--workdir",
        default=None,
        help="the directory the artifacts are relative to (default: current directory)",
    )
    verify.add_argument("--json", action="store_true", help="machine readable output")

    benchmark = sub.add_parser(
        "benchmark",
        help="run the simulated benchmark (SIMULATED, not a real world measurement)",
    )
    benchmark.add_argument("--trials", type=int, default=100, help="number of trials")
    benchmark.add_argument("--seed", type=int, default=0, help="random seed")
    benchmark.add_argument("--json", action="store_true", help="machine readable output")
    benchmark.add_argument(
        "--output",
        default=None,
        help="write the JSON result to this file as well",
    )
    return parser


def _load_state(memory_dir: Path) -> dict[str, Any]:
    """Load the state of a project (async helper, run by the caller)."""

    async def _run() -> dict[str, Any]:
        manager = StateManager(memory_dir)
        return await manager.load()

    return asyncio.run(_run())


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def cmd_status(args: argparse.Namespace) -> int:
    """Show the roadmap progress, the breaker state and the last error."""
    memory_dir = Path(args.memory_dir)
    try:
        state = _load_state(memory_dir)
    except AgenTetherError as exc:
        if args.json:
            _print_json({"ok": False, "error": str(exc)})
        else:
            print(f"error: {exc}", file=sys.stderr)
        return EXIT_PROBLEM

    roadmap = list(state.get("roadmap", []))
    completed = list(state.get("completed_steps", []))
    breaker = dict(state.get("breaker") or {})
    failure = state.get("last_failure")
    payload = {
        "ok": True,
        "memory_dir": str(memory_dir),
        "schema_version": state.get("schema_version"),
        "roadmap": roadmap,
        "completed_steps": completed,
        "progress": {
            "done": len(completed),
            "total": len(roadmap),
        },
        "breaker": {
            "open": bool(breaker.get("open")),
            "step": breaker.get("step"),
            "attempts": breaker.get("attempts"),
            "reason": breaker.get("reason"),
            "last_error": breaker.get("last_error"),
            "opened_at": breaker.get("opened_at"),
        },
        "last_failure": failure,
        "needs_human": state.get("needs_human", {}),
        "updated_at": state.get("updated_at"),
    }
    if args.json:
        _print_json(payload)
        return EXIT_OK

    print(f"project: {memory_dir}")
    print(f"schema version: {payload['schema_version']} (this build understands {SCHEMA_VERSION})")
    if roadmap:
        print("roadmap:")
        for name in roadmap:
            mark = "x" if name in completed else " "
            print(f"  [{mark}] {name}")
    else:
        print("roadmap: (not recorded)")
    print(f"progress: {len(completed)}/{len(roadmap)} steps completed")
    print(f"breaker: {'OPEN' if breaker.get('open') else 'closed'}")
    if breaker.get("open"):
        print(f"  step: {breaker.get('step')}")
        print(f"  attempts: {breaker.get('attempts')}")
        print(f"  reason: {breaker.get('reason')}")
        print(f"  last error: {breaker.get('last_error')}")
    if failure:
        print(
            f"last failure: {failure.get('step')} ({failure.get('status')}): "
            f"{failure.get('reason')}"
        )
    needs_human = state.get("needs_human") or {}
    if needs_human:
        print("waiting for human input:")
        for name, reason in needs_human.items():
            print(f"  {name}: {reason}")
    return EXIT_OK


def cmd_reset_breaker(args: argparse.Namespace) -> int:
    """Close an open circuit breaker."""

    async def _run() -> None:
        manager = StateManager(Path(args.memory_dir))
        await manager.set_breaker(False, "")

    try:
        asyncio.run(_run())
    except AgenTetherError as exc:
        if args.json:
            _print_json({"ok": False, "error": str(exc)})
        else:
            print(f"error: {exc}", file=sys.stderr)
        return EXIT_PROBLEM
    if args.json:
        _print_json({"ok": True, "breaker": "closed"})
    else:
        print("circuit breaker closed")
    return EXIT_OK


def cmd_doctor(args: argparse.Namespace) -> int:
    """Check the project memory and report actionable problems."""
    memory_dir = Path(args.memory_dir)
    problems: list[str] = []
    notes: list[str] = []

    # The stale files are collected first: loading the state creates a
    # StateManager, which prunes the stale temporary files itself.
    stale = _stale_tmp_files(memory_dir)
    if stale:
        notes.append(
            f"{len(stale)} stale .tmp file(s) older than one hour: "
            + ", ".join(path.name for path in stale)
        )

    memory_path = memory_dir / MEMORY_FILENAME
    if not memory_path.exists():
        problems.append(f"{memory_path} does not exist")
    else:
        try:
            text = memory_path.read_text(encoding="utf-8")
        except OSError as exc:
            problems.append(f"could not read {memory_path}: {exc}")
            text = ""
        if text:
            if STATE_MARKER not in text:
                problems.append(f"{memory_path} does not contain the state marker {STATE_MARKER!r}")
            has_start = "<!-- agentether:human:start -->" in text or (
                "<!-- contextguard:human:start -->" in text
            )
            has_end = "<!-- agentether:human:end -->" in text or (
                "<!-- contextguard:human:end -->" in text
            )
            if not has_start:
                notes.append(
                    "the file has no human section markers; AgenTether will add them "
                    "on the next write"
                )
            elif not has_end:
                problems.append(
                    "the human section start marker is present but the end marker is "
                    "missing; the file was edited by hand"
                )
            try:
                state = _load_state(memory_dir)
            except AgenTetherError as exc:
                problems.append(str(exc))
            else:
                version = state.get("schema_version")
                if version != SCHEMA_VERSION:
                    problems.append(
                        f"schema version {version} differs from {SCHEMA_VERSION}; "
                        "AgenTether migrates it automatically on the next run"
                    )

    payload = {
        "ok": not problems,
        "memory_dir": str(memory_dir),
        "problems": problems,
        "notes": notes,
    }
    if args.json:
        _print_json(payload)
    else:
        for problem in problems:
            print(f"problem: {problem}")
        for note in notes:
            print(f"note: {note}")
        if not problems:
            print("no problems found")
    return EXIT_PROBLEM if problems else EXIT_OK


def _stale_tmp_files(memory_dir: Path) -> list[Path]:
    """Return the ``*.tmp`` files older than one hour."""
    cutoff = time.time() - 3600
    found: list[Path] = []
    try:
        entries = list(memory_dir.glob("*.tmp"))
    except OSError:
        return found
    for entry in entries:
        try:
            if entry.is_file() and entry.stat().st_mtime < cutoff:
                found.append(entry)
        except OSError:
            continue
    return found


def cmd_verify(args: argparse.Namespace) -> int:
    """Re-check the recorded artifacts and the recorded output hashes."""
    memory_dir = Path(args.memory_dir)
    workdir = Path(args.workdir).resolve() if args.workdir else Path.cwd()
    try:
        state = _load_state(memory_dir)
    except AgenTetherError as exc:
        if args.json:
            _print_json({"ok": False, "error": str(exc)})
        else:
            print(f"error: {exc}", file=sys.stderr)
        return EXIT_PROBLEM

    telemetry = state.get("telemetry", {})
    step_files = state.get("step_files", {})
    checks: list[dict[str, Any]] = []
    problems: list[str] = []

    for step, record in sorted(telemetry.items()):
        artifacts = list((record or {}).get("artifacts") or [])
        missing: list[str] = []
        rejected: list[str] = []
        for artifact in artifacts:
            try:
                resolved = resolve_within(workdir, artifact)
            except PathNotAllowedError:
                rejected.append(artifact)
                continue
            if not resolved.exists():
                missing.append(artifact)
        relative = step_files.get(step)
        hash_ok: bool | None = None
        if isinstance(relative, str) and relative:
            path = memory_dir / relative
            if path.exists():
                expected = sha256_text(path.read_text(encoding="utf-8", errors="replace"))
                hash_ok = True
                if not expected:
                    hash_ok = False
        entry = {
            "step": step,
            "artifacts": artifacts,
            "missing": missing,
            "rejected": rejected,
            "output_hash_checked": hash_ok is not None,
        }
        checks.append(entry)
        if missing:
            problems.append(f"step '{step}': missing artifacts: {', '.join(missing)}")
        if rejected:
            problems.append(f"step '{step}': artifact paths are not allowed: {', '.join(rejected)}")

    payload = {
        "ok": not problems,
        "memory_dir": str(memory_dir),
        "checks": checks,
        "problems": problems,
    }
    if args.json:
        _print_json(payload)
    else:
        for check in checks:
            status = "ok" if not check["missing"] and not check["rejected"] else "problem"
            print(f"{check['step']}: {status} ({len(check['artifacts'])} artifact(s))")
        for problem in problems:
            print(f"problem: {problem}")
        if not problems:
            print("all recorded artifacts exist")
    return EXIT_PROBLEM if problems else EXIT_OK


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Run the simulated benchmark."""
    result: BenchmarkResult = run_benchmark(trials=args.trials, seed=args.seed)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if args.json:
        _print_json(result.to_dict())
    else:
        print(result.to_markdown())
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Entry point of the ``agentether`` command.

    Args:
        argv: The argument vector.  ``None`` means ``sys.argv[1:]``.

    Returns:
        The process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "version", False):
        from . import __version__

        print(__version__)
        return EXIT_OK
    if not args.command:
        parser.print_help()
        return EXIT_USAGE

    handlers = {
        "status": cmd_status,
        "reset-breaker": cmd_reset_breaker,
        "doctor": cmd_doctor,
        "verify": cmd_verify,
        "benchmark": cmd_benchmark,
    }
    handler = handlers[args.command]
    try:
        return handler(args)
    except AgenTetherError as exc:
        if getattr(args, "json", False):
            _print_json({"ok": False, "error": str(exc)})
        else:
            print(f"error: {exc}", file=sys.stderr)
        return EXIT_PROBLEM


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
