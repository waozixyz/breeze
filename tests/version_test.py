#!/usr/bin/env python3
"""Exercise the release guard and updater in disposable checkouts."""

from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class VersionTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="inbe-version-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        paths = (
            "CHANGELOG.md", "Makefile", "mkfile", "update_version.sh",
            "src/core/version.h", "src/core/version.zi",
            "src/storage/sync_result.zi",
            "droid/app/build.gradle", "windows/inbe.rc",
            "packaging/click/manifest.json", "packaging/click/control",
            "packaging/click/inbe.metainfo.xml",
            "packaging/linux/appimage/inbe.appdata.xml",
            "packaging/snap/snap/gui/inbe.metainfo.xml",
            "packaging/snap/snap/snapcraft.yaml",
            "packaging/firefox-addons/manifest.json",
            "scripts/check-version.py", "scripts/list-expected-release-assets.sh",
            "scripts/check-site-release-assets.sh", "scripts/publish-openstore.sh",
            ".github/workflows/release.yml", "site/build.sh",
        )
        for name in paths:
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / name, destination)
        shutil.copytree(REPO / "fastlane", self.root / "fastlane")
        self.version = re.search(r'^#define APP_VERSION_STRING "([^"]+)"',
                                 self.read("src/core/version.h"), re.MULTILINE)[1]

    def read(self, name):
        return (self.root / name).read_text()

    def write(self, name, content):
        (self.root / name).write_text(content)

    def check(self, *arguments, success=True):
        result = subprocess.run(
            [sys.executable, str(self.root / "scripts/check-version.py"), *arguments],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def snapshot(self):
        return {str(path.relative_to(self.root)): path.read_bytes()
                for path in self.root.rglob("*") if path.is_file()}

    def test_valid_metadata_is_read_only(self):
        before = self.snapshot()
        self.assertEqual(self.check("--print-version").stdout, self.version + "\n")
        self.assertEqual(before, self.snapshot())

    def test_build_gate_rejects_mismatch_after_success(self):
        (self.root / "vendor").mkdir()
        (self.root / "build/packages").mkdir(parents=True)
        # The package links below are already in place; the manifest and a
        # newer packages.mk keep Make from fetching them again.
        for name in ("ziran.toml", "ziran.lock", "scripts/packages.sh",
                "mk/sync.mk", "mk/package-freebsd.mk"):
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / name, self.root / name)
        (self.root / "build/packages.mk").write_text("PACKAGES_READY := 1\n")
        (self.root / "build/packages/kryon").symlink_to(REPO / "build/packages/kryon", target_is_directory=True)

        def build():
            return subprocess.run(["make", "version-check"], cwd=self.root,
                                  capture_output=True, text=True, check=False)

        valid = build()
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
        name = "droid/app/build.gradle"
        self.write(name, self.read(name).replace(self.version, "9.8.7"))
        invalid = build()
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("expected", invalid.stdout + invalid.stderr)

    def test_each_package_mismatch_is_rejected(self):
        for name in ("droid/app/build.gradle", "packaging/click/manifest.json",
                     "packaging/click/control", "packaging/firefox-addons/manifest.json",
                     "packaging/click/inbe.metainfo.xml",
                     "packaging/linux/appimage/inbe.appdata.xml",
                     "packaging/snap/snap/gui/inbe.metainfo.xml",
                     "packaging/snap/snap/snapcraft.yaml", "windows/inbe.rc"):
            with self.subTest(path=name):
                original = self.read(name)
                self.assertIn(self.version, original)
                self.write(name, original.replace(self.version, "9.8.7"))
                self.check(success=False)
                self.write(name, original)

    def test_header_missing_duplicate_malformed_and_inconsistent(self):
        original = self.read("src/core/version.h")
        line = f'#define APP_VERSION_STRING "{self.version}"'
        for modified in (original.replace(line, ""), original + "\n" + line + "\n",
                         original + "\n#define APP_VERSION_STRING\n",
                         original + '\n# define APP_VERSION_STRING "9.8.7"\n',
                         original.replace(line, '#define APP_VERSION_STRING "Unreleased"'),
                         re.sub(r"APP_VERSION_MAJOR \d+", "APP_VERSION_MAJOR 99", original)):
            with self.subTest(header=modified):
                self.write("src/core/version.h", modified)
                self.check(success=False)
        self.write("src/core/version.h", original)

    def test_obsolete_reader_is_rejected(self):
        name = ".github/workflows/release.yml"
        self.write(name, self.read(name) + "\n# Read INBE_VERSION_STRING\n")
        self.assertIn("INBE_VERSION_STRING", self.check(success=False).stderr)

    def test_ziran_version_missing_or_stale_is_rejected(self):
        name = "src/core/version.zi"
        original = self.read(name)
        self.write(name, original.replace(f'VersionString :: "{self.version}"',
                                          'VersionString :: "9.8.7"'))
        self.assertIn(name, self.check(success=False).stderr)
        (self.root / name).unlink()
        self.assertIn("missing", self.check(success=False).stderr)

    def test_missing_package_blocks_updater_before_any_write(self):
        (self.root / "windows/inbe.rc").unlink()
        before = self.snapshot()
        result = subprocess.run(["bash", str(self.root / "update_version.sh")],
                                capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_release_asset_reader(self):
        script = self.root / "scripts/list-expected-release-assets.sh"
        result = subprocess.run(["sh", str(script)], capture_output=True, text=True, check=True)
        self.assertIn(f"inbe-{self.version}.apk", result.stdout.splitlines())
        for invalid in ("", "Unreleased", "2.0", "2.0.0\n3.0.0", "02.0.0"):
            with self.subTest(version=invalid):
                result = subprocess.run(["sh", str(script), invalid], capture_output=True, check=False)
                self.assertNotEqual(result.returncode, 0)

    def test_updater_bumps_once_and_is_idempotent(self):
        initial_code = int(re.search(r"versionCode (\d+)", self.read("droid/app/build.gradle"))[1])
        name = "CHANGELOG.md"
        self.write(name, self.read(name).replace(f"## [{self.version}]", "## [9.8.7]", 1))
        self.check(success=False)
        script = self.root / "update_version.sh"
        subprocess.run(["bash", str(script)], capture_output=True, text=True, check=True)
        self.assertEqual(self.check("--print-version").stdout, "9.8.7\n")
        self.assertIn(f"versionCode {initial_code + 1}", self.read("droid/app/build.gradle"))
        before = self.snapshot()
        subprocess.run(["bash", str(script)], capture_output=True, text=True, check=True)
        self.assertEqual(before, self.snapshot())


if __name__ == "__main__":
    unittest.main()
