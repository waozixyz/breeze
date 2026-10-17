#!/usr/bin/env python3
"""Refuse new or changed files over 1 MB unless .github/large-files.txt lists them.

Git keeps every version of a file forever, so drafts, renders and design
explorations belong in the ignored backup/ folder. Files the app ships may be
listed in .github/large-files.txt (one path or glob per line). Files stored
in Git LFS are small pointers in Git and always pass.

    check-file-size.py --staged        the pre-commit hook: what is staged
    check-file-size.py --since REV     CI: files changed from REV to HEAD
    check-file-size.py --tracked       every tracked file, for maintenance
"""
import argparse
import fnmatch
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ".github/large-files.txt"
LIMIT = 1024 * 1024


def git(root, *argv, data=None):
    return subprocess.run(["git", "--no-optional-locks", "-C", str(root), *argv], input=data,
                          check=True, capture_output=True, text=True).stdout


def allowlist_text(root, revision):
    """The allowlist as staged (""), as of a commit, or on disk (None)."""
    if revision is not None:
        try:
            return git(root, "show", f"{revision}:{ALLOWLIST}")
        except subprocess.CalledProcessError:
            if revision != "":
                return ""
    path = root / ALLOWLIST
    return path.read_text() if path.is_file() else ""


def allowed_patterns(root, revision):
    text = allowlist_text(root, revision)
    patterns = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            patterns.append(line)
    return patterns


def sizes(root, revision, paths):
    """Blob size of each path in the index (revision "") or a commit."""
    if not paths:
        return {}
    request = "".join(f"{revision}:{path}\n" for path in paths)
    answer = git(root, "cat-file", "--batch-check=%(objecttype) %(objectsize)", data=request)
    found = {}
    for path, line in zip(paths, answer.splitlines()):
        fields = line.split()
        if len(fields) == 2 and fields[0] == "blob":
            found[path] = int(fields[1])
    return found


def changed_paths(root, mode, since):
    if mode == "staged":
        output = git(root, "diff", "--cached", "--name-only", "--diff-filter=AM", "--no-renames", "-z")
    elif mode == "since":
        output = git(root, "diff", "--name-only", "--diff-filter=AM", "--no-renames", "-z", since, "HEAD")
    else:
        output = git(root, "ls-files", "-z")
    return [path for path in output.split("\0") if path]


def oversized(root, mode, since=""):
    revision = "" if mode == "staged" else "HEAD"
    patterns = allowed_patterns(root, None if mode == "tracked" else revision)
    found = []
    for path, size in sizes(root, revision, changed_paths(root, mode, since)).items():
        if size > LIMIT and not any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns):
            found.append((path, size))
    return sorted(found)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--since", metavar="REV")
    mode.add_argument("--tracked", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    chosen = "staged" if args.staged else "since" if args.since else "tracked"
    found = oversized(args.root, chosen, args.since or "")
    if not found:
        return 0
    print("Files over 1 MB:", file=sys.stderr)
    for path, size in found:
        print(f"  {path} ({size / 1024 / 1024:.1f} MB)", file=sys.stderr)
    print("Keep drafts, renders and explorations in the ignored backup/ folder. If the app ships the "
          f"file, list it in {ALLOWLIST} in the same commit.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
