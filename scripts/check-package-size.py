#!/usr/bin/env python3
"""Enforce shipped size budgets and one shared, architecture-independent package."""
import argparse
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def within(name, size, maximum):
    if size > maximum:
        raise ValueError(f"{name}: {size:,} bytes exceeds {maximum:,}-byte budget")


def check(path, budgets):
    if path.suffix not in (".apk", ".aab"):
        within("Linux binary", path.stat().st_size, budgets["linux_binary_bytes"])
        return f"Linux binary: {path.stat().st_size / 1e6:.2f} MB"
    bundle = path.suffix == ".aab"
    prefix = "base/" if bundle else ""
    with zipfile.ZipFile(path) as archive:
        files = archive.infolist()
        package_path = prefix + "assets/inbe.zib"
        packages = [entry for entry in files if entry.filename.endswith("/inbe.zib")]
        if len(packages) != 1 or packages[0].filename != package_path:
            raise ValueError("Expected exactly one shared assets/inbe.zib")
        package = packages[0]
        within("Portable app package", package.file_size, budgets["app_package_bytes"])
        libraries = [entry for entry in files
                     if entry.filename.startswith(prefix + "lib/")
                     and entry.filename.endswith("/libmain.so")]
        if not libraries:
            raise ValueError("Missing native application libraries")
        for library in libraries:
            within(library.filename, library.file_size, budgets["native_library_bytes"])
            # A portable package header may occur as a tiny reader constant;
            # embedding megabytes of images is caught by the library budget.
        if bundle:
            size = sum(entry.compress_size for entry in files
                       if entry.filename.startswith("base/"))
            within("Delivered bundle payload", size, budgets["bundle_payload_bytes"])
        else:
            size = path.stat().st_size
            key = "apk_universal_bytes" if len(libraries) > 1 else "apk_single_abi_bytes"
            within("APK", size, budgets[key])
        return (f"{path.name}: {size / 1e6:.2f} MB; {len(libraries)} ABI(s); "
                f"one shared package ({package.file_size / 1e6:.2f} MB unpacked)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", type=Path, nargs="*")
    parser.add_argument("--assets", action="store_true")
    args = parser.parse_args()
    if not args.artifacts and not args.assets:
        parser.error("supply an artifact or --assets")
    budgets = json.loads((ROOT / "packaging/size-budgets.json").read_text())
    try:
        if args.assets:
            animation = sum(path.stat().st_size for path in
                            (ROOT / "assets/practices/sunsalutation/characters").glob("*/*.png"))
            within("Animation PNGs", animation, budgets["animation_png_bytes"])
            print(f"PASS animation: {animation / 1e6:.2f} MB")
        for path in args.artifacts:
            print("PASS " + check(path, budgets))
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"FAIL package size: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
