"""One-off patch script: the claims ledger in the orchestrator."""

import pathlib

p = pathlib.Path("src/agentether/orchestrator.py")
t = p.read_text(encoding="utf-8")

old = """from .logging_utils import logger
from .loop_detector import LoopDetector, StallDetector"""
new = """from .ledger import ClaimsLedger
from .logging_utils import logger
from .loop_detector import LoopDetector, StallDetector"""
assert old in t
t = t.replace(old, new)

old = """@dataclass
class _AttemptResult:
    \"\"\"Internal result of a single attempt.\"\"\"

    telemetry: Telemetry | None = None
    raw_output: str = ""
    usage: Usage | None = None
    failure: _Failure | None = None"""
new = """@dataclass
class _AttemptResult:
    \"\"\"Internal result of a single attempt.\"\"\"

    telemetry: Telemetry | None = None
    raw_output: str = ""
    usage: Usage | None = None
    model: str | None = None
    verification: dict[str, Any] | None = None
    failure: _Failure | None = None"""
assert old in t
t = t.replace(old, new)

old = """        self._loop_retries: dict[str, int] = {}"""
new = """        self._loop_retries: dict[str, int] = {}
        self._claims = ClaimsLedger(self._state.memory_dir)"""
assert old in t
t = t.replace(old, new)

# the invocation returns the model as well
old = """        try:
            if inspect.iscoroutinefunction(target):
                outcome = cast("Awaitable[Any]", target(context, *args, **kwargs))
                raw = await asyncio.wait_for(self._await_worker(outcome), timeout)
            else:
                raw = await asyncio.wait_for(
                    self._call_in_thread(target, context, *args, **kwargs), timeout
                )"""
new = """        try:
            if inspect.iscoroutinefunction(target):
                outcome = cast("Awaitable[Any]", target(context, *args, **kwargs))
                raw = await asyncio.wait_for(self._await_worker(outcome), timeout)
            else:
                raw = await asyncio.wait_for(
                    self._call_in_thread(target, context, *args, **kwargs), timeout
                )"""
assert old in t

old = """        if not isinstance(raw, str):
            return str(raw)
        return raw"""
new = """        if isinstance(raw, WorkerOutput):
            return raw.text, raw.usage, raw.model
        if not isinstance(raw, str):
            return str(raw), None, None
        return raw, None, None"""
assert old in t
t = t.replace(old, new)

old = """    ) -> str:
        target = func
        timeout = self._timeout_seconds"""
new = """    ) -> tuple[str, Usage | None, str | None]:
        target = func
        timeout = self._timeout_seconds"""
assert old in t
t = t.replace(old, new)

old = """        try:
            raw_output, usage = await self._invoke(func, context, args, kwargs)"""
new = """        try:
            raw_output, usage, model = await self._invoke(func, context, args, kwargs)"""
assert old in t
t = t.replace(old, new)

# every return of _attempt carries the model
t = t.replace("""                raw_output=raw_output,
                usage=usage,
            )""", """                raw_output=raw_output,
                usage=usage,
                model=model,
            )""")
t = t.replace("""            return _AttemptResult(
                failure=_Failure(
                    exception=VerificationFailedError(
                        step_name, result.reason, result.evidence
                    ),""", """            return _AttemptResult(
                verification={
                    "ok": False,
                    "reason": result.reason,
                    "evidence": result.evidence,
                },
                model=model,
                failure=_Failure(
                    exception=VerificationFailedError(
                        step_name, result.reason, result.evidence
                    ),""")
t = t.replace("""        if telemetry.status == "completed":
            return _AttemptResult(telemetry=telemetry, raw_output=raw_output)""",
"""        if telemetry.status == "completed":
            return _AttemptResult(
                telemetry=telemetry,
                raw_output=raw_output,
                usage=usage,
                model=model,
                verification=verification,
            )""")

# the verification result is computed before the status is handled
old = """        if telemetry.status == "completed" and verifiers:
            verification = await self._verify(step_name, telemetry, raw_output, verifiers)
            if verification is not None:
                return _AttemptResult("""
new = """        verification: dict[str, Any] | None = None
        if telemetry.status == "completed" and verifiers:
            verification = await self._verify(step_name, telemetry, raw_output, verifiers)
            if verification is not None:
                return _AttemptResult("""
assert old in t
t = t.replace(old, new)

# the claim is recorded after every attempt that produced a claim
old = """            outcome = await self._attempt(step_name, func, args, kwargs, context, verifiers)
            self._budget.record_attempt("""
new = """            outcome = await self._attempt(step_name, func, args, kwargs, context, verifiers)
            if outcome.telemetry is not None:
                self._claims.append(
                    step=step_name,
                    attempt=attempt,
                    claimed_status=outcome.telemetry.status,
                    claimed_artifacts=list(outcome.telemetry.artifacts),
                    model=outcome.model,
                    verification=outcome.verification,
                )
            self._budget.record_attempt("""
assert old in t
t = t.replace(old, new)
p.write_text(t, encoding="utf-8")
print("orchestrator patched")
