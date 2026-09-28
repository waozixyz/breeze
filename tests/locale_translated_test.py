#!/usr/bin/env python3
"""Law: no locale keeps English text by accident.

A string identical to its English source in another locale must be listed in
tests/locale_same_as_english.txt (brand names, loanwords, format strings). Any new
untranslated string fails here, and an allowlist entry that has since been
translated must be removed."""

from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parent.parent
locales = root / "locales"


def entries(path):
    values, key, lines = {}, None, []
    for line in path.read_text(encoding="utf-8").split("\n"):
        header = re.fullmatch(r"\[([a-z0-9_]+)\]", line)
        if header:
            key, lines = header.group(1), []
        elif line == "---" and key is not None:
            values[key] = "\n".join(lines)
            key = None
        else:
            lines.append(line)
    return values


allowed = set()
for line in (root / "tests/locale_same_as_english.txt").read_text(encoding="utf-8").splitlines():
    if line.strip() and not line.startswith("#"):
        allowed.add(tuple(line.split()))

english = entries(locales / "en.txt")
found = set()
for path in sorted(locales.glob("*.txt")):
    code = path.stem
    if code in ("en", "index"):
        continue
    for key, value in entries(path).items():
        if english.get(key) == value and any(c.isalpha() for c in value) and len(value) > 2:
            found.add((code, key))

untranslated = sorted(found - allowed)
stale = sorted(allowed - found)
for code, key in untranslated:
    print(f"{code}: {key} is still English: {english[key]!r}")
for code, key in stale:
    print(f"{code}: {key} is translated now; remove it from same_as_english.txt")
if untranslated or stale:
    sys.exit(1)
print("Locales: every string is translated or explicitly allowed to match English")
