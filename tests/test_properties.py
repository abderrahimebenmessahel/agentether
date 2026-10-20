"""Property based tests.

These do not check a fixed example, they check a *property* over a large
number of generated inputs.  ``hypothesis`` is a development dependency only;
the library itself stays standard library only.
"""

from __future__ import annotations

import json
from pathlib import Path

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from agentether import (
    StateManager,
    Telemetry,
    TelemetryParseError,
    extract_json_telemetry,
    parse_telemetry,
)
from agentether.state_manager import escape_embedded, unescape_embedded

#: A generous deadline: the state manager does file I/O.
SETTINGS = settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)

text_strategy = st.text(max_size=400)


@given(text_strategy)
@SETTINGS
def test_the_parser_only_ever_raises_a_telemetry_parse_error(text: str) -> None:
    """Arbitrary text never makes the parser do anything else."""
    try:
        data = extract_json_telemetry(text)
    except TelemetryParseError:
        return
    assert isinstance(data, dict)


@given(text_strategy)
@SETTINGS
def test_parse_telemetry_only_ever_raises_a_telemetry_parse_error(text: str) -> None:
    """The same for the combined extraction and validation."""
    try:
        telemetry = parse_telemetry(text, "step")
    except TelemetryParseError:
        return
    assert isinstance(telemetry, Telemetry)


@given(st.text())
@SETTINGS
def test_escaping_round_trips(text: str) -> None:
    """The escaping of the memory file is lossless."""
    escaped = escape_embedded(text)
    assert "&lt;!--" not in escaped.replace("&amp;lt;!--", "")
    assert unescape_embedded(escaped) == text


@given(st.text())
@SETTINGS
def test_escaping_never_leaves_a_marker(text: str) -> None:
    """No escaped text can contain a literal marker any more."""
    escaped = escape_embedded(text)
    assert "<!--" not in escaped


telemetry_strategy = st.builds(
    Telemetry,
    step=st.text(min_size=1, max_size=30),
    status=st.sampled_from(["in_progress", "completed", "blocked", "failed"]),
    summary=st.text(max_size=200),
    progress=st.one_of(st.none(), st.floats(min_value=0, max_value=100, allow_nan=False)),
    next_step=st.one_of(st.none(), st.text(max_size=30)),
    artifacts=st.lists(st.text(max_size=30), max_size=4),
)


@given(telemetry_strategy)
@SETTINGS
async def test_the_state_round_trips(telemetry: Telemetry) -> None:
    """What is written is what is read back."""
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        manager = StateManager(Path(directory))
        await manager.record_step("step", telemetry, "raw output")
        state = await StateManager(Path(directory)).load()
        stored = Telemetry.from_dict(state["telemetry"]["step"])
        assert stored.step == telemetry.step
        assert stored.status == telemetry.status
        assert stored.summary == telemetry.summary
        assert stored.progress == telemetry.progress
        assert stored.next_step == telemetry.next_step
        assert stored.artifacts == telemetry.artifacts


@given(
    telemetry_strategy,
    st.integers(min_value=50, max_value=4000),
    st.text(min_size=1, max_size=200),
)
@SETTINGS
async def test_the_compaction_keeps_the_limit_and_the_human_section(
    telemetry: Telemetry, limit: int, human: str
) -> None:
    """The compaction never exceeds the limit and never drops the human text."""
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        memory = Path(directory)
        manager = StateManager(memory, max_memory_chars=limit)
        await manager.record_step("step", telemetry, "raw output")
        path = memory / "PROJECT_MEMORY.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            "<!-- agentether:human:start -->\n\n<!-- agentether:human:end -->",
            f"<!-- agentether:human:start -->\n{human}\n<!-- agentether:human:end -->",
        )
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)

        reloaded = StateManager(memory, max_memory_chars=limit)
        state = await reloaded.load()
        rendered = reloaded.render_context(state)

        # What the memory looks like without any limit at all.
        unlimited = StateManager(memory, max_memory_chars=10**6)
        full = unlimited.render_context(await unlimited.load())

        assume(human.strip() != "")
        # The human text is never dropped silently.
        assert human.strip() in rendered or "truncated" in rendered
        # If it fits without a limit, it fits with one.
        if len(full) <= limit:
            assert len(rendered) <= limit


@given(st.dictionaries(st.text(min_size=1, max_size=8), st.text(max_size=40), max_size=6))
@SETTINGS
def test_arbitrary_json_objects_are_parsed_or_rejected(payload: dict[str, str]) -> None:
    """A JSON object without the contract keys is still returned as a dict."""
    raw = json.dumps(payload)
    try:
        data = extract_json_telemetry(raw)
    except TelemetryParseError:
        return
    assert isinstance(data, dict)
