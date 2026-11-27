#!/usr/bin/env python3
"""Distinguish public TSX component calls from the removed positional API."""

from pathlib import Path
import re
import sys


PUBLIC = {"Button": "button", "Toggle": "toggle", "Checkbox": "checkbox"}
IMPORT = (
    r'\bimport\s*\{(?P<names>[^}]+)\}\s*from\s*'
    r'(?P<quote>[\'"])(?P<module>kryon/tsx/(?:button|toggle|checkbox))(?P=quote)'
)
LITERALS = re.compile(
    r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'
    r"'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`"
)
SOURCE = re.compile(IMPORT + "|" + LITERALS.pattern)
CALL = re.compile(r'(?<![\w.])(Button|Toggle|Checkbox)\s*\(')
REMOVED_PROPS = re.compile(r'(?<![\w.])(Button|Toggle|Checkbox)Props\b')


def violations(path, source):
    imported = set()
    if path.suffix in {".ts", ".tsx"}:
        for match in SOURCE.finditer(source):
            if match["names"] is None:
                continue
            for item in match["names"].split(","):
                names = re.split(r"\s+as\s+", item.strip())
                if names[0] in PUBLIC and match["module"] == "kryon/tsx/" + PUBLIC[names[0]]:
                    imported.add(names[-1])
    # Preserve offsets and newlines while ignoring examples in strings/comments.
    code = LITERALS.sub(lambda match: re.sub(r"[^\n]", " ", match[0]), source)
    rejected = list(REMOVED_PROPS.finditer(code))
    for match in CALL.finditer(code):
        if match[1] not in imported or not code[match.end():].lstrip().startswith("{"):
            rejected.append(match)
    return sorted({source.count("\n", 0, match.start()) + 1 for match in rejected})


def main():
    failed = []
    for root in map(Path, sys.argv[1:] or ["src", "apps"]):
        paths = root.rglob("*") if root.is_dir() else [root]
        for path in sorted(paths):
            if path.suffix not in {".zi", ".ts", ".tsx"}:
                continue
            for line in violations(path, path.read_text()):
                failed.append(f"{path}:{line}: use a public Kryon TSX component with native props")
    for failure in failed[:25]:
        print(failure, file=sys.stderr)
    if len(failed) > 25:
        print(f"... {len(failed) - 25} further invalid calls", file=sys.stderr)
    return bool(failed)


if __name__ == "__main__":
    sys.exit(main())
