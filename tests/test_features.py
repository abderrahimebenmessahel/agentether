"""Tests for the features of 0.3.0: the claims ledger, the chain, the report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agentether import (
    AutoOrchestrator,
    CircuitBreakerOpenError,
    StepContext,
    WorkerOutput,
    artifacts_exist,
    json_schema_subset,
    markdown_has_headings,
    python_syntax_valid,
)
from agentether.cli import main
from agentether.ledger import (
    ClaimsLedger,
    chain_hash,
    compute_stats,
    read_claims,
    verify_chain,
)
from agentether.report import build_report, render_html, render_markdown


def telemetry_answer(step: str, **extra: object) -> str:
    """A telemetry answer for the given step."""
    payload: dict[str, object] = {
        "step": step,
        "status": "completed",
        "summary": "done",
        "progress": 100,
        "next_step": None,
        "artifacts": [],
    }
    payload.update(extra)
    return json.dumps(payload)


# ----------------------------------------------------------------------
# the claims ledger
# ----------------------------------------------------------------------
async def test_every_claim_is_recorded(memory_dir: Path, work_dir: Path) -> None:
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
        workdir=str(work_dir),
    )

    @orch.guard_step("research", verify=[artifacts_exist()])
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research", artifacts=["missing.md"])

    with pytest.raises(CircuitBreakerOpenError):
        await research()

    claims = read_claims(memory_dir)
    assert len(claims) == 1
    assert claims[0]["step"] == "research"
    assert claims[0]["claimed_status"] == "completed"
    assert claims[0]["verification"]["ok"] is False
    assert "missing.md" in claims[0]["verification"]["reason"]


async def test_the_model_is_recorded_when_the_worker_names_it(
    memory_dir: Path, work_dir: Path
) -> None:
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
        workdir=str(work_dir),
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> WorkerOutput:
        return WorkerOutput(text=telemetry_answer("research"), model="some/model")

    await research()
    claims = read_claims(memory_dir)
    assert claims[0]["model"] == "some/model"


def test_the_false_claim_rate() -> None:
    records: list[dict[str, Any]] = [
        {"step": "a", "claimed_status": "completed", "verification": {"ok": True}},
        {"step": "a", "claimed_status": "completed", "verification": {"ok": False}},
        {"step": "b", "claimed_status": "in_progress", "verification": None},
    ]
    stats = compute_stats(records)
    assert stats.total_claims == 3
    assert stats.completed_claims == 2
    assert stats.verified_true == 1
    assert stats.verified_false == 1
    assert stats.false_claim_rate == pytest.approx(0.5)
    assert stats.by_step["a"]["verified_false"] == 1


# ----------------------------------------------------------------------
# the hash chain
# ----------------------------------------------------------------------
def test_the_claims_ledger_is_a_hash_chain(tmp_path: Path) -> None:
    ledger = ClaimsLedger(tmp_path)
    ledger.append(step="a", attempt=1, claimed_status="completed")
    ledger.append(step="a", attempt=2, claimed_status="completed")
    lines, breaks = verify_chain(tmp_path / "claims.jsonl")
    assert lines == 2
    assert breaks == []


def test_a_changed_line_breaks_the_chain(tmp_path: Path) -> None:
    ledger = ClaimsLedger(tmp_path)
    ledger.append(step="a", attempt=1, claimed_status="completed")
    ledger.append(step="a", attempt=2, claimed_status="completed")
    path = tmp_path / "claims.jsonl"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("completed", "failed"), encoding="utf-8")
    lines, breaks = verify_chain(path)
    assert lines == 2
    assert breaks, "the chain must report the break"
    # The second line no longer follows the (edited) first one.
    assert breaks[0].line == 2


def test_a_removed_line_breaks_the_chain(tmp_path: Path) -> None:
    ledger = ClaimsLedger(tmp_path)
    ledger.append(step="a", attempt=1, claimed_status="completed")
    ledger.append(step="a", attempt=2, claimed_status="completed")
    ledger.append(step="a", attempt=3, claimed_status="completed")
    path = tmp_path / "claims.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    # The second line is removed: the third one no longer follows the first.
    path.write_text(lines[0] + lines[2], encoding="utf-8")
    _, breaks = verify_chain(path)
    assert breaks
    assert breaks[0].line == 2


def test_the_chain_hash_is_the_sha256_of_the_line() -> None:
    import hashlib

    line = '{"a": 1}'
    assert chain_hash(line) == hashlib.sha256(line.encode("utf-8")).hexdigest()


async def test_the_event_log_is_a_hash_chain(memory_dir: Path) -> None:
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research")

    await research()
    lines, breaks = verify_chain(memory_dir / "events.jsonl")
    assert lines >= 1
    assert breaks == []


# ----------------------------------------------------------------------
# the new verifiers
# ----------------------------------------------------------------------
async def test_python_syntax_valid(work_dir: Path, memory_dir: Path) -> None:
    from agentether import Telemetry, VerifyContext

    ctx = VerifyContext(
        step="research",
        telemetry=Telemetry(step="research", status="completed", summary="s", progress=100),
        raw_output="",
        memory_dir=memory_dir,
        workdir=work_dir,
    )
    (work_dir / "ok.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    result = await python_syntax_valid("ok.py")(ctx)
    assert result.ok is True

    (work_dir / "broken.py").write_text("def f(:\n", encoding="utf-8")
    result = await python_syntax_valid("broken.py")(ctx)
    assert result.ok is False
    assert "not valid Python" in result.reason


async def test_markdown_has_headings(work_dir: Path, memory_dir: Path) -> None:
    from agentether import Telemetry, VerifyContext

    ctx = VerifyContext(
        step="research",
        telemetry=Telemetry(step="research", status="completed", summary="s", progress=100),
        raw_output="",
        memory_dir=memory_dir,
        workdir=work_dir,
    )
    (work_dir / "notes.md").write_text("# Title\n## Findings\n", encoding="utf-8")
    result = await markdown_has_headings("notes.md", ["## Findings"])(ctx)
    assert result.ok is True
    result = await markdown_has_headings("notes.md", ["## Context"])(ctx)
    assert result.ok is False
    assert "## Context" in result.reason


async def test_json_schema_subset(work_dir: Path, memory_dir: Path) -> None:
    from agentether import Telemetry, VerifyContext

    ctx = VerifyContext(
        step="research",
        telemetry=Telemetry(step="research", status="completed", summary="s", progress=100),
        raw_output="",
        memory_dir=memory_dir,
        workdir=work_dir,
    )
    schema = {
        "type": "object",
        "required": ["a", "b"],
        "properties": {
            "a": {"type": "integer", "minimum": 1},
            "b": {"type": "string", "enum": ["x", "y"]},
        },
    }
    (work_dir / "data.json").write_text('{"a": 3, "b": "x"}', encoding="utf-8")
    result = await json_schema_subset("data.json", schema)(ctx)
    assert result.ok is True

    (work_dir / "bad.json").write_text('{"a": 0, "b": "z"}', encoding="utf-8")
    result = await json_schema_subset("bad.json", schema)(ctx)
    assert result.ok is False
    assert result.evidence["problems"]


# ----------------------------------------------------------------------
# the commands
# ----------------------------------------------------------------------
async def test_the_stats_command(
    memory_dir: Path, work_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
        workdir=str(work_dir),
    )

    @orch.guard_step("research", verify=[artifacts_exist()])
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research", artifacts=["missing.md"])

    with pytest.raises(CircuitBreakerOpenError):
        await research()

    assert main(["stats", str(memory_dir), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["overall"]["total_claims"] == 1
    assert payload["overall"]["false_claim_rate"] == 1.0


async def test_the_audit_command(memory_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research")

    await research()

    assert main(["audit", str(memory_dir), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


async def test_the_audit_command_reports_a_broken_chain(
    memory_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research")

    await research()
    path = memory_dir / "events.jsonl"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("step_completed", "step_broken "), encoding="utf-8")

    assert main(["audit", str(memory_dir), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False


async def test_the_report_command(memory_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research")

    await research()

    assert main(["report", str(memory_dir)]) == 0
    out = capsys.readouterr().out
    assert "# AgenTether run report" in out
    assert "research" in out


async def test_the_html_report_escapes_the_agent_text(memory_dir: Path) -> None:
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research", summary="<script>alert(1)</script>")

    await research()
    report = build_report(memory_dir)
    html_text = render_html(report)
    assert "<script>alert(1)</script>" not in html_text
    assert "&lt;script&gt;" in html_text


async def test_the_markdown_report_is_readable(memory_dir: Path) -> None:
    orch = AutoOrchestrator(
        roadmap=["research"],
        memory_dir=str(memory_dir),
        timeout_seconds=5,
        max_retries=1,
    )

    @orch.guard_step("research")
    async def research(ctx: StepContext) -> str:
        return telemetry_answer("research")

    await research()
    report = build_report(memory_dir)
    text = render_markdown(report)
    assert "Claims recorded" in text
    assert "| Step | Attempt | Claimed | Summary | Verified |" in text
