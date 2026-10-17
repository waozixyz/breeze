#!/usr/bin/env python3
"""Allow a new release only with a passing phone check of its exact app.

`make release` (scripts/phone-check.py --record) writes
releases/phone-checks/VERSION.json with the content identity of every app
path (app_tree). The released commit must have that same app content; tests,
docs and tooling (phone_check.TOOLING) may change after the check, any app
path may not.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("phone_check", ROOT / "scripts/phone-check.py")
phone_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phone_check)


def changes_app(path):
    return phone_check.is_app_path(path)


def changed_since(root, commit, revision):
    """App files that differ between the checked commit and the release, if it is known."""
    try:
        names = phone_check.git(root, "diff", "--name-only", "--no-renames", commit, revision).splitlines()
    except subprocess.CalledProcessError:
        return []
    return [name for name in names if changes_app(name)]


def validate(root, version, revision="HEAD"):
    path = root / phone_check.RECEIPTS / f"{version}.json"
    if not path.is_file():
        raise ValueError(f"{version} has no phone check; run make release with the development Moto "
                         "connected")
    receipt = json.loads(path.read_text())
    if receipt.get("schema") != 2:
        raise ValueError("the phone check was recorded without the app's content; run make release again")
    if receipt.get("version") != version:
        raise ValueError("the phone check is for a different version")
    if receipt.get("apk", {}).get("version_name") != version:
        raise ValueError("the checked APK has a different version")
    checked = receipt.get("app_tree", "")
    if not re.fullmatch(r"[0-9a-f]{64}", checked):
        raise ValueError("the phone check has no app content identity")
    timing = receipt.get("practice", {})
    if receipt.get("passed") is not True or not phone_check.smooth(timing) or timing.get("seconds", 0) < 55:
        raise ValueError(f"the phone check did not pass: {timing}")
    if not phone_check.resumed_in_place(timing):
        raise ValueError("the app came back from the background with a shifted layout: "
                         f"{timing.get('resume_layout_shift')}")
    if phone_check.app_tree(root, revision) != checked:
        changed = changed_since(root, receipt.get("source_commit", ""), revision)
        detail = ": " + ", ".join(changed[:10]) if changed else ""
        raise ValueError("the app changed after its phone check" + detail)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--revision", default="HEAD", help="commit to check (default HEAD)")
    args = parser.parse_args()
    try:
        receipt = validate(args.root, args.version, args.revision)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Phone check required: {error}", file=sys.stderr)
        return 1
    timing = receipt["practice"]
    print(f"{args.version} passed its phone check on {receipt['device']['model']}: {timing['fps']} fps, "
          f"{timing['late_percent']}% late frames")
    return 0


if __name__ == "__main__":
    sys.exit(main())
