#!/usr/bin/env bash
# Run the full check suite for one Python version inside WSL.
# Usage: AGENTETHER_SRC=<path of the checkout> bash run_linux_matrix.sh 3.10
# The virtual environments live outside the source tree so that the linters
# never see them.
#
# The tree is synced from the Windows checkout first: the tests must not
# run from /mnt/c, which is slow and has the wrong permissions.
set -uo pipefail
export PATH="$HOME/.local/bin:$PATH"
# The checkout of the project, as WSL sees it.  The path is read from the
# environment: the path of the machine of the maintainer is not a property
# of the project.
if [ -z "${AGENTETHER_SRC:-}" ]; then
  echo "AGENTETHER_SRC is not set." >&2
  echo "It must be the path of the checkout of the project, as WSL sees it," >&2
  echo "for example: AGENTETHER_SRC=/mnt/c/path/to/the/checkout" >&2
  exit 2
fi
SOURCE="$AGENTETHER_SRC"
TARGET="$HOME/agentether-linux"
PY="$1"
VENV="$HOME/venvs/cg${PY/./}"
mkdir -p "$HOME/venvs"
echo "################ Python ${PY} ################"
echo "--- syncing the tree ---"
mkdir -p "$TARGET"
rm -rf "$TARGET/src" "$TARGET/tests" "$TARGET/benchmarks" "$TARGET/docs" "$TARGET/examples"
cp -r "$SOURCE/src" "$SOURCE/tests" "$SOURCE/benchmarks" "$SOURCE/docs" "$SOURCE/examples" "$TARGET/"
cp "$SOURCE/pyproject.toml" "$SOURCE/CHANGELOG.md" "$SOURCE/README.md" "$TARGET/"
cp "$SOURCE/scan_secrets.py" "$SOURCE/packaging_check.py" "$SOURCE/mutation_triage.py" "$TARGET/"
cp "$SOURCE/.gitattributes" "$SOURCE/run_linux_matrix.sh" "$TARGET/"
# The copy comes from a Windows checkout: the line endings are normalized
# here, because ruff format --check expects the endings of the platform.
find "$TARGET" \( -name "*.py" -o -name "*.md" -o -name "*.toml" -o -name "*.sh" \)   -print | while read -r file; do
  sed -i 's/$//' "$file"
done
cd "$TARGET" || exit 1
if [ ! -d "$VENV" ]; then
  uv venv --python "$PY" "$VENV" 2>&1 | tail -1
fi
# The install is refreshed every time: the version of the metadata of an
# editable install follows the version of pyproject.toml, and the tests
# compare it with the version of the source.
uv pip install --python "$VENV/bin/python" -q -e ".[dev]" 2>&1 | tail -2
"$VENV/bin/python" -V
echo "--- pytest ---"
"$VENV/bin/python" -m pytest -q --cov=src/agentether --cov-report=term 2>&1 | tail -4
echo "--- mypy --strict ---"
"$VENV/bin/python" -m mypy --strict 2>&1 | tail -3
echo "--- ruff check ---"
"$VENV/bin/python" -m ruff check . 2>&1 | tail -2
echo "--- ruff format --check ---"
"$VENV/bin/python" -m ruff format --check . 2>&1 | tail -2
