#!/usr/bin/env python3
"""Run the real F-Droid build and source scanner in an isolated builder.

The caller supplies this checkout at WORKSPACE/build/xyz.waozi.inbe. F-Droid
cleans and resets it, so this entry point refuses the owner's ordinary checkout.
The local runner must use a private Podman :O mount; Actions uses its disposable
job checkout. Neither the Ziran source cache nor local overrides are reused.
"""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
APP_ID = "xyz.waozi.inbe"
REPO = "https://github.com/waozixyz/inbe.git"


def run(*argv, **kwargs):
    return subprocess.run(argv, check=True, text=True, **kwargs)


def main():
    workspace = Path.cwd().resolve()
    if ROOT != workspace / "build" / APP_ID:
        raise SystemExit("Refusing to reset an ordinary checkout; use the isolated F-Droid runner")
    if os.environ.get("GITHUB_ACTIONS") != "true":
        filesystem = subprocess.check_output(
            ["stat", "-f", "-c", "%T", ROOT], text=True).strip()
        if not Path("/run/.containerenv").exists() or filesystem != "overlayfs":
            raise SystemExit("Local F-Droid checks require a private Podman overlay")
    for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS",
                 "ZIRAN", "ZIRAN_PACKAGE_SOURCES"):
        os.environ.pop(name, None)
    os.environ["YUE_DESKTOP_RECOVERY"] = "0"
    os.environ["XDG_CACHE_HOME"] = str(workspace / "cache")
    if (workspace / "cache" / "ziran").exists():
        raise SystemExit("F-Droid must start with an empty Ziran source cache")
    if (ROOT / "ziran.local.toml").exists():
        raise SystemExit("F-Droid must use the committed lock without local overrides")
    run("git", "config", "--global", "--add", "safe.directory", str(ROOT))
    commit = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"], text=True).strip()
    version = subprocess.check_output(
        ["python3", "scripts/check-version.py", "--print-version"], cwd=ROOT, text=True).strip()
    # Android's versionCode is synchronized by update_version.sh.
    import re
    code = int(re.search(r"versionCode\s+(\d+)",
                         (ROOT / "droid/app/build.gradle").read_text())[1])
    recipe = json.loads((ROOT / "packaging/fdroid-build.json").read_text())
    build = dict(versionName=version, versionCode=code, commit=commit, **recipe)
    metadata = {
        "Categories": ["Sports & Health"], "License": "BSD-3-Clause",
        "SourceCode": "https://github.com/waozixyz/inbe",
        "AutoName": "Inner Breeze", "RepoType": "git", "Repo": REPO,
        "Builds": [build], "AutoUpdateMode": "Version", "UpdateCheckMode": "Tags",
        "CurrentVersion": version, "CurrentVersionCode": code,
    }
    from fdroidserver import metadata as fdroid_metadata
    folder = workspace / "metadata"
    folder.mkdir(exist_ok=True)
    fdroid_metadata.write_metadata(folder / (APP_ID + ".yml"), fdroid_metadata.App(metadata))
    (workspace / "build" / (".fdroidvcs-" + APP_ID)).write_text("git " + REPO + "\n")
    # The already checked-out commit is the exact candidate, which may not
    # have been pushed yet. F-Droid still performs its normal reset and clean.
    (workspace / "config.yml").write_text(
        "sdk_path: /opt/android-sdk\n"
        "gradle: /home/vagrant/gradlew-fdroid/gradlew-fdroid\n")
    run("fdroid", "build", "--verbose", "--test", "--no-refresh", "--no-tarball",
        "--scan-binary", APP_ID + ":" + str(code))
    apk = workspace / "tmp" / (APP_ID + "_" + str(code) + ".apk")
    if not apk.is_file():
        raise SystemExit("F-Droid did not produce the expected unsigned APK")
    print("F-Droid source and APK scans and unsigned build passed:", apk, flush=True)


if __name__ == "__main__":
    main()
