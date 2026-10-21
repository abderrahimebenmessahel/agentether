"""Rebuild the template of the report from the filled report.

The tables of the report are **extracted** from the generated documents
by :mod:`fill_report`; the template must therefore hold the markers and
not the tables, or the tables of the template would freeze the numbers
of the day it was written.

    python benchmarks/report_template.py docs/final-report-2026-10-21.md
"""

from __future__ import annotations

import sys
from pathlib import Path

#: The header of a table and the marker that replaces it.  The first
#: table of a header wins, so the order of the list is the order of the
#: tables in the document.
HEADERS: list[tuple[str, str]] = [
    ("| Provider | Model | Pilot (naive, natural) |", "{{TABLE:V3-MODELS}}"),
    ("| Model | Arm | N | Dropped |", "{{TABLE:V3-INJECTED}}"),
    ("| Model | Arm | N | Dropped |", "{{TABLE:V3-NATURAL}}"),
    (
        "| Model | N | MDE | H1: correct completion | H2: false completion (primary) | H3:",
        "{{TABLE:V3-VERDICTS}}",
    ),
    (
        "| Model | N | MDE | H1: correct completion | H2: false completion (primary) |",
        "{{TABLE:V3-NAIVE-VERDICTS}}",
    ),
    ("| Model | Condition | H4 (paired) |", "{{TABLE:V3-H4}}"),
    ("| Model | Condition | Arm | N | Correct |", "{{TABLE:V3-HONESTY}}"),
]


def table_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """The blocks of the table of a document."""
    blocks: list[tuple[int, int]] = []
    index = 0
    while index < len(lines):
        if lines[index].startswith("|"):
            start = index
            while index < len(lines) and lines[index].startswith("|"):
                index += 1
            blocks.append((start, index))
            continue
        index += 1
    return blocks


def main() -> int:
    """Rebuild the template."""
    report = Path(sys.argv[1])
    lines = report.read_text(encoding="utf-8").splitlines()
    blocks = table_blocks(lines)
    out: list[str] = []
    index = 0
    block_index = 0
    while index < len(lines):
        if block_index < len(blocks) and index == blocks[block_index][0]:
            start, end = blocks[block_index]
            header = lines[start]
            marker = None
            for candidate, name in HEADERS:
                if header.startswith(candidate):
                    marker = name
                    break
            if marker is None:
                out.extend(lines[start:end])
            else:
                out.append(marker)
            index = end
            block_index += 1
            continue
        out.append(lines[index])
        index += 1
    template = Path(__file__).resolve().parent / report.stem.replace(
        "final-report-", "report-template-"
    )
    template.with_suffix(".md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"template: {template.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
