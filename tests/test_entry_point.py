"""Tests for the module entry point."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import agentether


def test_the_module_can_be_run() -> None:
    # The subprocess must use the package this test imported, not another
    # one that happens to be installed.  The path is derived from the
    # imported package, so the test also works in a copied tree (the
    # mutation testing copies the checkout before it mutates it).
    source_root = str(Path(agentether.__file__).resolve().parents[1])
    environment = dict(os.environ)
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = source_root if not existing else source_root + os.pathsep + existing
    result = subprocess.run(
        [sys.executable, "-m", "agentether", "--version"],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "0.3.0a1"
