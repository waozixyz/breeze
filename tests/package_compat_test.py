#!/usr/bin/env python3
"""Run app packages across Inner Breeze versions before they reach phones.

Forward: this build runs every package the Waozi node serves to an app with its
host interface. Phones still hold those packages when they install this app.

Reverse: the last released app runs each package built here that declares a
host interface the released app accepts, so a package update that claims to
support older apps cannot break them.

Each package is loaded with --bundle, which validates it and fails the run when
the host rejects it, and its app is opened and rendered once.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "waozixyz/inbe"
# (ledger name, app ID, local bundle, --feature name)
PACKAGES = (
    ("inbe", "inbe", "build/inbe.zib", None),
    ("lists", "inbe.lists", "build/cells/lists.zib", "lists"),
    ("habits", "inbe.habits", "build/cells/habits.zib", "habits"),
    ("practices", "inbe.practices", "build/cells/practices.zib", "practices"),
    ("diary", "inbe.diary", "build/cells/diary.zib", "diary"),
    ("lumi", "inbe.lumi", "build/cells/lumi.zib", "lumi"),
    ("leaderboard", "inbe.leaderboard", "build/cells/leaderboard.zib", None),
)
SCRUBBED = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS",
            "SESSION_MANAGER", "GDK_DISPLAY")


def fetch(url, limit):
    request = urllib.request.Request(url, headers={"User-Agent": "Inbe-Compatibility-Test/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"{url} exceeds {limit} bytes")
    return data


def host_range(ledger):
    """Apps released before version ranges accept only their own interface."""
    return ledger.get("oldest_host_api", ledger["host_api"]), ledger["host_api"]


def declared_host(ledger, name):
    return ledger["apps"][name].get("host_api", ledger["host_api"])


def run_app(binary, bundle, feature, output, label):
    """Open one package and render its app once on a private display."""
    environment = {key: value for key, value in os.environ.items() if key not in SCRUBBED}
    environment.update(YUE_DESKTOP_RECOVERY="0", SDL_AUDIODRIVER="dummy", APP_NO_TRAY="1")
    image = output / (label + ".png")
    log = output / (label + ".log")
    image.unlink(missing_ok=True)
    command = ["xvfb-run", "-a", "-n", "361", "-s", "-screen 0 1280x900x24", str(binary),
               "--bundle", str(bundle), *(["--feature", feature] if feature else []),
               "--screenshot", str(image), "--screenshot-width", "540", "--screenshot-height", "960"]
    with log.open("w") as stream:
        result = subprocess.run(command, env=environment, stdout=stream, stderr=subprocess.STDOUT,
                                timeout=180)
    text = log.read_text(errors="replace")
    if result.returncode != 0 or not image.exists():
        raise AssertionError(f"{label}: the app rejected the package (exit {result.returncode})\n{text[-2000:]}")
    if "cell launch rejected" in text:
        raise AssertionError(f"{label}: the package loaded but its app did not open\n{text[-2000:]}")
    # A host call whose records do not fit fails inside the package and the
    # screen silently loses that part, so any failed call fails the check.
    failures = sorted({line for line in text.splitlines() if "portable execution failed" in line})
    if failures:
        raise AssertionError(f"{label}: package calls failed: " + "; ".join(failures))
    with Image.open(image) as picture:
        if max(ImageStat.Stat(picture.convert("RGB")).stddev) < 2:
            raise AssertionError(f"{label}: the app rendered a blank screen")


def forward(binary, origin, ledger, output):
    oldest, current = host_range(ledger)
    checked = 0
    for name, app_id, _, feature in PACKAGES:
        route = f"{origin}/api/v2/packages/{app_id}"
        try:
            metadata = json.loads(fetch(f"{route}/latest?host_api={current}&module_api={ledger['module_api']}", 65536))
        except urllib.error.HTTPError as error:
            if error.code == 404:
                print(f"forward {app_id}: the node has no release this build can run")
                continue
            raise
        if not oldest <= metadata["host_api"] <= current or metadata["module_api"] != ledger["module_api"]:
            print(f"forward {app_id}: skipped {metadata['version']}, built for host "
                  f"{metadata['host_api']} outside {oldest}..{current}")
            continue
        artifact = metadata["artifacts"][0]
        data = fetch(f"{route}/{artifact['sha256']}.zib", artifact["size"])
        if len(data) != artifact["size"] or hashlib.sha256(data).hexdigest() != artifact["sha256"]:
            raise AssertionError(f"forward {app_id}: the node served bytes that differ from its release")
        bundle = output / f"published-{name}.zib"
        bundle.write_bytes(data)
        run_app(binary, bundle, feature, output, f"forward-{name}")
        print(f"forward {app_id} {metadata['version']} (host {metadata['host_api']}): runs in this build")
        checked += 1
    return checked


def released_app(tag, output):
    """Unpack the release's Linux AppImage without FUSE."""
    image = output / "released.AppImage"
    image.write_bytes(fetch(f"https://github.com/{REPOSITORY}/releases/download/{tag}/"
                            "inbe-linux-x86_64.AppImage", 256 * 1024 * 1024))
    image.chmod(image.stat().st_mode | stat.S_IXUSR)
    environment = {key: value for key, value in os.environ.items() if key not in SCRUBBED}
    subprocess.run([str(image), "--appimage-extract"], cwd=output, env=environment, check=True,
                   stdout=subprocess.DEVNULL, timeout=300)
    return output / "squashfs-root/AppRun"


def reverse(tag, ledger, output):
    released = json.loads(fetch(f"https://raw.githubusercontent.com/{REPOSITORY}/{tag}/apps/versions.json", 65536))
    oldest, current = host_range(released)
    candidates = [package for package in PACKAGES
                  if oldest <= declared_host(ledger, package[0]) <= current and
                  ledger["module_api"] == released["module_api"]]
    if not candidates:
        print(f"reverse {tag}: no package here declares host {oldest}..{current}; nothing to check")
        return 0
    binary = released_app(tag, output)
    for name, app_id, path, feature in candidates:
        bundle = ROOT / path
        if not bundle.exists():
            raise AssertionError(f"reverse {app_id}: {path} is missing; build the packages first")
        run_app(binary, bundle, feature, output, f"reverse-{name}")
        print(f"reverse {app_id} (declares host {declared_host(ledger, name)}): runs in {tag}")
    return len(candidates)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path, nargs="?", help="this build's app; needed unless --skip-forward")
    parser.add_argument("--origin", default="https://api.waozi.xyz")
    parser.add_argument("--release", help="Release tag to check new packages against (default: the latest)")
    parser.add_argument("--skip-forward", action="store_true")
    parser.add_argument("--skip-reverse", action="store_true")
    args = parser.parse_args()
    ledger = json.loads((ROOT / "apps/versions.json").read_text())
    output = ROOT / "build/package-compat-test"
    output.mkdir(parents=True, exist_ok=True)
    checked = 0
    if not args.skip_forward:
        if args.binary is None:
            parser.error("the forward check needs this build's app binary")
        checked += forward(args.binary.resolve(strict=True), args.origin.rstrip("/"), ledger, output)
    if not args.skip_reverse:
        tag = args.release
        if tag is None:
            latest = json.loads(fetch(f"https://api.github.com/repos/{REPOSITORY}/releases/latest", 1 << 20))
            tag = latest["tag_name"]
        with tempfile.TemporaryDirectory(prefix="inbe-released-", dir=output) as directory:
            checked += reverse(tag, ledger, Path(directory))
    print(f"Package compatibility: {checked} package runs passed")


if __name__ == "__main__":
    sys.exit(main())
