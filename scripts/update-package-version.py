#!/usr/bin/env python3
"""Synchronize one module's ledger from its numeric changelog entry."""
import json
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parent.parent
names = {"inbe": "inbe", "lists": "lists", "habits": "habits",
         "practices": "practice", "diary": "diary"}
if len(sys.argv) != 2 or sys.argv[1] not in names:
    raise SystemExit("usage: ./update_version.sh --module inbe|lists|habits|practices|diary")
name = sys.argv[1]
changelog = (root / "apps" / names[name] / "CHANGELOG.md").read_text()
version = re.search(r"^## \[((?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8}))\]", changelog, re.M)
if not version:
    raise SystemExit("module changelog needs a numeric release entry")
path = root / "apps/versions.json"
ledger = json.loads(path.read_text())
component = ledger["apps"][name]
latest = version[1]
if tuple(map(int, latest.split("."))) < tuple(map(int, component["version"].split("."))):
    raise SystemExit("module version cannot decrease")
if latest != component["version"]:
    component["version"] = latest
    component["sequence"] += 1
    if component["sequence"] > 2**31 - 1:
        raise SystemExit("module sequence limit reached")
    path.write_text(json.dumps(ledger, indent=2) + "\n")
print(f"{name} {latest}, sequence {component['sequence']}; native wrapper version retained")
