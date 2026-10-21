# The checklist of the release of `0.3.0a1`

> **Nothing of this list is done.**  The release of `0.3.0a1` is the
> decision of the maintainer: the repository is **private**, no tag was
> pushed and nothing was uploaded to PyPI.  This file says what would
> have to be done, and what was checked the day of the release.

## What is ready

| | Item | Where |
| --- | --- | --- |
| 1 | The version is `0.3.0a1` in the package, in `pyproject.toml` and in the CHANGELOG | `tests/test_version.py` fails when they diverge |
| 2 | The CHANGELOG entry of the release is written | `CHANGELOG.md`, the section `[0.3.0a1] - unreleased` |
| 3 | The tests pass on Windows and on Linux, on Python 3.10 to 3.14 | the CI has **ten** cells and a dependency audit |
| 4 | `mypy --strict` is clean | the CI and `run_linux_matrix.sh` |
| 5 | `ruff check` and `ruff format --check` are clean | the CI and `run_linux_matrix.sh` |
| 6 | The coverage of the package is measured | `pytest --cov=src/agentether` |
| 7 | The wheel and the sdist are built and `twine check` passes | `python -m build && python -m twine check dist/*` |
| 8 | The wheel works in a fresh venv, on Windows and on Linux | `packaging_check.py` and the venv of `~/wheel-check` |
| 9 | The tree, the history, the result files, the logs and the wheel hold **no** secret | `python scan_secrets.py` |
| 10 | The evidence of the trial is generated from the raw cells and checked by a test | `docs/evidence.md` and `tests/test_evidence_consistency.py` |

## What the maintainer has to decide

1. **Make the repository public?**  It is private today.  Nothing was
   published.
2. **Tag and release.**  The tag would be `0.3.0a1` (PEP 440, an alpha
   of the 0.3.0 series).  No tag was pushed.
3. **Publish on PyPI.**  The name `agentether` was checked and is free.
   **Use a test upload first** (`twine upload --repository testpypi
   dist/*`) and check the page: the long description of the project is
   a Markdown file and PyPI renders it, and a broken link or a broken
   table is visible forever.  The wheel and the sdist pass `twine
   check`.
4. **The WSL password.**  The brief of the session says it is `0`.  It
   should be changed, and it is not written anywhere in this repository.

## The commands of the release, in the order they would run

```bash
# 1. the gates, once more, on the commit that is released
PYTHONPATH=src python -m pytest -q --cov=src/agentether --cov-report=term-missing
python -m mypy --strict
python -m ruff check .
python -m ruff format --check .

# 2. the package
rm -rf dist
python -m build
python -m twine check dist/*

# 3. the wheel in a fresh venv
python packaging_check.py --wheel dist/agentether-0.3.0a1-py3-none-any.whl

# 4. the secrets
python scan_secrets.py

# 5. the tag and the release (THE DECISION OF THE MAINTAINER)
git tag -a 0.3.0a1 -m "0.3.0a1: the declarative expectations of a step"
git push origin 0.3.0a1
gh release create 0.3.0a1 dist/* --notes-file CHANGELOG.md

# 6. the publication on PyPI (THE DECISION OF THE MAINTAINER)
twine upload --repository testpypi dist/*   # the test first
twine upload dist/*

# 7. the tag of the release, in the repository
gh release edit 0.3.0a1 --notes-file CHANGELOG.md
```

## What must not happen

* **no money**: no credit is bought, no payment method is added, no key
  is rotated, and a provider that answers `HTTP 402` stops the run at
  once;
* **no secret in the repository**: the keys live in the environment of
  the machine and nowhere else;
* **nothing is published before the maintainer says so**.
