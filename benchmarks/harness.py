"""The harness of the evidence trial: the protocol, the faults and the arms.

The three arms of the trial must differ **only** in the way they supervise a
claim.  Everything else -- the prompt, the tasks, the fault schedule, the way
the files of an answer reach the sandbox, the way the belief of an arm is
derived -- has to be identical, or the comparison measures the harness
instead of the policies.

The first run of the trial (run 1, 2026-10-20) did not satisfy that rule and
its numbers are therefore **not** a comparison of the three arms.  The five
defects that were found are listed in ``docs/evidence.md``; each of them has
a regression test in ``tests/test_trial_arms.py``.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from tasks import Check, TaskSpec

from agentether import (
    AutoOrchestrator,
    StepContext,
    TelemetryParseError,
    WorkerOutput,
    artifacts_exist,
    extract_json_telemetry,
    parse_telemetry,
)

__all__ = [
    "PROTOCOL",
    "ArmResult",
    "Caller",
    "artifacts_present",
    "build_prompt",
    "fault_for",
    "inject_fault",
    "parse_file_blocks",
    "run_arm_agentether",
    "run_arm_naive",
    "run_arm_simple_retry",
    "task_is_correct",
    "write_answer_files",
]

#: The attempt cap of the simple-retry and of the agentether arm.  The naive
#: arm makes one call per step by definition.
ATTEMPT_CAP = 3

#: The probability that a fault is injected into an attempt.
FAULT_RATE = 0.20

#: The seed of the fault schedule.
FAULT_SEED = 20261020

#: The prompt of a step.  It is the **same** for the three arms.
#:
#: The scale of ``progress`` and the meaning of ``status`` are spelled out:
#: the telemetry contract of AgenTether treats a completed step with a
#: progress below 100 as drift, and run 1 never told the model that, so every
#: completed step was rejected.  That was a defect of the harness, not of the
#: model, and the fix was applied to every arm.
PROTOCOL = """\
You are working inside a sandbox. You cannot use tools: you return the content
of every file in a fenced block whose first line is "FILE: <relative path>".

Example:

FILE: notes.md
# Notes
## Context
...

Rules:
- one fenced block per file, and the first line of the block must be
  "FILE: <path>" followed by the content of the file;
- the path must be relative, without ".." and without a drive letter;
- write every file the step asks for, with exactly the content that is asked
  for (the exact headings, the exact keys, the exact numbers);
- end your answer with a single JSON object with the keys "step", "status",
  "summary", "progress", "next_step" and "artifacts";
- the value of "step" must be exactly "{step}";
- "status" must be "completed" only when you really produced every file of
  the step, and "in_progress" otherwise;
- "progress" is a number between 0 and 100, and it must be 100 when the
  status is "completed";
- "summary" is one short paragraph saying what was done;
- "next_step" is the name of the next step, or null on the last step;
- "artifacts" lists every file you produced in this step, as relative paths.
"""

_FENCE = re.compile(r"```[^\r\n]*\r?\n(?P<body>.*?)```", re.DOTALL)
_FILE_HEAD = re.compile(r"^\s*FILE:\s*(?P<path>[^\r\n`]+?)\s*$")
_MAX_FILE_BYTES = 64_000
_MAX_SANDBOX_BYTES = 512_000


# ----------------------------------------------------------------------
# the protocol
# ----------------------------------------------------------------------
def build_prompt(step: Any) -> str:
    """The prompt of a step.  Every arm uses this exact string."""
    return f"{step.instruction}\n\n{PROTOCOL.format(step=step.name)}"


def parse_file_blocks(answer: str) -> list[tuple[str, str]]:
    """Extract the ``FILE: path`` blocks of an answer."""
    found: list[tuple[str, str]] = []
    for match in _FENCE.finditer(answer):
        body = match.group("body")
        lines = body.splitlines()
        if not lines:
            continue
        head = _FILE_HEAD.match(lines[0])
        if head is None:
            continue
        found.append((head.group("path").strip(), "\n".join(lines[1:])))
    return found


def write_answer_files(answer: str, sandbox: Path) -> list[str]:
    """Write the files of an answer into the sandbox (path confined).

    Every arm calls this for **every** answer it receives, whatever the
    claim says.  A file that the model produced is a fact of the sandbox, not
    a consequence of the claim: run 1 wrote the files only when the claim
    said "completed", which made the simple-retry arm throw away work that
    the naive arm kept.
    """
    written: list[str] = []
    total = 0
    for path, content in parse_file_blocks(answer):
        if not path or path.startswith("/") or ".." in Path(path).parts:
            continue
        encoded = content.encode("utf-8")[:_MAX_FILE_BYTES]
        if total + len(encoded) > _MAX_SANDBOX_BYTES:
            break
        target = sandbox / path
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(encoded)
        except OSError:
            continue
        written.append(path)
        total += len(encoded)
    return written


# ----------------------------------------------------------------------
# the injected faults
# ----------------------------------------------------------------------
def _telemetry_of(answer: str) -> tuple[str, str]:
    """The telemetry JSON of an answer and the text before it."""
    start = answer.rfind("{")
    if start < 0:
        return "", answer
    end = answer.rfind("}")
    if end < start:
        return "", answer
    return answer[start : end + 1], answer[:start]


def inject_fault(answer: str, fault: str, previous: str | None) -> str:
    """Apply one injected fault to an answer.

    Args:
        answer: The answer of the model.
        fault: The name of the fault.
        previous: The most recent answer of the same task (for the replay
            fault).

    Returns:
        The faulty answer.
    """
    if fault == "drop_file_block":
        return re.sub(r"```[^\r\n]*\r?\n.*?```", "", answer, flags=re.DOTALL)
    if fault == "truncate_file":
        blocks = list(_FENCE.finditer(answer))
        if not blocks:
            return answer
        first = blocks[0]
        body = first.group("body")
        half = body[: len(body) // 2]
        new_block = "```\n" + half + "\n```"
        return answer[: first.start()] + new_block + answer[first.end() :]
    if fault == "corrupt_telemetry":
        telemetry, head = _telemetry_of(answer)
        if not telemetry:
            return answer + "\n{not json at all}"
        broken = telemetry.replace('"status"', '"stat us"')
        return head + "\n" + broken
    if fault == "wrong_step":
        telemetry, head = _telemetry_of(answer)
        if not telemetry:
            return answer
        broken = re.sub(r'"step"\s*:\s*"[^"]*"', '"step": "some_other_step"', telemetry)
        return head + "\n" + broken
    if fault == "replay_previous":
        return previous if previous is not None else answer
    if fault == "lie":
        # The claim stays, the file block goes.
        return re.sub(r"```[^\r\n]*\r?\n.*?```", "", answer, flags=re.DOTALL)
    return answer


def fault_for(task_index: int, step_index: int, attempt: int) -> str | None:
    """The fault of one attempt (or ``None``).

    The schedule is a **function** of the task, the step and the attempt
    number *within that step*.  Every arm therefore meets the same schedule;
    it is a function and not a fixed list, so an arm that retries more
    simply walks further along it.  Run 1 keyed the schedule on a counter
    that ran across the whole task, so two arms that made a different number
    of attempts met different faults for the same step.

    Args:
        task_index: The index of the task.
        step_index: The index of the step inside the task.
        attempt: The attempt number inside the step, starting at 1.
    """
    rng = random.Random(f"{FAULT_SEED}:{task_index}:{step_index}:{attempt}")
    if rng.random() >= FAULT_RATE:
        return None
    return rng.choice(
        [
            "drop_file_block",
            "truncate_file",
            "corrupt_telemetry",
            "wrong_step",
            "replay_previous",
            "lie",
        ]
    )


# ----------------------------------------------------------------------
# the ground truth
# ----------------------------------------------------------------------
def run_check(check: Check, sandbox: Path) -> bool:
    """Run one ground truth check."""
    target = sandbox / check.path
    if check.kind == "file_exists":
        return target.is_file()
    if not target.is_file():
        return False
    if check.kind in ("contains", "headings"):
        content = target.read_text(encoding="utf-8", errors="replace")
        return bool(check.value in content)
    if check.kind == "python_valid":
        source = target.read_text(encoding="utf-8", errors="replace")
        try:
            compile(source, str(target), "exec")
        except SyntaxError:
            return False
        return True
    if check.kind == "json_keys":
        data = _load_json(target)
        if not isinstance(data, dict):
            return False
        return all(key in data for key in check.value.split(","))
    if check.kind == "json_value":
        data = _load_json(target)
        if not isinstance(data, dict):
            return False
        key, _, expected = check.value.partition("=")
        return bool(str(data.get(key)) == expected)
    return False


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None


def task_is_correct(task: TaskSpec, sandbox: Path) -> bool:
    """Whether every ground truth check of the task passes."""
    return all(run_check(check, sandbox) for check in task.checks)


def artifacts_present(task: TaskSpec, sandbox: Path) -> bool:
    """Whether every expected file is on disk (part of the ground truth)."""
    return bool(task.expected_files) and all(
        (sandbox / path).exists() for path in task.expected_files
    )


# ----------------------------------------------------------------------
# the arms
# ----------------------------------------------------------------------
class Caller(Protocol):
    """Who the arms call.  A live model in the trial, a script in the tests."""

    async def call(self, prompt: str) -> WorkerOutput:
        """One request.  Raises when the call fails."""
        ...


@dataclass
class ArmResult:
    """What an arm did with one task.

    Attributes:
        attempts: The number of model calls the arm made.
        step_verdicts: For every step, whether the arm considered it done.
        believed: Whether the arm believes the **task** is done.  It is true
            when every step was considered done.
        verifier_rejections: The number of failed verifications.
        loop_detections: The number of detected loops.
        failures: A short description of every step that was not done.
    """

    attempts: int
    step_verdicts: list[bool]
    believed: bool
    verifier_rejections: int = 0
    loop_detections: int = 0
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable copy."""
        return {
            "attempts": self.attempts,
            "step_verdicts": list(self.step_verdicts),
            "believed": self.believed,
            "verifier_rejections": self.verifier_rejections,
            "loop_detections": self.loop_detections,
            "failures": list(self.failures),
        }


def _claim_is_completed(answer: str) -> bool:
    """Whether an answer claims that the step is done.

    The naive arm **trusts the claim**: the last telemetry object of the
    answer is read and its status is taken at face value.  The step name is
    not checked, because a naive agent would not check it.
    """
    try:
        data = extract_json_telemetry(answer)
    except TelemetryParseError:
        return False
    return str(data.get("status", "")) == "completed"


def _contract_is_completed(answer: str, step_name: str) -> bool:
    """Whether an answer satisfies the telemetry contract of the step.

    The simple-retry arm parses the contract: the step name must match and
    the status must be "completed".
    """
    try:
        telemetry = parse_telemetry(answer, step_name)
    except TelemetryParseError:
        return False
    return telemetry.status == "completed"


async def run_arm_naive(
    task: TaskSpec,
    sandbox: Path,
    caller: Caller,
    condition: str,
    task_index: int,
) -> ArmResult:
    """Arm A: one call per step, the claim is trusted.

    The arm never retries and never checks a file.  It writes the files of
    every answer into the sandbox (the files are a fact of the sandbox, not
    a consequence of the claim) and it believes a step is done when the
    model said so.
    """
    attempts = 0
    verdicts: list[bool] = []
    failures: list[str] = []
    previous: str | None = None
    for step_index, step in enumerate(task.steps):
        try:
            output = await caller.call(build_prompt(step))
        except Exception as exc:
            # The call failed (a timeout, a transport error): a naive agent
            # has no answer, so it has no claim, and it moves on.
            failures.append(f"{step.name}: the call failed ({type(exc).__name__})")
            verdicts.append(False)
            continue
        attempts += 1
        answer = output.text
        if condition == "injected":
            fault = fault_for(task_index, step_index, 1)
            if fault is not None:
                answer = inject_fault(answer, fault, previous)
        previous = answer
        write_answer_files(answer, sandbox)
        done = _claim_is_completed(answer)
        if not done:
            failures.append(f"{step.name}: the claim was not 'completed'")
        verdicts.append(done)
    return ArmResult(
        attempts=attempts,
        step_verdicts=verdicts,
        believed=all(verdicts) and bool(verdicts),
        failures=failures,
    )


async def run_arm_simple_retry(
    task: TaskSpec,
    sandbox: Path,
    caller: Caller,
    condition: str,
    task_index: int,
) -> ArmResult:
    """Arm B: retry on a contract failure, an exception or a timeout.

    This is the baseline most people would write: the answer must satisfy
    the telemetry contract, and a failing step is retried up to
    :data:`ATTEMPT_CAP` times.  There is no verification of the artifacts, no
    loop detection and no drift check.

    The files of **every** answer reach the sandbox, including the answers
    of the attempts that failed the contract: a file that the model
    produced must not be destroyed by a retry.
    """
    attempts = 0
    verdicts: list[bool] = []
    failures: list[str] = []
    previous: str | None = None
    for step_index, step in enumerate(task.steps):
        done = False
        for attempt in range(1, ATTEMPT_CAP + 1):
            try:
                output = await caller.call(build_prompt(step))
            except Exception:
                # A timeout or a transport error: the classic baseline just
                # tries again.  The files of the previous answer stay.
                continue
            attempts += 1
            answer = output.text
            if condition == "injected":
                fault = fault_for(task_index, step_index, attempt)
                if fault is not None:
                    answer = inject_fault(answer, fault, previous)
            previous = answer
            write_answer_files(answer, sandbox)
            if _contract_is_completed(answer, step.name):
                done = True
                break
        if not done:
            failures.append(f"{step.name}: the contract was not satisfied")
        verdicts.append(done)
    return ArmResult(
        attempts=attempts,
        step_verdicts=verdicts,
        believed=all(verdicts) and bool(verdicts),
        failures=failures,
    )


async def run_arm_agentether(
    task: TaskSpec,
    sandbox: Path,
    memory_dir: Path,
    caller: Caller,
    condition: str,
    task_index: int,
) -> ArmResult:
    """Arm C: the full library.

    The orchestrator supervises the step: the telemetry contract, the drift
    checks, the verifiers, the loop detector, the budget and the breaker.

    Two settings make the arm comparable with the other two, and both are
    documented in ``docs/evidence.md``:

    - ``strict_order=False``: the roadmap order is not enforced, so a step
      that could not be done does not stop the task.  The naive and the
      simple-retry arm walk through every step whatever happened, and the
      trial compares the supervision of the claims, not the enforcement of
      the roadmap.
    - the verifier is ``artifacts_exist()``: the claimed files must exist.
      It does not use the hidden ground truth of the task, which would give
      the arm an unfair advantage.

    The breaker is closed again before every step.  The breaker of
    AgenTether protects a *project* against a step that fails again and
    again; in the trial the steps are independent, and the other two arms
    move on to the next step when a step is hopeless.

    The prompt of this arm is the one the library builds
    (:meth:`StepContext.build_prompt`): the task, the roadmap position, the
    project memory, the telemetry contract and the corrective hint of the
    previous attempt.  The other two arms repeat the same prompt on every
    attempt.  That difference is a **confound of the correct-completion
    rate** and it is reported as such; it does not touch the false
    completion rate, which is the primary endpoint.
    """
    orchestrator = AutoOrchestrator(
        roadmap=[step.name for step in task.steps],
        memory_dir=str(memory_dir),
        timeout_seconds=120.0,
        max_retries=ATTEMPT_CAP,
        workdir=str(sandbox),
        backoff_base=0.0,
        events_enabled=True,
        resume=False,
        strict_order=False,
    )
    rejections = 0
    loops = 0

    def on_event(payload: dict[str, Any]) -> None:
        nonlocal rejections, loops
        if payload.get("event") == "verification_failed":
            rejections += 1
        if payload.get("event") == "loop_detected":
            loops += 1

    orchestrator.on("verification_failed", on_event)
    orchestrator.on("loop_detected", on_event)

    attempts = 0
    verdicts: list[bool] = []
    failures: list[str] = []
    previous: str | None = None

    for step_index, step in enumerate(task.steps):
        task_text = build_prompt(step)
        # Every step starts with a closed breaker (see the docstring).
        await orchestrator.reset_breaker()

        @orchestrator.guard_step(step.name, verify=[artifacts_exist()])
        async def _worker(
            ctx: StepContext, _task: str = task_text, _index: int = step_index
        ) -> str:
            nonlocal attempts, previous
            output = await caller.call(ctx.build_prompt(_task))
            attempts += 1
            answer = output.text
            if condition == "injected":
                # ``ctx.attempt`` is the attempt number inside the step, so
                # the arm walks the same fault schedule as the others.
                fault = fault_for(task_index, _index, ctx.attempt)
                if fault is not None:
                    answer = inject_fault(answer, fault, previous)
            previous = answer
            write_answer_files(answer, ctx.workdir)
            return answer

        done = False
        try:
            outcome = await _worker()
            done = outcome.telemetry.status == "completed"
        except Exception as exc:
            failures.append(f"{step.name}: {type(exc).__name__}: {exc}")
        if not done:
            failures.append(f"{step.name}: the step was not completed")
        verdicts.append(done)

    return ArmResult(
        attempts=attempts,
        step_verdicts=verdicts,
        believed=all(verdicts) and bool(verdicts),
        verifier_rejections=rejections,
        loop_detections=loops,
        failures=failures,
    )
