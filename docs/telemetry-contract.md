# The telemetry contract

The worker answers with **text**.  The text must end with a single JSON
object that describes what the worker did.  ContextGuard parses it, validates
it and refuses the step when it does not make sense.

## The object

```json
{
  "step": "research",
  "status": "completed",
  "summary": "Found three sources and wrote them up.",
  "progress": 100,
  "next_step": "write",
  "artifacts": ["notes/research.md"]
}
```

| Field | Required | Type | Meaning |
| --- | --- | --- | --- |
| `step` | yes | string | The roadmap step that was performed. |
| `status` | yes | string | One of `in_progress`, `completed`, `blocked`, `failed`. |
| `summary` | yes | string | One short paragraph: what was done and what was found. |
| `progress` | no | number 0-100 or `null` | How far the step is. |
| `next_step` | no | string or `null` | The next roadmap step, `null` on the last step. |
| `artifacts` | no | list of strings | Files, URLs or identifiers that were produced. |

Unknown fields are ignored, so the contract can grow.

## What ContextGuard checks

* `step` must equal the step that was requested.  A mismatch is a
  `ContextDriftError` and is retried.
* `status` must be one of the four allowed values.  An unknown status is a
  `ContextDriftError`.
* `status == "completed"` with a `progress` below 100 is a
  `ContextDriftError`: the agent says it is done but admits it is not.
* `next_step` must be the next roadmap step (`null` on the last step).  A
  mismatch is **only a warning** unless the orchestrator was built with
  `strict_next_step=True`, in which case it is a `ContextDriftError`.
* `artifacts` are paths that must exist inside the work directory when a
  verifier is attached.

## How the answer is extracted

The extraction is deliberately forgiving about prose and strict about
structure:

1. fenced code blocks (```` ```json ... ``` ````) are tried first;
2. otherwise every `{` in the text is offered to
   `json.JSONDecoder().raw_decode`, so nested objects and braces inside
   strings are handled correctly;
3. the **last** candidate that carries `step` and `status` wins; if no
   candidate has them, the last dictionary found is used;
4. if there is no JSON at all, the step fails with a
   `TelemetryParseError`.

Trailing commas are invalid JSON and are **not** repaired -- the step fails
cleanly and is retried with a hint.  Inputs above 1,000,000 characters are
refused before any parsing happens.

## How the status is handled

| Status | What ContextGuard does |
| --- | --- |
| `completed` | The verifiers run, the step is persisted, the result is returned. |
| `in_progress` | The attempt failed.  The step is retried with the hint "step not completed, continue". |
| `blocked` | The reason is persisted, a "Needs human input" entry is written and the step is **not** retried.  The human can answer in their own section of `PROJECT_MEMORY.md`, which releases the step. |
| `failed` | The reason is persisted and the step is **not** retried.  The error is raised as an `AgentExecutionError`. |

## The prompt

`ctx.build_prompt(task)` assembles the prompt from four parts:

1. the task,
2. the roadmap position (which step, and what is done, pending and current),
3. the compacted project memory (including the human section),
4. the telemetry contract above, plus the corrective hint of the previous
   attempt when there was one.
