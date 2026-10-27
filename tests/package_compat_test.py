#!/usr/bin/env python3
"""Run app packages across Inner Breeze versions before they reach phones.

Forward: this build runs every package the Waozi node serves to an app with its
host interface. Phones still hold those packages when they install this app.

Reverse: the last released app runs each package built here that declares a
host interface the released app accepts, so a package update that claims to
support older apps cannot break them. Packages reach only apps that run their
format: an app released before the ZX format never asks the node for `.zx`
packages, so there is nothing to check against it.

Bundled packages are loaded with --bundle, which validates them and fails the
run when the host rejects them. The node's Arcade, and Chess while the node
still serves it on its own, are installed through More apps, played against
the computer and restarted to check the saved game.
"""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "waozixyz/breeze"
# (ledger name, app ID, local bundle, --feature name)
PACKAGES = (
    ("inbe", "inbe", "build/inbe.zx", None),
    ("lists", "inbe.lists", "build/apps/lists.zx", "lists"),
    ("habits", "inbe.habits", "build/apps/habits.zx", "habits"),
    ("practices", "inbe.practices", "build/apps/practices.zx", "practices"),
    ("diary", "inbe.diary", "build/apps/diary.zx", "diary"),
    ("lumi", "inbe.lumi", "build/apps/lumi.zx", "lumi"),
    ("leaderboard", "inbe.leaderboard", "build/apps/leaderboard.zx", None),
)
SCRUBBED = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS",
            "SESSION_MANAGER", "GDK_DISPLAY")


def fetch(url, limit):
    headers = {"User-Agent": "Inbe-Compatibility-Test/1.0"}
    # Anonymous GitHub API calls share 60 an hour per address, which CI
    # runners exhaust; Actions passes its token as GITHUB_TOKEN. Release
    # downloads redirect to signed storage URLs that must not carry it.
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and urllib.parse.urlsplit(url).hostname == "api.github.com":
        headers["Authorization"] = f"Bearer {token}"
        headers["Accept"] = "application/vnd.github+json"
    request = urllib.request.Request(url, headers=headers)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read(limit + 1)
            if len(data) > limit:
                raise ValueError(f"{url} exceeds {limit} bytes")
            return data
        except urllib.error.HTTPError as error:
            if error.code not in (408, 429, 500, 502, 503, 504) or attempt == 3:
                raise
        except urllib.error.URLError as error:
            reason = error.reason
            temporary_dns = isinstance(reason, socket.gaierror) and reason.errno == socket.EAI_AGAIN
            if not (temporary_dns or isinstance(reason, (TimeoutError, ConnectionError))) or attempt == 3:
                raise
        except (TimeoutError, ConnectionError, http.client.IncompleteRead):
            if attempt == 3:
                raise
        destination = urllib.parse.urlsplit(url)
        print(f"Temporary package transport failure for {destination.hostname}{destination.path}; retrying")
        time.sleep(2 ** attempt)


def host_range(ledger):
    """Apps released before version ranges accept only their own interface."""
    return ledger.get("oldest_host_api", ledger["host_api"]), ledger["host_api"]


def latest_release_tag():
    """GitHub's public latest link avoids shared anonymous API rate limits."""
    request = urllib.request.Request(f"https://github.com/{REPOSITORY}/releases/latest",
                                     headers={"User-Agent": "Inbe-Compatibility-Test/1.0"}, method="HEAD")
    with urllib.request.urlopen(request, timeout=60) as response:
        target = urllib.parse.urlsplit(response.geturl())
    prefix = f"/{REPOSITORY}/releases/tag/"
    if target.scheme != "https" or target.hostname != "github.com" or not target.path.startswith(prefix):
        raise ValueError("GitHub's latest release link did not resolve to this repository's release")
    tag = urllib.parse.unquote(target.path[len(prefix):])
    if not tag or "/" in tag:
        raise ValueError("GitHub's latest release link returned no release tag")
    return tag


def declared_host(ledger, name):
    return ledger["apps"][name].get("host_api", ledger["host_api"])


def run_app(binary, bundle, feature, output, label):
    """Open one package and render its app once on a private display."""
    environment = {key: value for key, value in os.environ.items() if key not in SCRUBBED}
    environment.update(YUE_DESKTOP_RECOVERY="0", SDL_AUDIODRIVER="dummy", APP_NO_TRAY="1")
    image = output / (label + ".png")
    log = output / (label + ".log")
    image.unlink(missing_ok=True)
    command = ["xvfb-run", "-a", "-n", "361", "-s", "-noreset -screen 0 1280x900x24", str(binary),
               "--bundle", str(bundle), *(["--feature", feature] if feature else []),
               "--screenshot", str(image), "--screenshot-width", "540", "--screenshot-height", "960"]
    with tempfile.TemporaryDirectory(prefix=label + '-profile-', dir=output) as profile, log.open("w") as stream:
        environment['APP_DATA_ROOT'] = profile
        result = subprocess.run(command, env=environment, stdout=stream, stderr=subprocess.STDOUT,
                                timeout=180)
    text = log.read_text(errors="replace")
    if result.returncode != 0 or not image.exists():
        raise AssertionError(f"{label}: the app rejected the package (exit {result.returncode})\n{text[-2000:]}")
    if any(message in text for message in ("app launch rejected", "cell launch rejected")):
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
            metadata = json.loads(fetch(f"{route}/latest?host_api={current}&module_api={ledger['module_api']}&format=zx", 65536))
        except urllib.error.HTTPError as error:
            if error.code == 404:
                print(f"forward {app_id}: the node has no release this build can run")
                continue
            raise
        floor = ledger["apps"][name].get("oldest_host_api", oldest)
        if not floor <= metadata["host_api"] <= current or metadata["module_api"] != ledger["module_api"]:
            print(f"forward {app_id}: skipped {metadata['version']}, built for host "
                  f"{metadata['host_api']} outside {floor}..{current}")
            continue
        artifact = metadata["artifacts"][0]
        data = fetch(f"{route}/{artifact['sha256']}.zx", artifact["size"])
        if len(data) != artifact["size"] or hashlib.sha256(data).hexdigest() != artifact["sha256"]:
            raise AssertionError(f"forward {app_id}: the node served bytes that differ from its release")
        bundle = output / f"published-{name}.zx"
        bundle.write_bytes(data)
        run_app(binary, bundle, feature, output, f"forward-{name}")
        print(f"forward {app_id} {metadata['version']} (host {metadata['host_api']}): runs in this build")
        checked += 1
    return checked


def published_release(origin, ledger, app_id, output):
    """Download the node's release of app_id for this build, or None if it serves none."""
    oldest, current = host_range(ledger)
    route = f"{origin}/api/v2/packages/{app_id}"
    try:
        metadata = json.loads(fetch(
            f"{route}/latest?host_api={current}&module_api={ledger['module_api']}&format=zx", 65536))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    if not oldest <= metadata["host_api"] <= current or metadata["module_api"] != ledger["module_api"]:
        raise AssertionError(f"The published {app_id} package does not support this host")
    artifact = metadata["artifacts"][0]
    data = fetch(f"{route}/{artifact['sha256']}.zx", artifact["size"])
    if len(data) != artifact["size"] or hashlib.sha256(data).hexdigest() != artifact["sha256"]:
        raise AssertionError(f"The node's {app_id} bytes differ from its release")
    directory = output / ("published-" + app_id.split(".")[-1])
    directory.mkdir(parents=True, exist_ok=True)
    bundle = directory / (app_id.split(".")[-1] + ".zx")
    bundle.write_bytes(data)
    (directory / "release.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return bundle, metadata


def published_release_retried(origin, ledger, app_id, output, attempts=6, delay=15):
    """The node restarts for a minute or so whenever it is deployed; ask
    again for a while before deciding that it serves no release."""
    for attempt in range(attempts):
        try:
            return published_release(origin, ledger, app_id, output)
        except (OSError, ValueError) as error:
            if attempt == attempts - 1:
                raise
            print(f"forward {app_id}: the node did not answer ({error}); asking again")
            time.sleep(delay)
    return None


def published_companions(origin, bundle):
    """The art and games a published collection downloads, fetched from the
    node beside it as Arcade's build lays them out."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from node_app_games import required_games
    from practice_content import bundle_assets
    catalog = json.loads(bundle_assets(bundle.read_bytes())["assets/apps/catalog.json"])
    sizes = {child["sha256"]: child["bytes"] for child in catalog["children"]}
    if catalog.get("art"):
        sizes[catalog["art"]["sha256"]] = catalog["art"]["bytes"]
    games = bundle.parent / "arcade.games"
    games.mkdir(exist_ok=True)
    for name in sorted(required_games(bundle)):
        digest = name.removesuffix(".zx")
        data = fetch(f"{origin}/api/v2/packages/inbe.arcade/{name}", sizes[digest])
        if len(data) != sizes[digest] or hashlib.sha256(data).hexdigest() != digest:
            raise AssertionError(f"The node's Arcade download {digest} differs from its catalog")
        (games / name).write_bytes(data)
    metadata = {"children": catalog["children"], "art": catalog.get("art")}
    bundle.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")


def published_games(binary, origin, ledger, output):
    """Install and play the node's games, independently of Arcade's checkout.

    Arcade carries Chess; Chess on its own is checked only while the node
    still serves it. At least one of them must be served.
    """
    environment = {key: value for key, value in os.environ.items() if key not in SCRUBBED}
    environment["YUE_DESKTOP_RECOVERY"] = "0"
    checked = 0
    for app_id, test in (("inbe.arcade", "tests/arcade_ui_test.sh"), ("inbe.chess", "tests/chess_ui_test.sh")):
        published = published_release_retried(origin, ledger, app_id, output)
        if published is None:
            print(f"forward {app_id}: the node serves no release")
            continue
        bundle, metadata = published
        extra = []
        if app_id == "inbe.arcade":
            # Arcade packs no games: its covers, downloads and offline reopen.
            published_companions(origin, bundle)
            extra = ["--downloads-only"]
        subprocess.run(["sh", str(ROOT / test), str(binary), str(bundle), *extra],
                       env=environment, check=True, timeout=600)
        print(f"forward {app_id} {metadata['version']}: install, play, board and saved restart passed")
        checked += 1
    if checked == 0:
        raise AssertionError("The node serves neither Arcade nor Chess")
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
    if released.get("package_format", "zib") != ledger.get("package_format", "zib"):
        print(f"reverse {tag}: the released app runs {released.get('package_format', 'zib')} packages and is "
              f"never offered these {ledger.get('package_format', 'zib')} ones; nothing to check")
        return 0
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
        binary = args.binary.resolve(strict=True)
        origin = args.origin.rstrip("/")
        checked += forward(binary, origin, ledger, output)
        checked += published_games(binary, origin, ledger, output)
    if not args.skip_reverse:
        tag = args.release
        if tag is None:
            tag = latest_release_tag()
        with tempfile.TemporaryDirectory(prefix="inbe-released-", dir=output) as directory:
            checked += reverse(tag, ledger, Path(directory))
    print(f"Package compatibility: {checked} package runs passed")


if __name__ == "__main__":
    sys.exit(main())
