"""Collect the cells of a run into the file the evidence document reads.

The progress file of a run holds one JSON line per cell.  A cell whose
**requests** are zero is not a measurement: it is a cell the arm could
not measure because the run was stopped (the daily cap was reached) in the
middle of it.  Such a cell is dropped here, and the count of the dropped
cells is printed: nothing is hidden.

    python benchmarks/collect_cells.py --progress logs/trial-v3-cerebras/progress.jsonl \\
        --out benchmarks/results/trial-v3-cerebras-cells.jsonl

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trial import is_measurement

__all__ = ["collect"]


def collect(cells: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """The cells that are measurements, and the number of the dropped ones.

    A cell is a measurement when the arm got **at least one answer** from
    the model.  A cell whose calls were all refused by the provider (a
    rate limit) is **not** a measurement, and neither is the cell of a run
    that was stopped in the middle of it.  The rule is the same as the
    one of the resume of a run (:func:`trial.is_measurement`), so a cell
    that the collector drops is a cell the next run does again.

    Args:
        cells: The cells of the progress file.

    Returns:
        The cells with at least one request, and the number of the cells
        that were dropped.
    """
    kept = [cell for cell in cells if is_measurement(cell)]
    return kept, len(cells) - len(kept)


def main(argv: list[str] | None = None) -> int:
    """Read the progress file and write the cells file."""
    parser = argparse.ArgumentParser(description="Collect the cells of a run.")
    parser.add_argument("--progress", required=True, help="the progress file of the run")
    parser.add_argument("--out", required=True, help="the cells file to write")
    args = parser.parse_args(argv)

    path = Path(args.progress)
    cells: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    empty = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        # The cells that are **not measurements** are dropped **before**
        # the deduplication: a run that was stopped in the middle of a
        # cell wrote one, and the next run does that cell again.  Keeping
        # the first occurrence of the key would keep that one and lose
        # the measurement.
        if not is_measurement(record):
            empty += 1
            continue
        key = (
            str(record.get("model", "")),
            str(record.get("arm", "")),
            str(record.get("condition", "")),
            str(record.get("task", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        cells.append(record)
    kept, _dropped = collect(cells)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for cell in kept:
            handle.write(json.dumps(cell, sort_keys=True) + "\n")
    print(f"cells kept: {len(kept)}")
    print(
        "cells dropped (not a measurement: the run was stopped, or the"
        " provider refused the calls): " + str(empty)
    )
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
