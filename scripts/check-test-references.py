#!/usr/bin/env python3
"""Fail when a test entry point in tests/ is run by nothing.

A test entry point counts as referenced when a make file, a GitHub workflow
or action, a git hook or a script names it, or when another referenced file
in tests/ names it (a .py run by a referenced _test.sh, for example). Shell
loops such as `for t in a b; do sh tests/$${t}_test.sh; done` are expanded
before searching.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve().relative_to(ROOT).as_posix()

ENTRY_POINT = re.compile(
    r"(_test\.(py|sh|mjs)|_device\.py|_emulator\.py)$")

# Files outside tests/ whose text can run a test.
REFERENCE_ROOTS = (
    "Makefile",
    "GNUmakefile",
    "makefile",
    "mk/",
    ".github/",
    ".githooks/",
    "scripts/",
)

# Entry points allowed to stay unreferenced, each with its reason. Files they
# use count as referenced through them. Remove an entry as soon as a make
# target, workflow or script runs the file; the check reports stale entries.
PHONE = "runs by hand against a connected phone or emulator, not in CI"
ALLOWED_UNREFERENCED = {
    "tests/android_picture_window_emulator.py": PHONE,
    "tests/android_text_selection_device.py": PHONE,
}


def listed_files() -> list[str]:
    try:
        output = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT, check=True, capture_output=True, text=True).stdout
        names = output.splitlines()
    except (OSError, subprocess.CalledProcessError):
        names = [path.relative_to(ROOT).as_posix()
                 for path in ROOT.rglob("*") if path.is_file()]
    return sorted(name for name in names
                  if (ROOT / name).is_file()
                  and "/__pycache__/" not in name
                  and "/.gradle/" not in name)


def is_reference_root(name: str) -> bool:
    for root in REFERENCE_ROOTS:
        if root.endswith("/") and name.startswith(root):
            return True
        if name == root:
            return True
    return False


def read_text(name: str) -> str:
    try:
        return (ROOT / name).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


LOOP = re.compile(
    r"\bfor\s+(\w+)\s+in\s+([^;\n]+?)\s*;\s*(?:\\\n\s*)?do\b(.*?)\bdone\b",
    re.DOTALL)


def expand_loops(text: str) -> str:
    """Append each shell for-loop body once per literal loop word."""
    expanded = [text]
    for match in LOOP.finditer(text):
        variable, words, body = match.groups()
        for word in words.split():
            if "$" in word or "(" in word:
                continue
            copy = body
            for form in ("$${" + variable + "}", "$$" + variable,
                         "${" + variable + "}", "$" + variable):
                copy = copy.replace(form, word)
            expanded.append(copy)
    return "\n".join(expanded)


TOKEN = re.compile(r"[\w.+-]+")
IMPORT = re.compile(r"""(?:\bimport|\bfrom)\s+"?([\w/.-]+)""")


def mentioned(text: str, by_name: dict[str, list[str]],
              by_module: dict[str, list[str]]) -> set[str]:
    """Return the tests/ files a text names by file or module name."""
    found: set[str] = set()
    for token in TOKEN.findall(text):
        found.update(by_name.get(token.rstrip("."), ()))
    for module in IMPORT.findall(text):
        found.update(by_module.get(module.rsplit("/", 1)[-1], ()))
    return found


def reachable(texts: list[str], by_name: dict[str, list[str]],
              by_module: dict[str, list[str]], start: set[str]) -> set[str]:
    """Follow mentions from texts through every tests/ file they reach."""
    reached = set(start)
    pending = list(texts)
    pending.extend(expand_loops(read_text(name)) for name in start)
    while pending:
        for name in mentioned(pending.pop(), by_name, by_module) - reached:
            reached.add(name)
            pending.append(expand_loops(read_text(name)))
    return reached


def main() -> int:
    files = listed_files()
    tests = [name for name in files if name.startswith("tests/")]
    by_name: dict[str, list[str]] = {}
    by_module: dict[str, list[str]] = {}
    for name in tests:
        path = Path(name)
        by_name.setdefault(path.name, []).append(name)
        if path.suffix in (".py", ".zi"):
            by_module.setdefault(path.stem, []).append(name)

    root_texts = [expand_loops(read_text(name)) for name in files
                  if name != SELF and is_reference_root(name)]
    referenced = reachable(root_texts, by_name, by_module, set())
    # Files an allowlisted entry point uses count as referenced through it.
    allowed = set(ALLOWED_UNREFERENCED) & set(tests)
    covered = reachable([], by_name, by_module, referenced | allowed)

    entry_points = [name for name in tests if ENTRY_POINT.search(name)]
    missing = [name for name in entry_points if name not in covered]
    stale = [name for name in ALLOWED_UNREFERENCED
             if name in referenced or name not in entry_points]

    for name in missing:
        print(f"{name}: no make target, workflow, script or referenced test "
              "runs it; wire it into a make target or delete it",
              file=sys.stderr)
    for name in stale:
        print(f"{name}: remove it from ALLOWED_UNREFERENCED in {SELF}; "
              "it is referenced now or no longer exists", file=sys.stderr)
    if missing or stale:
        return 1
    print(f"test references: all {len(entry_points)} test entry points "
          "are run by a make target, workflow or script")
    return 0


if __name__ == "__main__":
    sys.exit(main())
