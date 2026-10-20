# Telemetry contract (draft)

> **Status: draft.**  This document describes the contract that AgenTether
> enforces.  It is written so that another implementation could interoperate
> with AgenTether: the same telemetry, the same file layout, the same
> semantics.  It is not a standard and it is not stable yet.

Version: 1.0 (draft) -- applies to AgenTether 0.3.0a1.

## The object

The answer of a worker must end with a single JSON object:

```json
{
  "step": "research",
  "status": "completed",
  "summary": "Found three sources.",
  "progress": 100,
  "next_step": "write",
  "artifacts": ["notes/research.md"]
}
```

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `step` | string | yes | The roadmap step that was performed.  Must equal the step that was requested. |
| `status` | string | yes | One of `in_progress`, `completed`, `blocked`, `failed`. |
| `summary` | string | yes | One short paragraph: what was done and what was found. |
| `progress` | number (0-100) or null | no | How far the step is. |
| `next_step` | string or null | no | The next roadmap step; `null` on the last step. |
| `artifacts` | list of strings | no | The relative paths that were produced. |

Unknown fields are ignored, so the contract may grow.

## The extraction

1. A fenced code block whose first line is `FILE: <path>` holds the content
   of a file; the harness writes it into the sandbox (path confined, size
   capped).
2. The telemetry object is the **last** JSON object in the answer.  A fenced
   ```json block is preferred; otherwise every `{` is offered to
   `json.JSONDecoder().raw_decode`, and a candidate that starts inside an
   already decoded object is discarded.
3. The candidate that carries `step` and `status` wins; if no candidate has
   them, the last dictionary is used.
4. Trailing commas are invalid JSON and are **not** repaired.
5. A response above 1,000,000 characters is refused before any parsing.

## The status semantics

| Status | What the supervisor does |
| --- | --- |
| `completed` | The verifiers run, the step is persisted, the result is returned. |
| `in_progress` | The attempt failed; the step is retried with the hint "step not completed, continue". |
| `blocked` | The reason is persisted and a "Needs human input" entry is written; the step is **not** retried until the human section changes. |
| `failed` | The reason is persisted and raised as an `AgentExecutionError`; the step is not retried. |

## The drift checks

* `step` != the requested step -> drift (retryable).
* `status` not in the four values -> drift (retryable).
* `status == "completed"` with `progress < 100` -> drift (retryable).
* `next_step` != the next roadmap step (`null` on the last step) -> a
  **warning**, unless the supervisor was built with `strict_next_step=True`,
  in which case it is drift (retryable).

## The conformance test suite

An implementation that wants to claim conformance should be able to pass the
following checks.  AgenTether's own tests are the reference; the names below
are the ones in `tests/`:

| Check | Test |
| --- | --- |
| The telemetry is extracted from prose, from a fenced block, from nested JSON and from braces inside strings. | `tests/test_parser.py` |
| An invalid telemetry raises a parse error, never anything else. | `tests/test_properties.py::test_the_parser_only_ever_raises_a_telemetry_parse_error` |
| A wrong step, an unknown status and a low progress are drift errors. | `tests/test_orchestrator.py` |
| A claim that is not backed by a file is rejected by a verifier. | `tests/test_invariants.py::test_a_failed_verification_never_marks_the_step_completed` |
| A model cannot forge the markers of the memory file. | `tests/test_rename_migration.py` |

## What this draft does not define

* The file format of the project memory (see `state-file-format-v2.md`).
* How a verifier decides that a claim is true.  The contract only says that
  a claim may be checked; the checks are the user's business.
* Anything about the model itself.
