#!/usr/bin/env python3
"""Check shared artifact structure without imposing a file-size ceiling."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/package-size-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
SPEC = importlib.util.spec_from_file_location("package_size", ROOT / "scripts/check-package-size.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PackageSizeTest(unittest.TestCase):
    def check_archive(self, entries, suffix=".apk"):
        with tempfile.TemporaryDirectory(dir=OUTPUT) as work:
            path = Path(work) / ("test" + suffix)
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, data in entries.items():
                    archive.writestr(name, data)
            return MODULE.check(path)

    def test_one_shared_package_for_four_abis(self):
        entries = {"assets/inbe.zx": b"portable program and artwork",
                   "assets/apps.zx": b"reviewed Apps controller"}
        for abi in ("arm64-v8a", "armeabi-v7a", "x86", "x86_64"):
            entries[f"lib/{abi}/libmain.so"] = b"native platform host"
        self.assertIn("4 ABI(s); one shared package", self.check_archive(entries))

    def test_missing_shared_package_fails(self):
        with self.assertRaisesRegex(ValueError, "exactly one shared"):
            self.check_archive({"lib/arm64-v8a/libmain.so": b"embedded artwork"})

    def test_duplicate_package_fails(self):
        with self.assertRaisesRegex(ValueError, "exactly one shared"):
            self.check_archive({"assets/inbe.zx": b"package", "assets/copy/inbe.zx": b"package"})

    def test_native_library_has_no_individual_size_limit(self):
        for suffix in (".apk", ".aab"):
            with self.subTest(suffix=suffix):
                prefix = "base/" if suffix == ".aab" else ""
                self.assertIn("one shared package", self.check_archive({
                    prefix + "assets/inbe.zx": b"package",
                    prefix + "assets/apps.zx": b"controller",
                    prefix + "lib/x86/libmain.so": b"x" * 5_600_000,
                }, suffix=suffix))

    def test_missing_native_library_fails(self):
        with self.assertRaisesRegex(ValueError, "Missing native application libraries"):
            self.check_archive({"assets/inbe.zx": b"package",
                                "assets/apps.zx": b"controller"})

    def test_bundle_checks_delivered_payload_without_crash_symbols(self):
        self.assertIn("one shared package", self.check_archive({
            "base/assets/inbe.zx": b"package", "base/assets/apps.zx": b"controller",
            "base/lib/arm64-v8a/libmain.so": b"host",
            "BUNDLE-METADATA/com.android.tools.build.debugsymbols/symbols": b"symbol" * 10000,
        }, suffix=".aab"))

    def test_artifacts_above_former_size_limits_are_accepted(self):
        # Stream a package larger than every former artifact ceiling without
        # allocating it all in memory. Structural checks still run below.
        chunk = bytes(1024 * 1024)
        with tempfile.TemporaryDirectory(dir=OUTPUT) as work:
            binary = Path(work) / "breeze-linux-x86_64"
            with binary.open("wb") as stream:
                stream.truncate(70 * len(chunk))
            self.assertIn("Linux binary:", MODULE.check(binary))
            for suffix in (".apk", ".aab"):
                prefix = "base/" if suffix == ".aab" else ""
                path = Path(work) / ("large" + suffix)
                with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as archive:
                    with archive.open(prefix + "assets/inbe.zx", "w") as package:
                        for _ in range(70):
                            package.write(chunk)
                    archive.writestr(prefix + "assets/apps.zx", b"controller")
                    archive.writestr(prefix + "lib/arm64-v8a/libmain.so", b"host")
                self.assertIn("one shared package", MODULE.check(path))

    def test_missing_shared_controller_fails(self):
        with self.assertRaisesRegex(ValueError, "exactly one shared assets/apps.zx"):
            self.check_archive({"assets/inbe.zx": b"package",
                                "lib/arm64-v8a/libmain.so": b"host"})

    def test_duplicate_controller_fails(self):
        with self.assertRaisesRegex(ValueError, "exactly one shared assets/apps.zx"):
            self.check_archive({"assets/inbe.zx": b"package",
                                "assets/apps.zx": b"controller",
                                "assets/copy/apps.zx": b"controller",
                                "lib/arm64-v8a/libmain.so": b"host"})


if __name__ == "__main__":
    unittest.main()
