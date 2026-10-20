"""One-off patch script: the head hash, the claim on a failed verification, the report summary."""

import pathlib

# ------------------------------------------------------------------ ledger --
p = pathlib.Path("src/agentether/ledger.py")
t = p.read_text(encoding="utf-8")

old = '''def chain_hash(line: str) -> str:
    """Return the SHA-256 of a log line (without its trailing newline)."""
    return hashlib.sha256(line.encode("utf-8")).hexdigest()'''
new = '''def chain_hash(line: str) -> str:
    """Return the SHA-256 of a log line (without its trailing newline)."""
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def head_path(path: Path) -> Path:
    """The file that holds the hash of the last line of a log."""
    return path.with_name(path.name + ".head")


def write_head(path: Path, digest: str) -> None:
    """Write the hash of the last line of a log.

    The head is what makes a change to the *last* line detectable: the chain
    alone cannot tell that the final line was edited.
    """
    target = head_path(path)
    temporary = target.with_name(target.name + ".tmp")
    try:
        temporary.write_text(digest + "\\n", encoding="utf-8")
        os.replace(temporary, target)
    except OSError:  # pragma: no cover - unwritable directory
        with contextlib.suppress(OSError):
            temporary.unlink()


def read_head(path: Path) -> str:
    """Read the hash of the last line of a log (empty when there is none)."""
    target = head_path(path)
    try:
        return target.read_text(encoding="utf-8").strip()
    except OSError:
        return ""'''
assert old in t
t = t.replace(old, new, 1)
t = t.replace("""import hashlib
import json
import os
import time""", """import contextlib
import hashlib
import json
import os
import time""")

old = '''def verify_chain(path: Path) -> tuple[int, list[ChainBreak]]:
    """Verify the hash chain of a log file.

    Args:
        path: The log file.

    Returns:
        ``(lines_checked, breaks)``.  An empty list of breaks means the chain
        is intact.
    """
    if not path.exists():
        return 0, []
    breaks: list[ChainBreak] = []
    previous_hash = GENESIS_HASH
    number = 0
    with path.open("r", encoding="utf-8") as handle:
        for number, raw in enumerate(handle, start=1):
            line = raw.rstrip("\\n")
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                breaks.append(
                    ChainBreak(number, previous_hash, "", "the line is not valid JSON")
                )
                previous_hash = chain_hash(line)
                continue
            claimed = record.get("prev")
            if claimed != previous_hash:
                breaks.append(
                    ChainBreak(
                        number,
                        str(claimed),
                        previous_hash,
                        "the line does not follow the previous one",
                    )
                )
            previous_hash = chain_hash(line)
    return number, breaks'''
new = '''def verify_chain(path: Path) -> tuple[int, list[ChainBreak]]:
    """Verify the hash chain of a log file.

    Two things are checked: every line must carry the hash of the previous
    one, and the head file must carry the hash of the last line (that is what
    makes a change to the *last* line visible).

    Args:
        path: The log file.

    Returns:
        ``(lines_checked, breaks)``.  An empty list of breaks means the chain
        is intact.
    """
    if not path.exists():
        return 0, []
    breaks: list[ChainBreak] = []
    previous_hash = GENESIS_HASH
    number = 0
    last_hash = GENESIS_HASH
    with path.open("r", encoding="utf-8") as handle:
        for number, raw in enumerate(handle, start=1):
            line = raw.rstrip("\\n")
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                breaks.append(
                    ChainBreak(number, previous_hash, "", "the line is not valid JSON")
                )
                previous_hash = chain_hash(line)
                last_hash = previous_hash
                continue
            claimed = record.get("prev")
            if claimed != previous_hash:
                breaks.append(
                    ChainBreak(
                        number,
                        str(claimed),
                        previous_hash,
                        "the line does not follow the previous one",
                    )
                )
            previous_hash = chain_hash(line)
            last_hash = previous_hash
    head = read_head(path)
    if head and last_hash != head:
        breaks.append(
            ChainBreak(
                number,
                head,
                last_hash,
                "the last line does not match the recorded head hash",
            )
        )
    return number, breaks'''
assert old in t
t = t.replace(old, new, 1)

old = '''        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\\n") as handle:
                handle.write(line + "\\n")
        except OSError:  # pragma: no cover - unwritable directory
            return record
        self._last_hash = chain_hash(line)
        return record'''
new = '''        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\\n") as handle:
                handle.write(line + "\\n")
        except OSError:  # pragma: no cover - unwritable directory
            return record
        self._last_hash = chain_hash(line)
        write_head(self.path, self._last_hash)
        return record'''
assert old in t
t = t.replace(old, new, 1)

old = '''    def __init__(self, memory_dir: str | os.PathLike[str]) -> None:
        self.path = Path(memory_dir) / CLAIMS_FILENAME
        self._last_hash = GENESIS_HASH
        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8") as handle:
                    for raw in handle:
                        line = raw.rstrip("\\n")
                        if line.strip():
                            self._last_hash = chain_hash(line)
            except OSError:  # pragma: no cover - unreadable ledger
                pass'''
new = '''    def __init__(self, memory_dir: str | os.PathLike[str]) -> None:
        self.path = Path(memory_dir) / CLAIMS_FILENAME
        self._last_hash = GENESIS_HASH
        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8") as handle:
                    for raw in handle:
                        line = raw.rstrip("\\n")
                        if line.strip():
                            self._last_hash = chain_hash(line)
            except OSError:  # pragma: no cover - unreadable ledger
                pass
        else:
            write_head(self.path, GENESIS_HASH)'''
assert old in t
t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print("ledger patched")

# ------------------------------------------------------------------ events --
p = pathlib.Path("src/agentether/events.py")
t = p.read_text(encoding="utf-8")
old = """from .ledger import GENESIS_HASH, chain_hash"""
new = """from .ledger import GENESIS_HASH, chain_hash, write_head"""
assert old in t
t = t.replace(old, new, 1)
old = """        self._last_hash = chain_hash(line.rstrip("\\n"))
        return record"""
new = """        self._last_hash = chain_hash(line.rstrip("\\n"))
        write_head(self.path, self._last_hash)
        return record"""
assert old in t
t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print("events patched")

# ------------------------------------------------------------- orchestrator --
p = pathlib.Path("src/agentether/orchestrator.py")
t = p.read_text(encoding="utf-8")
old = """                return _AttemptResult(
                    verification={
                        "ok": False,
                        "reason": str(getattr(error, "reason", error)),
                        "evidence": dict(getattr(error, "evidence", {})),
                    },
                    model=model,
                    failure=failure,
                    raw_output=raw_output,
                    usage=usage,
                )"""
new = """                return _AttemptResult(
                    # The claim itself is kept: the agent *did* claim to be
                    # done, and the claim is what the ledger records.
                    telemetry=telemetry,
                    verification={
                        "ok": False,
                        "reason": str(getattr(error, "reason", error)),
                        "evidence": dict(getattr(error, "evidence", {})),
                    },
                    model=model,
                    failure=failure,
                    raw_output=raw_output,
                    usage=usage,
                )"""
assert old in t
t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print("orchestrator patched")
