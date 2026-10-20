"""Tests for the telemetry extraction."""

from __future__ import annotations

import json

import pytest

from agentether import TelemetryParseError, extract_json_telemetry, parse_telemetry


def test_plain_json_object() -> None:
    raw = json.dumps({"step": "research", "status": "completed", "summary": "ok", "progress": 100})
    data = extract_json_telemetry(raw)
    assert data["step"] == "research"
    assert data["status"] == "completed"


def test_filler_text_around_json() -> None:
    raw = (
        "Sure! I looked into the topic.\n\n"
        "Here is the summary of my work:\n"
        '{"step": "research", "status": "completed", "summary": "found three sources"}\n\n'
        "Let me know if you need anything else."
    )
    data = extract_json_telemetry(raw)
    assert data["summary"] == "found three sources"


def test_fenced_block_is_preferred() -> None:
    raw = (
        "Some prose.\n"
        "```json\n"
        '{"step": "research", "status": "completed", "summary": "fenced"}\n'
        "```\n"
        "Trailing prose."
    )
    data = extract_json_telemetry(raw)
    assert data["summary"] == "fenced"


def test_fenced_block_without_language_tag() -> None:
    raw = '```\n{"step": "a", "status": "completed", "summary": "s"}\n```'
    data = extract_json_telemetry(raw)
    assert data["step"] == "a"


def test_nested_json_object() -> None:
    raw = json.dumps(
        {
            "step": "research",
            "status": "completed",
            "summary": "nested",
            "details": {"sources": [{"name": "a", "id": 1}], "count": 1},
        }
    )
    data = extract_json_telemetry(raw)
    assert data["details"]["count"] == 1
    assert data["summary"] == "nested"


def test_braces_inside_strings() -> None:
    raw = json.dumps(
        {
            "step": "research",
            "status": "completed",
            "summary": 'the API returns {"error": "not found"} for bad ids',
        }
    )
    data = extract_json_telemetry(raw)
    assert data["summary"] == 'the API returns {"error": "not found"} for bad ids'


def test_multiple_objects_last_valid_wins() -> None:
    raw = (
        '{"step": "old", "status": "in_progress", "summary": "first"}\n'
        "and then\n"
        '{"step": "research", "status": "completed", "summary": "second"}\n'
    )
    data = extract_json_telemetry(raw)
    assert data["summary"] == "second"


def test_non_dict_json_is_ignored() -> None:
    raw = '[1, 2, 3]\n{"step": "research", "status": "completed", "summary": "ok"}'
    data = extract_json_telemetry(raw)
    assert data["step"] == "research"


def test_trailing_comma_is_not_tolerated() -> None:
    raw = '{"step": "research", "status": "completed", "summary": "ok",}'
    with pytest.raises(TelemetryParseError):
        extract_json_telemetry(raw)


def test_no_json_raises() -> None:
    with pytest.raises(TelemetryParseError):
        extract_json_telemetry("I refuse to answer in JSON.")


def test_oversized_input_is_refused() -> None:
    payload = "x" * 1_000_001
    with pytest.raises(TelemetryParseError) as excinfo:
        extract_json_telemetry(payload)
    assert "too large" in str(excinfo.value)


def test_input_at_the_limit_is_accepted() -> None:
    payload = "x" * 1_000_000
    with pytest.raises(TelemetryParseError) as excinfo:
        extract_json_telemetry(payload)
    # Still no JSON, but the refusal must be about the missing JSON, not size.
    assert "too large" not in str(excinfo.value)


def test_parse_telemetry_returns_telemetry() -> None:
    raw = json.dumps(
        {
            "step": "research",
            "status": "completed",
            "summary": "done",
            "progress": 100,
            "next_step": "write",
            "artifacts": ["notes.md"],
        }
    )
    telemetry = parse_telemetry(raw, "research")
    assert telemetry.step == "research"
    assert telemetry.status == "completed"
    assert telemetry.progress == 100
    assert telemetry.next_step == "write"
    assert telemetry.artifacts == ["notes.md"]


def test_parse_telemetry_reports_the_step_name() -> None:
    with pytest.raises(TelemetryParseError) as excinfo:
        parse_telemetry("no json here", "research")
    assert excinfo.value.step == "research"


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "completed", "summary": "s"},
        {"step": "research", "summary": "s"},
        {"step": "research", "status": "completed"},
        {"step": 42, "status": "completed", "summary": "s"},
        {"step": "research", "status": "wat", "summary": "s"},
        {"step": "research", "status": "completed", "summary": "s", "progress": 200},
        {"step": "research", "status": "completed", "summary": "s", "artifacts": [1]},
    ],
)
def test_invalid_payloads_are_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(TelemetryParseError):
        parse_telemetry(json.dumps(payload), "research")
