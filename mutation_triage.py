"""Triage the mutants that survived, per file.

``mutmut`` says that a mutant *survived* when the test suite still passes
with it.  A survivor is not a bug: it is either an **equivalent mutant**
(the change does not change the behaviour) or a **gap of the test suite**
(the behaviour changed and no test noticed).  The two must be told apart,
otherwise the number of survivors says nothing.

The tool reads the ``.meta`` files of a ``mutmut`` run and classifies every
survivor by the *shape* of its change and by what that shape means:

``equivalent``
    The change cannot be seen by the caller: a keyword argument is
    replaced by ``None`` and the parameter really defaults to ``None``
    (this is checked with the abstract syntax tree of the module, not
    guessed), or the condition of an ``if`` is replaced by a constant that
    reproduces the original branch.
``cosmetic``
    Only the wording of a message changes: the behaviour of the library
    is the same, only what it says is different.
``gap``
    The behaviour changes and no test noticed.  These are the ones that
    need a test.

    cd ~/agentether-linux && ~/venvs/mut/bin/python mutation_triage.py

The tool writes ``mutation-triage.json`` and prints the counts.
"""

from __future__ import annotations

import ast
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

MUTANTS = Path("mutants")
OUTPUT = Path("mutation-triage.json")
SOURCE = Path("src/agentether")


#: A keyword argument of a call.
_KEYWORD = re.compile(r"^\s*(?P<name>[A-Za-z_][\w.]*)\s*=")
#: A string that is the key of a mapping.
_KEY_USE = re.compile(r"(\.get\(|\.pop\(|\[)\s*(['\"])")
#: A bare string literal.
_BARE_STRING = re.compile(r"""^\(?\s*(['"])(?P<value>.*?)\1\s*\)?,?\s*$""")
#: A call of a function or of a method with a keyword argument.
_CALL_WITH_KEYWORD = re.compile(r"^\s*(?P<name>[A-Za-z_][\w.]*)\s*=\s*(?P<value>.+?),?\s*$")


def _changed_lines(diff: str) -> tuple[str, str]:
    """The line that was removed and the line that was added."""
    removed = ""
    added = ""
    for line in diff.splitlines():
        if line.startswith("-") and not line.startswith("---"):
            removed += line[1:]
        elif line.startswith("+") and not line.startswith("+++"):
            added += line[1:]
    return removed, added


def _shape(removed: str, added: str) -> str:
    """The shape of a change."""
    if _KEYWORD.match(removed) and re.search(r"=\s*(None|True|False)\s*,?\s*$", added):
        return "argument"
    if re.search(r"\b(True|False)\b", removed) and re.search(r"\b(True|False)\b", added):
        return "boolean"
    if re.search(r"\d", removed) and re.search(r"\d", added):
        return "number"
    if re.search(r"(==|!=|<=|>=|<|>)", removed) and re.search(r"(==|!=|<=|>=|<|>)", added):
        return "comparison"
    if re.search(r"(['\"])", removed) and re.search(r"(['\"])", added):
        return "string"
    if re.search(r"\b(is|not in|in)\b", removed) and re.search(r"\b(is|not in|in)\b", added):
        return "comparison"
    return "other"


def _is_constant_condition(removed: str, added: str) -> bool:
    """Whether the change makes the condition of a branch constant.

    ``x is None or True`` and ``x is None and False`` are the two shapes
    of ``mutmut``: the condition of the branch becomes a constant.
    """
    return bool(re.search(r"\bor True\b", added) or re.search(r"\band False\b", added))


def _is_message(removed: str) -> bool:
    """Whether a string literal is the wording of a message.

    A message is an argument of a logging call, of ``raise`` or of an
    ``f`` string: changing it does not change the behaviour of the
    library, only what it says.
    """
    text = removed.strip()
    if text.startswith(('f"', "f'")):
        return True
    if not _BARE_STRING.match(text):
        return False
    if _KEY_USE.search(removed):
        return False
    # A bare string that is an argument of a call: a message when the call
    # is a logging call or an exception, a key otherwise.
    return bool(re.search(r"(logger\.|raise |\.format\(|f\")", removed))


def _functions_of_the_package(folder: Path) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Every function and method of the package, by name."""
    functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for path in sorted(folder.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - the package always parses
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.setdefault(node.name, node)
    return functions


def _parameters_of(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    """The default of every parameter of a function."""
    arguments = node.args
    names = [item.arg for item in arguments.posonlyargs + arguments.args]
    pairs = list(zip(names, arguments.defaults, strict=False))
    pairs += list(
        zip(
            [item.arg for item in arguments.kwonlyargs],
            arguments.kw_defaults,
            strict=False,
        )
    )
    return dict(pairs)


def _fields_of_a_class(tree: ast.AST) -> dict[str, Any]:
    """The default of every field of every class of a module."""
    fields: dict[str, Any] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fields.setdefault(item.target.id, item.value)
    return fields


def _callee_of_the_call(
    function: ast.FunctionDef | ast.AsyncFunctionDef, parameter: str
) -> str | None:
    """The name of the function that is called with the given keyword.

    The call is looked up in the body of the function that holds the
    mutation, so the callee of ``resume=resume`` is found and not guessed.
    """
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg == parameter:
                target = node.func
                if isinstance(target, ast.Name):
                    return target.id
                if isinstance(target, ast.Attribute):
                    return target.attr
    return None


def _defaults_of_the_package(folder: Path) -> dict[str, list[Any]]:
    """The defaults of every parameter of the package, by parameter name.

    The key is the name of a parameter; the value is the list of the
    defaults of that parameter in the functions that have it.
    """
    """The defaults of every parameter of every function of the package.

    The key is the name of the function (a method is reachable by the
    name of its method alone); the value maps the name of a parameter to
    the node of its default.
    """
    defaults: dict[str, dict[str, Any]] = {}
    for path in sorted(folder.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - the package always parses
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            arguments = node.args
            names = [item.arg for item in arguments.posonlyargs + arguments.args]
            pairs = list(zip(names, arguments.defaults, strict=False))
            pairs += list(
                zip(
                    [item.arg for item in arguments.kwonlyargs],
                    arguments.kw_defaults,
                    strict=False,
                )
            )
            for parameter, default in pairs:
                if default is not None:
                    defaults.setdefault(parameter, []).append(default)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            fields: dict[str, Any] = {}
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields[item.target.id] = item.value
            for parameter, default in fields.items():
                if default is not None:
                    defaults.setdefault(parameter, []).append(default)
    return defaults


def _defaults_of_the_module(path: Path) -> dict[str, dict[str, Any]]:
    """The default of every parameter of every function of a module.

    The key is the name of the function; the value maps the name of a
    parameter to the node of its default (``None`` when the parameter has
    no default at all).
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    defaults: dict[str, dict[str, Any]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        arguments = node.args
        names = [item.arg for item in arguments.posonlyargs + arguments.args]
        pairs = list(zip(names, arguments.defaults, strict=False))
        pairs += list(
            zip(
                [item.arg for item in arguments.kwonlyargs],
                arguments.kw_defaults,
                strict=False,
            )
        )
        defaults[node.name] = dict(pairs)
    return defaults


def _is_state_format(removed: str) -> bool:
    """Whether a change touches the format of the state file.

    The keys of the file and the way it is written are described in
    ``docs/spec/state-file-format-v2.md``: a change there is a change of
    a documented contract, not a detail.
    """
    if re.search(r'state\[', removed) or re.search(r'state\.get\(', removed):
        return True
    return bool(re.search(r"json\.dumps\(state", removed))


def _is_key_string(removed: str) -> bool:
    """Whether a string literal is the key of a mapping.

    The key of the state file is part of the format that
    ``docs/spec/state-file-format-v2.md`` describes: changing it changes
    the behaviour of the library.
    """
    return bool(_KEY_USE.search(removed))


def _is_equivalent_argument(removed: str, added: str, defaults: dict[str, dict[str, Any]]) -> bool:
    """Whether replacing a keyword argument by ``None`` is equivalent.

    The verdict is taken from the abstract syntax tree of the module: the
    parameter must really default to ``None``.  When the callee cannot be
    found, the verdict is ``False``: the survivor is then a gap that
    nobody looked at, which is the honest answer.
    """
    match = _CALL_WITH_KEYWORD.match(removed)
    if match is None:
        return False
    parameter = match.group("name")
    # The callee is not on the line: the value of the argument is the
    # name of the parameter itself, so the parameter of the *callee* has
    # the same name.  The verdict is taken from every function of the
    # package that has a parameter of that name: the mutation is
    # equivalent when all of them default to None.
    seen = defaults.get(parameter)
    if not seen:
        return False
    return all(isinstance(default, ast.Constant) and default.value is None for default in seen)


#: The calls that only *record* something: a change in their argument
#: changes what the library writes down, not what it does.
RECORDERS = frozenset(
    {
        "_emit",
        "append_attempt",
        "append_event",
        "set_breaker",
        "record_claim",
        "write",
        "logger.info",
        "logger.warning",
        "logger.error",
        "logger.debug",
    }
)


def _is_equivalent_call(
    removed: str,
    parameter: str,
    function: ast.FunctionDef | ast.AsyncFunctionDef | None,
    functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
    fields: dict[str, Any],
) -> bool:
    """Whether a keyword argument that becomes ``None`` is equivalent.

    The callee is found in the body of the function that holds the
    mutation; the verdict comes from the signature of the callee (or from
    the fields of its class).  When the callee cannot be found, the
    verdict is ``False``: the survivor is then a gap that nobody looked
    at, which is the honest answer.
    """
    if function is None:
        return False
    callee = _callee_of_the_call(function, parameter)
    if callee is None:
        return False
    target = functions.get(callee)
    if target is not None:
        default = _parameters_of(target).get(parameter)
        if default is None:
            # The parameter has no default at all: the call would fail.
            return False
        return isinstance(default, ast.Constant) and default.value is None
    default = fields.get(parameter)
    if default is None:
        return False
    return isinstance(default, ast.Constant) and default.value is None


def _holder_of(
    mutant: str, functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef]
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """The function that holds a mutation.

    The name of a mutant looks like
    ``package.module.xǁClassǁmethodǁ...``; the method is the function
    that was mutated.
    """
    parts = mutant.split("ǁ")
    if len(parts) < 3:
        return None
    name = re.sub(r"__mutmut_\d+$", "", parts[2])
    return functions.get(name)


def main() -> int:
    """Classify every survivor of the run."""
    from mutmut.mutation.diff_apply import get_diff_for_mutant

    report: dict[str, Any] = {}
    verdicts: Counter[str] = Counter()
    shapes: Counter[str] = Counter()
    total = 0
    survived = 0
    for meta_path in sorted(MUTANTS.glob("src/agentether/*.py.meta")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        exits = meta["exit_code_by_key"]
        survivors = [key for key, code in exits.items() if code == 0]
        total += len(exits)
        survived += len(survivors)
        if not survivors:
            continue
        name = meta_path.name[: -len(".meta")]
        source = SOURCE / name
        functions = _functions_of_the_package(SOURCE)
        fields = _fields_of_a_class(ast.parse(source.read_text(encoding="utf-8")))
        entries: list[dict[str, Any]] = []
        for mutant in survivors:
            try:
                diff = get_diff_for_mutant(mutant, path=source)
            except Exception as exc:  # pragma: no cover - the internals of mutmut
                entries.append(
                    {"name": mutant, "shape": "error", "verdict": "gap", "error": str(exc)[:120]}
                )
                verdicts["gap"] += 1
                continue
            removed, added = _changed_lines(diff)
            shape = _shape(removed, added)
            shapes[shape] += 1
            if shape == "argument":
                parameter = _CALL_WITH_KEYWORD.match(removed)
                parameter = parameter.group("name") if parameter else ""
                holder = _holder_of(mutant, functions)
                if _is_equivalent_call(removed, parameter, holder, functions, fields):
                    verdict = "equivalent"
                elif _callee_of_the_call(holder, parameter) in RECORDERS if holder else False:
                    verdict = "gap (record)"
                else:
                    verdict = "gap (behaviour)"
            elif _is_state_format(removed):
                verdict = "gap (format)"
            elif shape == "string" and _is_key_string(removed):
                verdict = "gap (behaviour)"
            elif shape == "string":
                verdict = "cosmetic"
            elif _is_constant_condition(removed, added):
                verdict = "equivalent"
            else:
                verdict = "gap (behaviour)"
            verdicts[verdict] += 1
            entries.append(
                {
                    "name": mutant,
                    "shape": shape,
                    "verdict": verdict,
                    "removed": removed.strip()[:200],
                    "added": added.strip()[:200],
                }
            )
        report[name] = {
            "mutants": len(exits),
            "survived": len(survivors),
            "entries": entries,
        }
    payload = {
        "total_mutants": total,
        "total_survived": survived,
        "verdicts": dict(verdicts.most_common()),
        "shapes": dict(shapes.most_common()),
        "files": report,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"mutants: {total}")
    print(f"survived: {survived}")
    for verdict, count in verdicts.most_common():
        print(f"  {verdict}: {count}")
    print("shapes:")
    for shape, count in shapes.most_common():
        print(f"  {shape}: {count}")
    print(f"written: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
