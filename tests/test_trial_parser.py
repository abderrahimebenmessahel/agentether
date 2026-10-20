"""The parser of the files of an answer, and the faults built on it.

The parser of the trial v2 closed a file on the next fence whatever it
was, so a Markdown file that shows how to run a script (a code block
**inside** the file) was cut in the middle: the file on disk was the
beginning of the file, the rest was lost, and three of the seventeen false
completions of the trial v2 were caused by that and not by the model.

The parser now follows the rule of CommonMark (a fence with an info string
opens a block and never closes another one, and a block closes on a fence
at least as long as its own), and the prompt of the trial v3 asks for
**four** backticks.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))

from harness import (
    fenced_blocks,
    inject_fault,
    parse_file_blocks,
    write_answer_files,
)

NESTED = """\
````
FILE: README.md
# Project

Run it with:
```bash
python build.py
```

The script defines `build_thing` and prints 15.
````
"""

TWO_FILES = """\
````
FILE: build.py
def build_thing():
    pass
````

````
FILE: README.md
# Project
````
"""

SPELLING_BEFORE = """\
FILE: notes.md
```
# Notes
## Context
hello
```
"""


def test_a_file_with_a_code_block_inside_is_not_cut() -> None:
    """The block of a file is closed by its own fence and not by another one."""
    blocks = parse_file_blocks(NESTED)
    assert len(blocks) == 1
    path, content = blocks[0]
    assert path == "README.md"
    assert "python build.py" in content
    assert "The script defines `build_thing` and prints 15." in content


def test_two_files_are_two_blocks() -> None:
    """Every file of an answer is found."""
    blocks = parse_file_blocks(TWO_FILES)
    assert [path for path, _ in blocks] == ["build.py", "README.md"]


def test_the_spelling_before_the_block_is_accepted() -> None:
    """The ``FILE:`` line may stand before the block."""
    blocks = parse_file_blocks(SPELLING_BEFORE)
    assert len(blocks) == 1
    path, content = blocks[0]
    assert path == "notes.md"
    assert "## Context" in content


def test_a_fence_with_an_info_string_never_closes_a_block() -> None:
    """The rule of CommonMark: `````bash`` opens a block."""
    answer = "````\nFILE: a.md\ntext\n```bash\ncode\n```\nmore\n````\n"
    blocks = fenced_blocks(answer)
    assert len(blocks) == 1
    assert "more" in blocks[0][2]


def test_the_file_is_written_whole(tmp_path: Path) -> None:
    """The sandbox holds the whole file, and not its beginning."""
    written = write_answer_files(NESTED, tmp_path)
    assert written == ["README.md"]
    content = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "The script defines `build_thing` and prints 15." in content


def test_the_fault_that_drops_the_blocks_removes_every_block() -> None:
    """The fault works with the fences of the protocol of the trial v3."""
    answer = inject_fault(TWO_FILES, "drop_file_block", None)
    assert "FILE:" not in answer
    assert parse_file_blocks(answer) == []


def test_the_fault_that_lies_keeps_the_claim() -> None:
    """The claim of the model survives the fault."""
    answer = '````\nFILE: a.md\ntext\n````\n{"step": "s", "status": "completed"}\n'
    faulty = inject_fault(answer, "lie", None)
    assert "FILE:" not in faulty
    assert '"status": "completed"' in faulty


def test_the_fault_that_truncates_halves_the_first_block() -> None:
    """The fault cuts the first file of the answer in the middle."""
    answer = "````\nFILE: a.md\n" + ("x" * 100) + "\n````\n"
    faulty = inject_fault(answer, "truncate_file", None)
    blocks = parse_file_blocks(faulty)
    assert len(blocks) == 1
    path, content = blocks[0]
    assert path == "a.md"
    assert len(content) < 60


def test_the_fault_that_replays_returns_the_previous_answer() -> None:
    """The replay fault returns the previous answer."""
    assert inject_fault("new", "replay_previous", "old") == "old"


@pytest.mark.parametrize("fault", ["drop_file_block", "truncate_file", "lie", "wrong_step"])
def test_a_fault_never_raises(fault: str) -> None:
    """Every fault of the schedule works on an answer that holds nothing."""
    assert isinstance(inject_fault("", fault, None), str)
    assert isinstance(inject_fault("no block here", fault, None), str)
