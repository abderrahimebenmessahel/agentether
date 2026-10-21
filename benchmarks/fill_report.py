"""Fill the tables of the report from the generated documents.

The report quotes the tables of `docs/evidence.md` and of
`docs/natural-frequency.md`; they are **extracted**, not typed, so the
report cannot contradict the generated documents.  The prose of the
report lives in the template (`benchmarks/report-template-*.md`) and the
markers of the tables are replaced by the tables themselves.

    python benchmarks/fill_report.py docs/final-report-2026-10-21.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence.md"
NATURAL = ROOT / "docs" / "natural-frequency.md"


def section(text: str, title: str, level: str = "###") -> str:
    """The section that follows a title, up to the next heading."""
    marker = f"{level} {title}"
    if marker not in text:
        raise SystemExit(f"the title {title!r} is not in the document")
    rest = text[text.index(marker) + len(marker) :]
    block: list[str] = []
    for line in rest.splitlines():
        if line.startswith("#"):
            break
        block.append(line)
    return "\n".join(block)


def table(text: str, title: str, level: str = "###") -> str:
    """The first table of a section, without the prose around it."""
    block = section(text, title, level)
    rows: list[str] = []
    for line in block.splitlines():
        if line.startswith("|"):
            rows.append(line)
            continue
        if rows:
            break
    return "\n".join(rows)


def sections_with_tables(text: str, level: str = "##") -> str:
    """Every section of a level and the table that follows it."""
    out: list[str] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith(level + " ") and not line.startswith(level * 2):
            out.append("")
            out.append(line)
            index += 1
            while index < len(lines) and not lines[index].startswith(level + " "):
                if lines[index].startswith("|"):
                    out.append(lines[index])
                index += 1
            continue
        index += 1
    return chr(10).join(out).strip()


def total_row(table_text: str) -> tuple[int, int, float]:
    """The numbers of the "total" row of a table of totals."""
    for line in table_text.splitlines():
        cells = [cell.strip().strip("*") for cell in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0] == "total":
            return int(cells[1]), int(cells[2]), float(cells[3])
    raise SystemExit("the table of the totals has no total row")


def spaced(number: int) -> str:
    """The number with the thin spaces of the report (1 234 567)."""
    return f"{number:,}".replace(",", " ")


def totals_both(v3: str, v2: str) -> str:
    """The table of the totals of the two runs together."""
    a = total_row(table(v3, "The request and token totals"))
    b = total_row(table(v2, "The request and token totals"))
    lines = [
        "| Run | Requests | Tokens | Wall clock (s) |",
        "| --- | --- | --- | --- |",
        f"| trial v3 (the 20th and the 21st of October) | {spaced(a[0])} |"
        f" {spaced(a[1])} | {a[2]:.1f} |",
        f"| trial v2 (the supplementary run of the 20th of October) | {spaced(b[0])} |"
        f" {spaced(b[1])} | {b[2]:.1f} |",
        f"| **total** | **{spaced(a[0] + b[0])}** | **{spaced(a[1] + b[1])}** |"
        f" **{a[2] + b[2]:.1f}** |",
    ]
    return chr(10).join(lines)


def totals_growth(v3: str, v2: str) -> str:
    """The sentence of the growth of the trial v3 since the 20th of October."""
    a = total_row(table(v3, "The request and token totals"))
    b = total_row(table(v2, "The request and token totals"))
    return (
        f"The trial v3 grew by {spaced(a[0])} requests and {spaced(a[1])} tokens since "
        f"the report of the 20th of October, and the trial v2 did not move at all: "
        f"its {spaced(b[0])} requests and its {spaced(b[1])} tokens are the same "
        "numbers as then."
    )


def main() -> int:
    """Fill the report."""
    report = Path(sys.argv[1])
    template = (
        Path(__file__).resolve().parent / report.stem.replace("final-report-", "report-template-")
    ).with_suffix(".md")
    source = template if template.exists() else report
    text = source.read_text(encoding="utf-8")
    evidence = EVIDENCE.read_text(encoding="utf-8")
    natural = NATURAL.read_text(encoding="utf-8") if NATURAL.exists() else ""

    # The v3 run is the first section of the evidence document; the v2 run
    # is the second one.  The tables of the v3 run are the ones that the
    # report quotes.
    v3 = evidence[evidence.index("## Trial v3") : evidence.index("## Trial v2")]
    v2 = evidence[evidence.index("## Trial v2") :]

    replacements = {
        "{{TABLE:V3-MODELS}}": table(v3, "The models of the run"),
        "{{TABLE:V3-TOTALS}}": table(v3, "The request and token totals"),
        "{{TABLE:V3-INJECTED}}": table(v3, "Condition: injected"),
        "{{TABLE:V3-NATURAL}}": table(v3, "Condition: natural"),
        "{{TABLE:V3-VERDICTS}}": table(v3, "The verdicts"),
        "{{TABLE:V3-NAIVE-VERDICTS}}": table(v3, "The verdicts against the naive arm"),
        "{{TABLE:V3-H4}}": table(v3, "The contribution of the declarative expectations (H4)"),
        "{{TABLE:V3-HONESTY}}": table(v3, "The cost of honesty"),
        "{{TABLE:V2-TOTALS}}": table(v2, "The request and token totals"),
        "{{TABLE:TOTALS-BOTH}}": totals_both(v3, v2),
        "{{TOTALS-GROWTH}}": totals_growth(v3, v2),
        "{{TABLE:NATURAL-FREQUENCY}}": sections_with_tables(natural)
        if natural
        else "(the document of the natural frequency is not there yet)",
    }
    for marker, value in replacements.items():
        text = text.replace(marker, value)

    left = re.findall(r"\{\{[A-Z0-9\-]+\}\}", text)
    if left:
        raise SystemExit(f"the markers {left} were not filled")
    report.write_text(text, encoding="utf-8")
    print(f"filled: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
