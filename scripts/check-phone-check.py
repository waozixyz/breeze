#!/usr/bin/env python3
"""Allow a new release only with a passing phone check of its exact sources.

scripts/phone-check.py --record writes releases/phone-checks/VERSION.json for
the commit it checked. The released commit may differ from that commit only in
paths that do not change the app, such as the receipt itself.
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


def git(root, *argv):
    return subprocess.run(["git", "-C", str(root), *argv], check=True, capture_output=True,
                          text=True).stdout


def changes_app(path):
    return any(path == source or path.startswith(source + "/") for source in phone_check.SOURCE_PATHS)


def validate(root, version):
    path = root / "releases/phone-checks" / f"{version}.json"
    if not path.is_file():
        raise ValueError(f"{version} has no phone check; run scripts/phone-check.py --record on the "
                         "development Moto and commit the receipt")
    receipt = json.loads(path.read_text())
    if receipt.get("schema") != 1 or receipt.get("version") != version:
        raise ValueError("the phone check is for a different version")
    if receipt.get("apk", {}).get("version_name") != version:
        raise ValueError("the checked APK has a different version")
    commit = receipt.get("source_commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("the phone check has no full source commit")
    timing = receipt.get("practice", {})
    if receipt.get("passed") is not True or not phone_check.smooth(timing) or timing.get("seconds", 0) < 55:
        raise ValueError(f"the phone check did not pass: {timing}")
    if not phone_check.resumed_in_place(timing):
        raise ValueError("the app came back from the background with a shifted layout: "
                         f"{timing.get('resume_layout_shift')}")
    if subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", commit, "HEAD"],
                      capture_output=True).returncode != 0:
        raise ValueError(f"the checked commit {commit} is not part of this release")
    changed = [name for name in git(root, "diff", "--name-only", commit, "HEAD").splitlines()
               if changes_app(name)]
    if changed:
        raise ValueError("the app changed after its phone check: " + ", ".join(changed[:10]))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        receipt = validate(args.root, args.version)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Phone check required: {error}", file=sys.stderr)
        return 1
    timing = receipt["practice"]
    print(f"{args.version} passed its phone check on {receipt['device']['model']}: {timing['fps']} fps, "
          f"{timing['late_percent']}% late frames")
    return 0


if __name__ == "__main__":
    sys.exit(main())
