#!/usr/bin/env python3
"""Seed the Ziran package cache from source checkouts that are already on disk.

A builder that supplies dependency sources itself (F-Droid srclibs, a release
source tree, an offline mirror) should not need the network. For every entry
in ziran.lock, and for the locked toolchain, this looks for a local Git
checkout that contains the locked commit and clones it into the cache
directory `ziran fetch` would use. A checkout is found by its repository or
package name in:

  $ZIRAN_PACKAGE_SOURCES   when set
  ../srclib                F-Droid's srclib layout, when present

Submodules of a seeded package are filled from a local source with the
submodule's name the same way. Anything not found is left for
`ziran fetch` to download, and a checkout without the locked commit is never
used.
"""

from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parent.parent


def git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "protocol.file.allow=always", *args],
                          cwd=cwd, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "ziran" / "sources"


def source_id(url: str, commit: str) -> str:
    # Matches PkgSourceId in Ziran's package tool.
    return "p" + hashlib.sha256(f"{url}\n{commit}".encode()).hexdigest()[:16]


def key(name: str) -> str:
    name = name.lower()
    if name.endswith(".git"):
        name = name[:-4]
    return name.replace("_", "-")


def source_dirs() -> list[Path]:
    dirs = []
    explicit = os.environ.get("ZIRAN_PACKAGE_SOURCES")
    if explicit:
        dirs.append(Path(explicit))
    srclib = root.parent / "srclib"
    if srclib.is_dir():
        dirs.append(srclib)
    return [d.resolve() for d in dirs if d.is_dir()]


def index_sources(dirs: list[Path]) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for directory in dirs:
        for child in sorted(directory.iterdir()):
            if child.is_dir():
                found.setdefault(key(child.name), child)
    return found


def has_commit(repo: Path, commit: str) -> bool:
    return git("-C", str(repo), "cat-file", "-e",
               f"{commit}^{{commit}}").returncode == 0


def find(sources: dict[str, Path], commit: str, *names: str) -> Path | None:
    for name in names:
        candidate = sources.get(key(name))
        if candidate is not None and has_commit(candidate, commit):
            return candidate
    return None


def seed_submodules(checkout: Path, sources: dict[str, Path]) -> None:
    listed = git("-C", str(checkout), "config", "-f", ".gitmodules",
                 "--get-regexp", r"^submodule\..*\.url$")
    if listed.returncode != 0:
        return
    for line in listed.stdout.splitlines():
        setting, url = line.split(" ", 1)
        name = setting[len("submodule."):-len(".url")]
        path = git("-C", str(checkout), "config", "-f", ".gitmodules",
                   f"submodule.{name}.path").stdout.strip()
        tree = git("-C", str(checkout), "ls-tree", "HEAD", path).stdout.split()
        if len(tree) < 3 or tree[1] != "commit":
            continue
        local = find(sources, tree[2], Path(path).name, url.rstrip("/").rsplit("/", 1)[-1])
        if local is None:
            continue
        result = git("-C", str(checkout), "-c", f"url.{local}.insteadOf={url}",
                     "submodule", "update", "--init", "--quiet", "--", path)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)


def seed(url: str, commit: str, sources: dict[str, Path], *names: str) -> bool:
    destination = cache_dir() / source_id(url, commit)
    if destination.exists():
        return False
    local = find(sources, commit, url.rstrip("/").rsplit("/", 1)[-1], *names)
    if local is None:
        return False
    staging = destination.with_name(destination.name + ".seed")
    shutil.rmtree(staging, ignore_errors=True)
    staging.parent.mkdir(parents=True, exist_ok=True)
    for step in (("clone", "--quiet", "--no-checkout", str(local), str(staging)),
                 ("-C", str(staging), "checkout", "--quiet", "--detach", commit)):
        result = git(*step)
        if result.returncode != 0:
            shutil.rmtree(staging, ignore_errors=True)
            sys.stderr.write(result.stderr)
            return False
    # Ziran's cache keeps the upstream URL; the local path was only the source.
    git("-C", str(staging), "remote", "set-url", "origin", url)
    seed_submodules(staging, sources)
    staging.rename(destination)
    print(f"packages: using local source {local} for {names[0] if names else url}")
    return True


def main() -> None:
    sources = index_sources(source_dirs())
    if not sources:
        return
    lock = json.loads((root / "ziran.lock").read_text())
    edges = {value: name for name, value in lock["root"]["dependencies"].items()}
    for package in lock["packages"]:
        seed(package["url"], package["commit"], sources,
             edges.get(package["id"], package["name"]), package["name"])
    tool = lock["toolchain"]
    seed(tool["url"], tool["commit"], sources, "ziran")


if __name__ == "__main__":
    main()
