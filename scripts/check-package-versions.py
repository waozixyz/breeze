#!/usr/bin/env python3
"""Check independent app release versions without changing the ledger."""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys

NAMES = {"inbe": "inbe", "lists": "lists", "habits": "habits",
         "practices": "practice", "diary": "diary", "lumi": "lumi"}
VERSION = r"(?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8})"


def validate(root):
    ledger = json.loads((root / "apps/versions.json").read_text())
    for api in ("host_api", "module_api"):
        if type(ledger.get(api)) is not int or not 0 < ledger[api] <= 2147483647:
            raise ValueError(f"invalid {api}")
    if set(ledger["apps"]) != set(NAMES):
        raise ValueError("the ledger must contain the root and all five cells")
    for name, source in NAMES.items():
        component = ledger["apps"][name]
        expected_id = "inbe" if name == "inbe" else "inbe." + name
        if component.get("id") != expected_id:
            raise ValueError(f"{name}: expected app ID {expected_id}")
        if not isinstance(component.get("version"), str) or not re.fullmatch(VERSION, component["version"]):
            raise ValueError(f"{name}: invalid numeric release version")
        if type(component.get("sequence")) is not int or not 0 < component["sequence"] <= 2147483647:
            raise ValueError(f"{name}: invalid release sequence")
        if component.get("bundled") is not True:
            raise ValueError(f"{name}: every cell must be bundled for offline use")
        changelog = root / "apps" / source / "CHANGELOG.md"
        headings = re.findall(r"^## \[([^\]]+)\] - ([^\n]+)$", changelog.read_text(), re.M)
        if not headings or not re.fullmatch(VERSION, headings[0][0]):
            raise ValueError(f"{name}: first changelog entry must be a numeric release")
        date.fromisoformat(headings[0][1])
        if headings[0][0] != component["version"]:
            raise ValueError(f"{name}: changelog and ledger differ; run ./update_version.sh --cell {name}")
    return ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        validate(args.root)
    except (OSError, KeyError, ValueError, TypeError) as error:
        print(f"Package version check failed: {error}", file=sys.stderr)
        return 1
    print("Independent package changelogs, versions, sequences and bundled apps agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
