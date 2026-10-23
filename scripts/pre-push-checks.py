#!/usr/bin/env python3
"""Run the quick local checks that match what a push changes.

Git runs this from .githooks/pre-push with the pushed refs on stdin, so the
checks that fail most often on GitHub (versions, translations, fonts, the
canonical UI APIs, the app bundles and the workflows) fail here first, in a
minute or two. `make pre-push-check` runs it for everything not yet on
origin/master. The checks read the working tree; `git push --no-verify`
skips them.
"""

import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
ZERO = "0" * 40


def git(*arguments):
    return subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout


def pushed_ranges(lines):
    """(base, tip) for each pushed ref that adds commits."""
    ranges = []
    for line in lines:
        parts = line.split()
        if len(parts) != 4 or parts[1] == ZERO:
            continue
        tip, remote = parts[1], parts[3]
        if remote == ZERO:
            remote = git("merge-base", tip, "origin/master").strip()
        ranges.append((remote, tip))
    return ranges


def changed_files(ranges):
    files = set()
    for base, tip in ranges:
        files.update(path for path in git("diff", "--name-only", base, tip).splitlines() if path)
    return sorted(files)


def plan(files):
    """The checks for these changed files, in the order they run."""
    def any_of(*prefixes):
        return any(path.startswith(prefixes) for path in files)

    def any_suffix(*suffixes):
        return any(path.endswith(suffixes) for path in files)

    checks = [("version files agree", ["python3", "scripts/check-version.py"]),
              ("package versions", ["make", "-s", "package-version-test"])]
    if any_of("locales/", "assets/fonts/") or any_suffix(".zi"):
        checks.append(("translations and fonts", ["make", "-s", "locale-check"]))
    if any_suffix(".zi"):
        checks.append(("canonical UI APIs", ["make", "-s", "clean-text-api-check", "button-api-check"]))
    if any_of("apps/", "src/cells/", "locales/"):
        checks.append(("app bundles", ["make", "-s", "cells-test"]))
    if any_of(".github/workflows/", "scripts/package-release.py", "scripts/release",
              "scripts/check-version.py", "tests/release_test.py", "tests/package_workflow_test.py"):
        checks.append(("release workflow", ["python3", "tests/release_test.py"]))
        checks.append(("package workflow", ["python3", "tests/package_workflow_test.py"]))
    python = [path for path in files if path.endswith(".py") and (ROOT / path).is_file()]
    if python:
        checks.append(("Python syntax", ["python3", "-m", "py_compile", *python]))
    if any_of("src/web_boot.js", "tests/web_storage_test.mjs"):
        checks.append(("web storage", ["node", "tests/web_storage_test.mjs"]))
    scripts = [path for path in files if path.endswith((".js", ".mjs")) and (ROOT / path).is_file()]
    for path in scripts:
        checks.append((path + " syntax", ["node", "--check", path]))
    return checks


def run(checks, ranges):
    failed = []
    for base, tip in ranges:
        result = subprocess.run(["git", "diff", "--check", base, tip], cwd=ROOT,
                                capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stdout + result.stderr, end="")
            failed.append("whitespace in the pushed commits")
    environment = dict(os.environ)
    # Python caches under the checkout would be swept into commits.
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    for name, command in checks:
        started = time.monotonic()
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, env=environment)
        seconds = time.monotonic() - started
        if result.returncode == 0:
            print(f"pre-push: {name} passed ({seconds:.0f} s)")
            continue
        output = (result.stdout + result.stderr).strip().splitlines()
        print("\n".join(output[-25:]))
        print(f"pre-push: {name} FAILED: {' '.join(command)}")
        failed.append(name)
    return failed


def main():
    if sys.argv[1:] == ["--unpushed"]:
        lines = [f"HEAD {git('rev-parse', 'HEAD').strip()} refs/heads/master "
                 f"{git('rev-parse', 'origin/master').strip()}"]
    else:
        lines = sys.stdin.read().splitlines()
    ranges = pushed_ranges(lines)
    if not ranges:
        return 0
    files = changed_files(ranges)
    if not files:
        return 0
    failed = run(plan(files), ranges)
    if failed:
        print("pre-push: not pushed. Fix: " + ", ".join(failed) +
              " (git push --no-verify skips these checks)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
