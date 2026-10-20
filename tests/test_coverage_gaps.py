"""Tests that cover the paths the other tests do not reach.

They exist for the coverage of the error paths of the verifiers, the commands
and the report -- the branches that only run when something goes wrong.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentether import (
    StateManager,
    Telemetry,
    VerifyContext,
    callable_verifier,
    file_contains,
    file_exists,
    json_file_valid,
    json_schema_subset,
    llm_judge,
    markdown_has_headings,
    python_syntax_valid,
)
from agentether.cli import main
from agentether.ledger import ClaimsLedger, read_claims, verify_chain
from agentether.report import build_report, render_html, render_markdown
from agentether.verifier import (
    PathNotAllowedError,
    executable_is_inside_workdir,
    resolve_within,
)


def make_context(work_dir: Path, memory_dir: Path) -> VerifyContext:
    """A verify context for the work directory."""
    return VerifyContext(
        step="research",
        telemetry=Telemetry(step="research", status="completed", summary="s", progress=100),
        raw_output="",
        memory_dir=memory_dir,
        workdir=work_dir,
    )


# ----------------------------------------------------------------------
# the verifiers: the failure paths
# ----------------------------------------------------------------------
async def test_every_file_verifier_rejects_a_missing_file(work_dir: Path, memory_dir: Path) -> None:
    ctx = make_context(work_dir, memory_dir)
    for verifier in (
        file_exists("missing.md"),
        file_contains("missing.md", "x"),
        json_file_valid("missing.json"),
        json_schema_subset("missing.json", {"type": "object"}),
        markdown_has_headings("missing.md", ["## A"]),
        python_syntax_valid("missing.py"),
    ):
        result = await verifier(ctx)
        assert result.ok is False
        assert "does not exist" in result.reason


async def test_every_file_verifier_rejects_a_path_outside_the_workdir(
    work_dir: Path, memory_dir: Path
) -> None:
    ctx = make_context(work_dir, memory_dir)
    for verifier in (
        file_exists("../escape.md"),
        file_contains("/etc/passwd", "x"),
        json_file_valid("../escape.json"),
        json_schema_subset("../escape.json", {}),
        markdown_has_headings("../escape.md", ["## A"]),
        python_syntax_valid("../escape.py"),
    ):
        result = await verifier(ctx)
        assert result.ok is False
        assert "not allowed" in result.reason or "absolute" in result.reason


async def test_a_file_that_is_a_directory_is_not_a_file(work_dir: Path, memory_dir: Path) -> None:
    (work_dir / "a-directory").mkdir()
    ctx = make_context(work_dir, memory_dir)
    result = await file_exists("a-directory")(ctx)
    assert result.ok is False
    assert "not a file" in result.reason


async def test_the_json_schema_subset_checks_the_type(work_dir: Path, memory_dir: Path) -> None:
    ctx = make_context(work_dir, memory_dir)
    (work_dir / "data.json").write_text('"a string"', encoding="utf-8")
    result = await json_schema_subset("data.json", {"type": "object"})(ctx)
    assert result.ok is False
    assert "the type" in result.reason


async def test_the_json_schema_subset_checks_arrays_and_enums(
    work_dir: Path, memory_dir: Path
) -> None:
    ctx = make_context(work_dir, memory_dir)
    (work_dir / "list.json").write_text("[1, 2]", encoding="utf-8")
    schema = {"type": "array", "items": {"type": "string"}}
    result = await json_schema_subset("list.json", schema)(ctx)
    assert result.ok is False
    (work_dir / "list.json").write_text('["a", "b"]', encoding="utf-8")
    result = await json_schema_subset("list.json", schema)(ctx)
    assert result.ok is True


async def test_the_json_schema_subset_reports_a_broken_file(
    work_dir: Path, memory_dir: Path
) -> None:
    ctx = make_context(work_dir, memory_dir)
    (work_dir / "data.json").write_text("{not json", encoding="utf-8")
    result = await json_schema_subset("data.json", {"type": "object"})(ctx)
    assert result.ok is False
    assert "not valid JSON" in result.reason


async def test_a_verifier_that_returns_nothing_is_a_success(
    work_dir: Path, memory_dir: Path
) -> None:
    ctx = make_context(work_dir, memory_dir)
    result = await callable_verifier(lambda ctx: None)(ctx)
    assert result.ok is True


async def test_a_verifier_that_returns_something_odd_fails(
    work_dir: Path, memory_dir: Path
) -> None:
    ctx = make_context(work_dir, memory_dir)
    result = await callable_verifier(lambda ctx: 42)(ctx)
    assert result.ok is False
    assert "unsupported" in result.reason


async def test_the_llm_judge_uses_the_same_adapter(work_dir: Path, memory_dir: Path) -> None:
    ctx = make_context(work_dir, memory_dir)
    result = await llm_judge(lambda ctx: "the answer is wrong")(ctx)
    assert result.ok is False
    assert result.reason == "the answer is wrong"


def test_resolve_within_rejects_an_empty_path(tmp_path: Path) -> None:
    with pytest.raises(PathNotAllowedError):
        resolve_within(tmp_path, "   ")


def test_executable_is_inside_workdir_for_a_bare_name(tmp_path: Path) -> None:
    # A name that is not on the PATH cannot be inside the work directory.
    assert executable_is_inside_workdir("definitely-not-a-real-command", tmp_path) is False


# ----------------------------------------------------------------------
# the ledger
# ----------------------------------------------------------------------
def test_read_claims_skips_a_broken_line(tmp_path: Path) -> None:
    path = tmp_path / "claims.jsonl"
    path.write_text('{"step": "a"}\nnot json\n', encoding="utf-8")
    records = read_claims(tmp_path)
    assert len(records) == 1


def test_the_ledger_continues_an_existing_chain(tmp_path: Path) -> None:
    first = ClaimsLedger(tmp_path)
    first.append(step="a", attempt=1, claimed_status="completed")
    second = ClaimsLedger(tmp_path)
    second.append(step="a", attempt=2, claimed_status="completed")
    lines, breaks = verify_chain(tmp_path / "claims.jsonl")
    assert lines == 2
    assert breaks == []


def test_a_ledger_of_an_unreadable_file_starts_over(tmp_path: Path) -> None:
    path = tmp_path / "claims.jsonl"
    path.write_bytes(b"\xff\xfe not utf-8\n")
    ledger = ClaimsLedger(tmp_path)
    ledger.append(step="a", attempt=1, claimed_status="completed")
    assert path.exists()


# ----------------------------------------------------------------------
# the report and the commands
# ----------------------------------------------------------------------
async def test_the_report_of_an_empty_project(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    assert report["claims"] == []
    assert report["events"] == []
    markdown = render_markdown(report)
    assert "_(no roadmap recorded)_" in markdown
    html = render_html(report)
    assert "<html" in html
    assert "no roadmap recorded" in html


async def test_the_report_of_a_broken_state(tmp_path: Path) -> None:
    (tmp_path / "PROJECT_MEMORY.md").write_text("broken", encoding="utf-8")
    report = build_report(tmp_path)
    assert report["roadmap"] == []


def test_the_stats_command_of_an_empty_project(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["stats", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["overall"]["total_claims"] == 0
    assert payload["overall"]["false_claim_rate"] == 0.0


def test_the_stats_command_in_text(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["stats", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "claims recorded" in out
    assert "false claim rate" in out


def test_the_audit_command_of_an_empty_project(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["audit", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert main(["audit", str(tmp_path)]) == 0
    assert "not present" in capsys.readouterr().out


def test_the_report_command_writes_a_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "report.md"
    assert main(["report", str(tmp_path), "--output", str(target)]) == 0
    assert "report written to" in capsys.readouterr().out
    assert target.exists()


def test_the_report_command_in_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["report", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["memory_dir"] == str(tmp_path)


def test_the_report_command_in_html(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["report", str(tmp_path), "--format", "html"]) == 0
    out = capsys.readouterr().out
    assert "<html" in out


def test_the_status_command_of_a_broken_project(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "PROJECT_MEMORY.md").write_text("broken", encoding="utf-8")
    assert main(["status", str(tmp_path), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False


# ----------------------------------------------------------------------
# the state manager
# ----------------------------------------------------------------------
async def test_the_state_manager_rejects_a_negative_budget(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        StateManager(tmp_path, max_memory_chars=-1)


async def test_the_state_manager_of_a_missing_directory(tmp_path: Path) -> None:
    manager = StateManager(tmp_path / "deep" / "memory")
    state = await manager.load()
    assert state["completed_steps"] == []


async def test_the_reset_of_a_state_manager(tmp_path: Path) -> None:
    manager = StateManager(tmp_path)
    await manager.record_step(
        "research",
        Telemetry(step="research", status="completed", summary="s", progress=100),
        "out",
    )
    await manager.reset()
    state = await manager.load()
    assert state["completed_steps"] == []
    assert not list((tmp_path / "steps").glob("*.md"))


async def test_a_budget_exceeded_is_recorded(tmp_path: Path) -> None:
    manager = StateManager(tmp_path)
    await manager.record_budget_exceeded("research", "tokens", 100, 120)
    state = await manager.load()
    assert state["last_failure"]["status"] == "budget_exceeded"
    assert "tokens" in state["last_failure"]["reason"]
