#!/usr/bin/env python3
"""Install the latest published Linux desktop release without stopping the app."""

import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import urllib.request
import xml.etree.ElementTree as ET


APPCAST = "https://github.com/waozixyz/breeze/releases/latest/download/appcast.json"
RELEASES = "https://github.com/waozixyz/breeze/releases/download/"
APP_ID = "xyz.waozi.inbe"
FILES = (
    "bin/breeze",
    f"share/applications/{APP_ID}.desktop",
    f"share/icons/hicolor/512x512/apps/{APP_ID}.png",
    f"share/metainfo/{APP_ID}.metainfo.xml",
)


def version_tuple(version):
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("Release version must contain three numeric components")
    return tuple(map(int, version.split(".")))


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def atomic_copy(source, destination, mode=None):
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".breeze-update-", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as output, source.open("rb") as incoming:
            shutil.copyfileobj(incoming, output)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, mode if mode is not None else source.stat().st_mode & 0o777)
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def artifact_for(appcast):
    version = appcast["version"]
    version_tuple(version)
    architecture = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine())
    if architecture is None:
        raise ValueError("Desktop updates support Linux x86_64 and aarch64")
    artifact = appcast["channels"]["deb-" + architecture]
    expected_url = f"{RELEASES}v{version}/inbe_{version}_{architecture}.deb"
    if artifact["url"] != expected_url:
        raise ValueError("Desktop artifact is outside the expected Breeze release")
    if not re.fullmatch(r"[a-fA-F0-9]{64}", artifact["sha256"]):
        raise ValueError("Desktop artifact has no valid SHA-256 digest")
    if type(artifact["size"]) is not int or not 0 < artifact["size"] <= 256 * 1024 * 1024:
        raise ValueError("Desktop artifact size is invalid")
    return artifact


def open_url(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Inner-Breeze-Desktop-Updater/1"})
    return urllib.request.urlopen(request, timeout=60)


def download(artifact, destination):
    checksum = hashlib.sha256()
    size = 0
    with open_url(artifact["url"]) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > artifact["size"]:
                raise ValueError("Desktop download exceeds its declared size")
            checksum.update(chunk)
            output.write(chunk)
    if size != artifact["size"] or checksum.hexdigest() != artifact["sha256"].lower():
        raise ValueError("Desktop download failed size or SHA-256 verification")


def installed_version(prefix):
    metadata = prefix / FILES[-1]
    if not metadata.exists():
        return (0, 0, 0)
    releases = ET.parse(metadata).findall("./releases/release")
    return max((version_tuple(entry.attrib["version"]) for entry in releases), default=(0, 0, 0))


def install_package(package, prefix, backup_dir, version):
    with tempfile.TemporaryDirectory(prefix="breeze-desktop-package-") as temporary:
        extracted = Path(temporary)
        subprocess.run(["dpkg-deb", "--extract", str(package), str(extracted)], check=True)
        sources = [extracted / "usr" / name for name in FILES]
        if not all(source.is_file() and not source.is_symlink() for source in sources):
            raise ValueError("Desktop package is missing required files")
        if installed_version(extracted / "usr") != version_tuple(version):
            raise ValueError("Desktop package metadata does not match its release")
        with sources[0].open("rb") as binary:
            if binary.read(4) != b"\x7fELF":
                raise ValueError("Desktop package has no native executable")
        dependencies = subprocess.run(["ldd", str(sources[0])], text=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if dependencies.returncode != 0 or "not found" in dependencies.stdout:
            raise ValueError("Desktop package needs unavailable libraries: " + dependencies.stdout)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        backup = backup_dir / stamp
        existing = [name for name in FILES if (prefix / name).exists()]
        for name in existing:
            destination = backup / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(prefix / name, destination)
        try:
            # Publish metadata first and replace the executable last. Running
            # processes retain their original inode and are never interrupted.
            for name in reversed(FILES):
                atomic_copy(extracted / "usr" / name, prefix / name)
        except Exception:
            for name in FILES:
                if name in existing:
                    atomic_copy(backup / name, prefix / name)
                else:
                    (prefix / name).unlink(missing_ok=True)
            raise
    return backup


def update(prefix, backup_dir):
    state = prefix / "state/inner-breeze-desktop"
    state.mkdir(parents=True, exist_ok=True)
    with (state / "update.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with open_url(APPCAST) as response:
            document = response.read(65537)
        if len(document) > 65536:
            raise ValueError("Release appcast is too large")
        appcast = json.loads(document)
        artifact = artifact_for(appcast)
        version = appcast["version"]
        if installed_version(prefix) > version_tuple(version):
            print("Installed desktop version is newer than the published release; keeping it.")
            return
        receipt_path = state / "installed.json"
        previous = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
        executable = prefix / FILES[0]
        if (previous.get("version") == version and executable.exists()
                and previous.get("binary_sha256") == digest(executable)
                and all((prefix / name).exists() for name in FILES)):
            print(f"Inner Breeze {version} is already installed.")
            return
        with tempfile.TemporaryDirectory(prefix="breeze-desktop-download-") as temporary:
            package = Path(temporary) / "inbe.deb"
            download(artifact, package)
            backup = install_package(package, prefix, backup_dir, version)
        receipt = {
            "version": version,
            "installed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "artifact": artifact,
            "binary_sha256": digest(executable),
            "backup": str(backup),
            "release_url": appcast["notes_url"],
        }
        temporary_receipt = state / "installed.json.new"
        temporary_receipt.write_text(json.dumps(receipt, indent=2) + "\n")
        os.replace(temporary_receipt, receipt_path)
        if shutil.which("update-desktop-database"):
            subprocess.run(["update-desktop-database", str(prefix / "share/applications")], check=True)
        print(f"Installed Inner Breeze {version}. Running app processes were preserved.")


def unit_quote(value):
    return '"' + str(value).replace("%", "%%").replace("\\", "\\\\").replace('"', '\\"') + '"'


def enable_automatic(prefix, backup_dir):
    updater = prefix / "libexec/inner-breeze-update.py"
    atomic_copy(Path(__file__).resolve(), updater, 0o755)
    units = Path.home() / ".config/systemd/user"
    units.mkdir(parents=True, exist_ok=True)
    command = " ".join(map(unit_quote, ["/usr/bin/python3", updater, "--prefix", prefix,
                                        "--backup-dir", backup_dir]))
    (units / "inner-breeze-update.service").write_text(
        "[Unit]\nDescription=Keep the Inner Breeze desktop release current\n\n"
        "[Service]\nType=oneshot\nExecStart=" + command + "\n"
        "Nice=10\nCPUQuota=25%\nMemoryMax=256M\nTasksMax=16\nTimeoutStartSec=300\n")
    (units / "inner-breeze-update.timer").write_text(
        "[Unit]\nDescription=Check for Inner Breeze desktop releases every 30 minutes\n\n"
        "[Timer]\nOnStartupSec=2min\nOnUnitActiveSec=30min\nPersistent=true\n\n"
        "[Install]\nWantedBy=timers.target\n")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", "inner-breeze-update.timer"], check=True)
    print("Automatic desktop updates enabled: every 30 minutes and after login.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, default=Path.home() / ".local")
    parser.add_argument("--backup-dir", type=Path,
                        default=Path(__file__).resolve().parent.parent / "backup/desktop-updates")
    parser.add_argument("--enable-automatic", action="store_true")
    args = parser.parse_args()
    if platform.system() != "Linux":
        parser.error("This installer requires Linux")
    prefix = args.prefix.resolve()
    backup_dir = args.backup_dir.resolve()
    update(prefix, backup_dir)
    if args.enable_automatic:
        enable_automatic(prefix, backup_dir)


if __name__ == "__main__":
    main()
