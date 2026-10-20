"""Tests for the module entry point."""

from __future__ import annotations

import subprocess
import sys


def test_the_module_can_be_run() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "agentether", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "0.2.0"
