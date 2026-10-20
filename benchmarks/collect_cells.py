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
from pathlib import Path
from typing import Any

__all__ = ["collect"]


def collect(cells: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """The cells that are measurements, and the number of the dropped ones.

    Args:
        cells: The cells of the progress file.

    Returns:
        The cells with at least one request, and the number of the cells
        that were dropped.
    """
    kept = [cell for cell in cells if int(cell.get("attempts", 0) or 0) > 0]
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
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
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
    kept, dropped = collect(cells)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for cell in kept:
            handle.write(json.dumps(cell, sort_keys=True) + "\n")
    print(f"cells kept: {len(kept)}")
    print(f"cells dropped (no attempt: the run was stopped in the middle): {dropped}")
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
