"""SDK cache validation and corrupt-download recovery never skip required tools."""
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("android_sdk", ROOT / ".github/scripts/install-android-sdk.py")
sdk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdk)
PACKAGE = "cmake;3.22.1"


def component(root, version="3.22.1"):
    directory = root / "cmake/3.22.1"
    (directory / "bin").mkdir(parents=True)
    (directory / "source.properties").write_text("Pkg.Revision=" + version + "\n")
    (directory / "package.xml").write_text('<repository><localPackage path="' + PACKAGE + '"/></repository>')
    binary = directory / "bin/cmake"
    binary.write_text("#!/bin/sh\nprintf '%s\\n' 'cmake version " + version + "'\n")
    binary.chmod(0o755)


class AndroidSdkInstallTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="inbe-sdk-fixture-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manager = self.root / "sdkmanager"
        self.manager.write_text("#!/usr/bin/env python3\n" + '''
import json, os, pathlib, shutil, sys
root = pathlib.Path(__file__).parent
stage = pathlib.Path(next(x.split('=',1)[1] for x in sys.argv if x.startswith('--sdk_root=')))
state = root / 'attempts.json'
attempts = json.loads(state.read_text()) if state.exists() else []
assert all(not pathlib.Path(old).exists() for old in attempts), 'partial download reused'
attempts.append(str(stage)); state.write_text(json.dumps(attempts))
(stage / '.temp').mkdir(); (stage / '.temp/corrupt.zip').write_bytes(b'not a zip')
if len(attempts) == 1 or os.environ.get('SDK_FIXTURE_ALWAYS_FAIL'):
    print('Error on ZipFile unknown archive', file=sys.stderr); sys.exit(1)
shutil.copytree(root / 'download/cmake', stage / 'cmake')
''')
        self.manager.chmod(0o755)
        component(self.root / "download")

    def test_verified_cache_needs_no_network_or_download(self):
        component(self.root)
        sdk.install(self.root, [PACKAGE], self.manager, sleep=lambda _: None)
        self.assertFalse((self.root / "attempts.json").exists())

    def test_corrupt_archive_is_retried_in_a_new_stage(self):
        (self.root / "cmake/3.22.1").mkdir(parents=True)
        (self.root / "cmake/3.22.1/partial.zip").write_bytes(b"broken old cache")
        sdk.install(self.root, [PACKAGE], self.manager, sleep=lambda _: None)
        self.assertEqual(len(json.loads((self.root / "attempts.json").read_text())), 2)
        self.assertTrue(sdk.valid(self.root, PACKAGE))
        self.assertFalse((self.root / "cmake/3.22.1/partial.zip").exists())
        self.assertFalse(list(self.root.glob(".inbe-sdk-*")))

    def test_repeated_failure_stops_and_preserves_unrelated_components(self):
        other = self.root / "ndk/keep.txt"
        other.parent.mkdir()
        other.write_text("untouched")
        with mock.patch.dict(os.environ, SDK_FIXTURE_ALWAYS_FAIL="1"):
            with self.assertRaisesRegex(RuntimeError, "three fresh attempts"):
                sdk.install(self.root, [PACKAGE], self.manager, sleep=lambda _: None)
        self.assertEqual(other.read_text(), "untouched")
        self.assertEqual(len(json.loads((self.root / "attempts.json").read_text())), 3)
        self.assertFalse(list(self.root.glob(".inbe-sdk-*")))

    def test_wrong_version_and_unsafe_package_path_are_rejected(self):
        component(self.root, "3.21.0")
        self.assertFalse(sdk.valid(self.root, PACKAGE))
        for package in ("cmake;../outside", "ndk;/", "unknown;3.22.1"):
            with self.subTest(package=package), self.assertRaises(ValueError):
                sdk.component_path(self.root, package)

    def test_official_android_cmake_build_suffix_is_valid(self):
        component(self.root)
        binary = self.root / "cmake/3.22.1/bin/cmake"
        binary.write_text("#!/bin/sh\nprintf '%s\\n' 'cmake version 3.22.1-g37088a8'\n")
        self.assertTrue(sdk.valid(self.root, PACKAGE))

    def test_fdroid_explicit_sdk_works_without_sdk_environment_variables(self):
        component(self.root)
        packages = self.root / "packages.txt"
        packages.write_text(PACKAGE + "\n")
        environment = {key: value for key, value in os.environ.items()
                       if key not in ("ANDROID_HOME", "ANDROID_SDK_ROOT")}
        result = subprocess.run([sys.executable, str(ROOT / ".github/scripts/install-android-sdk.py"),
                                 "--sdk-root", str(self.root), "--sdkmanager", str(self.manager),
                                 "--packages", str(packages)], env=environment,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        workflow = (ROOT / ".github/workflows/fdroid.yml").read_text()
        self.assertIn('--sdk-root /opt/android-sdk --sdkmanager "$(command -v sdkmanager)"', workflow)

    def test_pinned_components_match_the_actual_android_build(self):
        gradle = (ROOT / "droid/app/build.gradle").read_text()
        makefile = (ROOT / "Makefile").read_text()
        expected = {"platforms;android-" + re.search(r"compileSdk (\d+)", gradle)[1],
                    "build-tools;" + re.search(r'buildToolsVersion "([0-9.]+)"', gradle)[1],
                    "ndk;" + re.search(r'ndkVersion "([0-9.]+)"', gradle)[1],
                    "cmake;" + re.search(r"ANDROID_CMAKE_DIR \?= .*?/cmake/([0-9.]+)", makefile)[1]}
        actual = set((ROOT / ".github/android-sdk-packages.txt").read_text().splitlines())
        self.assertEqual(actual, expected)

    def test_release_builds_start_early_but_publication_keeps_all_gates(self):
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        publication = workflow.split("\n  release:\n", 1)[1].split("\n    outputs:", 1)[0]
        self.assertIn("      - test", publication.splitlines())
        self.assertIn("      - verify-fdroid", publication.splitlines())
        self.assertIn("      - visual-test", publication.splitlines())
        self.assertIn("\n  visual-test:\n", workflow)
        android = workflow.split("\n  build-android:\n", 1)[1].split("\n  release:\n", 1)[0]
        self.assertIn("needs: secret-scan", android)
        self.assertLess(android.index("Verify and install Android SDK components"),
                        android.index("Fetch Ziran packages"))
        self.assertNotIn("ndk/25.1.8937393", android)


if __name__ == "__main__":
    unittest.main()
