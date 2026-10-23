#!/usr/bin/env python3
"""Install the pinned SDK components, retrying downloads in fresh staging areas."""
from pathlib import Path
import argparse
import os
import re
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def component_path(root, package):
    if not re.fullmatch(r"(?:platforms;android-[0-9]+|(?:build-tools|ndk|cmake);[0-9]+\.[0-9]+\.[0-9]+)", package):
        raise ValueError("invalid pinned SDK component: " + package)
    return root.joinpath(*package.split(";"))


def valid(root, package):
    directory = component_path(root, package)
    try:
        document = ET.parse(directory / "package.xml")
        if not any(element.tag.rsplit("}", 1)[-1] == "localPackage" and
                   element.get("path") == package for element in document.iter()):
            return False
        kind, version = package.split(";")
        if kind == "platforms":
            with zipfile.ZipFile(directory / "android.jar") as archive:
                return archive.testzip() is None
        properties = (directory / "source.properties").read_text()
        if not re.search(r"^Pkg\.Revision\s*=\s*" + re.escape(version) + r"\s*$", properties, re.M):
            return False
        if kind == "cmake":
            command = [directory / "bin/cmake", "--version"]
        elif kind == "build-tools":
            command = [directory / "aapt2", "version"]
        else:
            command = [next(directory.glob("toolchains/llvm/prebuilt/*/bin/clang")), "--version"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return False
        if kind == "cmake":
            expected = "cmake version " + re.escape(version) + r"(?:-[0-9A-Za-z.]+)?"
            return re.fullmatch(expected, result.stdout.splitlines()[0]) is not None
        return True
    except (OSError, UnicodeError, ET.ParseError, zipfile.BadZipFile, StopIteration, IndexError,
            subprocess.TimeoutExpired):
        return False


def merge_licenses(source, destination):
    """Keep runner-owned permissions and accepted licence hashes intact."""
    if not source.is_dir():
        return
    destination.mkdir(exist_ok=True)
    for license_file in source.iterdir():
        if not license_file.is_file():
            continue
        target = destination / license_file.name
        accepted = target.read_text().splitlines() if target.exists() else []
        additions = [line for line in license_file.read_text().splitlines()
                     if line.strip() and line not in accepted]
        if not additions:
            continue
        # copytree/copy2 also chmod and set timestamps. Hosted SDK licences
        # can be writable but owned by root, so metadata copying fails.
        with target.open("a") as output:
            output.write("\n" + "\n".join(additions) + "\n")


def install(root, packages, manager, sleep=time.sleep):
    root = Path(root).resolve()
    manager = Path(manager).resolve(strict=True)
    root.mkdir(parents=True, exist_ok=True)
    for package in packages:
        destination = component_path(root, package)
        if valid(root, package):
            print("Android SDK: verified cached " + package, flush=True)
            continue
        for attempt in range(1, 4):
            print(f"Android SDK: install {package}, attempt {attempt}/3", flush=True)
            # sdkmanager keeps partial archives beneath its SDK root. A new
            # stage guarantees that a corrupt ZIP cannot survive the retry.
            with tempfile.TemporaryDirectory(prefix=".inbe-sdk-", dir=root) as temporary:
                stage = Path(temporary)
                if (root / "licenses").is_dir():
                    shutil.copytree(root / "licenses", stage / "licenses")
                environment = dict(os.environ, ANDROID_HOME=str(stage), ANDROID_SDK_ROOT=str(stage))
                try:
                    result = subprocess.run([manager, "--sdk_root=" + str(stage), package],
                                            input=b"y\n" * 128, env=environment, timeout=600)
                except subprocess.TimeoutExpired:
                    result = None
                if result is not None and result.returncode == 0 and valid(stage, package):
                    source = component_path(stage, package)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if destination.exists():
                        destination.rename(stage / "incomplete-component")
                    source.rename(destination)
                    merge_licenses(stage / "licenses", root / "licenses")
                    if not valid(root, package):
                        raise RuntimeError("SDK component failed validation after installation: " + package)
                    break
                print("Android SDK: rejected incomplete or invalid " + package, flush=True)
            if attempt == 3:
                raise RuntimeError("Android SDK download failed after three fresh attempts: " + package)
            sleep(attempt * 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-root", type=Path,
                        default=os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME"))
    parser.add_argument("--sdkmanager", type=Path)
    parser.add_argument("--packages", type=Path, default=ROOT / ".github/android-sdk-packages.txt")
    args = parser.parse_args()
    if args.sdk_root is None:
        parser.error("ANDROID_SDK_ROOT or ANDROID_HOME must name the job's SDK")
    manager = args.sdkmanager or args.sdk_root / "cmdline-tools/latest/bin/sdkmanager"
    if args.sdkmanager is None and not manager.is_file():
        manager = Path(shutil.which("sdkmanager") or manager)
    packages = [line.strip() for line in args.packages.read_text().splitlines()
                if line.strip() and not line.lstrip().startswith("#")]
    install(args.sdk_root, packages, manager)


if __name__ == "__main__":
    main()
