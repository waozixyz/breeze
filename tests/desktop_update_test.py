#!/usr/bin/env python3
"""Exercise release integrity and replacement of a running desktop binary."""

import hashlib
import importlib.util
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "desktop_update", Path(__file__).resolve().parents[1] / "scripts/update-desktop.py")
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class DesktopUpdateTest(unittest.TestCase):
    def test_corrupt_download_is_rejected(self):
        artifact = {"url": "https://github.com/waozixyz/breeze/releases/download/v1.2.3/inbe.deb",
                    "size": 4, "sha256": hashlib.sha256(b"good").hexdigest()}
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(updater, "open_url", return_value=io.BytesIO(b"evil")):
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    updater.download(artifact, Path(temporary) / "inbe.deb")

    def test_artifact_cannot_point_to_another_repository(self):
        manifest = {"version": "1.2.3", "channels": {"deb-amd64": {
            "url": "https://github.com/another/project/releases/download/v1.2.3/inbe_1.2.3_amd64.deb",
            "sha256": "a" * 64, "size": 10}}}
        with patch.object(updater.platform, "machine", return_value="x86_64"):
            with self.assertRaisesRegex(ValueError, "outside"):
                updater.artifact_for(manifest)

    def test_package_install_preserves_running_process_and_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prefix = root / "installed"
            executable = prefix / "bin/breeze"
            executable.parent.mkdir(parents=True)
            shutil.copy2(shutil.which("sleep"), executable)
            original_digest = updater.digest(executable)
            process = subprocess.Popen([str(executable), "60"])
            try:
                package_root = root / "package"
                control = package_root / "DEBIAN/control"
                control.parent.mkdir(parents=True)
                control.parent.chmod(0o755)
                control.write_text("Package: inbe\nVersion: 1.2.3\nArchitecture: all\n"
                                   "Maintainer: Waozi <waozi@proton.me>\nDescription: update fixture\n")
                for name in updater.FILES:
                    destination = package_root / "usr" / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_text("fixture")
                shutil.copy2(shutil.which("true"), package_root / "usr/bin/breeze")
                (package_root / "usr" / updater.FILES[-1]).write_text(
                    '<component><releases><release version="1.2.3"/></releases></component>')
                package = root / "inbe.deb"
                subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(package_root), str(package)],
                               check=True, stdout=subprocess.DEVNULL)
                backup = updater.install_package(package, prefix, root / "backup", "1.2.3")
                self.assertIsNone(process.poll())
                self.assertEqual(updater.digest(backup / "bin/breeze"), original_digest)
                subprocess.run([str(executable)], check=True, timeout=5)
                self.assertEqual(updater.installed_version(prefix), (1, 2, 3))
                with self.assertRaisesRegex(ValueError, "metadata"):
                    updater.install_package(package, prefix, root / "backup", "1.2.4")
                self.assertEqual(updater.installed_version(prefix), (1, 2, 3))
            finally:
                process.terminate()
                process.wait()

    def test_newer_installed_version_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            prefix = Path(temporary) / "prefix"
            metadata = prefix / updater.FILES[-1]
            metadata.parent.mkdir(parents=True)
            metadata.write_text('<component><releases><release version="9.0.0"/></releases></component>')
            manifest = b'{"version":"1.2.3","channels":{}}'
            with patch.object(updater, "open_url", return_value=io.BytesIO(manifest)):
                with patch.object(updater, "artifact_for", return_value={}):
                    with patch.object(updater, "download") as download:
                        updater.update(prefix, Path(temporary) / "backup")
                        download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
