#!/usr/bin/env python3
"""Check independent app release versions without changing the ledger."""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys

NAMES = {"inbe": "inbe", "lists": "lists", "habits": "habits",
         "practices": "practice", "diary": "diary", "lumi": "lumi",
         "leaderboard": "leaderboard"}
VERSION = r"(?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8})"


def validate(root):
    ledger = json.loads((root / "apps/versions.json").read_text())
    for api in ("host_api", "oldest_host_api", "module_api"):
        if type(ledger.get(api)) is not int or not 0 < ledger[api] <= 65535:
            raise ValueError(f"invalid {api}")
    # The host runs packages from its oldest supported interface to its own.
    if ledger["oldest_host_api"] > ledger["host_api"]:
        raise ValueError("oldest_host_api is newer than host_api")
    if set(ledger["apps"]) != set(NAMES):
        raise ValueError("the ledger must contain the root and all six apps")
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
            raise ValueError(f"{name}: every app must be bundled for offline use")
        # The Inner Breeze release this version was made for, once per release.
        if "release" in component and (not isinstance(component["release"], str) or
                                       not re.fullmatch(VERSION, component["release"])):
            raise ValueError(f"{name}: invalid release version")
        # A package declares the oldest host interface it runs on, so apps
        # that keep an older host still receive it.
        host = component.get("host_api", ledger["host_api"])
        if type(host) is not int or not ledger["oldest_host_api"] <= host <= ledger["host_api"]:
            raise ValueError(f"{name}: host_api must be between oldest_host_api and host_api")
        # This host runs no package of the app built for an older interface:
        # its screens moved into the package, so the bundled copy runs instead.
        oldest = component.get("oldest_host_api", ledger["oldest_host_api"])
        if type(oldest) is not int or not ledger["oldest_host_api"] <= oldest <= host:
            raise ValueError(f"{name}: oldest_host_api must be between the ledger's and its host_api")
        changelog = root / "apps" / source / "CHANGELOG.md"
        headings = re.findall(r"^## \[([^\]]+)\] - ([^\n]+)$", changelog.read_text(), re.M)
        if not headings or not re.fullmatch(VERSION, headings[0][0]):
            raise ValueError(f"{name}: first changelog entry must be a numeric release")
        date.fromisoformat(headings[0][1])
        if headings[0][0] != component["version"]:
            raise ValueError(f"{name}: changelog and ledger differ; run ./update_version.sh --app {name}")
    # Apps the node offers are not bundled: they need no place in the root,
    # and a newer host interface of theirs does not hold the root back.
    for name, component in ledger.get("node_apps", {}).items():
        if not re.fullmatch(r"[a-z][a-z0-9]{1,23}", name) or name in NAMES or name in ("practice", "feedback"):
            raise ValueError(f"{name}: invalid node app name")
        if component.get("id") != "inbe." + name:
            raise ValueError(f"{name}: expected app ID inbe.{name}")
        if not isinstance(component.get("title"), str) or not component["title"]:
            raise ValueError(f"{name}: a node app needs the title the node lists")
        if not isinstance(component.get("version"), str) or not re.fullmatch(VERSION, component["version"]):
            raise ValueError(f"{name}: invalid numeric release version")
        if type(component.get("sequence")) is not int or not 0 < component["sequence"] <= 2147483647:
            raise ValueError(f"{name}: invalid release sequence")
        if "bundled" in component:
            raise ValueError(f"{name}: an app the node offers is never bundled")
        # A beta app is listed only where a person shows beta apps.
        if "beta" in component and component["beta"] is not True:
            raise ValueError(f"{name}: beta is true or absent")
        host = component.get("host_api", ledger["host_api"])
        if type(host) is not int or not ledger["oldest_host_api"] <= host <= ledger["host_api"]:
            raise ValueError(f"{name}: host_api must be between oldest_host_api and host_api")
        headings = re.findall(r"^## \[([^\]]+)\] - ([^\n]+)$",
                              (root / "apps" / name / "CHANGELOG.md").read_text(), re.M)
        if not headings or headings[0][0] != component["version"]:
            raise ValueError(f"{name}: changelog and ledger differ; run ./update_version.sh --app {name}")
        date.fromisoformat(headings[0][1])
    # The root package carries every app for offline use, so a host that
    # cannot run one of them cannot open the root package either.
    root_host = ledger["apps"]["inbe"].get("host_api", ledger["host_api"])
    for name, component in ledger["apps"].items():
        if component.get("host_api", ledger["host_api"]) > root_host:
            raise ValueError(f"inbe: host_api {root_host} is older than {name}'s; "
                             "the root package carries it")
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
