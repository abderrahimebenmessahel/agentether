"""One-off patch script: finish the claims ledger wiring (part 2)."""

import pathlib

p = pathlib.Path("src/agentether/orchestrator.py")
t = p.read_text(encoding="utf-8")


def sub(old: str, new: str, label: str) -> None:
    global t
    assert old in t, f"NOT FOUND: {label}"
    t = t.replace(old, new, 1)
    print("ok:", label)


# the verification failure carries the outcome, so the claim can record it
sub(
    """        if telemetry.status == "completed" and verifiers:
            verification = await self._verify(step_name, telemetry, raw_output, verifiers)
            if verification is not None:
                return _AttemptResult(""",
    """        verification: dict[str, Any] | None = None
        if telemetry.status == "completed" and verifiers:
            failure = await self._verify(step_name, telemetry, raw_output, verifiers)
            if failure is not None:
                error = failure.exception
                evidence = getattr(error, "evidence", {})
                reason = getattr(error, "reason", str(error))
                return _AttemptResult(
                    verification={"ok": False, "reason": reason, "evidence": evidence},
                    model=model,
                    failure=failure,
                )
            verification = {"ok": True, "reason": "", "evidence": {}}""",
    "verification handling",
)

sub(
    """        if telemetry.status == "completed":
            return _AttemptResult(telemetry=telemetry, raw_output=raw_output)""",
    """        if telemetry.status == "completed":
            return _AttemptResult(
                telemetry=telemetry,
                raw_output=raw_output,
                usage=usage,
                model=model,
                verification=verification,
            )""",
    "completed result",
)

# the model travels with the attempt result
t = t.replace(
    """                raw_output=raw_output,
                usage=usage,
            )""",
    """                raw_output=raw_output,
                usage=usage,
                model=model,
            )""",
)
t = t.replace(
    """                    raw_output=raw_output,
                    usage=usage,
                )""",
    """                    raw_output=raw_output,
                    usage=usage,
                    model=model,
                )""",
)
t = t.replace(
    """                raw_output=raw_output,
                usage=usage,
            )""",
    """                raw_output=raw_output,
                usage=usage,
                model=model,
            )""",
)

p.write_text(t, encoding="utf-8")
print("written")
