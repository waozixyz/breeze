#!/usr/bin/env python3
"""Materialize a fixed commit only inside the existing release container overlay."""
from pathlib import Path
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


def prepare(root, revision):
    root = Path(root).resolve(strict=True)
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


if __name__ == "__main__":
    try:
        prepare(sys.argv[1], sys.argv[2])
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print("release-ready: " + str(error), file=sys.stderr)
        sys.exit(2)
