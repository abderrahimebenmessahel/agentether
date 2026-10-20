# Contributing

Thanks for your interest.  AgenTether is small on purpose; most changes are
welcome as long as they keep the core **standard library only** and Python
3.10+.

## Getting set up

```bash
git clone <your fork>
cd AgenTether
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## The checks that must pass

```bash
pytest --cov=src/agentether --cov-report=term-missing
ruff check .
ruff format --check .
mypy .
```

All four are run in CI for Python 3.10 to 3.13 on Linux and Windows.

## Guidelines

* **Keep the core dependency free.**  Provider SDKs belong in
  `agentether.adapters` behind an optional extra, and they must be imported
  lazily.
* **Type everything.**  The project runs `mypy --strict`; `type: ignore` needs
  a comment explaining why.
* **Never trust model output.**  Paths from the model are untrusted: resolve
  them inside the work directory, reject absolute paths and `..`, and bound
  every size.
* **Test offline.**  No test may reach the network or sleep for real.  Use the
  injected clock and sleep functions.
* **Be honest in the docs.**  Do not claim real world effectiveness.  The
  benchmark is simulated and must be labelled as such everywhere.

## Reporting bugs

Open an issue with the smallest reproduction you can manage: the roadmap, the
worker function, what you expected and what happened.  A failing test is the
best reproduction.

## Releasing

1. Update the version in `pyproject.toml` and `agentether/__init__.py`.
2. Add a `CHANGELOG.md` entry.
3. Check that the PyPI name is still available and free.
4. `python -m build && twine upload dist/*`.
