#!/usr/bin/env python3
"""Check Inner Breeze on the development Moto and make its one release commit.

    make release              build the debug APK for the Moto, check it, commit
    make release APK=PATH     check an APK already built from these sources

1. The version is the newest numeric CHANGELOG.md entry, not yet tagged.
2. App files, CHANGELOG.md, the store notes and the receipts have no
   uncommitted changes (another session's work must be committed first), and
   every ziran.local.toml override sits clean on its locked commit, so the
   phone runs what CI builds.
3. An unpushed "Release Inner Breeze X.Y.Z" commit with later commits on top
   moves to the top (only refs move; the working tree and index stay as is),
   so the release remains one commit however many late fixes it needed.
4. ./update_version.sh syncs the version files into the release commit.
5. `make release-ready` must have passed for exactly this content.
6. The APK is built (unless given) and checked on the Moto; a passing check
   is recorded with the app's content identity (scripts/phone-check.py).
7. The receipt joins the release commit, and the release gate checks HEAD.

Nothing is pushed or tagged. Pushing master starts the Release workflow, so it
waits for the owner's say-so.
"""
import argparse
from datetime import datetime, timezone
import fnmatch
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
READY_STAMP = ROOT / "build/release-ready/stamp.json"
SUBJECT = "Release Inner Breeze {version}"
# What ./update_version.sh writes; only these may join the release commit.
VERSION_FILES = ("droid/app/build.gradle", "src/core/version.h", "src/core/version.zi", "windows/inbe.rc",
                 "packaging/*", "fastlane/metadata/android/en-US/changelogs/*.txt", "apps/*/CHANGELOG.md",
                 "apps/versions.json", "src/cells/versions.zi", "src/cells/host_api.zi")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


phone_check = load("phone_check", "scripts/phone-check.py")
gate = load("check_phone_check", "scripts/check-phone-check.py")


class Refused(Exception):
    pass


def git(*argv, env=None):
    return phone_check.git(ROOT, *argv, env=env)


def step(text):
    print(f"\n==> {text}", flush=True)


def changelog_version():
    found = re.search(r"^## \[(\d+\.\d+\.\d+)\]", (ROOT / "CHANGELOG.md").read_text(), re.M)
    if not found:
        raise Refused("CHANGELOG.md has no numeric release entry")
    return found[1]


def require_new_version(version):
    tag = f"refs/tags/v{version}"
    if subprocess.run(["git", "-C", ROOT, "rev-parse", "-q", "--verify", tag],
                      capture_output=True).returncode == 0:
        raise Refused(f"v{version} is already tagged; add the next version to CHANGELOG.md")
    remote = subprocess.run(["git", "-C", ROOT, "ls-remote", "--tags", "origin", tag],
                            capture_output=True, text=True, timeout=60)
    if remote.returncode == 0 and remote.stdout.strip():
        raise Refused(f"v{version} is already tagged on GitHub; add the next version to CHANGELOG.md")


def release_inputs_changed():
    changed = []
    for _, path in phone_check.status(ROOT):
        if path.startswith(phone_check.RECEIPTS + "/"):
            continue
        if phone_check.is_app_path(path) or path == "CHANGELOG.md" or path.startswith("fastlane/"):
            changed.append(path)
    return changed


def overrides():
    path = ROOT / "ziran.local.toml"
    if not path.is_file():
        return {}
    found = {}
    section = ""
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line.startswith("["):
            section = line
        elif section == "[overrides]" and "=" in line:
            name, value = (part.strip() for part in line.split("=", 1))
            found[name.lower()] = (ROOT / value.strip('"')).resolve()
    return found


def require_locked_overrides():
    locked = {package["name"].lower(): package["commit"]
              for package in json.loads((ROOT / "ziran.lock").read_text())["packages"]}
    problems = []
    for name, path in overrides().items():
        if name not in locked:
            continue
        head = phone_check.git(path, "rev-parse", "HEAD").strip()
        if head != locked[name]:
            problems.append(f"{name} ({path}) is at {head[:10]}, the lock pins {locked[name][:10]}")
            continue
        dirty = phone_check.status(path)
        if dirty:
            problems.append(f"{name} ({path}) has uncommitted changes: "
                            + ", ".join(entry for _, entry in dirty[:5]))
    if problems:
        raise Refused("the phone would not run what CI builds:\n  " + "\n  ".join(problems)
                      + "\nCommit and pin the package (ziran update NAME), or wait for its owner.")


def unpushed_release(version):
    subject = SUBJECT.format(version=version)
    log = git("log", "--format=%H%x00%P%x00%s", "origin/master..HEAD")
    found = []
    for line in log.splitlines():
        commit, parents, text = line.split("\0")
        if text == subject:
            if len(parents.split()) != 1:
                raise Refused(f"the release commit {commit[:10]} is a merge")
            found.append(commit)
    if len(found) > 1:
        raise Refused("several unpushed release commits: " + ", ".join(c[:10] for c in found))
    return found[0] if found else ""


def require_unpushed(commit):
    remote = subprocess.run(["git", "-C", ROOT, "ls-remote", "origin", "refs/heads/master"],
                            capture_output=True, text=True, timeout=60)
    if remote.returncode != 0 or not remote.stdout.strip():
        raise Refused("cannot read GitHub's master to confirm the release commit is unpushed")
    pushed = remote.stdout.split()[0]
    known = subprocess.run(["git", "-C", ROOT, "cat-file", "-e", pushed + "^{commit}"],
                           capture_output=True).returncode == 0
    if not known:
        raise Refused(f"GitHub's master {pushed[:10]} is not here; fetch it before releasing")
    if subprocess.run(["git", "-C", ROOT, "merge-base", "--is-ancestor", commit, pushed],
                      capture_output=True).returncode == 0:
        raise Refused(f"the release commit {commit[:10]} is already pushed")


def without_release_notes(commit, notes):
    """Leave note edits for the final release commit, using a private index."""
    with tempfile.TemporaryDirectory(prefix="inbe-release-notes-") as temporary:
        environment = dict(os.environ, GIT_INDEX_FILE=str(Path(temporary) / "index"))
        git("read-tree", commit, env=environment)
        for path in notes:
            entry = git("ls-tree", commit + "^", "--", path).strip()
            if entry:
                mode, _, blob = entry.split("\t", 1)[0].split()
                git("update-index", "--add", "--cacheinfo", mode, blob, path, env=environment)
            else:
                git("update-index", "--force-remove", "--", path, env=environment)
        tree = git("write-tree", env=environment).strip()
    return subprocess.run(["git", "-C", ROOT, "commit-tree", tree, "-p", commit + "^", "-F", "-"],
                          input="Release-note replay input\n", check=True, capture_output=True,
                          text=True).stdout.strip()


def replay(commit, parent, notes=()):
    """Commit `commit`'s change again on `parent`, without a working tree."""
    replayed = without_release_notes(commit, notes) if notes else commit
    merged = subprocess.run(["git", "-C", ROOT, "merge-tree", "--write-tree", "--merge-base",
                             commit + "^", parent, replayed], capture_output=True, text=True)
    if merged.returncode != 0:
        raise Refused(f"{commit[:10]} changes the release commit's files, so the release commit "
                      "cannot move to the top; nothing was changed")
    tree = merged.stdout.split()[0]
    name, email, date = git("log", "-1", "--format=%an%x00%ae%x00%ad", "--date=raw", commit).strip().split("\0")
    message = git("log", "-1", "--format=%B", commit)
    environment = dict(os.environ, GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email, GIT_AUTHOR_DATE=date)
    return subprocess.run(["git", "-C", ROOT, "commit-tree", tree, "-p", parent, "-F", "-"], input=message,
                          check=True, capture_output=True, text=True, env=environment).stdout.strip()


def move_to_top(release, version):
    """Replay the commits after the unpushed release commit onto its parent,
    then commit the release commit's files again on top. Only refs move; the
    working tree and the index keep every file as it is."""
    require_unpushed(release)
    head = git("rev-parse", "HEAD").strip()
    files = git("diff-tree", "--no-commit-id", "--name-only", "-r", "--no-renames", release).split()
    notes = [path for path in files if path == "CHANGELOG.md" or
             fnmatch.fnmatchcase(path, "fastlane/metadata/android/*/changelogs/*.txt")]
    later = git("rev-list", "--reverse", "--parents", f"{release}..{head}").splitlines()
    parent = release + "^"
    for line in later:
        commit, *parents = line.split()
        if len(parents) != 1:
            raise Refused(f"{commit[:10]} is a merge; nothing was changed")
        changed = set(git("diff-tree", "--no-commit-id", "--name-only", "-r", "--no-renames", commit).split())
        parent = replay(commit, git("rev-parse", parent).strip(), [path for path in notes if path in changed])
    subprocess.run(["git", "-C", ROOT, "update-ref", "-m", "release: move the release commit to the top",
                    "refs/heads/master", parent, head], check=True)
    commit_files(files, version, amend=False)
    print(f"Moved the release commit to the top ({len(files)} files).")


def commit_files(files, version, amend, details=""):
    message = SUBJECT.format(version=version) + ("\n\n" + details if details else "")
    subprocess.run(["git", "-C", ROOT, "add", "--", *files], check=True)
    argv = ["git", "-C", ROOT, "commit", "-q", "--only", "-m", message]
    if amend:
        argv.insert(4, "--amend")
    subprocess.run([*argv, "--", *files], check=True)


def release_at_head(version):
    subject = git("log", "-1", "--format=%s").strip()
    return subject == SUBJECT.format(version=version) and unpushed_release(version) != ""


def require_release_ready():
    try:
        stamp = json.loads(READY_STAMP.read_text())
    except (OSError, ValueError):
        raise Refused("make release-ready has not passed here; run it first") from None
    content = phone_check.release_content(ROOT, "HEAD")
    if stamp.get("passed") is not True or stamp.get("content") != content:
        raise Refused("make release-ready passed for other content "
                      f"({stamp.get('commit', '?')[:10]}); run it again for HEAD")


def build_apk(phone):
    abi = phone.shell("getprop", "ro.product.cpu.abi").strip()
    if not re.fullmatch(r"[a-z0-9_-]+", abi):
        raise Refused(f"the phone reported no usable ABI: {abi!r}")
    started = time.time()
    environment = dict(os.environ)
    for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS"):
        environment.pop(name, None)
    subprocess.run(["make", "-C", ROOT, "android-debug", f"ANDROID_ABI={abi}"], check=True, env=environment)
    apk = ROOT / f"droid/app/build/outputs/apk/debug/app-{abi}-debug.apk"
    if not apk.is_file() or apk.stat().st_mtime < started:
        raise Refused(f"the build did not produce {apk.relative_to(ROOT)}")
    return apk


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apk", type=Path, help="an APK built from the current sources")
    parser.add_argument("--host", default=os.environ.get("INBE_PHONE_HOST", "auto"))
    parser.add_argument("--serial", default=os.environ.get("INBE_PHONE_SERIAL", "ZE2223BQZT"))
    parser.add_argument("--phone-check-waiver", metavar="OWNER_AUTHORIZATION",
                        help="skip the Moto only when explicitly authorized by the owner for this release")
    args = parser.parse_args()
    if args.phone_check_waiver is not None and not args.phone_check_waiver.strip():
        parser.error("the phone-check waiver must quote the owner's explicit authorization")
    try:
        if git("symbolic-ref", "--short", "HEAD").strip() != "master":
            raise Refused("releases are made on master")
        version = changelog_version()
        step(f"Inner Breeze {version}")
        require_new_version(version)
        changed = release_inputs_changed()
        if changed:
            raise Refused("uncommitted app or release files; commit them or wait for their owner:\n  "
                          + "\n  ".join(changed))
        require_locked_overrides()

        release = unpushed_release(version)
        if release and release != git("rev-parse", "HEAD").strip():
            step("Moving the unpushed release commit above the later commits")
            move_to_top(release, version)

        step("Synchronizing version files (./update_version.sh)")
        subprocess.run([ROOT / "update_version.sh"], check=True, cwd=ROOT)
        synced = release_inputs_changed()
        stray = [path for path in synced
                 if not any(fnmatch.fnmatchcase(path, pattern) for pattern in VERSION_FILES)]
        if stray:
            raise Refused("files changed beside the version files (another session?); nothing was "
                          "committed:\n  " + "\n  ".join(stray))
        if synced:
            commit_files(synced, version, amend=release_at_head(version))
            print("Version files: " + ", ".join(synced))

        step("Requiring make release-ready for this content")
        require_release_ready()
        checked_app = phone_check.app_tree(ROOT, "HEAD")
        if phone_check.app_tree(ROOT) != checked_app:
            raise Refused("app files changed on disk; commit them or wait for their owner")

        if args.phone_check_waiver:
            receipt = dict(schema=3, status="waived", version=version, app_tree=checked_app,
                           source_commit=git("rev-parse", "HEAD").strip(),
                           reason=args.phone_check_waiver.strip(),
                           authorized_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            target = ROOT / phone_check.RECEIPTS / f"{version}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(receipt, indent=2) + "\n")
            step("Moto check explicitly waived by owner for this release")
        else:
            phone = phone_check.Phone(phone_check.resolve_host(args.host, args.serial), args.serial)
            if phone.adb("get-state").decode().strip() != "device":
                raise Refused("the development Moto is not connected and authorized")
            if args.apk:
                apk = args.apk.resolve(strict=True)
            else:
                step("Building the debug APK for the Moto")
                apk = build_apk(phone)
            if phone_check.app_tree(ROOT) != checked_app:
                raise Refused("app files changed during the build; run make release again")

            step(f"Phone check of {apk.name} on the Moto")
            subprocess.run([sys.executable, ROOT / "scripts/phone-check.py", apk, "--record",
                            "--host", phone.host, "--serial", args.serial], check=True)
        receipt = gate.validate(ROOT, version)
        if receipt["app_tree"] != checked_app:
            raise Refused("the recorded check is for other app content")

        step("Release commit")
        if receipt.get("status") == "waived":
            details = f"Moto check waived by owner: {receipt['reason']} App content {checked_app[:12]}."
        else:
            practice = receipt["practice"]
            details = (f"Phone check on the {receipt['device']['model']}: {practice['fps']} fps, "
                       f"{practice['late_percent']}% late frames, app content {checked_app[:12]}.")
        commit_files([f"{phone_check.RECEIPTS}/{version}.json"], version,
                     amend=release_at_head(version), details=details)
        gate.validate(ROOT, version, "HEAD")
        print(git("log", "-1", "--format=%h %s").strip())
        print("Not pushed. Pushing master starts the Release workflow, so push only with the owner's "
              "say-so: git push origin master")
        return 0
    except Refused as error:
        print(f"release: {error}", file=sys.stderr)
        return 1
    except (subprocess.CalledProcessError, ValueError, OSError) as error:
        print(f"release: stopped: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
