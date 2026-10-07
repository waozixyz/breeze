#!/usr/bin/env python3
"""Reject asset duplication and native-library growth in real ZIP inventories."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package_size", ROOT / "scripts/check-package-size.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PackageSizeTest(unittest.TestCase):
    def check_archive(self, entries, suffix=".apk", **limits):
        budgets = dict.fromkeys(("app_package_bytes", "native_library_bytes",
                                "apk_single_abi_bytes", "apk_universal_bytes",
                                "bundle_payload_bytes"), 10000)
        budgets.update(limits)
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / ("test" + suffix)
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, data in entries.items():
                    archive.writestr(name, data)
            return MODULE.check(path, budgets)

    def test_one_shared_package_for_four_abis(self):
        entries = {"assets/inbe.zib": b"portable program and artwork"}
        for abi in ("arm64-v8a", "armeabi-v7a", "x86", "x86_64"):
            entries[f"lib/{abi}/libmain.so"] = b"native platform host"
        self.assertIn("4 ABI(s); one shared package", self.check_archive(entries))

    def test_missing_shared_package_fails(self):
        with self.assertRaisesRegex(ValueError, "exactly one shared"):
            self.check_archive({"lib/arm64-v8a/libmain.so": b"embedded artwork"})

    def test_duplicate_package_fails(self):
        with self.assertRaisesRegex(ValueError, "exactly one shared"):
            self.check_archive({"assets/inbe.zib": b"package", "assets/copy/inbe.zib": b"package"})

    def test_native_asset_bloat_fails(self):
        with self.assertRaisesRegex(ValueError, "libmain.so"):
            self.check_archive({"assets/inbe.zib": b"package",
                                "lib/arm64-v8a/libmain.so": b"image" * 100},
                               native_library_bytes=100)

    def test_bundle_checks_delivered_payload_without_crash_symbols(self):
        self.assertIn("one shared package", self.check_archive({
            "base/assets/inbe.zib": b"package", "base/lib/arm64-v8a/libmain.so": b"host",
            "BUNDLE-METADATA/com.android.tools.build.debugsymbols/symbols": b"symbol" * 10000,
        }, suffix=".aab", bundle_payload_bytes=100))

    def test_total_apk_budget_fails(self):
        with self.assertRaisesRegex(ValueError, "APK"):
            self.check_archive({"assets/inbe.zib": b"package",
                                "lib/arm64-v8a/libmain.so": b"host"}, apk_single_abi_bytes=10)


if __name__ == "__main__":
    unittest.main()
