"""The version must be the same everywhere.

The first alpha of the 0.3.0 series was published as ``0.2.0`` in the wheel
and in ``--version`` while the CHANGELOG already announced ``0.3.0-alpha``.
Nothing caught it, because nothing compared the places.  These tests do.

The version is written once, in ``pyproject.toml``, and mirrored in
``src/agentether/__init__.py``.  The CHANGELOG heading and the distribution
metadata are checked against those two.
"""

from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version
from pathlib import Path

import pytest

from agentether import __version__

#: The version of this release.  Bumping it means bumping this constant and
#: the CHANGELOG heading; the other tests make sure nothing else drifts.
EXPECTED_VERSION = "0.3.0a1"

#: The root of the checkout (the directory that holds ``pyproject.toml``).
ROOT = Path(__file__).resolve().parents[1]


def _pyproject_version(text: str) -> str:
    """Read ``version`` from the ``[project]`` table of ``pyproject.toml``.

    A hand written reader is used instead of :mod:`tomllib` because
    ``tomllib`` only exists from Python 3.11 and the project supports 3.10.
    """
    in_project = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_project = stripped == "[project]"
            continue
        if in_project and stripped.startswith("version"):
            match = re.search(r'"([^"]+)"', stripped)
            if match is not None:
                return match.group(1)
    raise AssertionError("pyproject.toml has no version in its [project] table")


def _changelog_heading(text: str) -> str:
    """Read the version of the first (most recent) CHANGELOG section."""
    match = re.search(r"^##\s+\[([^\]]+)\]", text, re.MULTILINE)
    if match is None:
        raise AssertionError("CHANGELOG.md has no '## [version]' section")
    return match.group(1)


def test_the_declared_version_is_the_expected_one() -> None:
    assert __version__ == EXPECTED_VERSION


def test_the_package_and_the_project_file_agree() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert _pyproject_version(text) == __version__


def test_the_changelog_agrees_with_the_package() -> None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert _changelog_heading(text) == __version__


def test_the_installed_distribution_agrees_with_the_package() -> None:
    """The installed metadata must carry the same version.

    The test is skipped when the package is not installed (a plain source
    checkout), because there is then no metadata to compare.
    """
    try:
        installed = distribution_version("agentether")
    except PackageNotFoundError:
        pytest.skip("the package is not installed in this environment")
    assert installed == __version__


def test_no_other_version_is_mentioned_in_the_guides() -> None:
    """The prose must not announce a version of its own.

    Only the unreleased section of the CHANGELOG may name the current
    version; the older sections name the versions that really existed.
    """
    forbidden = {"0.3.0-alpha", "0.3.0-alpha.1", "v0.3.0-alpha"}
    for name in ("README.md", "docs/architecture.md", "docs/evidence.md"):
        path = ROOT / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for wrong in forbidden:
            assert wrong not in text, f"{name} still mentions {wrong}"
