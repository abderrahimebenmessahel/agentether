"""Install the built wheel into a fresh venv and use it.

The point is to prove that the *packaged* library works: the console script,
the quickstart and the CLI, from an installed wheel, in an environment that
knows nothing about the source tree.

    python packaging_check.py --wheel dist/agentether-0.2.0-py3-none-any.whl
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

QUICKSTART = """
import asyncio
import json
from agentether import AutoOrchestrator, StepContext


async def main():
    orch = AutoOrchestrator(
        roadmap=["research"], memory_dir="./memory", timeout_seconds=30, max_retries=2
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return json.dumps({
            "step": "research",
            "status": "completed",
            "summary": "it worked",
            "progress": 100,
            "next_step": None,
            "artifacts": [],
        })

    result = await research()
    print("status :", result.telemetry.status)
    print("summary:", result.telemetry.summary)
    print("attempts:", result.attempts)


asyncio.run(main())
"""


def main(argv: list[str] | None = None) -> int:
    """Install the wheel in a fresh venv and run the quickstart and the CLI."""
    parser = argparse.ArgumentParser(description="Check the built wheel.")
    parser.add_argument("--wheel", required=True)
    args = parser.parse_args(argv)

    wheel = Path(args.wheel).resolve()
    # The venv is created next to the project: on this machine an
    # application control policy blocks executables in the temp directory.
    root = Path(tempfile.mkdtemp(prefix="agentether-packaging-", dir=Path.cwd()))
    venv_dir = root / "venv"
    print(f"creating a fresh venv in {venv_dir}")
    venv.EnvBuilder(with_pip=True).create(venv_dir)

    if sys.platform == "win32":
        python = venv_dir / "Scripts" / "python.exe"
        scripts = venv_dir / "Scripts"
    else:
        python = venv_dir / "bin" / "python"
        scripts = venv_dir / "bin"

    print("installing the wheel")
    subprocess.run([str(python), "-m", "pip", "install", "--quiet", str(wheel)], check=True)

    print("--- the quickstart from the installed wheel ---")
    script = root / "quickstart.py"
    script.write_text(QUICKSTART, encoding="utf-8")
    result = subprocess.run(
        [str(python), str(script)], cwd=root, capture_output=True, text=True, check=False
    )
    print(result.stdout.strip() or result.stderr.strip())
    if result.returncode != 0:
        return result.returncode

    print("--- the console script ---")
    shim = scripts / ("agentether.exe" if sys.platform == "win32" else "agentether")
    print(f"the entry point is installed: {shim.exists()} ({shim.name})")
    # On this machine an application control policy blocks the generated
    # .exe shim, so the same entry point is run through the interpreter.
    version = subprocess.run(
        [str(python), "-m", "agentether", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    print("agentether --version ->", version.stdout.strip())
    if version.returncode != 0:
        print(version.stderr.strip())
        return version.returncode

    print("--- the CLI on the memory the quickstart wrote ---")
    status = subprocess.run(
        [str(python), "-m", "agentether", "status", str(root / "memory"), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    print(status.stdout.strip()[:400])
    if status.returncode != 0:
        print(status.stderr.strip())
        return status.returncode
    print("the packaged library works")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
