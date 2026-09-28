#!/usr/bin/env python3
"""Every LocaleText key used in the sources exists in every locale file."""

from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parent.parent
used = set()
for source in (root / "src").rglob("*.zi"):
    used |= set(re.findall(r'LocaleText\(\s*"([a-z0-9_]+)"', source.read_text(encoding="utf-8")))

failures = []
for locale in sorted((root / "locales").glob("*.txt")):
    if locale.name == "index.txt":
        continue
    keys = set(re.findall(r"(?m)^\[([a-z0-9_]+)\]$", locale.read_text(encoding="utf-8")))
    missing = sorted(used - keys)
    if missing:
        failures.append(f"{locale.name}: missing {', '.join(missing)}")

if failures:
    print("\n".join(failures), file=sys.stderr)
    sys.exit(1)
print(f"All {len(used)} used locale keys exist in every locale")
