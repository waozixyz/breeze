#!/usr/bin/env python3
"""Reject pre-namespace Text calls and duplicate public text-widget helpers.

Kryon's text widget is `Text.Draw(session, Text.Props.{...})`; the compiler
checks its argument types. This check rejects what types cannot: the removed
positional `Text(...)` call and `TextProps` name, and local helper variants
that duplicate a `Text.Props` field.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


SOURCE_SUFFIXES = {".c", ".h", ".zi"}
SKIPPED_DIRECTORIES = {".git", "build", "dist", "vendor", "vendor-builds"}
# A bare `Text(` call, not `Text.Draw(` or a member such as `value.Text(`.
LEGACY_TEXT_CALL = re.compile(r"(?<![\w.])Text\s*\(")
# The removed un-namespaced props type; `Text.Props` replaces it.
LEGACY_TEXT_PROPS = re.compile(r"(?<![\w.])TextProps\b")
TEXT_DECLARATION = re.compile(r"\bvoid\s+Text\s*\(\s*TextProps\s+[A-Za-z_]\w*\s*\)")
TEXT_VARIANT = re.compile(r"\bText(?:Wrapped|Colored|Disabled|InRect)\s*\(")


def source_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []

    for path in paths:
        if path.is_file():
            if path.suffix in SOURCE_SUFFIXES:
                files.append(path)
            continue

        for candidate in path.rglob("*"):
            if not candidate.is_file() or candidate.suffix not in SOURCE_SUFFIXES:
                continue
            if any(part in SKIPPED_DIRECTORIES for part in candidate.parts):
                continue
            files.append(candidate)

    return sorted(set(files))


def code_without_comments_or_strings(source: str) -> str:
    """Mask comments and literals while preserving newlines and offsets."""

    result = list(source)
    index = 0
    state = "code"

    while index < len(source):
        current = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""

        if state == "code":
            if current == "#":
                result[index] = " "
                index += 1
                state = "line_comment"
                continue
            if current == "/" and following == "/":
                result[index] = " "
                result[index + 1] = " "
                index += 2
                state = "line_comment"
                continue
            if current == "/" and following == "*":
                result[index] = " "
                result[index + 1] = " "
                index += 2
                state = "block_comment"
                continue
            if current == '"':
                result[index] = " "
                index += 1
                state = "string"
                continue
            if current == "'":
                result[index] = " "
                index += 1
                state = "character"
                continue
        elif state == "line_comment":
            if current == "\n":
                state = "code"
            else:
                result[index] = " "
        elif state == "block_comment":
            if current == "*" and following == "/":
                result[index] = " "
                result[index + 1] = " "
                index += 2
                state = "code"
                continue
            if current != "\n":
                result[index] = " "
        elif state in {"string", "character"}:
            if current == "\\" and following:
                result[index] = " "
                if following != "\n":
                    result[index + 1] = " "
                index += 2
                continue
            terminator = '"' if state == "string" else "'"
            if current == terminator:
                state = "code"
            if current != "\n":
                result[index] = " "

        index += 1

    return "".join(result)


def line_number(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def violations(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    return violations_in_source(source, path)


def violations_in_source(source: str, path: Path) -> list[str]:
    code = code_without_comments_or_strings(source)
    # A C host may still declare the native Text entry it implements.
    code = TEXT_DECLARATION.sub(lambda match: " " * len(match.group(0)), code)
    findings: list[str] = []

    for match in LEGACY_TEXT_CALL.finditer(code):
        findings.append(
            f"{path}:{line_number(source, match.start())}: "
            "draw text with Text.Draw(session, Text.Props.{...})"
        )

    for match in LEGACY_TEXT_PROPS.finditer(code):
        findings.append(
            f"{path}:{line_number(source, match.start())}: "
            "use Text.Props, not the removed TextProps name"
        )

    for match in TEXT_VARIANT.finditer(code):
        findings.append(
            f"{path}:{line_number(source, match.start())}: "
            "text variations belong in Text.Props, not a separate helper"
        )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    arguments = parser.parse_args()

    findings: list[str] = []
    for path in source_files(arguments.paths):
        findings.extend(violations(path))

    if findings:
        print("Clean Text API check failed:", file=sys.stderr)
        print("\n".join(findings), file=sys.stderr)
        return 1

    print("Clean Text API check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
