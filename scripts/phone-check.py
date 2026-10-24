#!/usr/bin/env python3
"""Check an exact Inner Breeze APK on the development Moto before release.

The APK is installed over the existing app, launched, and the Wim Hof session
is started through the app's own start-practice intent. SurfaceFlinger's frame
timestamps for the app's window are collected for the whole session, then the
app is sent to the background and resumed. With --record a passing result is
written to releases/phone-checks/VERSION.json with the app's content identity
(app_tree); the release workflow publishes a new version only when its app
content is exactly the checked one.
"""
import argparse
from datetime import datetime, timezone
import fnmatch
import hashlib
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = "xyz.waozi.inbe.MainActivity"
START_PRACTICE = "xyz.waozi.inbe.action.START_PRACTICE"
WIM_HOF = 0
# Paths whose content makes the shipped app: sources, build rules, the
# version files ./update_version.sh writes, and the design files that the
# practice and Lumi packages are built from. Changing any of them after the
# phone check needs a new check.
APP_PATHS = ("src", "droid", "apps", "assets", "locales", "themes", "fonts", "windows",
             "packaging", "unpackaged_assets", "web-assets", "site-icons", "mk", "Makefile",
             "GNUmakefile", "ziran.toml", "ziran.lock", "scripts",
             "design/tai-chi/text", "design/tai-chi/narration.json",
             "design/tai-chi/narration-lines.json", "design/tai-chi/narration-male.json",
             "design/tai-chi/narration-receipt.json", "design/tai-chi/narration-male-receipt.json",
             "design/sun-salutation/narration", "design/lumi-guide")
# Tooling under those paths that checks, tests, records or publishes the app
# without becoming part of it. A new script counts as app until listed here.
TOOLING = ("scripts/phone-check.py", "scripts/check-phone-check.py", "scripts/release.py",
           "scripts/release-ready.sh", "scripts/check-*", "scripts/*test*", "scripts/upload-*",
           "scripts/publish-*", "scripts/render-*", "scripts/screenshot-*",
           "scripts/generate-screenshots.sh", "scripts/moto-screenshot.sh", "scripts/emulator.sh",
           "scripts/create-avd.sh", "scripts/android-audio-e2e.sh",
           "scripts/audio-envelope-match.py", "scripts/make_appcast.py",
           "scripts/list-expected-release-assets.sh", "scripts/install-git-hooks.sh",
           "scripts/pre-push-checks.py",
           "packaging/size-budgets.json", "mk/tests-*.mk")
RECEIPTS = "releases/phone-checks"
# The breathing circle animates for the whole measured window, so the app
# must keep the display's refresh rate with only occasional late frames.
MINIMUM_REFRESH_SHARE = 0.94
MAXIMUM_LATE_PERCENT = 3.0
MAXIMUM_FRAME_MS = 250.0
# Leaving during a practice may pass through the floating window; the
# practice must come back with the layout it had, not shifted or cropped.
MAXIMUM_RESUME_LAYOUT_SHIFT = 2.0
PENDING = 9223372036854775807


def run(argv, *, timeout=60, **kwargs):
    return subprocess.run(list(map(str, argv)), check=True, capture_output=True,
                          timeout=timeout, **kwargs).stdout


class Phone:
    def __init__(self, host, serial):
        if not re.fullmatch(r"[A-Za-z0-9_.@-]+", host) or host.startswith("-"):
            raise ValueError("invalid ADB host")
        valid_serial = re.fullmatch(r"[A-Za-z0-9]+", serial) is not None
        if not valid_serial:
            address, separator, port = serial.rpartition(":")
            try:
                ipaddress.IPv4Address(address)
                valid_serial = bool(separator and port.isdecimal() and 1 <= int(port) <= 65535)
            except ipaddress.AddressValueError:
                valid_serial = False
        if not valid_serial:
            raise ValueError("invalid phone serial or wireless ADB address")
        self.host = host
        self.serial = serial

    def remote(self, *argv, timeout=60, **kwargs):
        if self.host == "local":
            return run(argv, timeout=timeout, **kwargs)
        return run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", self.host,
                    shlex.join(list(map(str, argv)))], timeout=timeout, **kwargs)

    def adb(self, *argv, **kwargs):
        return self.remote("adb", "-s", self.serial, *argv, **kwargs)

    def shell(self, *argv, **kwargs):
        return self.adb("shell", *argv, **kwargs).decode(errors="replace")

    def focused(self, package):
        # Launcher aliases name the window too, so any activity of the app counts.
        windows = self.shell("dumpsys", "window", "windows")
        line = next((line for line in windows.splitlines() if "mCurrentFocus=" in line), "")
        if f" {package}/" not in line:
            raise ValueError("Inner Breeze does not own the foreground window: " + line.strip())

    def screenshot(self, package, path):
        from PIL import Image, ImageStat

        self.focused(package)
        data = self.adb("exec-out", "screencap", "-p")
        with Image.open(io.BytesIO(data)) as image:
            body = image.convert("RGB").crop((0, image.height // 10, image.width, image.height * 9 // 10))
            if max(ImageStat.Stat(body).stddev) < 2:
                raise ValueError(f"Inner Breeze rendered a blank screen ({path.name})")
        path.write_bytes(data)

    def start(self, package, *extra):
        output = self.shell("am", "start", "-W", "-n", f"{package}/{ACTIVITY}", *extra)
        if "Status: ok" not in output and "Warning: Activity not started" not in output:
            raise ValueError("Inner Breeze did not start: " + output.strip())

    def pid(self, package):
        try:
            return self.shell("pidof", package).strip()
        except subprocess.CalledProcessError as error:
            if error.returncode == 1 and not error.stdout and not error.stderr:
                return ""
            raise


def apk_identity(apk):
    tools = sorted((Path(os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME") or
                         Path.home() / "Android/Sdk") / "build-tools").glob("*/aapt2"))
    if not tools:
        raise ValueError("aapt2 not found; set ANDROID_SDK_ROOT")
    badging = run([tools[-1], "dump", "badging", apk]).decode()
    match = re.search(r"package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'", badging)
    if not match:
        raise ValueError("the APK has no package identity")
    return dict(package=match[1], version_code=int(match[2]), version_name=match[3])


def is_app_path(path):
    if any(fnmatch.fnmatchcase(path, pattern) for pattern in TOOLING):
        return False
    return any(path == source or path.startswith(source + "/") for source in APP_PATHS)


def git(root, *argv, env=None):
    return subprocess.run(["git", "--no-optional-locks", "-C", str(root), *argv], check=True,
                          capture_output=True, text=True, env=env).stdout


def working_tree(root):
    """Tree of the tracked files as they are on disk, in a throwaway index."""
    git_dir = Path(git(root, "rev-parse", "--absolute-git-dir").strip())
    with tempfile.TemporaryDirectory(prefix="inbe-tree-") as temporary:
        index = Path(temporary) / "index"
        if (git_dir / "index").is_file():
            shutil.copyfile(git_dir / "index", index)
        env = dict(os.environ, GIT_INDEX_FILE=str(index))
        if not (git_dir / "index").is_file():
            git(root, "read-tree", "HEAD", env=env)
        git(root, "add", "--update", "--", ".", env=env)
        return git(root, "write-tree", env=env).strip()


def tree_identity(root, revision, include):
    """SHA-256 over the mode, blob and path of every included file.

    revision None means the tracked files on disk, so a check of uncommitted
    version files is identical to the commit that later holds them.
    """
    tree = working_tree(root) if revision is None else revision
    lines = git(root, "ls-tree", "-r", "--full-tree", tree).splitlines()
    chosen = [line for line in lines if include(line.split("\t", 1)[1])]
    return hashlib.sha256(("\n".join(chosen) + "\n").encode()).hexdigest()


def app_tree(root=ROOT, revision=None):
    """Content identity of the shipped app; tests, docs and tooling do not count."""
    return tree_identity(root, revision, is_app_path)


def release_content(root=ROOT, revision=None):
    """Identity of everything CI tests, without the phone-check receipts."""
    return tree_identity(root, revision, lambda path: not path.startswith(RECEIPTS + "/"))


def status(root, *paths):
    """(code, path) for every changed or untracked file, without touching the index."""
    output = subprocess.run(["git", "--no-optional-locks", "-C", str(root), "status", "--porcelain=v1",
                             "-z", "--untracked-files=all", "--no-renames", "--", *paths],
                            check=True, capture_output=True, text=True).stdout
    return [(entry[:2], entry[3:]) for entry in output.split("\0") if entry]


def changed_app_files(root):
    """App files that differ from HEAD on disk, and untracked app files."""
    changed = []
    untracked = []
    for code, path in status(root):
        if not is_app_path(path):
            continue
        if code == "??":
            untracked.append(path)
        else:
            changed.append(path)
    return changed, untracked


def source_state(revision=None):
    commit = git(ROOT, "rev-parse", (revision or "HEAD") + "^{commit}").strip()
    if revision:
        text = git(ROOT, "show", commit + ":src/core/version.zi")
        versions = re.findall(r'^VersionString :: "([0-9]+\.[0-9]+\.[0-9]+)"$', text, re.M)
        if len(versions) != 1:
            raise ValueError("the fixed candidate has no valid application version")
        return commit, [], [], versions[0]
    changed, untracked = changed_app_files(ROOT)
    version = run([sys.executable, ROOT / "scripts/check-version.py", "--print-version"]).decode().strip()
    return commit, changed, untracked, version


def require_build_receipt(apk, path, revision):
    """Bind a fixed-source phone run to the APK exported by its isolated build."""
    if path is None:
        raise ValueError("a fixed candidate requires its isolated APK build receipt")
    receipt = json.loads(path.read_text())
    digest = receipt.get("apk", {}).get("sha256")
    if (receipt.get("status") != "passed" or
            receipt.get("app_tree") != app_tree(ROOT, revision) or
            digest != hashlib.sha256(apk.read_bytes()).hexdigest()):
        raise ValueError("the APK build receipt does not match this fixed app content and APK")


def layout_shift(before, after):
    """Mean pixel difference of the practice header, which does not animate."""
    from PIL import Image, ImageChops, ImageStat

    with Image.open(before) as first, Image.open(after) as second:
        if first.size != second.size:
            return 255.0
        width, height = first.size
        box = (0, height * 4 // 100, width, height * 12 // 100)
        difference = ImageChops.difference(first.convert("RGB").crop(box), second.convert("RGB").crop(box))
        return round(sum(ImageStat.Stat(difference).mean) / 3, 1)


def frame_timing(phone, package, seconds):
    """Collect every presented frame of the app's window for the session."""
    # Android 9 names layers "<id> package/activity#N"; tokens are not layers.
    layers = [line.strip() for line in phone.shell("dumpsys", "SurfaceFlinger", "--list").splitlines()
              if f" {package}/" in " " + line.strip() and "Token{" not in line]
    if not layers:
        raise ValueError("Inner Breeze has no window layer")
    presented = {}
    period = 0
    deadline = time.monotonic() + seconds
    for layer in layers:
        phone.shell("dumpsys", "SurfaceFlinger", "--latency-clear", shlex.quote(layer))
    while time.monotonic() < deadline:
        for layer in layers:
            lines = phone.shell("dumpsys", "SurfaceFlinger", "--latency", shlex.quote(layer)).split("\n")
            if lines and lines[0].strip().isdigit():
                period = int(lines[0])
            for line in lines[1:]:
                fields = line.split()
                if len(fields) == 3 and fields[1].isdigit():
                    actual = int(fields[1])
                    if 0 < actual < PENDING:
                        presented.setdefault(layer, set()).add(actual)
        time.sleep(0.5)
    if not presented or period <= 0:
        raise ValueError("SurfaceFlinger reported no frames for Inner Breeze")
    frames = sorted(max(presented.values(), key=len))
    if len(frames) < 2:
        raise ValueError("Inner Breeze presented fewer than two frames")
    gaps = [(right - left) / 1e6 for left, right in zip(frames, frames[1:])]
    period_ms = period / 1e6
    late = sum(1 for gap in gaps if gap > period_ms * 1.5)
    ordered = sorted(gaps)
    return dict(seconds=round((frames[-1] - frames[0]) / 1e9, 2), frames=len(frames),
                refresh_hz=round(1000 / period_ms, 1),
                fps=round((len(frames) - 1) / ((frames[-1] - frames[0]) / 1e9), 1),
                late_percent=round(100 * late / len(gaps), 2),
                p95_frame_ms=round(ordered[int(len(ordered) * 0.95) - 1], 1),
                worst_frame_ms=round(ordered[-1], 1))


def smooth(timing):
    return (timing["refresh_hz"] >= 30 and timing["fps"] >= timing["refresh_hz"] * MINIMUM_REFRESH_SHARE and
            timing["late_percent"] <= MAXIMUM_LATE_PERCENT and
            timing["worst_frame_ms"] <= MAXIMUM_FRAME_MS)


def resumed_in_place(timing):
    return timing.get("resume_layout_shift", 255.0) <= MAXIMUM_RESUME_LAYOUT_SHIFT


def check(phone, apk, seconds, evidence):
    identity = apk_identity(apk)
    package = identity["package"]
    if phone.adb("get-state").decode().strip() != "device":
        raise ValueError("the phone is not connected and authorized")
    if phone.pid(package):
        raise ValueError("the development app is already running; leave it open until the owner closes it")
    transfer = ""
    try:
        if phone.host != "local":
            transfer = phone.remote("mktemp", "-d", "/tmp/inbe-phone-check-XXXXXXXX").decode().strip()
            if not re.fullmatch(r"/tmp/inbe-phone-check-[A-Za-z0-9]+", transfer):
                raise ValueError("unsafe transfer folder on the ADB host")
            remote = transfer + "/inbe.apk"
            phone.remote("sh", "-c", "umask 077; cat > " + shlex.quote(remote), input=apk.read_bytes(),
                         timeout=300)
        else:
            remote = apk
        if "Success" not in phone.adb("install", "-r", remote, timeout=300).decode():
            raise ValueError("the phone rejected the APK; its existing app and data were kept")
    finally:
        if transfer:
            phone.remote("rm", "-rf", transfer)
    phone.shell("input", "keyevent", "KEYCODE_WAKEUP")
    phone.shell("wm", "dismiss-keyguard")
    phone.shell("am", "force-stop", package)
    phone.start(package)
    time.sleep(4)
    pid = phone.pid(package)
    if not pid:
        raise ValueError("Inner Breeze did not stay running after launch")
    phone.screenshot(package, evidence / "launch.png")
    phone.start(package, "-a", START_PRACTICE, "--ei", "practice_id", str(WIM_HOF))
    time.sleep(3)
    phone.screenshot(package, evidence / "practice-start.png")
    timing = frame_timing(phone, package, seconds)
    phone.screenshot(package, evidence / "practice-end.png")
    if phone.pid(package) != pid:
        raise ValueError("Inner Breeze restarted during the practice")
    phone.shell("input", "keyevent", "KEYCODE_HOME")
    time.sleep(2)
    phone.start(package)
    time.sleep(2)
    if phone.pid(package) != pid:
        raise ValueError("Inner Breeze restarted when it returned from the background")
    phone.screenshot(package, evidence / "resume.png")
    timing["resume_layout_shift"] = layout_shift(evidence / "practice-end.png", evidence / "resume.png")
    model = phone.shell("getprop", "ro.product.model").strip()
    android = phone.shell("getprop", "ro.build.version.release").strip()
    return identity, timing, dict(model=model, android=android)


def resolve_host(host, serial):
    """'auto' is this machine when the phone is attached here, else the ThinkPad."""
    if host != "auto":
        return host
    attached = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
    return "local" if re.search(rf"^{re.escape(serial)}\s+device$", attached, re.M) else "wao@thinkpad.local"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--host", default=os.environ.get("INBE_PHONE_HOST", "auto"),
                        help="SSH host that runs adb, 'local', or 'auto' (this machine, then the ThinkPad)")
    parser.add_argument("--serial", default=os.environ.get("INBE_PHONE_SERIAL", "ZE2223BQZT"))
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--record", action="store_true",
                        help="write a passing result to releases/phone-checks/VERSION.json for the release gate")
    parser.add_argument("--revision", help="check the APK of this fixed committed candidate while master changes")
    parser.add_argument("--build-receipt", type=Path,
                        help="isolated APK build provenance, required with --revision")
    args = parser.parse_args()
    for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS"):
        os.environ.pop(name, None)
    apk = args.apk.resolve(strict=True)
    commit, changed, untracked, version = source_state(args.revision)
    if args.revision:
        require_build_receipt(apk, args.build_receipt, commit)
    if args.record and (untracked or args.seconds < 60):
        parser.error("a recorded check needs a full minute and no untracked app files:\n" + "\n".join(untracked))
    checked_app = app_tree(ROOT, commit if args.revision else None)
    if apk_identity(apk)["version_name"] != version:
        raise ValueError("the APK version differs from the candidate; no installation attempted")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence = ROOT / "backup/phone-checks" / f"{version}-{stamp}"
    evidence.mkdir(parents=True, exist_ok=True)
    phone = Phone(resolve_host(args.host, args.serial), args.serial)
    identity, timing, device = check(phone, apk, args.seconds, evidence)
    if identity["version_name"] != version:
        raise SystemExit(f"the APK is {identity['version_name']}, but the source is {version}")
    passed = smooth(timing) and resumed_in_place(timing)
    receipt = dict(schema=2, version=version, app_tree=checked_app, source_commit=commit,
                   uncommitted=sorted(changed),
                   apk=dict(sha256=hashlib.sha256(apk.read_bytes()).hexdigest(), **identity),
                   device=device, practice=dict(name="Wim Hof", **timing),
                   limits=dict(minimum_refresh_share=MINIMUM_REFRESH_SHARE, maximum_late_percent=MAXIMUM_LATE_PERCENT,
                               maximum_frame_ms=MAXIMUM_FRAME_MS,
                               maximum_resume_layout_shift=MAXIMUM_RESUME_LAYOUT_SHIFT),
                   checks=["installed without clearing existing data", "launch", "Wim Hof frame timing",
                           "background and resume"],
                   passed=passed, checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    (evidence / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if args.record and not args.revision and app_tree(ROOT) != checked_app:
        raise SystemExit("app files changed during the check; nothing was recorded")
    if args.record and passed:
        target = ROOT / RECEIPTS / f"{version}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"Recorded {target.relative_to(ROOT)} for app content {checked_app[:12]}; "
              "make release commits it.")
    if not resumed_in_place(timing):
        print(f"FAILED: the practice layout changed after resuming (difference {timing['resume_layout_shift']}); "
              f"compare practice-end.png and resume.png in {evidence.relative_to(ROOT)}")
    print(f"{device['model']} (Android {device['android']}): {timing['fps']} fps over {timing['seconds']} s, "
          f"{timing['late_percent']}% late frames, worst {timing['worst_frame_ms']} ms -> "
          f"{'smooth' if smooth(timing) else 'NOT smooth'}; evidence in {evidence.relative_to(ROOT)}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
