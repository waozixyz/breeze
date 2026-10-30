#!/usr/bin/env python3
"""Materialize a fixed commit only inside the existing release container overlay."""
from pathlib import Path
import json
import os
import shutil
import stat
import subprocess
import sys


def remove_read_only(function, path, error):
    """Let rmtree remove entries of read-only directories, such as a backup's.

    The mode changes only the overlay's copy; the checkout keeps its own."""
    parent = os.path.dirname(path)
    os.chmod(parent, stat.S_IMODE(os.lstat(parent).st_mode) | stat.S_IRWXU)
    if os.path.isdir(path) and not os.path.islink(path):
        os.chmod(path, stat.S_IMODE(os.lstat(path).st_mode) | stat.S_IRWXU)
        shutil.rmtree(path, onexc=remove_read_only)
    else:
        function(path)


def tracked_files(git):
    """Yield each tracked file's path and its mode and blob."""
    for entry in git("ls-files", "--stage", "-z").split(b"\0"):
        if not entry or entry.startswith(b"160000 "):
            continue
        info, path = entry.split(b"\t", 1)
        mode, blob = info.split()[:2]
        yield os.fsdecode(path), mode.decode() + " " + blob.decode()


def write_times(record, times):
    record.parent.mkdir(parents=True, exist_ok=True)
    temporary = record.with_name(record.name + ".tmp")
    temporary.write_text(json.dumps(times))
    temporary.replace(record)


def restore_unchanged_times(git, root, record):
    """Give each file whose content matches the last run its earlier time.

    Materializing writes every file anew, so make and CMake would rebuild
    everything. The record maps each path to its blob and its time; changed
    files keep the current time. It is written before building, so a failed
    build cannot leave outputs that look newer than a later content change."""
    previous = json.loads(record.read_text()) if record.exists() else {}
    current = {}
    for name, identity in tracked_files(git):
        known = previous.get(name)
        if known and known[0] == identity:
            os.utime(root / name, ns=(known[1], known[1]), follow_symlinks=False)
            current[name] = known
        else:
            current[name] = [identity, (root / name).lstat().st_mtime_ns]
    write_times(record, current)
    print("release-ready: kept the times of unchanged files", flush=True)


def record_final_times(git, root, record):
    """After a passing build, keep the times the build left, such as those of
    generated tracked files it rewrote with the same content."""
    times = {name: [identity, (root / name).lstat().st_mtime_ns]
             for name, identity in tracked_files(git)}
    write_times(record, times)


def overlay_git(root):
    """Return Git for root once it is proven to be a private release overlay."""
    filesystem = subprocess.check_output(
        ["stat", "-f", "-c", "%T", root], text=True).strip()
    mounts = [line.split() for line in Path("/proc/self/mountinfo").read_text().splitlines()]
    private_mount = any(fields[4] == str(root) and fields[fields.index("-") + 1] == "overlay"
                        for fields in mounts)
    if root not in (Path("/src"), Path("/sync-server")) or filesystem != "overlayfs" or not private_mount:
        raise ValueError("release source is not a dedicated private overlay; refusing to change it")
    if not (root / ".git").is_dir() or (root / ".git").is_symlink():
        raise ValueError("release overlay must contain the canonical Git directory")

    def git(*arguments):
        return subprocess.check_output(
            ["git", "-c", "safe.directory=" + str(root), "-c", "core.hooksPath=/dev/null",
             "-C", str(root), *arguments])

    return git


def prepare(root, revision, times_record=None):
    root = Path(root).resolve(strict=True)
    git = overlay_git(root)
    commit = git("rev-parse", revision + "^{commit}").decode().strip()
    git("config", "--global", "--add", "safe.directory", str(root))
    git("lfs", "install", "--skip-repo")
    git("update-ref", "--no-deref", "HEAD", commit)
    git("reset", "--hard", commit)
    # reset alone reuses unchanged lower-layer files. Recreating directories
    # makes them opaque in the overlay, hiding later peer additions as well.
    # Existing immutable submodules are retained and verified by their runner.
    retained = {".git", "build"}
    for entry in git("ls-files", "--stage", "-z").split(b"\0"):
        if entry.startswith(b"160000 "):
            retained.add(os.fsdecode(entry.split(b"\t", 1)[1]).split("/", 1)[0])
    for entry in root.iterdir():
        if entry.name in retained:
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry, onexc=remove_read_only)
        else:
            entry.unlink()
    git("checkout-index", "--all", "--force")
    git("diff", "--exit-code", commit, "--", ".")
    print("release-ready: fixed commit materialized in private overlay", flush=True)
    if times_record:
        restore_unchanged_times(git, root, root / times_record)


if __name__ == "__main__":
    try:
        if sys.argv[1] == "--record-times":
            root = Path(sys.argv[2]).resolve(strict=True)
            record_final_times(overlay_git(root), root, root / sys.argv[3])
        else:
            prepare(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print("release-ready: " + str(error), file=sys.stderr)
        sys.exit(2)
