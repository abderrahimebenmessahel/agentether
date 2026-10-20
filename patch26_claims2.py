"""One-off patch script: finish the claims ledger wiring."""

import pathlib

p = pathlib.Path("src/agentether/orchestrator.py")
t = p.read_text(encoding="utf-8")


def sub(old: str, new: str, label: str, count: int = 1) -> None:
    global t
    assert old in t, f"NOT FOUND: {label}"
    t = t.replace(old, new, count)
    print("ok:", label)


sub(
    """            raw_output, usage = await self._invoke(func, context, args, kwargs)""",
    """            raw_output, usage, model = await self._invoke(func, context, args, kwargs)""",
    "unpack",
)

sub(
    """            outcome = await self._attempt(step_name, func, args, kwargs, context, verifiers)
            self._budget.record_attempt(""",
    """            outcome = await self._attempt(step_name, func, args, kwargs, context, verifiers)
            if outcome.telemetry is not None:
                self._claims.append(
                    step=step_name,
                    attempt=attempt,
                    claimed_status=outcome.telemetry.status,
                    claimed_artifacts=list(outcome.telemetry.artifacts),
                    model=outcome.model,
                    verification=outcome.verification,
                )
            self._budget.record_attempt(""",
    "claim append",
)

# every attempt result that carries the raw output also carries the model
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

sub(
    """        if telemetry.status == "completed" and verifiers:
            verification = await self._verify(step_name, telemetry, raw_output, verifiers)
            if verification is not None:
                return _AttemptResult(""",
    """        verification: dict[str, Any] | None = None
        if telemetry.status == "completed" and verifiers:
            verification = await self._verify(step_name, telemetry, raw_output, verifiers)
            if verification is not None:
                return _AttemptResult(""",
    "verification variable",
)

sub(
    """                failure=_Failure(
                    exception=VerificationFailedError(
                        step_name, result.reason, result.evidence
                    ),""",
    """                verification={
                    "ok": False,
                    "reason": result.reason,
                    "evidence": result.evidence,
                },
                model=model,
                failure=_Failure(
                    exception=VerificationFailedError(
                        step_name, result.reason, result.evidence
                    ),""",
    "verification failure",
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

p.write_text(t, encoding="utf-8")
print("written")
