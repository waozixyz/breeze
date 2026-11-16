#!/usr/bin/env python3
"""Report artifact sizes and verify one shared, architecture-independent package."""
import argparse
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def check(path):
    if path.suffix not in (".apk", ".aab"):
        return f"Linux binary: {path.stat().st_size / 1e6:.2f} MB"
    bundle = path.suffix == ".aab"
    prefix = "base/" if bundle else ""
    with zipfile.ZipFile(path) as archive:
        files = archive.infolist()
        package_path = prefix + "assets/inbe.zx"
        packages = [entry for entry in files if entry.filename.endswith("/inbe.zx")]
        if len(packages) != 1 or packages[0].filename != package_path:
            raise ValueError("Expected exactly one shared assets/inbe.zx")
        package = packages[0]
        controllers = [entry for entry in files if entry.filename.endswith("/apps.zx")]
        if len(controllers) != 1 or controllers[0].filename != prefix + "assets/apps.zx":
            raise ValueError("Expected exactly one shared assets/apps.zx controller")
        libraries = [entry for entry in files
                     if entry.filename.startswith(prefix + "lib/")
                     and entry.filename.endswith("/libmain.so")]
        if not libraries:
            raise ValueError("Missing native application libraries")
        if bundle:
            size = sum(entry.compress_size for entry in files
                       if entry.filename.startswith("base/"))
        else:
            size = path.stat().st_size
        return (f"{path.name}: {size / 1e6:.2f} MB; {len(libraries)} ABI(s); "
                f"one shared package ({package.file_size / 1e6:.2f} MB unpacked)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", type=Path, nargs="+")
    args = parser.parse_args()
    try:
        for path in args.artifacts:
            print("PASS " + check(path))
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"FAIL package artifact: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
