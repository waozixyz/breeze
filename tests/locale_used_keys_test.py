#!/usr/bin/env python3
"""Every LocaleText key used in the sources exists in every locale file, and
each translation keeps the placeholders of its English text."""

from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parent.parent
used = set()
for directory in (root / "src", root / "apps"):
    for source in directory.rglob("*.zi"):
        used |= set(re.findall(r'(?:LocaleText|[A-Za-z]+LocaleHost)\(\s*"([a-z0-9_]+)"', source.read_text(encoding="utf-8")))

# Placeholders the app's formatters substitute.
placeholder = re.compile(r"%(?:%|0?\d*d|s|i)")
unsupported = re.compile(r"%l+[dui]")


def entries(path):
    values = {}
    key = None
    lines = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        header = re.match(r"^\[([a-z0-9_]+)\]$", line)
        if header:
            key = header.group(1)
            lines = []
        elif line == "---":
            if key is not None:
                values[key] = "\n".join(lines)
            key = None
        elif key is not None:
            lines.append(line)
            values[key] = "\n".join(lines)
    return values


english = entries(root / "locales/en.txt")
failures = []
for locale in sorted((root / "locales").glob("*.txt")):
    if locale.name == "index.txt":
        continue
    values = entries(locale)
    missing = sorted(used - set(values))
    if missing:
        failures.append(f"{locale.name}: missing {', '.join(missing)}")
    for key, text in values.items():
        if unsupported.search(text):
            failures.append(f"{locale.name}: {key} uses an unsupported placeholder")
        if key in english and sorted(placeholder.findall(text)) != sorted(placeholder.findall(english[key])):
            failures.append(f"{locale.name}: {key} placeholders differ from English")

if failures:
    print("\n".join(failures), file=sys.stderr)
    sys.exit(1)
print(f"All {len(used)} used locale keys exist in every locale with matching placeholders")
