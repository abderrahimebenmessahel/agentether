"""Tests for the semantic loop and stall detection."""

from __future__ import annotations

from context_guard import LoopDetector, LoopPolicy, StallDetector, StallPolicy, Telemetry
from context_guard.loop_detector import fingerprint, jaccard, normalize


def test_normalize_masks_numbers_and_ids() -> None:
    assert normalize("Processed 42 items") == normalize("Processed 43 items")
    assert normalize("id a1b2c3d4e5f6") == normalize("id 0f9e8d7c6b5a")
    assert normalize("2024-01-01T10:00:00 done") == normalize("2025-02-02T11:11:11 done")


def test_fingerprints_of_equivalent_answers_match() -> None:
    first = fingerprint("Processed 42 items in 3 seconds, all good")
    second = fingerprint("Processed 43 items in 4 seconds, all good")
    assert jaccard(first, second) > 0.9


def test_fingerprints_of_different_answers_differ() -> None:
    first = fingerprint("The research phase found three credible sources")
    second = fingerprint("The writing phase produced the final report")
    assert jaccard(first, second) < 0.5


def test_loop_detector_trips_on_near_identical_output() -> None:
    detector = LoopDetector(LoopPolicy(repeat_window=3, similarity_threshold=0.9))
    template = "Working on the report, iteration {token}. The summary stays the same. " * 3
    # The loop trips as soon as three consecutive answers are alike.
    for token in ("a1b2c3d4", "e5f6a7b8"):
        verdict = detector.record("research", template.format(token=token))
        assert verdict.loop is False
    verdict = detector.record("research", template.format(token="09182736"))
    assert verdict.loop is True
    assert verdict.window == 3
    assert verdict.similarity > 0.9
    assert "change strategy" in verdict.hint


def test_loop_detector_does_not_trip_on_genuinely_different_output() -> None:
    detector = LoopDetector(LoopPolicy(repeat_window=3))
    texts = [
        "I searched for primary sources and found three papers.",
        "I compared the two frameworks and wrote down the differences.",
        "I drafted the summary section and checked the numbers.",
        "I reviewed the final document for consistency.",
    ]
    for text in texts:
        verdict = detector.record("research", text)
        assert verdict.loop is False


def test_loop_detector_can_be_disabled() -> None:
    detector = LoopDetector(LoopPolicy(enabled=False))
    text = "the same text " * 10
    for _ in range(5):
        verdict = detector.record("research", text)
        assert verdict.loop is False


def test_stall_detector_trips_on_repeated_in_progress() -> None:
    detector = StallDetector(StallPolicy(stall_window=3))
    for _ in range(3):
        telemetry = Telemetry(step="research", status="in_progress", summary="working")
        verdict = detector.record("research", telemetry)
    assert verdict.stalled is True
    assert "in_progress" in verdict.hint


def test_stall_detector_ignores_progress() -> None:
    detector = StallDetector(StallPolicy(stall_window=3))
    for progress in (10, 20, 30):
        telemetry = Telemetry(
            step="research", status="in_progress", summary="working", progress=progress
        )
        verdict = detector.record("research", telemetry)
    assert verdict.stalled is False


def test_stall_detector_ignores_completed_steps() -> None:
    detector = StallDetector(StallPolicy(stall_window=2))
    for _ in range(3):
        telemetry = Telemetry(step="research", status="completed", summary="done")
        verdict = detector.record("research", telemetry)
    assert verdict.stalled is False
