#!/usr/bin/env python3
"""Reject Click binaries that require a newer runtime than their framework."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile


def verify(package):
    with tempfile.TemporaryDirectory(prefix="click-abi-") as temporary:
        root = Path(temporary)
        subprocess.run(["dpkg-deb", "-x", str(package), str(root)], check=True)
        subprocess.run(["dpkg-deb", "-e", str(package), str(root / "DEBIAN")], check=True)
        manifest = json.loads((root / "DEBIAN/manifest").read_text())
        if manifest["framework"] != "ubuntu-sdk-20.04" or manifest["architecture"] != "arm64":
            raise ValueError("expected the ARM64 ubuntu-sdk-20.04 package")
        policy_file = manifest["hooks"]["inbe"]["apparmor"]
        policy = json.loads((root / policy_file).read_text())
        if not {"audio", "networking"}.issubset(policy.get("policy_groups", [])):
            raise ValueError("Ubuntu Touch audio and account sync require audio/networking policies")
        for name in ("libEGL.so.1", "libGLESv2.so.2", "libGLdispatch.so.0"):
            if (root / "usr/lib" / name).exists():
                raise ValueError(f"{name}: use the framework's device graphics driver")
        checked = 0
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            with path.open("rb") as stream:
                if stream.read(4) != b"\x7fELF":
                    continue
            relative = path.relative_to(root)
            header = subprocess.check_output(["readelf", "-h", str(path)], text=True)
            if not re.search(r"Machine:\s+AArch64\b", header):
                raise ValueError(f"{relative}: expected an AArch64 ELF")
            versions = subprocess.check_output(["readelf", "--version-info", str(path)], text=True)
            required = [tuple(map(int, match.split(".")))
                        for match in re.findall(r"\bGLIBC_(\d+\.\d+(?:\.\d+)?)\b", versions)]
            newest = max(required, default=(0, 0))
            if newest > (2, 31):
                raise ValueError(f"{relative}: GLIBC_{'.'.join(map(str, newest))} exceeds Focal's 2.31")
            print(f"{relative}: ARM64, newest GLIBC_{'.'.join(map(str, newest))}")
            checked += 1
        if not checked:
            raise ValueError("package contains no ELF executables or libraries")
        print(f"Click ABI: {checked} ELF files match the Focal ARM64 framework")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    verify(parser.parse_args().package.resolve())
