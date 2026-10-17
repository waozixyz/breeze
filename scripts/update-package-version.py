#!/usr/bin/env python3
"""Synchronize package versions from their numeric changelog entries.

`NAME` synchronizes one package from its changelog. `--release X.Y.Z` gives
every bundled package a new version for Inner Breeze X.Y.Z, once: a package
whose changelog already has a newer entry takes it, every other one gets a
maintenance entry, and the root package lists the apps it brings. Bundles
share host code and Kryon, so a release changes them all; versioning them
together keeps the node from refusing a changed package under an old version.
"""
from datetime import date
import json
from pathlib import Path
import re
import sys

NAMES = {"inbe": "inbe", "lists": "lists", "habits": "habits",
         "practices": "practice", "diary": "diary", "lumi": "lumi",
         "leaderboard": "leaderboard"}
TITLES = {"lumi": "Lumi", "habits": "Habits", "practices": "Practices",
          "lists": "Lists", "diary": "Diary", "leaderboard": "Leaderboard"}
VERSION = r"(?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8})"


def numbers(version):
    return tuple(map(int, version.split(".")))


def written(changelog):
    found = re.search(r"^## \[(" + VERSION + r")\]", changelog, re.M)
    if not found:
        raise SystemExit("module changelog needs a numeric release entry")
    return found[1]


def advance(component, version):
    if numbers(version) < numbers(component["version"]):
        raise SystemExit("module version cannot decrease")
    if version != component["version"]:
        component["version"] = version
        component["sequence"] += 1
        if component["sequence"] > 2**31 - 1:
            raise SystemExit("module sequence limit reached")
        return True
    return False


def app_version(root):
    return written((root / "CHANGELOG.md").read_text())


def sync(root, ledger, name):
    node_apps = ledger.get("node_apps", {})
    changelog = (root / "apps" / NAMES.get(name, name) / "CHANGELOG.md").read_text()
    component = node_apps.get(name) or ledger["apps"].get(name)
    if component is None:
        component = {"id": "inbe." + name, "version": written(changelog), "sequence": 1,
                     "bundled": True}
        ledger["apps"][name] = component
    # A bundled package versioned while a release is prepared is not
    # versioned again for that release.
    if advance(component, written(changelog)) and name in NAMES:
        component["release"] = app_version(root)
    return component


def release(root, ledger, version, today):
    # The root package comes last: it brings the apps' new versions.
    for name in (*TITLES, "inbe"):
        component = ledger["apps"][name]
        if component.get("release") == version:
            continue
        path = root / "apps" / NAMES[name] / "CHANGELOG.md"
        changelog = path.read_text()
        target = written(changelog)
        if numbers(target) <= numbers(component["version"]):
            major, minor, patch = numbers(component["version"])
            target = f"{major}.{minor}.{patch + 1}"
            if name == "inbe":
                apps = [TITLES[app] + " " + ledger["apps"][app]["version"] for app in TITLES]
                note = f"Bring {', '.join(apps[:-1])} and {apps[-1]} for Inner Breeze {version}."
            else:
                note = f"Maintenance release for Inner Breeze {version}."
            first = changelog.index("\n## [") + 1
            path.write_text(changelog[:first] + f"## [{target}] - {today}\n\n- {note}\n\n" + changelog[first:])
        advance(component, target)
        component["release"] = version


def main(arguments):
    root = Path(__file__).resolve().parent.parent
    path = root / "apps/versions.json"
    ledger = json.loads(path.read_text())
    # Apps the node offers keep their own entries and are never bundled.
    node_apps = ledger.get("node_apps", {})
    if len(arguments) == 2 and arguments[0] == "--release" and re.fullmatch(VERSION, arguments[1]):
        release(root, ledger, arguments[1], date.today().isoformat())
        message = f"every bundled package versioned for Inner Breeze {arguments[1]}"
    elif len(arguments) == 1 and (arguments[0] in NAMES or arguments[0] in node_apps):
        component = sync(root, ledger, arguments[0])
        message = f"{arguments[0]} {component['version']}, sequence {component['sequence']}; native wrapper version retained"
    else:
        raise SystemExit("usage: ./update_version.sh --cell inbe|lists|habits|practices|diary|lumi|leaderboard|"
                         + "|".join(sorted(node_apps)) + "\n       update-package-version.py --release X.Y.Z")
    for cell in ledger["apps"].values():
        cell["bundled"] = True
    path.write_text(json.dumps(ledger, indent=2) + "\n")
    print(message)


if __name__ == "__main__":
    main(sys.argv[1:])
