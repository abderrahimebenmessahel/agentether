"""Scan the repository for secrets.  Prints only counts and file names.

The script never prints a secret: it only reports where a pattern matched
and how many characters the match had.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

#: Patterns that look like a leaked key.
PATTERNS: dict[str, re.Pattern[str]] = {
    "openrouter_key": re.compile(r"sk-or-v1-[A-Za-z0-9]{16,}"),
    "openai_key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "anthropic_key": re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}"),
    "bearer_header": re.compile(r"Bearer\s+[A-Za-z0-9\-_\.]{20,}"),
    "generic_assignment": re.compile(
        r"(?i)(api[_-]?key|secret|token|password)\s*[=:]\s*[\"'][^\"'\s]{16,}[\"']"
    ),
}

#: The files that are allowed to contain a fake key (the tests).
ALLOWED = {
    "tests/test_openrouter.py",
}


def scan_text(text: str) -> list[tuple[str, int]]:
    """Return the patterns that match and the length of every match."""
    hits: list[tuple[str, int]] = []
    for name, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            hits.append((name, len(match.group(0))))
    return hits


def main() -> int:
    """Scan the working tree and the git history."""
    root = Path(".")
    print("=== working tree ===")
    problems = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix in {".pyc", ".png", ".jpg", ".zip"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        hits = scan_text(text)
        if hits:
            relative = path.as_posix()
            if relative in ALLOWED:
                print(f"  {relative}: {len(hits)} match(es) -- the fake key of a test")
                continue
            problems += len(hits)
            print(f"  {relative}: {[(name, length) for name, length in hits]}")
    print(f"problems in the working tree: {problems}")

    print("=== git history ===")
    log = subprocess.run(
        ["git", "log", "--all", "-p", "--no-color"],
        capture_output=True,
        text=True,
        check=False,
    )
    history_hits = scan_text(log.stdout)
    print(f"matches in the git history: {len(history_hits)}")
    for name, length in history_hits[:10]:
        print(f"  {name} (length {length})")

    print("=== the environment ===")
    for name, value in os.environ.items():
        if name.lower() in ("minimax", "minimax_api_key", "openrouter_api_key"):
            print(f"  {name}: present, length {len(value)} (never printed)")

    return 1 if problems or history_hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
