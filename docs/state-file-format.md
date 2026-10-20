# The state file format (schema version 2)

`PROJECT_MEMORY.md` lives in the memory directory and has two owners: the
library and the human.

## Layout

```markdown
# Project Memory

<!-- Managed by AgenTether. Edit the code, not this file. -->
<!-- The section between the human markers is never rewritten by AgenTether. -->

## Roadmap

- [x] research
- [ ] write

## Completed Steps

### research

Found three sources and wrote them up.

## Needs human input

- `write`: I need the API key to continue

## Verification

- `research`: passed

<!-- agentether:human:start -->
The customer wants bullet points, no more than five.
<!-- agentether:human:end -->

<!-- agentether:state -->
```json
{ "schema_version": 2, "...": "..." }
```
```

## Who owns what

| Part | Owner | Behaviour |
| --- | --- | --- |
| Title, roadmap checklist | library | Regenerated on every write. |
| `## Completed Steps` | library | Regenerated from the recorded telemetry. |
| `## Needs human input` | library | Regenerated from the recorded blocked steps. |
| `## Verification` | library | Regenerated from the last verification of each step. |
| The section between the human markers | **human** | Preserved byte for byte. Never rewritten. |
| The block after `<!-- agentether:state -->` | library | The machine readable state. |

If the human section does not fit into the memory budget, it is truncated
with a visible marker and a warning is logged.  It is never dropped silently.

## The state block

The JSON block after the state marker is the source of truth.  `load()`
reads it; a missing or malformed block raises `StateCorruptionError` (the
library never silently resets a project).

```json
{
  "schema_version": 2,
  "roadmap": ["research", "write"],
  "completed_steps": ["research"],
  "telemetry": {
    "research": {
      "step": "research",
      "status": "completed",
      "summary": "Found three sources and wrote them up.",
      "progress": 100,
      "next_step": "write",
      "artifacts": ["notes/research.md"]
    }
  },
  "step_files": {"research": "steps/01_research.md"},
  "attempts": {
    "research": [
      {
        "ts": "2026-10-20T09:12:33Z",
        "attempt": 1,
        "outcome": "parse_error",
        "error": "Could not parse telemetry for step 'research': ...",
        "output_length": 412,
        "output_sha256": "3b1f..."
      }
    ]
  },
  "verifications": {
    "research": {"ok": true, "reason": "", "evidence": {}, "ts": "..."}
  },
  "needs_human": {},
  "human_hash": "e3b0c442...",
  "budget": {
    "attempts": 7,
    "tokens": 18422,
    "cost": 0.0312,
    "elapsed_seconds": 42.5
  },
  "breaker": {
    "open": false,
    "reason": null,
    "step": null,
    "attempts": 0,
    "last_error": null,
    "opened_at": null
  },
  "last_failure": null,
  "updated_at": "2026-10-20T09:12:33Z"
}
```

`human_hash` is the SHA-256 of the normalised human section.  When it
changes, a step that is waiting for human input may run again.

`budget` holds what the run has spent so far.  It is written with every
attempt and restored when the orchestrator starts, so the budgets are global
per **project** and not per process: a run that was interrupted and started
again continues to spend the same budget.

## Escaping: the model cannot forge a marker

Every string the model controls -- the summary, the reported step name, the
artifact paths, the reason a step is blocked -- is escaped when it is
written: a literal `<!--` becomes `&lt;!--`.  The model can therefore never
put a marker of the library into the file, and the parser never has to guess
which block is the real one.

On top of that the parser is deliberately strict:

* the machine block is taken from the **last** state marker that stands on a
  line of its own (the library always writes it last);
* the human section is the region between the **last** human end marker
  before that block and the nearest human start marker before it -- the
  region the library itself wrote;
* the JSON block ends at the **last** fence in the file, so a summary that
  contains ` ``` ` cannot truncate it.

The escaped text is unescaped again when the state is read, so the state that
comes back is the state that was written.

## The other files in the memory directory

| Path | Content |
| --- | --- |
| `PROJECT_MEMORY.md` | The file described above. |
| `PROJECT_MEMORY.md.bak` | A copy of the file before an automatic migration. |
| `steps/NN_<slug>.md` | The raw output of the most recent recorded attempt of a step. |
| `steps/NN_<slug>.attempts.jsonl` | One JSON line per attempt: timestamp, attempt number, outcome kind, error, output length and output SHA-256.  The full output is only stored when `store_raw_outputs=True`. |
| `events.jsonl` | One JSON line per supervisor event, with a monotonic sequence number and an ISO-8601 UTC timestamp.  Rotated to `events.jsonl.1` when it grows past `events_max_bytes`. |
| `*.tmp` | A temporary file of an atomic write.  Only files older than one hour are removed. |

## Migration from schema version 1

A version 1 file is migrated automatically the first time it is read:

1. the old file is copied to `PROJECT_MEMORY.md.bak`;
2. the missing sections (`attempts`, `verifications`, `needs_human`,
   `human_hash`, `breaker.opened_at`) are filled in with their defaults;
3. the file is rewritten as version 2.

No recorded step, telemetry or failure is lost.  The migration is covered by
`tests/test_state_manager.py`.

## Atomic writes

Every file is written with the same procedure:

1. a temporary file is created **in the same directory** (`tempfile.mkstemp`);
2. the content is written, flushed and `fsync`-ed;
3. the temporary file is renamed over the target (`os.replace`), which is
   atomic on POSIX and on Windows;
4. the directory is `fsync`-ed (skipped where the platform does not support
   it, logged as a warning otherwise);
5. on any error the temporary file is removed and the error is re-raised, so
   the previous file stays intact.

## Concurrency

Writers are serialised with an `asyncio.Lock` **inside one process**.  There
is no cross-process locking.  Give every orchestrator its own memory
directory.
