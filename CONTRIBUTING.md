# Contributing

AgenTether is small on purpose.  Most changes are welcome as long as they
keep the core **standard library only** and Python 3.10+.

## Getting set up

```bash
git clone https://github.com/abderrahimebenmessahel/agentether.git
cd agentether
python -m venv .venv && . .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## The checks that must pass

```bash
pytest --cov=src/agentether --cov-report=term-missing
ruff check .
ruff format --check .
mypy .
```

All four run in CI for Python 3.10 to 3.14 on Linux and Windows.

## Running the tests on Windows and on Linux

The test suite is offline and deterministic: no network, no real model, and
no test waits for real time (the clock and the backoff sleep are injectable).
The same commands work everywhere:

```bash
pytest                                  # Windows
pytest -q --cov=src/agentether          # Linux
```

The test that is **skipped on Windows** is the one that needs POSIX
features: the symlink escape test needs symlink privileges.  The process
group kill test runs on both platforms (POSIX uses `os.killpg`, Windows uses
`taskkill /T`).

## How to add a verifier

1. Write an async function that takes a `VerifyContext` and returns a
   `VerifyResult`:

   ```python
   async def my_check(ctx: VerifyContext) -> VerifyResult:
       path = ctx.workdir / "report.md"
       if not path.exists():
           return VerifyResult.failure("report.md is missing")
       return VerifyResult.success(size=path.stat().st_size)
   ```

2. Add it to `src/agentether/verifier.py` and export it from
   `src/agentether/__init__.py`.
3. Add a test in `tests/test_verifier.py`.
4. Write down the security notes: what the check reads, what it executes (if
   anything) and what it trusts.

A verifier must never execute model output, and every path it uses must be
resolved inside the work directory (use `resolve_within`).

## How to reproduce the evidence

The evidence in `docs/evidence.md` comes from two different things:

* **The simulated benchmark** -- deterministic, no network:

  ```bash
  python -m agentether benchmark --trials 1000 --seed 0
  ```

  The result must be identical on every platform.  If it is not, the
  determinism is broken.

* **The real model trial** -- a real model through OpenRouter.  The protocol
  is pre-registered in `docs/trial-protocol.md`; the runner is
  `benchmarks/trial.py`:

  ```bash
  export MINIMAX=...                    # the key, from the environment only
  python benchmarks/trial.py --tasks 10 --rate-limit 30 --model-cap 400
  python benchmarks/evidence.py --progress <workdir>/progress.jsonl --out docs/evidence.md
  ```

  The runner is **resumable**: it writes one JSON line per call, so a run
  that hits a daily limit continues with the same command.  The free tier of
  OpenRouter allows only a limited number of free requests per day, so a
  full run takes more than one day; report the N that was actually achieved.

  **If you change a prompt, change it for every arm** and record it in the
  "Changes after the first run" section of the protocol.

## The rules of the project

* **Never trust the model.**  A path from the model is resolved inside the
  work directory; a claim is checked, not believed.
* **Never `eval`, never `exec`, never unpickle, never `shell=True`.**
* **Never silently swallow an error.**  A failure of the state file is a
  `StateCorruptionError` with a message that says what to do.
* **Bound every size**: the model output, the memory, the event log, the
  attempt log.
* **Keep the human's section of the memory file byte for byte.**
* **Be honest in the documentation.**  A benchmark is a simulation unless it
  really called a model, and the two are never mixed in one number.

## Reporting a bug

Open an issue with the smallest reproduction you can manage: the roadmap, the
worker function, what you expected and what happened.  A failing test is the
best reproduction.
