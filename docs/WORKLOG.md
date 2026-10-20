# Worklog

A dated, external memory of the work.  It is committed, so that a session
that starts from nothing knows where the previous one stopped.

The repository is **AgenTether** (the import package `agentether`, the CLI
`agentether`, the distribution `agentether`).  The checkout is still called
`ContextGuard` on disk; that is the folder name, not the project name.

## 2026-10-20 — session 1: the maintainer's brief

The maintainer handed over a five phase brief.  The state of the tree when
this session started:

- `git log --oneline -20` ends at `cdd38c7 docs: record the mutation testing
  honestly`.  The working tree is clean, the branch is `main`, the remote is
  private.
- `docs/WORKLOG.md` did not exist; this file is it.
- `pyproject.toml` and `src/agentether/__init__.py` say **0.2.0** while
  `CHANGELOG.md` has an unreleased **0.3.0-alpha** entry.  The version
  mismatch is real and is Phase 1(a).
- `docs/evidence.md` says "Wall clock: 0 s" and the token totals are 0.  The
  result file `benchmarks/results/trial-20261020-partial.json` carries
  `wall_seconds: 0` and `input_tokens: 0 / output_tokens: 0` next to
  `requests: 291`.  Phase 1(b).
- The **simple-retry arm scored worse than the naive arm** in the first real
  trial (0.100 against 0.400, natural condition).  A broken baseline
  invalidates every comparison, so this is Phase 1(c) and it blocks Phase 4.
- The mutation run left ~174 survivors in `orchestrator.py` and
  `state_manager.py` untriaged.  Phase 1(d).

### What the trial data already shows (read from the committed result file)

`benchmarks/results/trial-20261020-partial.json`, natural condition, N = 10
tasks per cell, one model (`minimax/minimax-m3.1-flash:free`):

| task | naive | simple-retry | agentether |
| --- | --- | --- | --- |
| task01-harbour | correct (3 calls) | **wrong (5 calls)** | correct (6 calls) |
| task02-orchard | wrong (4) | wrong (7) | wrong (2) |
| task03-lantern | correct (3) | correct (3) | wrong (3) |
| task04-meridian | wrong (4) | wrong (9) | wrong (3) |
| task05-quarry | wrong (3) | wrong (8) | wrong (3) |
| task06-beacon | wrong (4) | wrong (8) | wrong (3) |
| task07-trellis | correct (3) | **wrong (6)** | wrong (3) |
| task08-compass | correct (4) | **wrong (8)** | correct (7) |
| task09-ferry | wrong (3) | wrong (5) | wrong (8) |
| task10-almanac | wrong (4) | wrong (6) | correct (9) |

The naive arm calls once per step (35 calls for 35 steps).  The simple-retry
arm calls 65 times for the same 35 steps: it retries 30 extra times and
still ends up wrong on seven tasks.  **A retry that makes things worse is a
bug in the arm, not a property of the model** — and the two arms do not even
treat the files of an answer the same way (see Phase 1(c)).

### Keys present in the environment (existence and length only, never the value)

`MINIMAX` (73, the OpenRouter key), `GROQ_API_KEY` (56), `GEMINI_API_KEY`
(53), `CEREBRAS_API_KEY` (52), `MISTRAL_API_KEY` (45).  `OPENROUTER_API_KEY`
and `ANTHROPIC_API_KEY` are absent.  The Windows variables are in the *user*
scope, so a child process needs them passed explicitly.

### Phase 1(a) — the version is now `0.3.0a1` everywhere

- `pyproject.toml`, `src/agentether/__init__.py` and the CHANGELOG heading
  now say `0.3.0a1` (PEP 440).  The `.. versionadded::` markers of the
  unreleased features follow, the `0.2.0` markers of the released features
  stay.
- The rename had mangled the comment that explains the name (it said the
  name "agentether" was taken and that the distribution was published as
  "agentether").  It now states the truth: `contextguard` is taken, so the
  distribution is `agentether`.
- The same rename had mangled the 0.2.0 entry of the CHANGELOG; it now
  describes what 0.2.0 actually was.
- `tests/test_version.py` is new: it compares the package, `pyproject.toml`,
  the CHANGELOG heading and the installed distribution, and it fails when they
  diverge.  It found a real problem on its first run: an orphan
  `src/agentether.egg-info` (a leftover of an earlier editable install, git
  ignored) still advertised `0.2.0`.  It was removed; the packaging step
  regenerates it.
- The version assertions of `tests/test_cli.py` and
  `tests/test_entry_point.py` now compare against `agentether.__version__`
  instead of repeating a literal.

Gate after this change: **325 passed, 4 skipped** (Windows, CPython 3.14.7),
`mypy --strict` clean on 53 files, `ruff check` clean, `ruff format --check`
clean on 81 files.

### NEXT ACTION

Phase 1(b): the token and elapsed-time accounting of the trial runner, and
the regeneration of `docs/evidence.md` from the raw JSON.

