# The state file format, version 2 (draft)

> **Status: draft.**  This is the format AgenTether 0.3.0-alpha reads and
> writes.  It is documented so that another implementation could interoperate
> with it.  It is not a standard and it may still change.

Version: 2 (draft).

## The file

The project memory is a single Markdown file, `PROJECT_MEMORY.md`, in the
memory directory.  It has two owners: the library and the human.

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

<!-- contextguard:human:start -->
Write it in bullet points, no more than five.
<!-- contextguard:human:end -->

<!-- contextguard:state -->
```json
{ "schema_version": 2, "...": "..." }
```
```

## The owners

| Part | Owner | Rule |
| --- | --- | --- |
| The title and the comment | library | Regenerated. |
| `## Roadmap` | library | Regenerated; the checklist marks the completed steps. |
| `## Completed Steps` | library | Regenerated from the recorded telemetry. |
| `## Needs human input` | library | Regenerated from the blocked steps. |
| `## Verification` | library | Regenerated from the last verification of every step. |
| The section between `<!-- contextguard:human:start -->` and `<!-- contextguard:human:end -->` | **human** | Preserved byte for byte.  Never rewritten. |
| The block after `<!-- contextguard:state -->` | library | The machine readable state. |

The human section is read back exactly as it is written, including a
carriage return.  The file is read with `newline=""` for that reason, and the
marker regexes accept a trailing carriage return, so a file that a Windows
editor saved with CRLF line endings still works.

## The escaping

Every string the model controls is escaped when it is written: a literal
`<!--` becomes `&lt;!--`, and the ampersand is escaped first, so the escaping
is lossless.  A model therefore cannot put a marker into the file, and the
parser takes the machine block from the **last** state marker and the human
section from the region the library itself wrote.

## The state block

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
  "budget": {"attempts": 7, "tokens": 18422, "cost": 0.0312, "elapsed_seconds": 42.5},
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

## The other files

| Path | Content |
| --- | --- |
| `PROJECT_MEMORY.md.bak` | The file before an automatic migration. |
| `steps/NN_<slug>.md` | The raw output of the most recent recorded attempt. |
| `steps/NN_<slug>.attempts.jsonl` | One line per attempt: the timestamp, the attempt number, the outcome kind, the error, the length of the output and its SHA-256.  The full output is only stored when `store_raw_outputs=True`. |
| `claims.jsonl` | One line per claim: what the agent claimed and what the verification said.  Hash chained. |
| `claims.jsonl.head` | The hash of the last line of the claims ledger. |
| `events.jsonl` | One line per supervisor event.  Hash chained. |
| `events.jsonl.head` | The hash of the last line of the event log. |
| `events.jsonl.1` | The previous event log, after a rotation. |
| `*.tmp` | A temporary file of an atomic write.  Only the ones older than an hour are removed. |

## The atomic write

1. A temporary file is created **in the same directory**.
2. The content is written, flushed and `fsync`-ed.
3. The temporary file is renamed over the target (`os.replace`), which is
   atomic on POSIX and on Windows.
4. The directory is `fsync`-ed.  Where the platform cannot do it (Windows),
   the failure is ignored; every other error is logged as a warning.
5. On any error the temporary file is removed and the error is re-raised, so
   the previous file stays intact.

## The concurrency

Writers are serialised with an `asyncio.Lock` **inside one process**.  There
is no cross-process locking: two orchestrators must not share a memory
directory.
