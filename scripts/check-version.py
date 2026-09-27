#!/usr/bin/env python3
"""Validate release metadata without changing files; optionally print the version."""

import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


VERSION_PATTERN = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
HEADER = "src/core/version.h"
ZIRAN_VERSION = "src/core/version.zi"
METAINFO = (
    "packaging/click/inbe.metainfo.xml",
    "packaging/linux/appimage/inbe.appdata.xml",
    "packaging/snap/snap/gui/inbe.metainfo.xml",
)


def unique(text, pattern, label):
    matches = re.findall(pattern, text, re.MULTILINE)
    if len(matches) != 1:
        raise ValueError(f"{label}: expected exactly one field, found {len(matches)}")
    return matches[0]


def validate(root, structure_only=False):
    def read(path):
        return (root / path).read_text(encoding="utf-8")

    headings = re.findall(r"^## \[(.*?)\].*$", read("CHANGELOG.md"), re.MULTILINE)
    if not headings or not re.fullmatch(VERSION_PATTERN, headings[0]):
        raise ValueError("CHANGELOG.md: first release must have a numeric X.Y.Z version")
    version = headings[0]
    release_date = unique(
        read("CHANGELOG.md"),
        rf"^## \[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})$",
        "CHANGELOG.md release date",
    )
    date.fromisoformat(release_date)

    def check(label, actual, expected):
        if not structure_only and actual != expected:
            raise ValueError(f"{label}: found {actual!r}, expected {expected!r}; run ./update_version.sh")

    header = read(HEADER)
    for part, expected in zip(("MAJOR", "MINOR", "PATCH", "STRING"),
                              (*version.split("."), f'"{version}"')):
        name = f"APP_VERSION_{part}"
        unique(header, rf"^[ \t]*#[ \t]*define[ \t]+{name}\b([^\n]*)$",
               f"{HEADER}: {name} definition")
        value = unique(header, rf"^#define {name} ([^\n]+)$", f"{HEADER}: {name}")
        pattern = rf'"{VERSION_PATTERN}"' if part == "STRING" else r"(?:0|[1-9][0-9]*)"
        if not re.fullmatch(pattern, value):
            raise ValueError(f"{HEADER}: malformed {name}")
        check(name, value, expected)

    ziran_path = root / ZIRAN_VERSION
    if ziran_path.is_file():
        ziran = read(ZIRAN_VERSION)
        for part, expected in zip(("Major", "Minor", "Patch", "String"),
                                  (*version.split("."), f'"{version}"')):
            value = unique(ziran, rf"^Version{part} :: ([^\n]+)$",
                           f"{ZIRAN_VERSION}: Version{part}")
            pattern = rf'"{VERSION_PATTERN}"' if part == "String" else r"(?:0|[1-9][0-9]*)"
            if not re.fullmatch(pattern, value):
                raise ValueError(f"{ZIRAN_VERSION}: malformed Version{part}")
            check(f"{ZIRAN_VERSION}: Version{part}", value, expected)
    elif not structure_only:
        raise ValueError(f"{ZIRAN_VERSION}: missing; run ./update_version.sh")

    gradle = read("droid/app/build.gradle")
    android_name = unique(gradle, r'^\s*versionName "([^"\n]+)"$', "Android versionName")
    if not re.fullmatch(VERSION_PATTERN, android_name):
        raise ValueError("Android versionName: malformed version")
    check("Android versionName", android_name, version)
    code = unique(gradle, r"^\s*versionCode ([1-9][0-9]*)$", "Android versionCode")

    windows = read("windows/inbe.rc")
    for field in ("FILEVERSION", "PRODUCTVERSION"):
        value = unique(windows, rf"^ {field} ([0-9]+,[0-9]+,[0-9]+,0)$", field)
        check(field, value, version.replace(".", ",") + ",0")
    for field in ("FileVersion", "ProductVersion"):
        value = unique(windows, rf'^\s*VALUE "{field}", "({VERSION_PATTERN})"$', field)
        check(field, value, version)

    for path in ("packaging/click/manifest.json", "packaging/firefox-addons/manifest.json"):
        content = read(path)
        unique(content, r'^\s*"version": "([^"\n]+)"[,]?$', f"{path}: version")
        value = json.loads(content)["version"]
        if not re.fullmatch(VERSION_PATTERN, value):
            raise ValueError(f"{path}: malformed version")
        check(path, value, version)

    path = "packaging/click/control"
    check(path, unique(read(path), rf"^Version: ({VERSION_PATTERN})$", path), version)
    path = "packaging/snap/snap/snapcraft.yaml"
    check(path, unique(read(path), rf"^version: '({VERSION_PATTERN})'$", path), version)

    for path in METAINFO:
        releases = ET.fromstring(read(path)).findall("./releases/release")
        if len(releases) != 1:
            raise ValueError(f"{path}: expected exactly one current release")
        release = releases[0]
        if not re.fullmatch(VERSION_PATTERN, release.get("version", "")):
            raise ValueError(f"{path}: malformed release version")
        date.fromisoformat(release.get("date", ""))
        check(path, release.get("version"), version)
        check(f"{path}: date", release.get("date"), release_date)

    # Inspect maintained application and release sources, never vendor/build output.
    sources = [root / path for path in ("Makefile", "mkfile", "update_version.sh", "site/build.sh")]
    for directory in ("src", "scripts", ".github"):
        sources.extend(path for path in (root / directory).rglob("*")
                       if path.suffix in (".c", ".h", ".zi", ".sh", ".py", ".yml", ".yaml", ".mjs"))
    for path in sources:
        for macro in re.findall(r"\b[A-Z][A-Z0-9_]*_VERSION_(?:STRING|MAJOR|MINOR|PATCH)\b",
                                path.read_text(encoding="utf-8")):
            if not macro.startswith("APP_VERSION_"):
                raise ValueError(f"{path.relative_to(root)}: noncanonical version macro {macro}")

    if not structure_only:
        changelog = root / f"fastlane/metadata/android/en-US/changelogs/{code}.txt"
        if not changelog.is_file() or not changelog.read_text(encoding="utf-8").strip():
            raise ValueError(f"missing Android release notes for versionCode {code}")
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--print-version", action="store_true")
    mode.add_argument("--check-structure", action="store_true",
                      help="updater preflight: allow different existing version values")
    args = parser.parse_args()
    try:
        version = validate(args.root, args.check_structure)
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        print(f"Version check failed: {error}", file=sys.stderr)
        return 1
    if args.print_version:
        print(version)
    else:
        print(f"Version {'structure' if args.check_structure else version}: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
