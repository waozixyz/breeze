#!/usr/bin/env python3
"""Scan tracked content for secrets without echoing secret values."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import math
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ZERO_SHA = "0" * 40

SKIP_PREFIXES = (
    ".git/",
    ".gradle/",
    ".local/",
    ".secrets/",
    "build/",
    "node_modules/",
    "tmp/",
    "vendor/",
    "vendor-builds/",
)

SKIP_SUFFIXES = (
    ".a",
    ".aab",
    ".apk",
    ".AppImage",
    ".class",
    ".dll",
    ".dylib",
    ".exe",
    ".ico",
    ".jar",
    ".jpg",
    ".jpeg",
    ".keystore",
    ".mp3",
    ".ogg",
    ".otf",
    ".png",
    ".so",
    ".snap",
    ".svgz",
    ".ttf",
    ".wasm",
    ".wav",
    ".webp",
    ".zip",
)

PLACEHOLDER_WORDS = (
    "changeme",
    "dummy",
    "example",
    "fake",
    "placeholder",
    "redacted",
    "replace",
    "sample",
    "test",
    "your",
)


@dataclasses.dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    min_entropy: float = 0.0


@dataclasses.dataclass(frozen=True)
class Finding:
    rule: str
    source: str
    path: str
    line: int
    fingerprint: str
    commit: str = ""
    blob: str = ""


RULES = (
    Rule("private-key-block", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----")),
    Rule("aws-access-key", re.compile(r"(?P<secret>(?:A3T[A-Z0-9]|AKIA|ASIA)[A-Z0-9]{16})")),
    Rule("github-token", re.compile(r"(?P<secret>gh[pousr]_[A-Za-z0-9_]{36,255}|github_pat_[A-Za-z0-9_]{22}_[A-Za-z0-9_]{59})")),
    Rule("google-api-key", re.compile(r"(?P<secret>AIza[0-9A-Za-z_-]{35})")),
    Rule("openai-api-key", re.compile(r"(?P<secret>sk-(?:proj-)?[A-Za-z0-9_-]{32,})")),
    Rule("slack-token", re.compile(r"(?P<secret>xox[baprs]-[A-Za-z0-9-]{20,})")),
    Rule("stripe-secret-key", re.compile(r"(?P<secret>sk_(?:live|test)_[A-Za-z0-9]{16,})")),
    Rule(
        "credential-assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|"
            r"password|passwd|private[_-]?key|secret)\b\s*[:=]\s*[\"']?"
            r"(?P<secret>[A-Za-z0-9+/_=.\-]{16,})"
        ),
        min_entropy=3.2,
    ),
)

ALLOWED_FINDINGS = {
    # Historical code/build strings that match the generic credential-assignment
    # heuristic but are not committed credentials.
    ("droid/app/build.gradle", "credential-assignment", "dd9958e19a3251bf"),
    ("src/storage/sync_account.c", "credential-assignment", "cb92a7d64e014e24"),
    ("src/storage/sync_account.zi", "credential-assignment", "c08d2d4080bf45d1"),
}


def git(*args: str, input_bytes: bytes | None = None) -> bytes:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=ROOT,
            input=input_bytes,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"check-secrets: git {' '.join(args)} failed") from exc


def is_skipped_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    return normalized.startswith(SKIP_PREFIXES) or normalized.endswith(SKIP_SUFFIXES)


def is_binary(data: bytes) -> bool:
    if b"\0" in data:
        return True
    sample = data[:4096]
    if not sample:
        return False
    control = sum(1 for byte in sample if byte < 9 or (13 < byte < 32))
    return control / len(sample) > 0.08


def entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = {char: value.count(char) for char in set(value)}
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def looks_like_placeholder(value: str) -> bool:
    lowered = value.lower()
    if value.startswith("$") or "${{" in value:
        return True
    if any(word in lowered for word in PLACEHOLDER_WORDS):
        return True
    if re.fullmatch(r"[A-Z0-9_]+", value) and "_" in value:
        return True
    if len(set(value)) <= 3:
        return True
    return False


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:16]


def scan_text(data: bytes, *, source: str, path: str, commit: str = "", blob: str = "") -> list[Finding]:
    if is_skipped_path(path) or is_binary(data):
        return []
    text = data.decode("utf-8", "replace")
    findings: list[Finding] = []
    seen: set[tuple[str, int, str]] = set()

    for line_number, line in enumerate(text.splitlines(), 1):
        if len(line) > 20000:
            continue
        for rule in RULES:
            for match in rule.pattern.finditer(line):
                value = match.groupdict().get("secret") or match.group(0)
                value = value.strip("\"'")
                if looks_like_placeholder(value):
                    continue
                if rule.min_entropy and entropy(value) < rule.min_entropy:
                    continue
                key = (rule.name, line_number, fingerprint(value))
                if (path, rule.name, key[2]) in ALLOWED_FINDINGS:
                    continue
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    Finding(
                        rule=rule.name,
                        source=source,
                        path=path,
                        line=line_number,
                        fingerprint=key[2],
                        commit=commit,
                        blob=blob,
                    )
                )
    return findings


def staged_files() -> list[str]:
    data = git("diff", "--cached", "--name-only", "--diff-filter=ACMRT", "-z")
    return [path.decode("utf-8", "replace") for path in data.split(b"\0") if path]


def tracked_files() -> list[str]:
    data = git("ls-files", "-z")
    return [path.decode("utf-8", "replace") for path in data.split(b"\0") if path]


def scan_staged() -> list[Finding]:
    findings: list[Finding] = []
    for path in staged_files():
        if is_skipped_path(path):
            continue
        try:
            data = git("show", f":{path}")
        except SystemExit:
            continue
        findings.extend(scan_text(data, source="staged", path=path))
    return findings


def scan_working_tree() -> list[Finding]:
    findings: list[Finding] = []
    for path in tracked_files():
        if is_skipped_path(path):
            continue
        full_path = ROOT / path
        if not full_path.is_file():
            continue
        findings.extend(scan_text(full_path.read_bytes(), source="working-tree", path=path))
    return findings


def scan_git_objects(rev_args: list[str], *, source: str) -> list[Finding]:
    data = git("rev-list", "--objects", *rev_args)
    findings: list[Finding] = []
    seen_objects: set[tuple[str, str]] = set()
    for raw_line in data.splitlines():
        parts = raw_line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        oid = parts[0].decode("ascii", "replace")
        path = parts[1].decode("utf-8", "replace")
        if (oid, path) in seen_objects or is_skipped_path(path):
            continue
        seen_objects.add((oid, path))
        if git("cat-file", "-t", oid).strip() != b"blob":
            continue
        blob = git("cat-file", "blob", oid)
        findings.extend(scan_text(blob, source=source, path=path, blob=oid))
    return findings


def commits_for_args(rev_args: list[str]) -> list[str]:
    if not rev_args:
        return []
    data = git("rev-list", *rev_args)
    return [line.decode("ascii", "replace") for line in data.splitlines() if line]


def commits_for_blob(blob: str) -> list[str]:
    if not blob:
        return []
    try:
        data = git("log", "--all", f"--find-object={blob}", "--format=%H")
    except SystemExit:
        return []
    commits: list[str] = []
    for line in data.splitlines():
        commit = line.decode("ascii", "replace")
        if commit and commit not in commits:
            commits.append(commit)
    return commits


def scan_commit(commit: str) -> list[Finding]:
    findings = scan_text(git("log", "-1", "--format=%B", commit), source="commit-message", path="<commit-message>", commit=commit)
    tree = git("ls-tree", "-r", "-z", "--full-tree", commit)
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        meta, raw_path = entry.split(b"\t", 1)
        mode, kind, oid = meta.decode("ascii", "replace").split()
        if kind != "blob":
            continue
        path = raw_path.decode("utf-8", "replace")
        if is_skipped_path(path):
            continue
        findings.extend(scan_text(git("cat-file", "blob", oid), source="commit", path=path, commit=commit, blob=oid))
    return findings


def scan_commits(rev_args: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for commit in commits_for_args(rev_args):
        findings.extend(scan_commit(commit))
    return findings


def pre_push_rev_args(remote: str, stdin: bytes) -> list[list[str]]:
    ranges: list[list[str]] = []
    for raw_line in stdin.splitlines():
        parts = raw_line.decode("utf-8", "replace").split()
        if len(parts) != 4:
            continue
        _local_ref, local_sha, _remote_ref, remote_sha = parts
        if local_sha == ZERO_SHA:
            continue
        if remote_sha == ZERO_SHA:
            ranges.append([local_sha, "--not", f"--remotes={remote}"])
        else:
            ranges.append([f"{remote_sha}..{local_sha}"])
    return ranges


def report(findings: list[Finding]) -> int:
    if not findings:
        print("check-secrets: no candidate secrets found")
        return 0

    print(f"check-secrets: found {len(findings)} candidate secret(s); values are redacted", file=sys.stderr)
    for finding in findings:
        location = f"{finding.path}:{finding.line}"
        details = [f"rule={finding.rule}", f"fingerprint={finding.fingerprint}"]
        if finding.commit:
            details.append(f"commit={finding.commit[:12]}")
        if finding.blob:
            details.append(f"blob={finding.blob[:12]}")
        if finding.blob and not finding.commit and finding.source == "history":
            commits = commits_for_blob(finding.blob)
            if commits:
                details.append("commits=" + ",".join(commit[:12] for commit in commits[:5]))
                if len(commits) > 5:
                    details.append(f"commit_count={len(commits)}")
        print(f"  {location} ({', '.join(details)})", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true", help="scan files staged for commit")
    mode.add_argument("--working-tree", action="store_true", help="scan tracked files in the working tree")
    mode.add_argument("--history", action="store_true", help="scan every reachable historical blob")
    mode.add_argument("--commits", nargs="+", metavar="REV", help="scan every commit in the given rev-list arguments")
    mode.add_argument("--pre-push", action="store_true", help="scan commits read from git pre-push stdin")
    parser.add_argument("hook_args", nargs="*", help=argparse.SUPPRESS)
    args = parser.parse_args()

    os.chdir(ROOT)
    if args.staged:
        findings = scan_staged()
    elif args.working_tree:
        findings = scan_working_tree()
    elif args.history:
        findings = scan_git_objects(["--all"], source="history")
    elif args.commits:
        findings = scan_commits(args.commits)
    else:
        remote = args.hook_args[0] if args.hook_args else "origin"
        ranges = pre_push_rev_args(remote, sys.stdin.buffer.read())
        findings = []
        for rev_args in ranges:
            findings.extend(scan_commits(rev_args))
    return report(findings)


if __name__ == "__main__":
    raise SystemExit(main())
