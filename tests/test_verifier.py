"""Tests for the built-in verifiers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from context_guard import (
    Telemetry,
    VerifyContext,
    VerifyResult,
    artifacts_exist,
    callable_verifier,
    command_succeeds,
    file_contains,
    file_exists,
    json_file_valid,
    llm_judge,
)
from context_guard.verifier import PathNotAllowedError, resolve_within


def make_context(
    workdir: Path,
    memory_dir: Path,
    *,
    artifacts: list[str] | None = None,
    raw_output: str = "",
) -> VerifyContext:
    """Build a verify context for a step."""
    telemetry = Telemetry(
        step="research",
        status="completed",
        summary="done",
        progress=100,
        artifacts=artifacts or [],
    )
    return VerifyContext(
        step="research",
        telemetry=telemetry,
        raw_output=raw_output,
        memory_dir=memory_dir,
        workdir=workdir,
    )


async def test_file_exists_passes(work_dir: Path, memory_dir: Path) -> None:
    (work_dir / "report.md").write_text("content", encoding="utf-8")
    result = await file_exists("report.md")(make_context(work_dir, memory_dir))
    assert result.ok is True
    assert result.evidence["size"] == 7


async def test_file_exists_fails_when_missing(work_dir: Path, memory_dir: Path) -> None:
    result = await file_exists("report.md")(make_context(work_dir, memory_dir))
    assert result.ok is False
    assert "does not exist" in result.reason


async def test_file_exists_fails_when_empty(work_dir: Path, memory_dir: Path) -> None:
    (work_dir / "empty.md").write_text("", encoding="utf-8")
    result = await file_exists("empty.md")(make_context(work_dir, memory_dir))
    assert result.ok is False
    assert "empty" in result.reason

    result = await file_exists("empty.md", non_empty=False)(make_context(work_dir, memory_dir))
    assert result.ok is True


async def test_file_contains(work_dir: Path, memory_dir: Path) -> None:
    (work_dir / "notes.md").write_text("the answer is 42", encoding="utf-8")
    ok = await file_contains("notes.md", r"\d+")(make_context(work_dir, memory_dir))
    assert ok.ok is True
    bad = await file_contains("notes.md", "unicorn")(make_context(work_dir, memory_dir))
    assert bad.ok is False
    assert "unicorn" in bad.reason


async def test_json_file_valid(work_dir: Path, memory_dir: Path) -> None:
    (work_dir / "data.json").write_text('{"a": 1}', encoding="utf-8")
    ok = await json_file_valid("data.json", ["a"])(make_context(work_dir, memory_dir))
    assert ok.ok is True
    missing = await json_file_valid("data.json", ["b"])(make_context(work_dir, memory_dir))
    assert missing.ok is False
    assert "missing required keys" in missing.reason

    (work_dir / "broken.json").write_text("{not json}", encoding="utf-8")
    broken = await json_file_valid("broken.json")(make_context(work_dir, memory_dir))
    assert broken.ok is False
    assert "not valid JSON" in broken.reason


async def test_artifacts_exist_passes(work_dir: Path, memory_dir: Path) -> None:
    (work_dir / "a.txt").write_text("a", encoding="utf-8")
    ctx = make_context(work_dir, memory_dir, artifacts=["a.txt"])
    result = await artifacts_exist()(ctx)
    assert result.ok is True
    assert result.evidence["checked"] == ["a.txt"]


async def test_artifacts_exist_fails_when_missing(work_dir: Path, memory_dir: Path) -> None:
    ctx = make_context(work_dir, memory_dir, artifacts=["missing.txt"])
    result = await artifacts_exist()(ctx)
    assert result.ok is False
    assert "missing.txt" in result.reason


async def test_artifacts_exist_rejects_traversal(work_dir: Path, memory_dir: Path) -> None:
    ctx = make_context(work_dir, memory_dir, artifacts=["../outside.txt"])
    result = await artifacts_exist()(ctx)
    assert result.ok is False
    assert "not allowed" in result.reason


async def test_artifacts_exist_rejects_absolute_paths(work_dir: Path, memory_dir: Path) -> None:
    ctx = make_context(work_dir, memory_dir, artifacts=[str(work_dir / "a.txt")])
    result = await artifacts_exist()(ctx)
    assert result.ok is False
    assert "not allowed" in result.reason


async def test_artifacts_exist_rejects_symlink_escape(
    work_dir: Path, memory_dir: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link = work_dir / "link.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):  # pragma: no cover - Windows without privileges
        pytest.skip("symlinks are not supported in this environment")
    ctx = make_context(work_dir, memory_dir, artifacts=["link.txt"])
    result = await artifacts_exist()(ctx)
    assert result.ok is False
    assert "not allowed" in result.reason


def test_resolve_within_rejects_escapes(tmp_path: Path) -> None:
    with pytest.raises(PathNotAllowedError):
        resolve_within(tmp_path, "../escape")
    with pytest.raises(PathNotAllowedError):
        resolve_within(tmp_path, str(tmp_path / "absolute"))
    with pytest.raises(PathNotAllowedError):
        resolve_within(tmp_path, "")


async def test_command_succeeds(work_dir: Path, memory_dir: Path) -> None:
    verifier = command_succeeds([sys.executable, "-c", "print('hello')"], timeout=30)
    result = await verifier(make_context(work_dir, memory_dir))
    assert result.ok is True
    assert "hello" in result.evidence["stdout"]


async def test_command_fails_on_non_zero_exit(work_dir: Path, memory_dir: Path) -> None:
    verifier = command_succeeds([sys.executable, "-c", "raise SystemExit(3)"], timeout=30)
    result = await verifier(make_context(work_dir, memory_dir))
    assert result.ok is False
    assert "exit code 3" in result.reason


async def test_command_times_out(work_dir: Path, memory_dir: Path) -> None:
    verifier = command_succeeds([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.2)
    result = await verifier(make_context(work_dir, memory_dir))
    assert result.ok is False
    assert "timed out" in result.reason


async def test_command_does_not_use_a_shell(work_dir: Path, memory_dir: Path) -> None:
    # The argument is passed literally, so the shell must not expand it.
    verifier = command_succeeds(
        [sys.executable, "-c", "import sys; print(sys.argv[1])", "$HOME && echo pwned"],
        timeout=30,
    )
    result = await verifier(make_context(work_dir, memory_dir))
    assert result.ok is True
    assert "$HOME && echo pwned" in result.evidence["stdout"]


async def test_command_runs_in_the_work_directory(work_dir: Path, memory_dir: Path) -> None:
    verifier = command_succeeds([sys.executable, "-c", "import os; print(os.getcwd())"], timeout=30)
    result = await verifier(make_context(work_dir, memory_dir))
    assert result.ok is True
    assert str(work_dir.resolve()) in result.evidence["stdout"]


async def test_callable_verifier_with_a_sync_function(work_dir: Path, memory_dir: Path) -> None:
    verifier = callable_verifier(lambda ctx: True)
    result = await verifier(make_context(work_dir, memory_dir))
    assert result.ok is True

    verifier = callable_verifier(lambda ctx: "the file is wrong")
    result = await verifier(make_context(work_dir, memory_dir))
    assert result.ok is False
    assert result.reason == "the file is wrong"


async def test_callable_verifier_with_an_async_function(work_dir: Path, memory_dir: Path) -> None:
    async def judge(ctx: VerifyContext) -> VerifyResult:
        return VerifyResult.failure("nope", checked=1)

    result = await callable_verifier(judge)(make_context(work_dir, memory_dir))
    assert result.ok is False
    assert result.evidence["checked"] == 1


async def test_callable_verifier_turns_exceptions_into_failures(
    work_dir: Path, memory_dir: Path
) -> None:
    def broken(ctx: VerifyContext) -> bool:
        raise RuntimeError("verifier is broken")

    result = await callable_verifier(broken)(make_context(work_dir, memory_dir))
    assert result.ok is False
    assert "verifier is broken" in result.reason


async def test_llm_judge_is_only_an_interface(work_dir: Path, memory_dir: Path) -> None:
    async def judge(ctx: VerifyContext) -> bool:
        return ctx.telemetry.status == "completed"

    result = await llm_judge(judge)(make_context(work_dir, memory_dir))
    assert result.ok is True
