#!/usr/bin/env python3
"""Package the latest changelog text for Lumi's offline update message."""
import argparse
import json
from pathlib import Path
import re


def release_notes(changelog):
    heading = re.search(r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}\s*$",
                        changelog, re.M)
    if not heading:
        raise ValueError("changelog needs a numeric release")
    body = changelog[heading.end():].split("\n## [", 1)[0]
    notes = []
    for line in body.splitlines():
        if line.startswith("- "):
            notes.append(line[2:].strip())
        elif line.startswith("  ") and notes:
            notes[-1] += " " + line.strip()
    if not notes:
        raise ValueError("release needs changelog notes")
    return {"version": heading[1], "notes": notes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("changelog", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = release_notes(args.changelog.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")


if __name__ == "__main__":
    main()
